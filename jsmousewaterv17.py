#RODENT REFRESHMENT REGULATOR VERSION 16 - Stackable Version
#Last updated 28/06/2024 by JSANSON

# Still have some slight bolding issues in the subheaders, but moving to fixing other things for now
# re-arranging buttons etc. Need to search code for redundancy etc. Also trying to move trigger fields below. Also add stagger def

#ISSUE: IMMENSE LAG

#   _    _  _____  _      _____  _____ ___  ___ _____    _____  _____    _____  _   _  _____   ______ ______ ______
#  | |  | ||  ___|| |    /  __ \|  _  ||  \/  ||  ___|  |_   _||  _  |  |_   _|| | | ||  ___|  | ___ \| ___ \| ___ |
#  | |  | || |__  | |    | /  \/| | | || .  . || |__      | |  | | | |    | |  | |_| || |__    | |_/ /| |_/ /| |_/ /
#  | |/\| ||  __| | |    | |    | | | || |\/| ||  __|     | |  | | | |    | |  |  _  ||  __|   |    / |    / |    /
#  \  /\  /| |___ | |____| \__/ | \_/ /| |  | || |___     | |  \ \_/ /    | |  | | | || |___   | |\ \ | |\ \ | |\ |
#   \/  \/ \____/ \_____/ \____/ \___/ \_|  |_/\____/     \_/   \___/     \_/  \_| |_/\____/   \_| \_|\_| \_|\_| \_|

#______________________________________________________________________________________________________________________________________________________________________________________________
#____________REQUIRED_PACKAGES_&_DEFINING_SOME_VARIABLES_______________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________


import RPi.GPIO as GPIO  # Allows for control over the RPi's GPIO pins
import time  # Importing system time etc.
import tkinter as tk  # UI
from tkinter import ttk, messagebox, Canvas, Frame, Scrollbar
import tkinter.simpledialog as simpledialog  # For no. of hats popup
import PIL
from PIL import Image, ImageTk
import threading  # Using threading to prevent the run program loop from preventing the main event loop from executing
import datetime  # for adding timecodes to print statements
import re  # regular expressions module, allows for string searching and manipulation
import smtplib  # packages for sending emails etc.
import requests  # emails
import json
import math  # used when rounding up the number of triggers needed for each relay pair
import sm_16relind
import sys

GPIO.setmode(GPIO.BOARD)  # Setting up the GPIO numbering mode to use the RP's native BCM numbering system for the GPIO pins (might not be needed anymore)

selected_relays = []  # List to store selected relay pins
INTERVAL = 3600  # Default interval: 1 hour
STAGGER = 1  # Default stagger: 1 second (between pump signals)
WINDOW_START = 8  # Default window start time: 8 AM
WINDOW_END = 20  # Default window end time: 8 PM
num_triggers = {}  # Dict. for num of triggers each relay pair needs (user specified)
num_columns = 8  # for placing stuff in the GUI (may be redundant now)
running = False

#Defining the GUI right away for functionality purposes (other GUI stuff located at the bottom of the code)
root = tk.Tk()
terminal_frame = tk.Frame(root)
terminal_output = tk.Text(terminal_frame, height=14)


