import cv2
import pyaudio
import socket
import struct
import sys
import time
import threading
import numpy as np
from zeroconf import Zeroconf, ServiceInfo
import evdev
from evdev import ecodes, InputDevice
from selectors import DefaultSelector, EVENT_READ

# Constants
IP_ADDRESS = '0.0.0.0'
PORT = 12345
AUDIO_CHUNK_SIZE = 1024
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480

def transfer_audio_stream(audio_device_index):
    # Create a PyAudio object for audio stream capture
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16,
                        channels=2,
                        rate=44100,
                        input=True,
                        frames_per_buffer=AUDIO_CHUNK_SIZE,
                        input_device_index=audio_device_index)

    # Create a socket for audio stream transfer
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((IP_ADDRESS, PORT + 1))

        while True:
            data = stream.read(AUDIO_CHUNK_SIZE)
            data_len = len(data)
            sock.sendall(struct.pack('>I', data_len))
            sock.sendall(data)

def transfer_video_stream(camera_device_index):
    # Open a video capture object for webcam video stream capture
    cap = cv2.VideoCapture(camera_device_index)

    # Create a socket for video stream transfer
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((IP_ADDRESS, PORT + 2))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buffer = cv2.imencode('.jpg', frame)
            data = buffer.tobytes()
            data_len = len(data)
            sock.sendall(struct.pack('>I', data_len))
            sock.sendall(data)

def transfer_input_devices():
    # Find USB keyboard and mouse devices
    devices = [InputDevice(path) for path in evdev.list_devices()]
    keyboard = None
    mouse = None

    for device in devices:
        if 'keyboard' in device.name.lower():
            keyboard = device
        if 'mouse' in device.name.lower():
            mouse = device
        if keyboard and mouse:
            break

    if not keyboard and not mouse:
        print("No USB keyboard or mouse found.")
        return

    # Create a socket to transfer data
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((IP_ADDRESS, PORT))

        # Register input devices with a selector
        selector = DefaultSelector()
        if keyboard:
            selector.register(keyboard, EVENT_READ)
        if mouse:
            selector.register(mouse, EVENT_READ)

        while True:
            for key, mask in selector.select():
                device = key.fileobj
                event = device.read_one()

                if event.type == evdev.ecodes.EV_KEY:  # Keyboard events
                    device_type = 0x01
                    event_type = 0x01 if event.value == 1 else 0x02
                    data = struct.pack('>BBh', device_type, event_type, event.code)
                    sock.sendall(data)

                if event.type == evdev.ecodes.EV_REL:  # Mouse events
                    if event.code in (ecodes.REL_X, ecodes.REL_Y):
                        device_type = 0x02
                        event_type = 0x03  # Move
                        button = 0x00
                        x, y = mouse.position()
                        data = struct.pack('>BBhii', device_type, event_type, button, x, y)
                        sock.sendall(data)

                if event.type == evdev.ecodes.EV_BTN:  # Mouse button events
                    device_type = 0x02
                    event_type = 0x01 if event.value == 1 else 0x02
                    button = event.code - ecodes.BTN_MOUSE
                    x, y = mouse.position()
                    data = struct.pack('>BBhii', device_type, event_type, button, x, y)
                    sock.sendall(data)

def main():
    audio_device_index = int(sys.argv[1])
    camera_device_index = int(sys.argv[2])

    # Threads for transferring audio and video streams
    audio_thread = threading.Thread(target=transfer_audio_stream, args=(audio_device_index,))
    video_thread = threading.Thread(target=transfer_video_stream, args=(camera_device_index,))
    input_devices_thread = threading.Thread(target=transfer_input_devices)

    audio_thread.start()
    video_thread.start()
    input_devices_thread.start()

    # Bonjour service registration
    service_type = "_usb_transfer._tcp.local."
    service_name = f"USB_Transfer_Service_{socket.gethostname()}._usb_transfer._tcp.local."

    zeroconf = Zeroconf()
    service_info = ServiceInfo(
        type_=service_type,
        name=service_name,
        addresses=[socket.inet_aton(IP_ADDRESS)],
        port=PORT,
        properties={},
        server=f"{socket.gethostname()}.local.",
    )

    zeroconf.register_service(service_info)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(service_info)
        zeroconf.close()

if __name__ == '__main__':
    main()

