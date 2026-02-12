# Arduino UNO Q App Lab Examples on /IOTCONNECT

This guide provides step-by-step instructions to set up the Arduino Uno Q hardware and integrate it with /IOTCONNECT,
Avnet's robust IoT platform to run IoT-connected Arduino App Lab demos.

1. [Install Arduino App Lab on Host Machine](#1-install-arduino-app-lab-on-host-machine)
2. [Clone This Repo Onto Your Arduino UNO Q](#2-clone-this-repo-onto-your-arduino-uno-q)
3. [Onboard Arduino into /IOTCONNECT](#3-onboard-arduino-into-iotconnect)
4. [Set Up /IOTCONNECT SDK and Relay Service](#4-set-up-iotconnect-sdk-and-relay-service)
5. [Choose a Lab Example, Clone It, and Copy the /IOTCONNECT Files](#5-choose-a-lab-example-clone-it-and-copy-the-iotconnect-files)
6. [Run the App and Confirm Telemetry](#6-run-the-app-and-confirm-telemetry)

## 1. Install Arduino App Lab on Host Machine

First, install Arduino App Lab on your PC:
   - https://www.arduino.cc/en/software/#app-lab-section

   <img src="images/app-lab-download.png" alt="App Lab download page" width="700">

Then, connect the UNO Q to your PC with a USB cable.

   <img src="images/app-lab-connect.png" alt="Connect to board" width="300">

Next, enter your Wi-Fi credentials and set up connectivity.

   <img src="images/app-lab-2-network.png" alt="Enter network credentials" width="300">

Update the board when prompted.

   <img src="images/app-lab-4-install-updates.png" alt="Install updates" width="300">

Now, restart the board.
 
Then, in **App Lab**, open **Examples** to view all available apps.

Finally, open the **App Lab terminal** (used to access the Uno Q terminal).

   <img src="images/app-lab-8-openterminal.png" alt="Open terminal" width="400">


## 2. Clone This Repo Onto Your Arduino UNO Q

Run these commands to clone this repository onto your Arduino to get access to the automation scripts and App Lab code: 

```bash
cd /home/arduino

git clone https://github.com/avnet-iotconnect/iotc-arduino-uno-q-workshop.git
cd iotc-arduino-uno-q-workshop

chmod +x scripts/*.sh
```


## 3. Onboard Arduino into /IOTCONNECT

Next you will need to onboard your device into /IOTCONNECT. This will be done via the online /IOTCONNECT user interface in 
conjunction with an automated bash script. Follow these steps to complete the process:

1. In a web browser, navigate to console.iotconnect.io and log into your account.

2. In the blue toolbar on the left edge of the page, hover over the "processor" icon and then in the resulting dropdown
   select "Device".

3. Now in the resulting Device page, click on the "Templates" tab of the blue toolbar at the bottom of the screen.

4. Right-click and then click "save link as" on [this link to the Arduino Uno Q App Lab device template](https://raw.githubusercontent.com/avnet-iotconnect/iotc-arduino-uno-q-workshop/refs/heads/main/app-configs/arduino-app-lab-template.json)
   to download the raw template file to your PC.

   > [!IMPORTANT]
   > Ensure that the template file saves as a `.json` file-type. Some browsers will default to a `.txt` file-type
   > which is not supported by the /IOTCONNECT template import feature.

6. Back in the /IOTCONNECT browser tab, click on the "Create Template" button in the top-right of the screen.

7. Click on the "Import" button in the top-right of the resulting screen.

8. Select your downloaded copy of the template from sub-step 4 and then click "save".

9. Click on the "Devices" tab of the blue toolbar at the bottom of the screen.

10. In the resulting page, click on the "Create Device" button in the top-right of the screen.

11. Customize the "Unique ID" and "Device Name" fields to your needs (both fields should be identical though).

12. Select the most appropriate option for your device from the "Entity" dropdown (only for organization, does not
    affect connectivity).

13. Select "arduino-app-lab" from the "Template" dropdown.

14. In the resulting "Device Certificate" field, select "Use my certificate." Leave this page as-is for now, you will finish it later.

15. Swapping over to the terminal of your Arduino, navigate to the `scripts` directory of the repo using this command:

```
cd /home/arduino/iotc-arduino-uno-q-workshop/scripts
```

15. Execute the automated device credentials script with this command:

```
bash ./credentials.sh
```

16. When prompted, press ENTER to have the script print out the generated device certificate.

17. Copy the device certificate text (including BEGIN and END lines) and paste the text into the certificate box in the /IOTCONNECT device creation page.  

18. Click the "Save and View" button to go to the page for your new device.

19. Now on your device's page in /IOTCONNECT, click on the black/white/green paper-and-cog icon in the top-right of the
    device page (just above "Connection Info") to download your device's configuration file.

20. Open the configuration file in a text editor and copy its entirety to your clipboard.

21. Back in the terminal of your Arduino, paste the contents of the configuration file from your clipboard as instructed by the next step
    of the script, and then press ENTER.

22. The onboarding process is complete. 


## 4. Set Up /IOTCONNECT SDK and Relay Service

Run these commands to install the /IOTCONNECT Python Lite SDK and then download and configure the /IOTCONNECT Relay Service.

```bash
cd /home/arduino/iotc-arduino-uno-q-workshop
sudo ./scripts/unoq_setup.sh --demo-dir /home/arduino/demo
```

## 5. Choose a Lab Example, Clone It, and Copy the /IOTCONNECT Files

In Arduino App Lab:
1) Browse examples from `app-bricks-examples`.
2) Copy the selected app into your workspace.
3) Note the app folder path (example: `/home/arduino/ArduinoApps/air-quality-on-led-matrix`).
4) Open the matching guide in `app-configs/<example>/README.md`.
5) Copy the /IOTCONNECT-enabled python files from the workshop repo into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/<example>/python/* /home/arduino/ArduinoApps/<app-folder>/python/
   ```

### Examples Index

Use these /IOTCONNECT-specific guides:

- [air-quality-monitoring](app-configs/air-quality-monitoring/README.md)
- [anomaly-detection](app-configs/anomaly-detection/README.md)
- [audio-classification](app-configs/audio-classification/README.md)
- [bedtime-story-teller](app-configs/bedtime-story-teller/README.md)
- [blink](app-configs/blink/README.md)
- [blink-with-ui](app-configs/blink-with-ui/README.md)
- [cloud-blink](app-configs/cloud-blink/README.md)
- [code-detector](app-configs/code-detector/README.md)
- [home-climate-monitoring-and-storage](app-configs/home-climate-monitoring-and-storage/README.md)
- [image-classification](app-configs/image-classification/README.md)
- [keyword-spotting](app-configs/keyword-spotting/README.md)
- [led-matrix-painter](app-configs/led-matrix-painter/README.md)
- [mascot-jump-game](app-configs/mascot-jump-game/README.md)
- [object-detection](app-configs/object-detection/README.md)
- [object-hunting](app-configs/object-hunting/README.md)
- [real-time-accelerometer](app-configs/real-time-accelerometer/README.md)
- [system-resources-logger](app-configs/system-resources-logger/README.md)
- [theremin](app-configs/theremin/README.md)
- [unoq-pin-toggle](app-configs/unoq-pin-toggle/README.md)
- [vibration-anomaly-detection](app-configs/vibration-anomaly-detection/README.md)
- [video-face-detection](app-configs/video-face-detection/README.md)
- [video-generic-object-detection](app-configs/video-generic-object-detection/README.md)
- [video-person-classification](app-configs/video-person-classification/README.md)
- [weather-forecast](app-configs/weather-forecast/README.md)

---

## 6. Run the App and Confirm Telemetry

1) Run the app in App Lab.
2) Confirm telemetry appears in /IOTCONNECT.
3) If you enabled commands, test a command from /IOTCONNECT and verify the app receives it.

Expected result: the selected App Lab example runs on the UNO Q and publishes telemetry to /IOTCONNECT.

> [!TIP]
> You can manually manage the /IOTCONNECT Relay Service on your device.
>
> To disconnect your device from /IOTCONNECT, stop the relay service:
> ```bash
> sudo systemctl stop iotc-relay
> ```
>
> To start it again:
> ```bash
> sudo systemctl start iotc-relay
> ```
>
> To restart:
> ```bash
> sudo systemctl restart iotc-relay
> ```
