#Version 3 = Trying with no GPIO pin activation, just the relays.

#____________REQUIRED_PACKAGES_____________________________________________________________________________________________________________________________________________________________________________________________________________
import RPi.GPIO as GPIO # Allows for control over the RP's GPIO pins
import time # Importing system time etc.
import tkinter as tk # UI
from tkinter import ttk
import PIL
from PIL import Image, ImageTk
import threading # Using threading to prevent the run program loop from preventing the main event loop from executing
import datetime #for adding timecodes to print statements
import smtplib #packages for sending emails etc.
import requests #emails
import json
import sm_16relind

rel = sm_16relind.SM16relind(0) # Initializing the relay hat
rel.set_all(0)  # Initialize all relays to be closed

#____________DEFINING_KEY_VARIABLES________________________________________________________________________________________________________________________________________________________________________________________________________
selected_relays = []  # List to store selected relay pins
INTERVAL = 3600  # Default interval: 1 hour
STAGGER = 1  # Default stagger: 1 second (between pump signals
WINDOW_START = 8  # Default window start time: 8 AM
WINDOW_END = 20  # Default window end time: 8 PM
num_triggers = {} #Dict. for num of triggers each relay pair needs (user specified)
num_columns = 8 # Arbitrary, change later as needed
running = False

# Function to add messages to the GUI-Integrated Terminal
def print_to_terminal(message):
    terminal_output.insert("end", message + "\n")
    terminal_output.see("end")


#____________GPIO_NUMBERING_SYSTEM_SETUP___________________________________________________________________________________________________________________________________________________________________________________________________
# Setting up the GPIO numbering mode to use the RP's native BCM numbering system for the GPIO pins.
# This is needed because the GPIO pins on the RP are not numbered sequentially. In addition, only 26 of the 40 are actually usable for input/output (The 14 others include the 5V, 3V inputs, and several grounds).
## 3 more pins (of the 26 remaining) are also taken up by the 16-relays hat (see below for details)
GPIO.setmode(GPIO.BOARD) #NOTE: I'm not sure if this is still needed now that I'm not using the GPIO pins. Experiment without this later

#____________EMAIL_FUNCTION_SETUP________________________________________________________________________________________________________________

def send_email(subject, content):
	api_key = "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"
	url = "https://api.brevo.com/v3/smtp/email"

	data = {
		"sender": {"name": "MouseMaster", "email": "rodentrefresher@gmail.com"},
		"to": [{"email": "conelab.uc@gmail.com"}],
		"subject": subject,
		"htmlContent": content
	}

	headers = {
		"accept": "application/json",
		"content-type": "application/json",
		"api-key": api_key
	}

	try:
		response = requests.post(url, headers=headers, data=json.dumps(data))
		response.raise_for_status()
		print (f"{datetime.datetime.now()} - Email sent successfully! Response: {response.text}")
		print_to_terminal(f"{datetime.datetime.now()} - Email sent successfully! Response: {response.text}")
	except requests.exceptions.RequestException as e:
		print (f"{datetime.datetime.now()} - Failed to send email: {e}")
		print_to_terminal(f"{datetime.datetime.now()} - Failed to send email: {e}")


#___________DEFINING_RELAY_PAIRS___________________________________________________________________________________________________________________________________________________________________________________________________________
# Since the COM terminals are responsible for 2 relays each, and because the voltage needs to be fed into these terminals, the relays must be triggered in pairs
RELAY_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]

#For use in the meat and potatoes later
RELAY_NAMES = {
	(1, 2): "Relays 1 & 2",
	(3, 4): "Relays 3 & 4",
	(5, 6): "Relays 5 & 6",
	(7, 8): "Relays 7 & 8",
	(9, 10): "Relays 9 & 10",
	(11, 12): "Relays 11 & 12",
	(13, 14): "Relays 13 & 14",
	(15, 16): "Relays 15 & 16",
}

#___________VARIABLES_THAT_THE_USER_CAN_ALTER______________________________________________________________________________________________________________________________________________________________________________________________
## These are all later integrated into the update_all_settings feature later on