#____________EMAIL_FUNCTION_SETUP______________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
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
        print(f"{datetime.datetime.now()} - Email sent successfully! Response: {response.text}")
        print_to_terminal(f"{datetime.datetime.now()} - Email sent successfully! Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"{datetime.datetime.now()} - Failed to send email: {e}")
        print_to_terminal(f"{datetime.datetime.now()} - Failed to send email: {e}")

#___________SCALEABILITY_BASED_ON_NUMBER_OF_HATS_______________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
def print_to_terminal(message): # To add messages to the GUI-Integrated Terminal (needs to be at top of function list)
    terminal_output.insert("end", message + "\n")
    terminal_output.see("end")

def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs.append((start_relay + i, start_relay + i + 1))
    return relay_pairs

def ask_number_of_hats():
    return simpledialog.askinteger("Input", "Enter the number of relay hats installed:", minvalue=1, maxvalue=8)

def initialize_relay_hats(num_hats):
    relay_list = []
    failed_hats = []
    for i in range(num_hats):
        try:
            relay = sm_16relind.SM16relind(stack=i)
            relay_list.append(relay)
        except Exception as e:
            print (f"Failed to initialize hat(s) no.{i + 1}: {e}")
            print_to_terminal(f"Failed to initialize hat(s) no.{i + 1}: {e}")
            relay_list.append(None)
            failed_hats.append(i + 1)
    if failed_hats:
        messagebox.showwarning("Initialization Warning", f"Failed to Initialize Hat(s): {', '.join(map(str, failed_hats))}")
    return relay_list

num_hats = simpledialog.askinteger("Relay Hats", "Enter the number of relay hats installed (1-8):", minvalue=1, maxvalue=8)
relays = initialize_relay_hats(num_hats)


RELAY_PAIRS = create_relay_pairs(num_hats)
RELAY_NAMES = {pair: f"Relays {pair[0]} & {pair[1]}" for pair in RELAY_PAIRS}

def set_relay(hat_index, relay, state):
    try:
        relays[hat_index].set(relay, state)
    except IndexError:
        print (f"{datetime.datetime.now()} - Error: Hat {hat_index + 1} is not initialized")

def set_all_relays(hat_index, state):
    try:
        relays[hat_index].set_all(state)
    except IndexError:
        print (f"{datetime.datetime.now()} - Error: Hat {hat_index + 1} is not initialized")

#____________MAIN_FUNCTION_LIST________________________________________________________________________________________________________________________________________________________________
#__________________________________________________________________________________________________________________________________________________________________________________________
def toggle_relay(relay_pair, var):  # relay pair tickbox functionality 
    global selected_relays
    if var.get():
        if relay_pair not in selected_relays:
            selected_relays.append(relay_pair)
        print(f"{datetime.datetime.now()} - Relay pair {relay_pair} enabled")
    else:
        if relay_pair in selected_relays:
            selected_relays.remove(relay_pair)
        print(f"{datetime.datetime.now()} - Relay pair {relay_pair} disabled")

def update_interval():
    global INTERVAL, num_triggers
    try:
        INTERVAL = int(interval_entry.get())
        print(f"{datetime.datetime.now()} - Interval Updated")
        print_to_terminal(f"{datetime.datetime.now()} - Interval Updated")
        num_triggers = update_num_triggers()  # so that the number of triggers is also updated
        print("Number of triggers for each relay pair:", num_triggers)
        print_to_terminal("Number of triggers for each relay pair:", num_triggers)
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid interval value (integer)")

def update_num_triggers():
    global trigger_entries, num_triggers
    num_triggers.clear()  # clear any lingering prev. values
    for relay_pair, entry in trigger_entries.items():
        try:
            count = int(entry.get())
            num_triggers[relay_pair] = count
        except ValueError:
            messagebox.showerror("Error", f"Invalid trigger count for relay pair {relay_pair}")
            return None
    print("Number of triggers for each relay pair:", num_triggers)
    print_to_terminal("Number of triggers for each relay pair:", num_triggers)
    return num_triggers

def update_stagger():
    global STAGGER
    try:
        STAGGER = int(stagger_entry.get())
        print(f"{datetime.datetime.now()} - Stagger Time Updated")
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
    print(f"{datetime.datetime.now()} - Program Started")
    print_to_terminal(f"{datetime.datetime.now()} - Program Started")

def stop_program():
    global running
    running = False
    print_to_terminal(f"{datetime.datetime.now()} - Program Stopped")
    for relay in relays:
        if relay is not None:
            relay.set_all(0) # This closes all relays when stopping program
    root.destroy()
    print (f"{datetime.datetime.now()} - Program Stopped")

# Creating a master function for updating all entered settings (in the advanced settings drop-down menu)
def update_all_settings():
    global INTERVAL, STAGGER, WINDOW_START, WINDOW_END, num_triggers, selected_relays
    try:
        INTERVAL = int(interval_entry.get())
        STAGGER = int(stagger_entry.get())
        WINDOW_START = int(window_start_entry.get())
        WINDOW_END = int(window_end_entry.get())

        # Updating selected relays and trigger counts from GUI
        selected_relays = [rp for rp, (chk, var) in relay_checkboxes.items() if var.get()]
        num_triggers = {rp: int(trigger_entries[rp].get()) for rp in relay_checkboxes if trigger_entries[rp].get().isdigit()}

        # Preparing output for terminal (+ return none if none are selected)
        if selected_relays:
            enabled_relay_pairs = ', '.join(f"({rp[0]} & {rp[1]})" for rp in selected_relays)
            triggers = ', '.join(f"R{rp[0]} & R{rp[1]} = {num_triggers.get(rp, 1)} Triggers" for rp in selected_relays)
        else:
            enabled_relay_pairs = "none"
            triggers = "none"

        settings_output = (
            f"{datetime.datetime.now()} - Settings have been updated to the following:\n"
            f"* Relay pairs enabled: {enabled_relay_pairs}\n"
            f"* Set Triggers for each enabled relay pair: {triggers}\n"
            f"* Current interval between trigger sessions: {INTERVAL} seconds\n"
            f"* Current Stagger time between successive triggers: {STAGGER} seconds\n"
            f"* Current Water window (24-hour time): {WINDOW_START:02d}:00 - {WINDOW_END:02d}:00\n"
        )

        print_to_terminal(settings_output)
        print(settings_output)
    except ValueError as e:
        print_to_terminal(f"Error in input values: {e}")
        messagebox.showerror("Input Error", "Please check your input values.")

#______________________________________________________________________________________________________________________________________________________________________________________________
#____________MEAT_AND_POTATOES_________________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
# Below is the main loop that runs indefinitely until the program is terminated using "KeyboardInterrupt", by using the exit program button, or by closing the window
# In the loop, the current system time is checked & the pumps are triggered if the current time matches the time interval. This is done by taking the modulus of "current_time" and "interval".
# The loop repeats every second to see if its time to trigger the pumps again.

# How the time delays work:
## Each relay pair is triggered the number of times specified by the user, according to the interval.
## After each trigger of the same relay pair, the STAGGER time passes before the next.
## Once all triggers for the relay pair are completed, there is an arbitrary delay of 1 second before moving onto the next enabled relay pair and repeating the process.


def program_loop():
	global running, num_triggers, selected_relays
	try:
		while running:
			current_hour = time.localtime().tm_hour
			if (WINDOW_START <= current_hour or current_hour < WINDOW_END) if WINDOW_START > WINDOW_END else (WINDOW_START <= current_hour < WINDOW_END):
				current_time = time.time()
				if current_time % INTERVAL < 1:
					relay_info = []
					for relay_pair in RELAY_PAIRS:
						if relay_pair in selected_relays:
							hat_index = (relay_pair[0] - 1) // 16
							relay_index = (relay_pair[0] - 1) % 16 + 1
							triggers = num_triggers.get(relay_pair, 1)
							for _ in range(triggers):
								set_relay(hat_index, relay_index, 1)
								set_relay(hat_index, relay_index + 1, 1)
								print (f"{datetime.datetime.now()} - Pumps connected to {RELAY_NAMES[relay_pair]} triggered")
								print_to_terminal(f"{datetime.datetime.now()} - Pumps connected to {RELAY_NAMES[relay_pair]} triggered")
								time.sleep(STAGGER)
								set_relay(hat_index, relay_index, 0)
								set_relay(hat_index, relay_index + 1, 0)
								time.sleep(STAGGER)

							relay_info.append(f"{RELAY_NAMES[relay_pair]} triggered {triggers} times")
					subject = "Pump Trigger Notification"
					content = (f"The pumps have been successfully triggered as follows:\n"
						f"{'; '.join(relay_info)}\n"
						f"** Next trigger due in {INTERVAL} seconds.\n\n"
						f"Current settings:\n"
						f"- Interval: {INTERVAL} seconds\n"
						f"- Stagger: {STAGGER} seconds\n"
						f"- Water window: {WINDOW_START:02d}:00 - {WINDOW_END:02d}:00\n"
						f"- Relays enabled: {', '.join(f'({rp[0]} & {rp[1]})' for rp in selected_relays) if selected_relays else 'None'}")
					send_email(subject, content)
					time.sleep(INTERVAL - 1)
	except KeyboardInterrupt:
		print (f"{datetime.datetime.now()} - Exiting Program")
		print_to_terminal(f"{datetime.datetime.now()} - Exiting Program")
	finally:
		for relay in relays:
			if relay is not None:
				relay.set_all(0)



#________MAKING_THE_GUI________________________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
# Generating the GUI
root.title("Rodent Refreshment Regulator")

# Establishing the lower bounds for the window size (to make sure nothing gets cut off)
## This will need to be experimented with as things in the UI change through development etc.)
MIN_WIDTH = 1800
MIN_HEIGHT = 1000

def enforce_min_size(event):  # Event handler for window resizing
    if root.winfo_width() < MIN_WIDTH:
        root.geometry(f"{MIN_WIDTH}x{root.winfo_height()}")
    if root.winfo_height() < MIN_HEIGHT:
        root.geometry(f"{root.winfo_width()}x{MIN_HEIGHT}")

root.bind("<Configure>", enforce_min_size)  # This binds the event handler to te window resize event

#_______TERMINAL_&_TERMINAL_SCROLLBAR__________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

# Frame for the GUI Terminal + scrollbar
## This is needed so that the terminal's scrollbar matches the vertical height of the terminal
terminal_frame.pack(side="bottom", fill="x")

# GUI-Integrated Terminal(Output only)
## I want this to always be at the bottom of the GUI, so assigning to root.
terminal_output.pack(side="bottom", fill="x")
terminal_output.insert("end", "System Messages will appear here.\n")

# Second Scrollbar for the GUI Terminal
terminal_scrollbar = tk.Scrollbar(terminal_frame, command=terminal_output.yview)
terminal_scrollbar.pack(side='right', fill='y', before=terminal_output)  # pack next to the terminal
terminal_output.config(yscrollcommand=terminal_scrollbar.set)  # Configures the scrollbar to work for the terminal

# Terminal Welcome message
print_to_terminal("Welcome to the Rodent Refreshment Regulator!")

#_______MAIN_SCROLLBAR_&_SCROLLABLE_CONTENT_STUFF______________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

# Creating a Canvas to make everyhing scrollable
canvas = tk.Canvas(root)
canvas.pack(side="left", fill="both", expand=True)

# Creating the scrollbar and linking it to the canvas
# DISABLED RIGHT NOW BECAUSE NOT NEEDED. MAY NEED LATER WHEN WORKING ON SCALABILITY!!!
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side='right', fill='y')
canvas.configure(yscrollcommand=scrollbar.set)  # Configures the canvas to use the scrollbar

