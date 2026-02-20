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

> [!TIP]
> Users can paste into the Arduino App Lab terminal using **RIGHT-CLICK**. Using CTRL+V is not supported in the App Lab Terminal.

```bash
cd /home/arduino
sudo mkdir -p /opt/demo && sudo chown $USER /opt/demo

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

5. Back in the /IOTCONNECT browser tab, click on the "Create Template" button in the top-right of the screen.

6. Click on the "Import" button in the top-right of the resulting screen.

7. Select your downloaded copy of the template from sub-step 4 and then click "save".

8. Click on the "Devices" tab of the blue toolbar at the bottom of the screen.

9. In the resulting page, click on the "Create Device" button in the top-right of the screen.

10. Customize the "Unique ID" and "Device Name" fields to your needs (both fields should be identical though).

11. Select the most appropriate option for your device from the "Entity" dropdown (only for organization, does not
    affect connectivity).

12. Select "arduino" from the "Template" dropdown.

13. In the resulting "Device Certificate" field, select "Use my certificate." Leave this page as-is for now, you will finish it later.

14. Swapping over to the terminal of your Arduino, navigate to the `scripts` directory of the repo using this command:

```
cd /home/arduino/iotc-arduino-uno-q-workshop/scripts
```

15. Execute the automated device credentials script with this command:

```
bash ./credentials.sh
```

16. If you generated a new certificate, when prompted, press ENTER to print it.  
    If you chose to reuse existing credentials, the script may skip certificate reprint.

17. Copy **(using CTRL+C)** the device certificate text (including BEGIN and END lines) and paste the text into the 
certificate box in the /IOTCONNECT device creation page.

18. Click the "Save and View" button to go to the page for your new device.

19. Now on your device's page in /IOTCONNECT, click on the black/white/green paper-and-cog icon in the top-right of the
    device page (just above "Connection Info") to download your device's configuration file.

20. Open the configuration file in a text editor and copy its entirety to your clipboard.

21. Back in the terminal of your Arduino, paste **(using RIGHT-CLICK, because CTRL+V does not work in the App Lab Terminal)** 
the contents (of the configuration file from your clipboard as instructed by the next step of the script, and then press ENTER.

22. The onboarding process is complete. 


## 4. Set Up /IOTCONNECT SDK and Relay Service

Run these commands to install the /IOTCONNECT Python Lite SDK and then download and configure the /IOTCONNECT Relay Service.

```bash
cd /home/arduino/iotc-arduino-uno-q-workshop
sudo ./scripts/unoq_setup.sh
```

>[!NOTE]
> If during the setup script a pop-up appears asking if you would like to restart select device services, simply press 
> ENTER.

## 5. Choose a Lab Example, Clone It, and Copy the /IOTCONNECT Files

In Arduino App Lab:
1) Browse the example applications after clicking "Examples" in the vertical toolbar on the left.
2) Click on the example application you wish to utilize.
3) Click on "Copy and edit app" in the top-right corner
4) Name your copy of the app (ideally similar to the app names in this repo)
5) Copy the /IOTCONNECT-enabled python files and relay client from the workshop repo into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/<example>/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
> [!TIP]
> For example, if you were using the "blink" app and you had named your copy "my-blink-app", your commands would be:
>   ```bash
>   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/blink/python/* /home/arduino/ArduinoApps/my-blink-app/python/
>   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/my-blink-app/python/
>   ```

### Examples Index

Use these /IOTCONNECT-specific guides:

>[!NOTE]
>`[DB]` = dashboard image and exported /IOTCONNECT dashboard JSON template available in the example's folder.
> 
>`[AH]` = additional hardware (not provided with standard Arduino Uno Q) is required for this app.

- [air-quality-monitoring](app-configs/air-quality-monitoring/README.md) `[DB]`
- [anomaly-detection](app-configs/anomaly-detection/README.md)
- [audio-classification](app-configs/audio-classification/README.md) `[DB]`
- [bedtime-story-teller](app-configs/bedtime-story-teller/README.md)
- [blink](app-configs/blink/README.md)
- [blink-with-ui](app-configs/blink-with-ui/README.md)
- [cloud-blink](app-configs/cloud-blink/README.md)
- [code-detector](app-configs/code-detector/README.md) `[AH]`
- [home-climate-monitoring-and-storage](app-configs/home-climate-monitoring-and-storage/README.md) `[DB]` `[AH]`
- [image-classification](app-configs/image-classification/README.md) `[DB]`
- [keyword-spotting](app-configs/keyword-spotting/README.md)  `[AH]`
- [led-matrix-painter](app-configs/led-matrix-painter/README.md)
- [mascot-jump-game](app-configs/mascot-jump-game/README.md)
- [object-detection](app-configs/object-detection/README.md) `[DB]`
- [object-hunting](app-configs/object-hunting/README.md) `[AH]`
- [real-time-accelerometer](app-configs/real-time-accelerometer/README.md) `[DB]` `[AH]`
- [system-resources-logger](app-configs/system-resources-logger/README.md) `[DB]`
- [theremin](app-configs/theremin/README.md) `[AH]`
- [unoq-pin-toggle](app-configs/unoq-pin-toggle/README.md)
- [vibration-anomaly-detection](app-configs/vibration-anomaly-detection/README.md) `[DB]` `[AH]`
- [video-face-detection](app-configs/video-face-detection/README.md) `[DB]` `[AH]`
- [video-generic-object-detection](app-configs/video-generic-object-detection/README.md) `[DB]` `[AH]`
- [video-person-classification](app-configs/video-person-classification/README.md) `[DB]` `[AH]`
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
>
> If telemetry does not show up and logs report `Address already in use`, check what is bound to TCP port `8899`:
> ```bash
> sudo ss -ltnp | grep ':8899'
> ```
> If a conflicting bridge service is using that port (for example `iotc-socat`), stop it and restart relay:
> ```bash
> sudo systemctl disable --now iotc-socat
> sudo systemctl restart iotc-relay
> ```