def toggle_relay(relay_pair):
	global selected_relays
	if relay_pair in selected_relays:
		selected_relays.remove(relay_pair)
		print (f"{datetime.datetime.now()} - Relay pair {relay_pair} turned off")
		print_to_terminal(f"{datetime.datetime.now()} - Relay pair {relay_pair} turned off")
	else:
		selected_relays.append(relay_pair)
		print (f"{datetime.datetime.now()} - Relay pair {relay_pair} turned on")
		print_to_terminal(f"{datetime.datetime.now()} - Relay pair {relay_pair} turned on")

def update_interval():
	global INTERVAL, num_triggers
	try:
		INTERVAL = int(interval_entry.get())
		print (f"{datetime.datetime.now()} - Interval Updated")
		print_to_terminal(f"{datetime.datetime.now()} - Interval Updated")
		num_triggers = update_num_triggers() # so that the number of triggers is also updated
		print ("Number of triggers for each relay pair:", num_triggers)
		print_to_terminal("Number of triggers for each relay pair:", num_triggers)
	except ValueError:
		messagebox.showerror("Error", "Please enter a valid interval value (integer)")

def update_num_triggers():
	global trigger_entries, num_triggers
	num_triggers.clear() # clear any lingering prev. values
	for relay_pair, entry in trigger_entries.items():
		try:
			count = int(entry.get())
			num_triggers[relay_pair] = count
		except ValueError:
			messagebox.showerror("Error", f"Invalid trigger count for relay pair {relay_pair}")
			return None
	print ("Number of triggers for each relay pair:", num_triggers)
	print_to_terminal("Number of triggers for each relay pair:", num_triggers)
	return num_triggers

def update_stagger():
	global STAGGER
	try:
		STAGGER = int(stagger_entry.get())
		print (f"{datetime.datetime.now()} - Stagger Time Updated")
		print_to_terminal(f"{datetime.datetime.now()} - Stagger Time Updated")
	except ValueError:
		messagebox.showerror("Error", "Please enter a valid stagger value (integer)")

def update_window():
	global WINDOW_START, WINDOW_END
	WINDOW_START = int(window_start_entry.get())
	WINDOW_END = int(window_end_entry.get())
	print_to_terminal(f"{datetime.datetime.now()} - Watering Window Updated")
	print (f"{datetime.datetime.now()} - Watering Window Updated")

def run_program():
	global running
	running = True
	threading.Thread(target=program_loop).start()
	print (f"{datetime.datetime.now()} - Program Started")
	print_to_terminal(f"{datetime.datetime.now()} - Program Started")

def stop_program():
	global running
	running = False
	print_to_terminal(f"{datetime.datetime.now()} - Program Stopped")
	rel.set_all(0)  # This closes all relays when stopping program
	root.destroy()
	print (f"{datetime.datetime.now()} - Program Stopped")

def create_trigger_entries():
	global trigger_entries, toggle_frame
	trigger_entries = {}
	# Assuming num_columns is already defined globally with a value of 4, as per your code
	# Adjust the grid row and column assignments according to num_columns
	for i, relay_pair in enumerate(RELAY_PAIRS):
		# Calculate grid position
		row = i // num_columns * 2
		column = i % num_columns # * 2 # Multiplying by 2 to leave space for the 'Triggers:' label and entry box
		# Checkbutton for each relay pair
		checkbutton = tk.Checkbutton(toggle_frame, text=f"Relays {relay_pair[0]} & {relay_pair[1]}",
		command=lambda rp=relay_pair: toggle_relay(rp))
		checkbutton.grid(row=row, column=column, padx=10, pady=(10,0), sticky="w")

		# Label for the 'Triggers:' text, placed underneath the Checkbutton
		label = tk.Label(toggle_frame, text="Triggers:")
		label.grid(row=row + 1, column=column, padx=10, pady=(0,10), sticky="w")

		# Entry box for the trigger count, placed next to the 'Triggers:' label
		entry = tk.Entry(toggle_frame, width=5)
		entry.insert(0, "1")  # Default to 1 trigger
		# adds padding and align to the left for proper UI fitting. padx is responsible for adding horizontal space between the label and entry field. May need to be adjusted as needed
		entry.grid(row=row + 1, column=column, padx=10, pady=(0,10), sticky="e")  # Using 'e' for east alignment
		trigger_entries[relay_pair] = entry