# horizontal scrollbar for lower resolution
scrollbar2 = tk.Scrollbar(root, orient="horizontal", command=canvas.xview)
scrollbar.pack(side='right', fill='y')
canvas.configure(xscrollcommand=scrollbar2.set)

# Placing the scrollable frame within the canvas
scrollable_frame = tk.Frame(canvas)
canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# This lambda ensures the scroll region adjusts dynamically to the size of scrollable_frame (i.e, with menus opening/closing)
scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

# Creating two sub-frames within the scrollable frame (for placing widgets on either the L/R of the gui
left_content_frame = tk.Frame(scrollable_frame)
left_content_frame.pack(side='left', fill='both', expand=True)

right_content_frame = tk.Frame(scrollable_frame)
right_content_frame.pack(side='right', fill='both')

#_______GUI_WELCOME_MESSAGE_&_SUBHEADERS_______________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

welcome_label = tk.Label(left_content_frame, text="Welcome to the Rodent Refreshment Regulator Wizard", font=("Arial", 24, "bold"))
welcome_label.pack(fill='x', padx=20, pady=(5, 3))

subheaders_text = """
Step 1: Answer the questions on the right side of the screen to suit your needs.
Step 2: Press the 'Suggest Settings' button to receive setting recommendations in the terminal below.
Step 3: Press the 'Push Settings' button to submit and save these setting reccomendations.
Step 4: (OPTIONAL) Adjust settings manually in the 'Advanced Settings' menu below if desired.\n               * Remember to save these changes using the 'Update Settings' button at the bottom of the Advanced Settings menu.
Step 5: See the notes section below for additional information, and run the program when ready.

Notes:
 * Questions pertaining to water volume are for EACH relay.
 * Water volume suggestions will always round UP based on the volume increments that your pumps are capable of outputting per trigger.\n      * The amount of water released defaults to 10uL/trigger.
 * Closing this window will stop the program. Please leave this window open for it to continue running.
 * An email can optionally be sent to you upon each successful pump trigger. See the ReadMe for setup instructions if desired.
 * CTRL+C is set to force close the program if required.
 * "Stagger" is the time that elapses between triggers of the same relay pair (if applicable). Changing this value is not recommended.\n      * This parameter is set based on the maximum electrical output of a Raspberry Pi-4. Only change if your hardware needs differ.
"""

