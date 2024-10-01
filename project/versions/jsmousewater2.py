#____________REQUIRED_PACKAGES________________________________________________________________________________________________________
import RPi.GPIO as GPIO # Allows for control over the RP's GPIO pins
import time # Importing system time etc.
import tkinter as tk # UI
import PIL
from PIL import Image, ImageTk
import threading # Using threading to prevent the run program loop from preventing the main event loop from executing
import datetime #for adding timecodes to print statements

#____________GPIO_NUMBERING_SYSTEM_SETUP______________________________________________________________________________________________
# Setting up the GPIO numbering mode to use the RP's native BCM numbering system for the GPIO pins.
# This is needed because the GPIO pins on the RP are not numbered sequentially. In addition, only 26 of the 40 are actually usable for>
## The 14 others include the 5V, 3V inputs, and several grounds.
## 3 more pins (of the 26 remaining) are also taken up by the 16-relays hat (see below for details)

GPIO.setmode(GPIO.BOARD)

#____________DEFINING_KEY_VARIABLES___________________________________________________________________________________________________
selected_pins = []  # List to store selected GPIO pins
INTERVAL = 3600  # Default interval: 1 hour
STAGGER = 1  # Default stagger: 1 second (between pump signals)
WINDOW_START = 8  # Default window start time: 8 AM
WINDOW_END = 20  # Default window end time: 8 PM
running = False

#____________DEFINING_PINS_AVAILABLE_FOR_CONNECTION_TO_PUMPS__________________________________________________________________________
GPIO_PINS = [8, 10, 12, 16, 18, 22, 24, 32]

#NOTE TO SELF: ADD ALL AVAILABLE HERE IN COMMENT FOR FUTURE USE
### I also needed to skip over pins that aren't set up for GPIO, since I'm using GPIO.BOARD NOW (see written doc I made)

# The first GPIO pin listed will correspond to Pump 1 and so forth. I have created a legend listed below:
# PIN 8 -- Pump 1
# PIN 10 -- Pump 2
# PIN 12 -- Pump 3
# PIN 16 -- Pump 4
# PIN 18 -- Pump 5
# PIN 22 -- Pump 6
# PIN 24 -- Pump 7
# PIN 32 -- Pump 8

#NOTE2 --- WILL NEED TO MAKE NEW DICTIONARY FUNCTION FOR UI LATER (CHECK HOW MANY AVAILABLE GPIO PINS FOR MAX AMOUNT OF PUMPS FIRST)


#_____________WATERPUMP_CLASS_________________________________________________________________________________________________________
# Below I am creating the waterpump class to control the logic for each pump (i.e., for each GPIO PIN connected to a relay on the hat)
# "__init__" is called to initialize each water pump object with their respective GPIO pin ("pump_pin"). This will declare the pins as>
# The "trigger" method activates each pump by setting their corresponding GPIO pin to high.
## GPIO.HIGH allows current to flow through the pin, while GPIO.LOW does not.

class WaterPump:
    def __init__(self, gpio_pin):
        self.gpio_pin = gpio_pin
        GPIO.setup(self.gpio_pin, GPIO.OUT)
        GPIO.output(self.gpio_pin, GPIO.LOW)  # This makes sure the pin is initially off

    def trigger(self):
        GPIO.output(self.gpio_pin, GPIO.HIGH)  # Activates the GPIO pin to turn on the pump
        print (f"{datetime.datetime.now()} - Pump connected to GPIO Pin {self.gpio_pin} triggered")
        time.sleep(1)  # Arbitrary time delay, may need to adjust later as needed
        GPIO.output(self.gpio_pin, GPIO.LOW)  # Turns off the GPIO pin


# This makes different instances of WaterPump for each relay pin using the free GPIO pins I defined above
pumps = [WaterPump(pin) for pin in GPIO_PINS]


#___________VARIABLES_THAT_THE_USER_CAN_ALTER_________________________________________________________________________________________

def toggle_pin(pin):
    if pin in selected_pins:
        selected_pins.remove(pin)
        print (f"{datetime.datetime.now()} - GPIO Pin {pin} turned off")
    else:
        selected_pins.append(pin)
        print (f"{datetime.datetime.now()} - GPIO Pin {pin} turned on")

def update_interval():
    global INTERVAL
    try:
        INTERVAL = int(interval_entry.get())
        print (f"{datetime.datetime.now()} - Interval Updated")
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid interval value (integer)")

def update_stagger():
    global STAGGER
    try:
        STAGGER = int(stagger_entry.get())
        print (f"{datetime.datetime.now()} - Stagger Time Updated")
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid stagger value (integer)")

def update_window():
    global WINDOW_START, WINDOW_END
    WINDOW_START = int(window_start_entry.get())
    WINDOW_END = int(window_end_entry.get())
    print (f"{datetime.datetime.now()} - Watering Window Updated")

def run_program():
    global running
    running = True
    threading.Thread(target=program_loop).start()
    print (f"{datetime.datetime.now()} - Program Started")

def stop_program():
    global running
    running = False
    root.destroy()
    print (f"{datetime.datetime.now()} - Program Stopped")

#____________MEAT_AND_POTATOES________________________________________________________________________________________________________________
# Below is the main loop that runs indefinitely until the program is terminated using "KeyboardInterrupt" (CTRL+C) or by using the exit program button
# In the loop, the current system time is checked, and the pumps are triggered if the chosen interval of time has elapsed AND the current time is within the specified time window
## This calculation is done by taking the modulus of "current_time" and "interval".

# The loop repeats every second to see if its time to trigger the pumps again.