def update_trigger_counts(): #for user feedback
	trigger_counts = get_trigger_counts()
	if trigger_counts is not None:
		print ("Trigger count updated successfully:", trigger_counts)
		print_to_terminal("Trigger count updated successfully:", trigger_counts)


def get_trigger_counts():
	trigger_counts = {}
	for relay_pair, entry in trigger_entries.items():
		try:
			count = int(entry.get())
			trigger_counts[relay_pair] = count
		except ValueError:
			messagebox.showerror("Error", f"Invalid trigger count for relay pair {relay_pair}")
			return None
	return trigger_counts


#Creating a master function for updating all entered settings
def update_all_settings():
        global INTERVAL, STAGGER, WINDOW_START, WINDOW_END, num_triggers, selected_relays
        try:
                INTERVAL = int(interval_entry.get())
                STAGGER = int(stagger_entry.get())
                WINDOW_START = int(window_start_entry.get())
                WINDOW_END = int(window_end_entry.get())
                temp_num_triggers = {}
                for relay_pair, entry in trigger_entries.items():
                        count = int(entry.get())
                        temp_num_triggers[relay_pair] = count
                num_triggers = temp_num_triggers  # Update the global variable after validation

                if selected_relays: # Check if any relay pairs are selected, otherwise print "none"
                        enabled_relay_pairs = ', '.join(f"({rp[0]} & {rp[1]})" for rp in selected_relays)
                        triggers = ', '.join(f"R{rp[0]} & R{rp[1]} = {num_triggers.get(rp, 1)} Triggers" for rp in selected_relays)
                else:
                        enabled_relay_pairs = "none"
                        triggers = "none"
		#For future jamie: "/n" starts a new line when printing something
                settings_output = (
                        f"{datetime.datetime.now()} - Settings have been updated to the following:\n"
                        f"* Relay pairs enabled: {enabled_relay_pairs}\n"
                        f"* Set Triggers for each enabled relay pair: {triggers}\n"
                        f"* Current interval between trigger sessions: {INTERVAL} seconds\n"
                        f"* Current Stagger time between successive triggers: {STAGGER} seconds\n"
                        f"* Current Water window (24-hour time): {WINDOW_START:02d}:00 - {WINDOW_END:02d}:00"
                )

                print (settings_output)
                print_to_terminal(settings_output)
        except ValueError as e:
                messagebox.showerror("Error", "Please enter valid numeric values for all settings.")


#____________MEAT_AND_POTATOES_____________________________________________________________________________________________________________________________________________________________________________________________________________
# Below is the main loop that runs indefinitely until the program is terminated using "KeyboardInterrupt" or by using the exit program button
# In the loop, the current system time is checked, and the pumps are triggered if the current time matches the specified time interval. This is done by taking the modulus of "current_time" and "interval".
# The loop repeats every second to see if its time to trigger the pumps again.

# How the time delays work:
## Each relay pair is triggered the number of times specified by the user, according to the interval.
## After each trigger of the same relay pair, the STAGGER time passes before the next.
## Once all triggers for the relay pair are completed, there is an arbitrary delay of 1 second before moving onto the next enabled relay pair and repeating the process.

# JJC Note: don't have to check 1000 a second your checking on the clock of the raspberry Pi
#JJC Note what about <= 1, is this a datetime object? cast to float? Indent to be inside the previous