def add_styled_text_single(left_content_frame, text):
    # Create a text widget with a vertical scrollbar
    text_frame = tk.Frame(left_content_frame)
    text_frame.pack(fill='x', padx=(25, 25), pady=(1, 1))

    text_widget = tk.Text(text_frame, wrap='word', height=18, font=("Arial", 12),
                          bg=left_content_frame.cget("bg"), bd=0, highlightthickness=0)
    text_widget.pack(side='left', fill='x', expand=True)

    text_widget.config(width=120)
    text_widget.config(yscrollcommand=scrollbar.set)

    text_widget.insert("1.0", text)  # Insert text into widget

    # Define bold tag with the appropriate font
    text_widget.tag_configure("bold", font=("Arial", 12, "bold"))

    # Defining what chars should be bolded
    bold_patterns = [
        r"Step \d+:",  # Bold "Step" followed by a number and colon
        r"Notes:",  # Bold "Notes:" with optional space
        r"EACH",  # Bold "EACH"
        r"UP",  # Bold "UP"
        r"\*",  # Bold all instances of "*"
        r"1",  # Need to add these lines and a few below because the numbers & colons in step 1, step 2 were not being bolded for some reason (same with the +C in CTRL+C)
        r"2",
        r"3",
        r"4",
        r"5",
        r":",
        r"\bC\b",
        r"\b+\b",
    ]
    # note: (\s) is for spaces, (\ b) is a boundary marker to distinguish words within words (not in use anymore)

    # Applying bold to bold_pattern matches
    for pattern in bold_patterns:
        start_index = "1.0"
        while True:
            start_index = text_widget.search(pattern, start_index, stopindex=tk.END, regexp=True)
            if not start_index:
                break
            # The following line calculates the end index by moving from the start_index to the end of the match
            length_of_match = len(text_widget.get(start_index, f"{start_index} wordend"))
            end_index = f"{start_index} + {length_of_match}c"
            text_widget.tag_add("bold", start_index, end_index)
            start_index = end_index  # Refresh/move on

        text_widget.config(state="disabled")  # Make widget read-only