# JJC Note: don't have to check 1000 a second your checking on the clock of the raspberry Pi

def program_loop():
    global running
    try:
        while running:
            current_hour = time.localtime().tm_hour # This is to retrieve the current hour
            if WINDOW_START <= current_hour < WINDOW_END: # To ensure water is only provided during set hours (mices' night cycle etc.)
                current_time = time.time()
            if current_time % INTERVAL < 1: # Determining whether it's time to trigger the pumps
                for pump in pumps:
#JJC Note what about <= 1, is this a datetime object? cast to float?
                    if pump.gpio_pin in selected_pins:
                        pump.trigger()
                        time.sleep(STAGGER) # Staggers the pump triggers with user-decided value
                time.sleep(1) # Checks again every sec
    except KeyboardInterrupt: # This command defaults to CTRL+C, if the Exit Program button stops working
        print (f"{datetime.datetime.now()} - Exiting Program")
    finally:
           GPIO.cleanup() # Avoids a runtime error (see more details below)



# ______________USER__INTERFACE__STUFF________________________________________________________________________________________________>

# Generating the GUI
root = tk.Tk()
root.title("Water Pump Control")

# For Toggling the GPIO pins on/off in the UI, and making sure that a more intuitive labeling system is used (NOTE LATER CONVERT TEXT TO PUMP NUMBER!!)
toggle_frame = tk.Frame(root)
toggle_frame.pack()
for i, pin in enumerate(GPIO_PINS):
    tk.Checkbutton(toggle_frame, text=f"GPIO Pin {pin}", command=lambda p=pin: toggle_pin(p)).grid(row=i // 4, column=i % 4)

# UI for specifying the interval
interval_frame = tk.Frame(root)
interval_frame.pack()
tk.Label(interval_frame, text="Interval (seconds):").grid(row=0, column=0)
interval_entry = tk.Entry(interval_frame)
interval_entry.insert(0, INTERVAL)
interval_entry.grid(row=0, column=1)
tk.Button(interval_frame, text="Apply", command=update_interval).grid(row=0, column=2)

# UI for specifying the stagger time
stagger_frame = tk.Frame(root)
stagger_frame.pack()
tk.Label(stagger_frame, text="Stagger (seconds):").grid(row=0, column=0)
stagger_entry = tk.Entry(stagger_frame)
stagger_entry.insert(0, STAGGER)
stagger_entry.grid(row=0, column=1)
tk.Button(stagger_frame, text="Apply", command=update_stagger).grid(row=0, column=2)

# UI for the time window the pumps are able to activate within
window_frame = tk.Frame(root)
window_frame.pack()
tk.Label(window_frame, text="Watering Window Start (24-hour format):").grid(row=0, column=0)
window_start_entry = tk.Entry(window_frame)
window_start_entry.insert(0, WINDOW_START)
window_start_entry.grid(row=0, column=1)
tk.Label(window_frame, text="Watering Window End (24-hour format):").grid(row=1, column=0)
window_end_entry = tk.Entry(window_frame)
window_end_entry.insert(0, WINDOW_END)
window_end_entry.grid(row=1, column=1)
tk.Button(window_frame, text="Apply", command=update_window).grid(row=1, column=2)

# Warning label for closing the program
warning_message = "*Only close the program via the 'Stop Program' Button. Closing the window via the top right will cause errors. CTRL+C closes everything if needed"
warning_label = tk.Label(root, text=warning_message, fg="red")
warning_label.pack()

# Run Button UI
run_button = tk.Button(root, text="Run Program", command=run_program)
run_button.pack()

# Stop Button UI
stop_button = tk.Button(root, text="Stop Program", command=stop_program)
stop_button.pack()

# Defining image paths
image1 = Image.open("/home/conelab/lablogo.jpg")
image2 = Image.open("/home/conelab/rockmouse.jpg")

# Converting the pictures to be compatible with tkinter
tk_image1 = ImageTk.PhotoImage(image1)
tk_image2 = ImageTk.PhotoImage(image2)

# Resizing the beautiful rock image
image2 = image2.resize((200,200), Image.LANCZOS)

# Defining the labels needed to display the images
left_image_label = tk.Label(root, image=tk_image1)
left_image_label.pack(side=tk.LEFT)

right_image_label = tk.Label(root, image=tk_image2)
right_image_label.pack(side=tk.RIGHT)

#Placing the two pictures side by side underneath the stop button  (so that they don't appear off screen like before)
left_image_label.pack(side=tk.TOP)
right_image_label.pack(side=tk.BOTTOM)


#__________GPIO_CLEANUP_IF_PROGRAM_IS_CLOSED_INCORRECTLY______________________________________________________________________________>

try:
        root.mainloop()
finally:
        GPIO.cleanup() # once the root destroy command has been executed via clicking the stop program button, this clears the GPIO pins


### TO DO
# PUSHBUTTON INCORPORATION TO PREVENT SD CARD FAILURE (PLUS A UI ELEMENT INDICATING HOW THE USER NEEDS TO DO THIS
# EMAIL AUTOMATION FOR IF THE PROGRAM SUDDENLY STOPS
# LEARN HOW TO STACK THE CARDS IF NEEDED (FOR THE PAPER)
# FIX UI WINDOW SIZE AND SCROLLING ETC.
# GO THROUGH AND INCORPORATE ALL REMAINING JJC EDITS


# UPDATE FEB 29:
# Relays turn on/off the voltage you provide, they do not amplify. as such, I can go back to a version of the program that just triggers the GPIO pins. No need for relays pairs etc.