def program_loop():
	global running, num_triggers, selected_relays
	try:
		while running:
			current_hour = time.localtime().tm_hour # This is to retrieve the current hour
			if WINDOW_START <= current_hour < WINDOW_END: # To ensure water is only provided during set hours (mices' night cycle)
				current_time = time.time()
				if current_time % INTERVAL < 1:  # Determining whether it's time to trigger the pumps (based on the interval)
					relay_info = []  # To gather information for the email
					for relay_pair in RELAY_PAIRS:  # Go through all relay pairs, not just the selected ones
						if relay_pair in selected_relays:  # Now only sned a trigger if the relay pair is selected (should fix the tickbox problem)
							triggers = num_triggers.get(relay_pair, 1)  # Get the trigger count, default to 1
							for _ in range(triggers):  # Trigger each selected relay pair the specified number of times
								relay1, relay2 = relay_pair
								rel.set(relay1, 1)  # Turns on the first relay in the pair
								rel.set(relay2, 1)  # Turns on the second relay in the pair
								print (f"{datetime.datetime.now()} - Pumps connected to {RELAY_NAMES[relay_pair]} triggered")
								print_to_terminal(f"{datetime.datetime.now()} - Pumps connected to {RELAY_NAMES[relay_pair]} triggered")
								time.sleep(STAGGER)
								rel.set(relay1, 0)  # Turns off the first relay in the pair
								rel.set(relay2, 0)  # Turns off the second relay in the pair
								time.sleep(STAGGER)  # Wait for stagger time after completing all triggers for a pair


							relay_info.append(f"{RELAY_NAMES[relay_pair]} triggered {triggers} times") # Adds the relay trigger info for the email

					# Email details
					subject = "Pump Trigger Notification"
					content = (f"The pumps have been successfully triggered as follows:\n"
						f"{'; '.join(relay_info)}\n"
						f"** Next trigger due in {INTERVAL} seconds.\n\n"
						f"Current settings:\n"
						f"- Interval: {INTERVAL} seconds\n"
						f"- Stagger: {STAGGER} seconds\n"
						f"- Water window: {WINDOW_START:02d}:00 - {WINDOW_END:02d}:00\n"
						f"- Relays enabled: {', '.join(f'({rp[0]} & {rp[1]})' for rp in selected_relays) if selected_relays else 'None'}")

					send_email(subject, content) #Now send the email
					time.sleep(INTERVAL - 1)  # Adjusting for the time already spent triggering relays


	except KeyboardInterrupt: #This command defaults to CTRL+C, needed if the program freezes etc.
		print (f"{datetime.datetime.now()} - Exiting Program")
		print_to_terminal(f"{datetime.datetime.now()} - Exiting Program")

	finally:
		rel.set_all(0) # Turns off all relays when the program exits


# ______________USER__INTERFACE__STUFF_____________________________________________________________________________________________________________________________________________________________________________________________________

# Generating the GUI
root = tk.Tk()
root.title("Rodent Refreshment Regulator")

# For creating tabs to navigate between in the GUI
notebook = ttk.Notebook(root)
tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)

notebook.add(tab1, text='Setup Wizard')
notebook.add(tab2, text='Control Panel')
notebook.pack(expand=True, fill="both")

# GUI-Integrated Terminal(Output only - shared by both tabs)
terminal_output = tk.Text(root, height=10)
terminal_output.pack(side="bottom", fill="x")
terminal_output.insert("end", "System Messages will appear here.\n")

# Terminal Welcome message
print_to_terminal("Welcome to the Rodent Refreshment Regulator!")

# Main frame for toggle buttons
toggle_frame = tk.Frame(root)
toggle_frame.pack(padx=10, pady=10)

# Create trigger entries UI
create_trigger_entries()

# Frame for interval and stagger
settings_frame = tk.Frame(root)
settings_frame.pack(fill='x', expand=True)

# Establishing the lower bounds for the window size (to make sure nothing gets cut off)
## This will need to be experimented with as things in the UI change through development etc.)
MIN_WIDTH = 1500
MIN_HEIGHT = 1000

def enforce_min_size(event): # Event handler for window resizing
	if root.winfo_width() < MIN_WIDTH:
		root.geometry(f"{MIN_WIDTH}x{root.winfo_height()}")
	if root.winfo_height() < MIN_HEIGHT:
		root.geometry(f"{root.winfo_width()}x{MIN_HEIGHT}")
root.bind("<Configure>", enforce_min_size) # This binds the event handler to te window resize event

# UI for specifying the interval
interval_frame = tk.Frame(root)
interval_frame.pack()
tk.Label(interval_frame, text="Interval (seconds):").grid(row=0, column=0, sticky="w")  # Alignsthe label to the left
interval_entry = tk.Entry(interval_frame)
interval_entry.insert(0, INTERVAL)
interval_entry.grid(row=0, column=1, sticky="w")  # Aligns the entry to the left

# Stagger UI
stagger_frame = tk.Frame(root)
stagger_frame.pack()
tk.Label(stagger_frame, text="Stagger (seconds):").grid(row=0, column=0, sticky="w")  # Aligns left
stagger_entry = tk.Entry(stagger_frame)
stagger_entry.insert(0, STAGGER)
stagger_entry.grid(row=0, column=1, sticky="w")

