# Project Explanation

This project aims to facilitate the transfer of audio and video data from a Linux machine like the steam deck to a Windows machine using a Bonjour-enabled network. The project is implemented using Python programming language and consists of two separate programs, one for the Linux machine and the other for the Windows machine.

## Linux Program

The Linux program uses the ALSA sound system to capture audio from the USB headset and forward it to the Windows machine. It also captures video data from the USB web cameras and forwards it to the Windows machine. Additionally, it captures USB mouse and keyboard data and forwards it to the Windows machine, enabling the user to control the Windows machine using their Linux machine.

## Windows Program

The Windows program receives the audio and video data from the Linux machine and plays the audio through the Windows default audio device. It also displays the video data on the Windows screen. The USB mouse and keyboard data received from the Linux machine is used to control the Windows machine, allowing the user to work with the Windows machine as if they were sitting in front of it.

## Bonjour Protocol

The Bonjour protocol is used to establish the connection between the Linux and Windows machines. Bonjour is an open-source implementation of the Zeroconf protocol, which allows devices to discover each other on a local network without any prior configuration. This makes it easy to set up the connection between the Linux and Windows machines, as no manual IP address configuration is required.

## Conclusion

Overall, this project provides a convenient solution for users who need to transfer audio and video data between Linux and Windows machines, as well as control a Windows machine from a Linux machine. The use of the Bonjour protocol simplifies the setup process, and the Python programming language provides a flexible and extensible framework for implementing the necessary functionality.
___

### Here is a comprehensive set of step-by-step installation instructions to set up both the Linux and Windows systems to run the scripts:

## Linux Setup:

# Update the package list and install necessary dependencies:
```bash
sql
Copy code
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3 python3-pip v4l2loopback-dkms v4l2loopback-utils ffmpeg smbclient
```
# Install the required Python libraries:

```bashCopy code
pip3 install numpy opencv-python-headless pyaudio pyzmq pybonjour pysmb
```
# Install and configure the v4l2loopback kernel module:
```bash
sudo modprobe v4l2loopback
```
# Create a virtual video device:
```bash
sudo modprobe v4l2loopback video_nr=10 card_label="virtualcam" exclusive_caps=1
```
- Note: Change video_nr=10 to a different number if /dev/video10 is already in use. You'll also need to update the Linux script to reflect the new device number.

# Place the Linux Python script in a directory of your choice, let's say ~/usb_sharing:
```bash
mkdir ~/usb_sharing
cp /path/to/your/linux_script.py ~/usb_sharing/
```
## Ensure that your USB devices (camera, microphone, keyboard, mouse, etc.) are connected to the Linux system.

# Run the Linux script:

```bash
python3 ~/usb_sharing/linux_script.py
```

### Windows Setup:

# Install Python from the official website: https://www.python.org/downloads/

# Install necessary Windows dependencies:

# Download and install the Visual Studio SDK Build Tools Core: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Install the v4l2loopback equivalent on Windows (for example, use OBS Virtual Camera): https://obsproject.com/forum/resources/obs-virtualcam.539/

# Install VB-Audio Virtual Cable: https://vb-audio.com/Cable/

# Install the required Python libraries:
```
pip install numpy opencv-python-headless pyaudio pyzmq zeroconf psutil pywin32 pypiwin32
```
# Place the Windows Python script in a directory of your choice, let's say C:\usb_sharing:
```
mkdir C:\usb_sharing
copy /path/to/your/windows_script.py C:\usb_sharing\
```
# Run the Windows script:
```
python C:\usb_sharing\windows_script.py
```
### After completing these steps, your Linux and Windows systems should be set up and ready for the USB device sharing script to be run. The devices on the Linux system will be accessible on the Windows system, and you'll be able to use them as if they were connected directly.
___

# To install the Python script named "usb_transfer.py" to run at the start of a Steam Link booting up and remain running even if you open another application, you can follow these steps:

## Connect to your Steam Link device via SSH. You can do this by enabling the developer options on your Steam Link and using an SSH client to connect to the device.

### Create a new systemd service file by running the following command:
sudo nano /etc/systemd/system/usb_transfer.service

## In the nano editor, add the following lines to the service file:
```
[Unit]
Description=USB Transfer Python Script

[Service]
ExecStart=/usr/bin/python3 /path/to/usb_transfer.py
Restart=always
User=steamlink
WorkingDirectory=/path/to/
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=usb_transfer

[Install]
WantedBy=multi-user.target
```

### Replace /path/to/ with the actual path to your Python script.
```
Save and close the nano editor by pressing Ctrl+X, then Y, and then Enter.
```
### Reload the systemd daemon by running the following command:
```bash
sudo systemctl daemon-reload
```
## Enable the new service to start on boot by running the following command:
```bash
sudo systemctl enable usb_transfer.service
```
## Start the service by running the following command:
```bash
sudo systemctl start usb_transfer.service
```
## The USB Transfer Python script should now start running at the start of the Steam Link booting up and remain running even if you open another application. You can check the status of the service by running the following command:
```bash
sudo systemctl status usb_transfer.service
```
