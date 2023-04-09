import cv2
import pyaudio
import socket
import struct
import threading
import time
import numpy as np
from zeroconf import Zeroconf, ServiceBrowser
import socket
import pyvjoy
import sys
import ctypes

# Constants
IP_ADDRESS = '0.0.0.0'
PORT = 12345
AUDIO_CHUNK_SIZE = 1024
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480

class USBTransferListener:
    def __init__(self):
        self.found_service = None
        self.cv = threading.Condition()

    def remove_service(self, zeroconf, service_type, service_name):
        pass

    def update_service(self, zeroconf, service_type, service_name):
        pass

    def add_service(self, zeroconf, service_type, service_name):
        info = zeroconf.get_service_info(service_type, service_name)
        with self.cv:
            self.found_service = info
            self.cv.notify_all()

def receive_audio_stream():
    # Create a PyAudio object for audio stream output
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16,
                        channels=2,
                        rate=44100,
                        output=True)

    # Create a socket for audio stream reception
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((IP_ADDRESS, PORT + 1))
        sock.listen(1)
        conn, addr = sock.accept()

        while True:
            data_len = conn.recv(4)
            if not data_len:
                break
            data_len = struct.unpack('>I', data_len)[0]
            data = conn.recv(data_len)
            stream.write(data)

def receive_video_stream():
    # Create a window to display the video stream
    cv2.namedWindow('Video Stream', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Video Stream', VIDEO_WIDTH, VIDEO_HEIGHT)

    # Create a socket for video stream reception
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((IP_ADDRESS, PORT + 2))
        sock.listen(1)
        conn, addr = sock.accept()

        while True:
            data_len = conn.recv(4)
            if not data_len:
                break
            data_len = struct.unpack('>I', data_len)[0]
            data = conn.recv(data_len)
            np_data = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_data, 1)
            cv2.imshow('Video Stream', frame)
            if cv2.waitKey(1) == 27:  # Escape key
                break

def receive_input_devices():
    # Create a virtual joystick object
    joystick = pyvjoy.VJoyDevice(1)

    # Create a socket for input device reception
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((IP_ADDRESS, PORT))
        sock.listen(1)
        conn, addr = sock.accept()

        while True:
            data = conn.recv(12)
            if not data:
                break
            device_type, event_type, event_code, *args = struct.unpack('>BBhii', data)

            if device_type == 0x01:  # Keyboard events
                if event_type == 0x01:  # Key down
                    ctypes.windll.user32.keybd_event(event_code, 0, 0, 0)
                elif event_type == 0x02:  # Key up
                    ctypes.windll.user32.keybd_event(event_code, 0, 0x0002, 0)

            elif device_type == 0x02:  # Mouse events
                if event_type == 0x01:  # Button down
                    ctypes.windll.user32.mouse_event(0x0002 if event_code == 0 else 0x0010, 0, 0, 0, 0)
                elif event_type == 0x02:  # Button up
                    ctypes.windll.user32.mouse_event(0x0004 if event_code == 0 else 0x0020, 0, 0, 0, 0)
                elif event_type == 0x03:  # Move
                    x, y = args
                    ctypes.windll.user32.SetCursorPos(x, y)

def main():
    listener = USBTransferListener()
    zeroconf = Zeroconf()
    service_browser = ServiceBrowser(zeroconf, "_usb_transfer._tcp.local.", listener)

    with listener.cv:
        while not listener.found_service:
            listener.cv.wait()

    linux_service = listener.found_service
    IP_ADDRESS = socket.inet_ntoa(linux_service.addresses[0])
    PORT = linux_service.port

    # Threads for receiving audio and video streams
    audio_thread = threading.Thread(target=receive_audio_stream)
    video_thread = threading.Thread(target=receive_video_stream)
    input_devices_thread = threading.Thread(target=receive_input_devices)

    audio_thread.start()
    video_thread.start()
    input_devices_thread.start()

    audio_thread.join()
    video_thread.join()
    input_devices_thread.join()

    zeroconf.close()

if __name__ == '__main__':
    main()

