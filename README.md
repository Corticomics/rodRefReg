
# Rodent Refreshment Regulator Version 17

**Last updated: 23/07/2024 by JS -- CURRENTLY A WIP**

The **Rodent Refreshment Regulator (RRR)** is a python-based application designed to automatically dispense precise amounts of water to laboratory mice at specified intervals. Below you will find detailed instructions on setting up, configuring, and running the system using a Raspberry Pi and up to eight stackable sixteen-relay hats from [Sequent Microsystems](https://sequentmicrosystems.com/products/sixteen-relays-8-layer-stackable-hat-for-raspberry-pi).


<img src="https://github.com/user-attachments/assets/d616c02f-4deb-492b-9152-173165b6e278" width="550" height="400">

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Hardware Overview](#hardware-overview)
- [Stacking the Hats](#stacking-the-hats)
- [Program Installation](#program-installation)
- [Configuration](#configuration)
- [Running the Program](#running-the-program)
- [Advanced Settings](#advanced-settings)
- [Pump Triger Notifications (Optional)](#pump-trigger-notifications-(optional))
- [Statistics](#statistics)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features
- User-friendly GUI with detailed instructions and headers for easy configuration.
- An optional "Suggest & Push Settings" feature that queries the user for how they wish to use the RRR.
- Customizable time intervals (in seconds) between water dispenses.
- Adjustable number of triggers per time interval, allowing for different amounts of water to be provided each time.
- Changeable time windows for water dispensing - allows for setting start/end times and having hours of the day that are excluded from water dispensing regardless of your chosen interval.
- Email notifications and/or Slack bot functionality to indicate successful water dispensing when using the RRR remotely.
- Advanced settings for fine-tuning system behavior.
- Log messages displayed in a GUI-integrated terminal.
- Contrary to the name, the RRR may be customized for non-rodent use as well.

## Requirements
- Raspberry Pi (tested on Raspberry Pi 4)
- 16-Relays hat from [Sequent Microsystems](https://sequentmicrosystems.com/products/sixteen-relays-8-layer-stackable-hat-for-raspberry-pi) (up to 8 hats depending on the scale of your setup).
- Python 3
- Required Python packages (see below)
- An assortment of copper wiring, tubing, and a large water reservoir (see below for details pertaining to quantity and sizing)
- (Optional) a 3D printer with PLA material for printing various support structures that may be valuable in your setup.
- One 10μL micropump for each mouse enclosure. We used model "LPMX0501600B A" from [The Lee Co.](https://www.theleeco.com/products/pumps/). We have attached the schematics for this model below, for reference.

Lee Co. Pump Schematics (Model LPMX0501600B A)|
:-------------------------:
 ![](https://github.com/user-attachments/assets/2b79a139-09c3-4f83-86e7-30d5e8bff458)

## Hardware Overview
1. **The Sixteen-Relays Hat:**
The RRR program sends triggers by enabling/disabling the relays atop the hat(s) on your raspberry pi. These hats are stackable depending on the number of relays required (1 relay = 1 water pump for a mouse enclosure), with each hat sporting 16 relays. Relays are sorted into pairs such that there exists one COM terminal (that supplies the power) for every two relays on the hat. As such, a finalized RRR setup using one hat for 16 enclosures would have eight power sources going into each com terminal on that hat, and a 10μL micropump wired into each of the 16 seperate relay ports. In our design, we use 12v power sources because our 10μL micropumps require 12v to trigger. Your voltage needs may differ however, so remember that the relay hats from Sequent Microsystems are designed to handle up to 24v per COM terminal.

**Note:** Due to the nature of these relays being sorted into pairs, the user-settings must be the same for each in a pair. For example, Relay pairs 1 & 2 could be configured to trigger 2 times (20μL) every 3 hours between the hours of 08:00 and 21:00, while Relay pairs 3 & 4 may have differing settings chosen. For this reason, mouse enclosures with the same water delivery needs should be wired into the same relay pair, and enclosures with differing needs should use a different relay pair (even if one of the relays in that pair must go unused).

2. **Grounding and Power Sources:**
For our system using one 16-relays hat, we used two wall adapters that each lead to eight 12v DC terminal plugs with a positive and negative port. These should be wired such that the positive terminals of each plug lead to the COM terminals on your hat, while the negative terminals should share a common ground. Furthermore, this common ground should also be connected to the grounding port on the 16-relays hat, and to the negative ports on each micropump as well. In our RRR setup illustrated below, we soldered a 1-to-24 common ground to serve this purpose.

**(add in pictures!)**

3. **Water Reservoir and Tubing:**
A water reservoir is required to provide water to each micropump being used. We recommend using a large container (our setup uses one that is 20 Liters) because the weight of the water within will help flush excess air from the tube. Additionally, a large water reservoir will allow for less frequent refilling, which is important as an empty reservoir will cause an intake of air into the tubes leading to your pumps, which will cause higher variance in the amount of water being released into each mouse enclosure. Furthermore, we used plastic tubing with an internal diameter of 2mm, and 10μL micropumps from [The Lee Co.](https://www.theleeco.com/products/pumps/) (model "LPMX0501600B A").

**Note:** An excess number of air bubbles in your tubing will likely be present to some extent regardless of the size of your water reservoir. In testing, we found that manually priming each input tube was highly useful in eliminating excess air (i.e., connecting the micropump to its water input tube while water is flowing through it). Following this, we were able to eliminate the remaining air bubbles by running the program 200 times per pump (i.e., setting the triggers per relay pair to 200 and allowing a single interval to elapse) prior to using them for the mice. This protocol greatly reduced the variance in the quanitiy of water released by each pump per trigger.

4. **Optional 3D-Printed Support Structures:**
While not essential for a working RRR system, we designed an assortment of 3D models (available in .STL format) that assist in the following ways:

   **4.1. Pump Tray:** A model to hold and prevent the pump from rolling in the top portion of the mouse enclosure (we also used a piece of electrical tape for further support).

PLA Print             |  STL Model
:-------------------------:|:-------------------------:
![](https://github.com/user-attachments/assets/e7547358-ae70-43be-ac31-f15cc8109734)  |  ![](https://github.com/Corticomics/rodRefReg/assets/161750793/7fb5f4ec-0b1e-40aa-97c0-f15f67131a87)

  
   **4.2. Water Collector:** A model to recieve the water tube within the mouse enclosure - features a section for water to be deposited while preventing access to the tube, to prevent mice from chewing on it.
  
PLA Print             |  STL Model
:-------------------------:|:-------------------------:
![](https://github.com/user-attachments/assets/eaf59835-7f2d-43e8-bb3f-c4f4f6b75afe)  |  ![](https://github.com/user-attachments/assets/d3829dac-94f1-4d78-852c-0760f312059d)

**Example Setup:** The pump tray with the water collector - without any water input or wiring.
:-------------------------:
![](https://github.com/user-attachments/assets/81885e1a-0429-4ffd-877d-c95c5e9a993a)


   **4.3.** A model to hold a 10ml syringe upright, for use as a makeshift water reservoir when initially testing the RRR system (using a 18G blunt fill needle). Model was adapted from a smaller version made by the [OHRBETS](https://github.com/agordonfennell/OHRBETS) team.

**PLA Print & STL Model**             |  **Example Setup**
:-------------------------:|:-------------------------:
![](https://github.com/user-attachments/assets/6bd396d4-2883-407b-a4df-f6587220d063)  |  ![](https://github.com/user-attachments/assets/09865246-e34a-4bd6-8d43-1b05d3d77901)

   **3D Printer Settings:**
   - We used a PRUSA I3 MK3 3D printer using standard PLA Material and a 0.3mm nozzle.
   - Bed Temperature was set to 70°.
   - Nozzle temperature was set to 210°
   - Flow rate set to 115%
   - Z-offset set to 0.1405 (this value will likely be unique from printer-to-printer, and is usually calibrated during the printer's first time setup, however we are highlighting its importance here because an improper z-offset caused us a slew of           printing difficulties in the past).

## Stacking the Hats 
**Note: You may skip this section if only using one 16-relays hat**

   **RS485/MODBUS Configuration:**
   As noted in the documentation for the 16-relays hat, the hats can be configured between RS485 and MODBUS configurations. For the purposes of running the RRR program as originally written, we recommend running the MODBUS configuration. This configuration allows for direct control from the raspberry pi and communicates with the relay hats using standard MODBUS commands. Utilizing this configuration requires no changes to the existing code.
   
   However, should you be attempting to extend the functionality of the RRR's code to allow for communication with other devices with RS485 interfaces (i.e., If you wanted to integrate the RRR's relay control system into a larger RS485 network potentally spanning multiple devices), then changes to the code will be necessary according to the documentaion provided by [Sequent Microsystems](https://sequentmicrosystems.com/products/sixteen-relays-8-layer-stackable-hat-for-raspberry-pi).
   
   **DIP Switches:**
   Each 16-relays hat has a six position DIP switch used as a RS485 port (if applicable) and to indicate their stack level. When using a RRR setup that involves multiple hats, ensure that the dip switches for each hat are correctly set to indicate their stack level according to the diagram below from Sequent Microsystems. Please note that despite being listed as hats 1-8 in the RRR's GUI, your first hat should be set to stack level 0, your second hat should be set to 1, and so on in a 0-7 fashion.

![Dip switch diagram2](https://github.com/Corticomics/rodRefReg/assets/161750793/f99ebd3d-7b86-44a6-b370-95083e91e388)

   Additionally, it should be highlighted that your chosen hat configuration (RS485 or MODBUS) will change how these dip switches need to be setup. Sequent microsystems has detailed documentation regarding this on their [site](https://sequentmicrosystems.com/products/sixteen-relays-8-layer-stackable-hat-for-raspberry-pi), however most RRR users using a simple MODBUS configuration will simply need to set all DIP switches for TX and RX to OFF (in addition to ensuring the stack levels for each hat are set).   

   **Declaring your Number of Hats:** 
   When initially launching the RRR program, you will be prompted to input the number of hats you are using in your setup. Based on this value, your GUI will scale accordingly. Be sure that all of your hats and their respective dip switches are installed correctly prior to running the RRR program in order to avoid errors. If you declare more hats than are physically installed, the program will notify you of which hats failed to initialize, but will still load a GUI that is structured for the number of hats you declared. If errors persist, please see the troubleshooting section below.
   
## Program Installation
1. **Clone the Repository:**
   ```sh
   git clone https://github.com/yourusername/rodent-refreshment-regulator.git
   cd rodent-refreshment-regulator
   ```

2. **Install Required Packages:**
   ```sh
   pip install RPi.GPIO
   pip install pillow
   pip install requests
   ```

3. **Setup the Relay Hat:**
   Connect the relay hat to the Raspberry Pi GPIO pins according to the relay hat documentation.

## Configuration
Before running the program, you need to configure the water dispensing intervals and time windows.

1. **Define Relay Pairs:**
   The relay pairs are predefined as follows:
   ```python
   RELAY_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
   ```

2. **Set Default Values:**
   Adjust the default values for interval, stagger, and time windows in the code:
   ```python
   INTERVAL = 3600  # Default interval: 1 hour
   STAGGER = 1  # Default stagger: 1 second
   WINDOW_START = 8  # Default window start time: 8 AM
   WINDOW_END = 20  # Default window end time: 8 PM
   ```

## Running the Program
1. **Launch the GUI:**
   ```sh
   python main.py
   ```

2. **Configure Settings via GUI:**
   - Follow the instructions provided in the welcome header.
   - Answer the questions on the right side of the screen to configure water volume and intervals.
   - Click the "Suggest Settings" button to receive setting recommendations.
   - Click the "Push Settings" button to save these settings.
   - Click "Run Program" to start the water dispensing process.
  
     **Note:** All setting changes, trigger notifications, and other alerts will be cast to the in-GUI terminal.

3. **Stop the Program:**
   - Click "Stop Program" or close the GUI window to stop the program.

## Advanced Settings
If more fine-tuned settings are desired, you may instead choose to ignore the suggest settings feature alltogether and manually change your settings within the "Advanced Settings" Section of the GUI. The parameters included in this section are:
- Enable or disable specific relay pairs
- Set the number of triggers for each relay pair
- Adjust interval and stagger times
- Define water window start and end times

## Pump Trigger Notifications (Optional)
**Method 1: Using Email**
The system can send email notifications upon successful water dispensing. We used the free-tier offered by [Brevo](https://www.brevo.com/)(formerly SendInBlue) to generate a unique API key required for the RRR's emailing feature, however any equivalent service will likely be sufficient. Once you have aquired the necessary information, you may update the program's code as shown below:

1. **Configure Email Settings:**
   Update the `send_email` function with your SMTP API key and recipient details:
   ```python
   api_key = "your-smtp-api-key"
   url = "https://api.your-smtp-service.com/v3/smtp/email"
   data = {
       "sender": {"name": "MouseMaster", "email": "your-email@example.com"},
       "to": [{"email": "recipient-email@example.com"}],
       "subject": subject,
       "htmlContent": content
   }
   ```
**Method 2: Using a SlackBot**
(fill in details pertaining to slackbot functionality here!)

# Statistics
Ensuring that the RRR system releases an accurate and consisent amount of water over time is crucial for its usability. To assess variance in water ouput using the RRR, we setup four micropumps from [The Lee Co.](https://www.theleeco.com/products/pumps/) (see our hardware overview above), and ran 30 trials whereby each pump was triggered 100 times per trial. After each set of 100 triggers (1 trial), the water released by each pump was recorded and subsequently emptied. In between each trial, the 3D-printed water collectors associated with each pump were re-weighed, in order to account for any residual water containted within prior to the next trial. It should also be noted that all of the tubing used in collecting this data was primed beforehand to eliminate excess air - as described in our priming protocol above. Below we have included the raw data we collected from these trials, as well as several statistical tests to assess variance between and within pumps.

  **Note:** It is important to highlight the innate variance of the micropumps (model LPMX0501600B A) we used from [The Lee Co.](https://www.theleeco.com/products/pumps/) As detailed in the schematics diagram we included above, this model can vary up to **± 1.5 μL per 10 μL trigger**. As such, this is the minimum amount of variance that the RRR system is capable of reaching, barring the use of an alternate 10μL micropump model.

## **Raw Data**

**Pump 1** | **Pump 2** 
:-------------------------:|:-------------------------:
![](https://github.com/user-attachments/assets/2b34bc31-b499-4118-8411-faba4edfc41c)  | ![](https://github.com/user-attachments/assets/961b877f-421b-40d1-8b01-09773301fb81) 

**Pump 3** | **Pump 4**
:-------------------------:|:-------------------------:
![](https://github.com/user-attachments/assets/d54d34aa-8d2a-4042-8a6f-3f66797405de)  | ![](https://github.com/user-attachments/assets/b67b939a-4247-4d9e-85c7-2f7516a23907)

## **Simple Descriptive Statistics**

<img src="https://github.com/user-attachments/assets/49b2eec0-d13d-4f6e-9ba0-d82d7d863eb6" width = "550">


## **Coefficient of Variation**

<img src="https://github.com/user-attachments/assets/b9c15fa1-267e-4743-a339-a497881c9c8c" width = "550">


## **Correlation Matrix**

<img src="https://github.com/user-attachments/assets/5b5557ab-a7d7-4bad-9135-8643a20e9259" width = "550">


## **Variance Between Pumps Over Trials**

![](https://github.com/user-attachments/assets/fa6d379c-ae6c-4468-a49e-8400d348f8ae)
(DESCRIBE HERE)

![Line graph](https://github.com/user-attachments/assets/2fa6ea2d-bc45-41bc-ab99-474fcae90e7d)
(DESCRIBE HERE)

## **Bootstrapped Variances for Differing Numbers of Trials:**

<img src="https://github.com/user-attachments/assets/a3f3d936-d3e3-49bf-9347-49e058d274d2" width = "500">

![boot](https://github.com/user-attachments/assets/996e44c0-8728-405c-a5fa-383a2c3d6e26)

   **Note:** As seen in the above data, variance is (DECRIPTION)

## **One-Way ANOVA**

<img width="300" alt="anova" src="https://github.com/user-attachments/assets/ed4f49c2-87a5-465f-bf51-b051ddbcd9bb">

Given that our p-value is notably smaller than our threshold of 0.05, we can say that significant differences in water output are present between pumps 1-4. Furthermore, the notaly high f-value suggests that substantial differences exist between the means of the water weights for pumps 1-4.

## Tukey's Honestly Significant Difference (HSD) Post-Hoc Test

<img width="1000" alt="tukey" src="https://github.com/user-attachments/assets/845aa84d-5566-4a8f-8cd7-dec4b8a5ddea">

**Interpretation:**
•	Pump 1 vs. Pump 2: The mean difference is -108.43, and the p-adj value is 0.001, indicating a significant difference.
•	Pump 1 vs. Pump 3: The mean difference is 8.07, and the p-adj value is 0.899, indicating no significant difference.
•	Pump 1 vs. Pump 4: The mean difference is -166.33, and the p-adj value is 0.001, indicating a significant difference.
•	Pump 2 vs. Pump 3: The mean difference is 116.50, and the p-adj value is 0.001, indicating a significant difference.
•	Pump 2 vs. Pump 4: The mean difference is -57.9, and the p-adj value is 0.001, indicating a significant difference.
•	Pump 3 vs. Pump 4: The mean difference is -174.40, and the p-adj value is 0.001, indicating a significant difference.

As such, while Pumps 1 and 3 are statistically similar, Pump 2 shows a significant difference when compared to both Pump 1 and Pump 3. Additionally, Pump 4 is significantly different from all other pumps.


## Statistics Overview
- need to mention how 4 is extremely off
- how individually testing pumps will likely be necessary due to their inherent variation between eachother being significantly different.


## Troubleshooting
- Ensure the Raspberry Pi and relay hat are properly connected, and that all components are grounded correctly.
- Check whether the software required for the 16-relays hat is correctly installed (available [here](https://github.com/SequentMicrosystems/16relind-rpi_\)). One indication of this being an issue is if your hat does not light up blue when the RRR program triggers.
- If your monitor flickers when the program is supposed to trigger, lowering the resolution can help.
- Verify interval and time window settings are correctly configured. Note that the interval time uses seconds, and the time window functionality uses 24-hour time.
- An initialization warning saying "failed to initialize hats" means that the RRR progam is having trouble detecting the number of hats that you have declared. Ensure that all hats are connected properly, and that you only enter the total number of hats that are currently installed on the Raspberry Pi prior to running the program.
- Review log messages in the GUI terminal for error details.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes. Ensure your code follows the project's coding standards and includes appropriate documentation.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

Enjoy using the Rodent Refreshment Regulator! If you have any questions or need further assistance, feel free to open an issue on GitHub or contact the project developers.