# Call to add styled text to the frame
add_styled_text_single(left_content_frame, subheaders_text)

#___________HOUSING_FOR_USER_QUESTIONS_________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
# Frames for the Qs and User Answers
questions_frame = tk.Frame(right_content_frame)
questions_frame = tk.LabelFrame(right_content_frame, text="Answer These For Setting Suggestions", font=("Arial", 12, "bold"))

questions_frame.pack(fill='x', padx=15, pady=(50, 30))

# User Questions to Suggest Settings
def create_user_questions(relay_pairs):
    questions = []
    for relay_pair in relay_pairs:
        questions.append(f"Water volume for relays {relay_pair[0]} & {relay_pair[1]} (uL):")
    questions.append("How often should each cage receive water? \n  (Seconds)")
    questions.append("Water window start (hour, 24-hour format):")
    questions.append("Water window end (hour, 24-hour format):")
    return questions

questions = create_user_questions(RELAY_PAIRS)
entries = {}

for i, question in enumerate(questions):  # For placement in the GUI
    label = tk.Label(questions_frame, text=question)
    label.grid(row=i, column=0, sticky="e", padx=5, pady=5)
    entry = tk.Entry(questions_frame, width=20)
    entry.insert(0, "0")  # Default each entry to 0
    entry.grid(row=i, column=1, sticky="w", padx=5, pady=5)
    entries[question] = entry