# Window Entry UI
window_frame = tk.Frame(root)
window_frame.pack()
tk.Label(window_frame, text="Water Window Start (24-hour format):").grid(row=0, column=0, sticky="w")
window_start_entry = tk.Entry(window_frame)
window_start_entry.insert(0, WINDOW_START)
window_start_entry.grid(row=0, column=1, sticky="w")
tk.Label(window_frame, text="Water Window End (24-hour format):").grid(row=1, column=0, sticky="w")
window_end_entry = tk.Entry(window_frame)
window_end_entry.insert(0, WINDOW_END)
window_end_entry.grid(row=1, column=1, sticky="w")

# Master Update Button
update_settings_button = tk.Button(root, text="Update Settings", command=update_all_settings)
update_settings_button.pack(pady=10)

# Frame for the bottom part of the GUI (warning message, run/stop buttons, and images)
bottom_frame = tk.Frame(root)
bottom_frame.pack(fill='x', expand=True)

# Warning labels
warning_message = "Closing this window will stop the program. Please leave this window open for it to continue running."
warning_label=tk.Label(root, text=warning_message, fg="red")
warning_label.pack(padx=0, pady=(0, 10), anchor="w")

warning_message2 = "An email will be sent to (conelab.uc@gmail.com) upon each successful pump trigger. CTRL+C force closes the program if needed."
warning_label2=tk.Label(root, text=warning_message2, fg = "red")
warning_label2.pack(padx=0, pady=(0,12), anchor="w")

# Run button
run_button = tk.Button(root, text="Run Program", command=run_program)
run_button.pack()

# Stop button
stop_button = tk.Button(root, text="Stop Program", command=stop_program)
stop_button.pack()

# Defining the image paths
image1_path = "/home/conelab/lablogo.jpg"
image2_path = "/home/conelab/rockmouse.jpg"

# Load and convert the images immediately to PhotoImage objects (for tkinter compatibility)
image1 = Image.open(image1_path)
tk_image1 = ImageTk.PhotoImage(image1)
image2 = Image.open(image2_path)
tk_image2 = ImageTk.PhotoImage(image2.resize((200,200), Image.LANCZOS)) # Resizing the beautiful rock image

root.tk_image1 = ImageTk.PhotoImage(Image.open(image1_path))
root.tk_image2 = ImageTk.PhotoImage(Image.open(image2_path)) # Resizing the beautiful rock image

# Creating labels for the images
left_image_label = tk.Label(root, image=tk_image1)
right_image_label = tk.Label(root, image=tk_image2)

# Making the images more visible (packing the labels)
left_image_label.pack(side=tk.LEFT)
right_image_label.pack(side=tk.RIGHT)# Making the images more visible (packing the labels)


#Placing the two pictures side by side underneath the stop button  (so that they don't appear off screen like before)
left_image_label.pack(side=tk.TOP)
right_image_label.pack(side=tk.BOTTOM)

root.mainloop() # Allows the tkinter event loop to run indefinitely (i.e., so the GUI can update etc.)

# So that the program stops when exiting the gui, instead of running in the background
def on_close():
        stop_program()
root.protocol("WM_DELETE_WINDOW", on_close)




## ADD A LEGEND FOR WHAT EACH UI ELEMENT MEANS (IE 1 TRIGGER = 10 MICROLITRES OF WATER ETC.)

### TO DO
#Grounding!
# PUSHBUTTON INCORPORATION TO PREVENT SD CARD FAILURE (PLUS A UI ELEMENT INDICATING HOW THE USER NEEDS TO DO THIS
# EMAIL AUTOMATION FOR IF THE PROGRAM SUDDENLY STOPS
# LEARN HOW TO STACK THE CARDS IF NEEDED (FOR THE PAPER)
# FIX UI WINDOW SIZE AND SCROLLING ETC.
# GO THROUGH AND INCORPORATE ALL REMAINING JJC EDITS


# Notes for later writing out the process to set this up
## sequentsystems github initialization packages
## Enable 12C in raspberry pi config
## download all packages
## Learn how to properly stack new hats (up to 8), and how to adapt the code to do so (or make it adaptable to any number of hats)
	## Good writeup on sequentsystems to help with this
