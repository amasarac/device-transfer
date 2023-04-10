import socket
import ssl
import pyaudio
import cv2
import numpy as np
import struct
import json
import ctypes
import platform
import os
import psutil
import win32file
import win32net
import win32wnet
from typing import Optional
from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo, ServiceListener

AUDIO_PORT = 8000
VIDEO_PORT = 8001
INPUT_DEVICES_PORT = 8002
CERT_FILE = "cert.pem"

class MyListener:
    def __init__(self):
        self.services = []

    def remove_service(self, zeroconf, service_type, name):
        self.services.remove(name)

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        self.services.append(info)

class CustomServiceListener(ServiceListener):

    def __init__(self):
        self.service_info: Optional[ServiceInfo] = None

    def remove_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        self.service_info = zeroconf.get_service_info(type_, name)
        print(f"Service {name} added, service info: {self.service_info}")

    def update_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        self.service_info = zeroconf.get_service_info(type_, name)
        print(f"Service {name} updated, service info: {self.service_info}")


def get_service_info(zeroconf: Zeroconf, service_type: str):
    listener = CustomServiceListener()
    browser = zeroconf.add_service_listener(service_type, listener)

    # Waiting for the listener to receive service information
    while listener.service_info is None:
        pass

    zeroconf.remove_service_listener(browser)
    return listener.service_info        
        
def save_cert(cert_data):
    with open(CERT_FILE, "wb") as cert_file:
        cert_file.write(cert_data)

def connect_service(service_info, port):
    address = socket.inet_ntoa(service_info.addresses[0])
    sock = socket.create_connection((address, port))

    if port != 445:  # Do not wrap SAMBA connection in SSL
        sock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ca_certs=CERT_FILE, server_side=False)

    return sock

def receive_audio_stream():
    zeroconf = Zeroconf()
    service_type = "_audio._tcp.local."
    service_info = get_service_info(zeroconf, service_type)
    zeroconf.close()

    sock = connect_service(service_info, AUDIO_PORT)

    p = pyaudio.PyAudio()
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

    try:
        while True:
            data_len = struct.unpack('<L', sock.recv(4))[0]
            data = sock.recv(data_len)
            stream.write(data)
    except (BrokenPipeError, ConnectionResetError, OSError):
        print("Audio stream disconnected")

    stream.stop_stream()
    stream.close()
    p.terminate()
    sock.close()

def receive_video_stream():
    zeroconf = Zeroconf()
    service_type = "_video._tcp.local."
    service_info = get_service_info(zeroconf, service_type)
    zeroconf.close()

    sock = connect_service(service_info, VIDEO_PORT)

    try:
        while True:
            # Receive the size of the frame
            data_len = struct.unpack('<L', sock.recv(4))[0]
            data = sock.recv(data_len)
            frame = np.frombuffer(data, dtype=np.uint8).reshape((240, 320, 3))
            cv2.imshow('USB Video Stream', frame)
            if cv2.waitKey(1) == ord('q'):
                break
    except (BrokenPipeError, ConnectionResetError, OSError):
        print("Video stream disconnected")

    cv2.destroyAllWindows()
    sock.close()

def receive_input_devices():
    zeroconf = Zeroconf()
    service_type = "_input._tcp.local."
    service_info = get_service_info(zeroconf, service_type)
    zeroconf.close()

    sock = connect_service(service_info, INPUT_DEVICES_PORT)

    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break

            input_data = json.loads(data.decode('utf-8'))
            event_type = input_data['type']
            event = input_data['event']

            # Key down
            if event_type == "key" and event == "down":
                key_code = int(input_data['key_code'])
                win32api.keybd_event(key_code, 0, 0, 0)

            # Key up
            elif event_type == "key" and event == "up":
                key_code = int(input_data['key_code'])
                win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Mouse move
            elif event_type == "mouse" and event == "move":
                x, y = input_data['x'], input_data['y']
                ctypes.windll.user32.SetCursorPos(x, y)

            # Mouse click
            elif event_type == "mouse" and event == "click":
                x, y = input_data['x'], input_data['y']
                button = input_data['button']
                pressed = input_data['pressed']
                if button == "left":
                    button_event = win32con.MOUSEEVENTF_LEFTDOWN if pressed else win32con.MOUSEEVENTF_LEFTUP
                elif button == "right":
                    button_event = win32con.MOUSEEVENTF_RIGHTDOWN if pressed else win32con.MOUSEEVENTF_RIGHTUP
                elif button == "middle":
                    button_event = win32con.MOUSEEVENTF_MIDDLEDOWN if pressed else win32con.MOUSEEVENTF_MIDDLEUP
                ctypes.windll.user32.mouse_event(button_event, x, y, 0, 0)

            # Mouse scroll
            elif event_type == "mouse" and event == "scroll":
                x, y = input_data['x'], input_data['y']
                dx, dy = input_data['dx'], input_data['dy']
                ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_WHEEL, x, y, int(dy * 120), 0)

        except (BrokenPipeError, ConnectionResetError, OSError):
            print("Input devices disconnected")
            break

    sock.close()

def mount_shared_drive():
    zeroconf = Zeroconf()
    service_type = "_smb._tcp.local."
    service_info = get_service_info(zeroconf, service_type)
    zeroconf.close()

    address = socket.inet_ntoa(service_info.addresses[0])
    unc_path = f"\\\\{address}\\{service_info.name}"

    for letter in range(ord("Z"), ord("A") - 1, -1):
        drive_letter = chr(letter) + ":"
        try:
            win32file.GetDiskFreeSpaceEx(drive_letter)
        except OSError:
            break

    win32wnet.WNetAddConnection2(win32net.RESOURCETYPE_DISK, drive_letter, unc_path, None, None, None)

if __name__ == "__main__":
    zeroconf = Zeroconf()
    service_type = "_bonjour._tcp.local."
    service_info = get_service_info(zeroconf, service_type)
    zeroconf.close()

    cert_data = ssl.PEM_cert_to_DER_cert(service_info.text[0].encode())
    save_cert(cert_data)

    audio_thread = threading.Thread(target=receive_audio_stream)
    audio_thread.start()

    video_thread = threading.Thread(target=receive_video_stream)
    video_thread.start()

    input_devices_thread = threading.Thread(target=receive_input_devices)
    input_devices_thread.start()

    mount_shared_drive()

    audio_thread.join()
    video_thread.join()
    input_devices_thread.join()