#___________SUGGEST_SETTINGS_FEATURE___________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

# Logic for suggesting trigger settings
def calculate_triggers(volume_needed):
    # because each trigger dispenses 10 micro-liters
    return math.ceil(volume_needed / 10)  # math.ceil ensures the value is rounded UP

# I'm creating this section below to work on a way for relay pairs to be given a different number of triggers by the user
cage_volumes_frame = ttk.Frame(scrollable_frame)
cage_volumes_frame.pack(fill='x', padx=10, pady=1)

cage_volume_questions = {}
cage_volume_entries = {}

def suggest_settings():
    try:
        frequency = int(entries["How often should each cage receive water? \n  (Seconds)"].get())
        window_start = int(entries["Water window start (hour, 24-hour format):"].get())
        window_end = int(entries["Water window end (hour, 24-hour format):"].get())

        suggestion_text = (
            f"Suggested Settings:\n"
            f"- Interval: {frequency} seconds\n"
            f"- Stagger: {'1'} seconds (Assumed)\n"  # Assuming a default or a calculated value
            f"- Water Window: {window_start}:00 to {window_end}:00\n"
        )

        # Iterate through relay pairs to suggest the number of triggers needed for each relay pair (based on user Qs)
        for i, relay_pair in enumerate(RELAY_PAIRS):
            question = f"Water volume for relays {relay_pair[0]} & {relay_pair[1]} (uL):"
            if question in entries:
                volume_per_relay = int(entries[question].get())
                triggers = calculate_triggers(volume_per_relay)
                suggestion_text += f"- {RELAY_NAMES[relay_pair]} should trigger {triggers} times to dispense {volume_per_relay} micro-liters each.\n"

        print_to_terminal(f"{datetime.datetime.now()} - {suggestion_text}")
    except ValueError as e:
        messagebox.showerror(f"{datetime.datetime.now()} - Input Error", "Please enter valid numbers for all settings.")

#__________PUSH_SETTINGS_FEATURE_______________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
# (based on the user inputs to the Qs at the top of the GUI)

