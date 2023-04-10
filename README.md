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