def push_settings():  # Goal is to automatically send the suggested settings to the "advanced settings" below and save them.
    try:
        # Interval
        interval_entry.delete(0, tk.END)
        interval_entry.insert(0, entries["How often should each cage receive water? \n  (Seconds)"].get())  # Updates based on user input for freq.

        # Stagger
        stagger_entry.delete(0, tk.END)
        stagger_entry.insert(0, "1")  # Defaults the "push settings" value for stagger to 1 second

        # Water window start and end time
        window_start_entry.delete(0, tk.END)
        window_start_entry.insert(0, entries["Water window start (hour, 24-hour format):"].get())
        window_end_entry.delete(0, tk.END)
        window_end_entry.insert(0, entries["Water window end (hour, 24-hour format):"].get())

        # Update triggers for each relay pair based on individual volumes
        for relay_pair, (chk, var) in relay_checkboxes.items():
            question = f"Water volume for relays {relay_pair[0]} & {relay_pair[1]} (uL):"
            if question in entries:
                volume_per_relay = int(entries[question].get())
                triggers = calculate_triggers(volume_per_relay)
                trigger_entries[relay_pair].delete(0, tk.END)
                trigger_entries[relay_pair].insert(0, str(triggers))

                # Now adding logic to disable the tickbox if volume is 0 (trigger value will also default to 0)
                if volume_per_relay == 0:
                    var.set(False)  # Uncheck if volume is zero
                else:
                    var.set(True)  # Check the box

        update_all_settings()  # saving pushed settings using master update function

        print_to_terminal(f"{datetime.datetime.now()} - Settings have been pushed to the control panel and updated.")
    except Exception as e:
        print_to_terminal(f"{datetime.datetime.now()} - Error pushing settings: {e}")

#________SUGGEST/PUSH/RUN/STOP_BUTTONS_________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

# Button frame
buttons_frame = tk.Frame(right_content_frame)
buttons_frame.pack(fill='x', padx=5, pady=(1, 1))

# Button Functionality
suggest_button = tk.Button(buttons_frame, text="Suggest Settings", command=suggest_settings)
push_button = tk.Button(buttons_frame, text="Push Settings", command=push_settings)
run_button = tk.Button(buttons_frame, text="Run Program", command=run_program)
stop_button = tk.Button(buttons_frame, text="Stop Program", command=stop_program)

# Button Placement
suggest_button.grid(row=0, column=0, padx=5, pady=0, sticky="w")
push_button.grid(row=0, column=1, padx=5, pady=0, sticky="w")
run_button.grid(row=0, column=2, padx=5, pady=0, sticky="w")
stop_button.grid(row=0, column=3, padx=5, pady=0, sticky="w")

# Button Size
suggest_button.config(height=3)
push_button.config(height=3)
run_button.config(height=3)
stop_button.config(height=3)

#_________ADVANCED_SETTINGS_MENU_______________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

# Parent frame for advanced settings
advanced_settings_frame = tk.Frame(left_content_frame)
advanced_settings_frame = tk.LabelFrame(left_content_frame, text="Advanced Settings", font=("Arial", 12, "bold"))
advanced_settings_frame.pack(fill='x', padx=10, pady=(30, 30))

# Frame for the on/off toggle buttons for the relay pairs
toggle_frame = tk.Frame(advanced_settings_frame)
toggle_frame.grid(row=7, column=0, padx=10, pady=10)

# Scaleable way of creatinng toggle and trigger settings that can recieve input from the setup page
relay_checkboxes = {}  # Dictionary to hold checkboxes for each relay pair
trigger_entries = {}  # Dictionary to hold trigger entry widgets for each relay pair

def create_trigger_entries():
    global trigger_entries, toggle_frame, relay_checkboxes
    trigger_entries.clear()
    relay_checkboxes.clear()
    for i, relay_pair in enumerate(RELAY_PAIRS):
        frame = tk.Frame(toggle_frame)
        frame.grid(row=i//4, column=i%4, padx=10, pady=(0, 10), sticky="w")

        var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(frame, text=f"Enable {RELAY_NAMES[relay_pair]}", variable=var, onvalue=True, offvalue=False)
        chk.pack(side='top', anchor='w')
        chk.select()
        relay_checkboxes[relay_pair] = (chk, var)

        label = tk.Label(frame, text="Triggers:")
        label.pack(side='left', pady=(2, 0))
        trigger_entry = tk.Entry(frame, width=5)
        trigger_entry.insert(0, "0")
        trigger_entry.pack(side='left')
        trigger_entries[relay_pair] = trigger_entry

create_trigger_entries()

# Frame for interval and stagger
settings_frame = tk.Frame(advanced_settings_frame)
settings_frame.grid(row=9, column=0, padx=10, pady=(10, 0))

# UI for specifying the interval
interval_frame = tk.Frame(advanced_settings_frame)
interval_frame.grid(row=10, column=0, padx=0, pady=(5, 0))
tk.Label(interval_frame, text="Interval (seconds):").grid(row=0, column=0, sticky="w")  # Alignsthe label to the left
interval_entry = tk.Entry(interval_frame)
interval_entry.insert(0, INTERVAL)
interval_entry.grid(row=0, column=1, sticky="w")  # Aligns the entry to the left

# Stagger UI
stagger_frame = tk.Frame(advanced_settings_frame)
stagger_frame.grid(row=11, column=0, padx=10, pady=(5, 0))
tk.Label(stagger_frame, text="Stagger (seconds):").grid(row=0, column=0, sticky="w")  # Aligns left
stagger_entry = tk.Entry(stagger_frame)
stagger_entry.insert(0, STAGGER)
stagger_entry.grid(row=0, column=1, sticky="w")

# Window Entry UI
window_frame = tk.Frame(advanced_settings_frame)
window_frame.grid(row=12, column=0, padx=10, pady=(5, 0))
tk.Label(window_frame, text="Water Window Start (24-hour format):").grid(row=0, column=0, sticky="w")
window_start_entry = tk.Entry(window_frame)
window_start_entry.insert(0, WINDOW_START)
window_start_entry.grid(row=0, column=1, sticky="w")
tk.Label(window_frame, text="Water Window End (24-hour format):").grid(row=1, column=0, sticky="w")
window_end_entry = tk.Entry(window_frame)
window_end_entry.insert(0, WINDOW_END)
window_end_entry.grid(row=1, column=1, sticky="w")

# Master Update Button
update_settings_button = tk.Button(advanced_settings_frame, text="Update Settings", command=update_all_settings)
update_settings_button.grid(row=13, column=0, sticky="w", padx=(230, 5), pady=10)  # Change Columnspan if too wide
update_settings_button.config(height=3)

#___________SILLY_IMAGE_STUFF__________________________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________
# in the future, find better spot for conelab logo and include it in the download package?

# Defining the image path(s)
image1_path = "/home/conelab/lablogo.jpg"

# Load and convert the images immediately to PhotoImage objects (for tkinter compatibility)
image1 = Image.open(image1_path)
tk_image1 = ImageTk.PhotoImage(image1)

# For creating image labels later:
root.tk_image1 = ImageTk.PhotoImage(Image.open(image1_path))

# Frame for images
image_frame = tk.Frame(right_content_frame)
image_frame.pack(fill='x', padx=(50, 10), pady=1)

# Creating labels for the images (now just one) and placing them into the image_frame using grid
left_image_label = tk.Label(image_frame, image=tk_image1)
left_image_label.grid(row=0, column=0, padx=(50, 10), pady=(15, 5), sticky="w")

# note: I'm putting the image into a label within the frame (instead of just in the frame), to better allow for more pics later if desired

# note to self: "sticky="w"" ensures that the labels align to the left of their grid cells. using "ew" can make them expand to entire cell width

#______________________________________________________________________________________________________________________________________________________________________________________________
#__________PROGRAM_CLOSURE_AND_OTHER_END_STUFF_________________________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________________

canvas.configure(scrollregion=canvas.bbox("all"))  # putting this at very end so the canvas updates its scroll region after ALL grid adjustments

# So that the program stops when exiting the gui, instead of running in the background
def on_close():
    stop_program()

root.protocol("WM_DELETE_WINDOW", on_close)  # Stops window when GUI is closed
root.mainloop()  # Allows the tkinter event loop to run indefinitely (i.e., so the GUI can update etc.)

