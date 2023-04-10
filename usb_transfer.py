import cv2
import pyaudio
import socket
import ssl
import struct
import sys
import time
import threading
import numpy as np
from zeroconf import Zeroconf, ServiceInfo
import evdev
from evdev import ecodes, InputDevice
from selectors import DefaultSelector, EVENT_READ
import os
import tempfile
from OpenSSL import crypto

# Constants
IP_ADDRESS = "0.0.0.0"  # Change this to your Linux machine's IP address
AUDIO_PORT = 8000
VIDEO_PORT = 8001
INPUT_DEVICES_PORT = 8002

# Added for Samba share
SAMBA_PORT = 445

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

def generate_self_signed_cert():
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "California"
    cert.get_subject().L = "San Francisco"
    cert.get_subject().O = "Example"
    cert.get_subject().OU = "USB Transfer"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, "sha256")

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        key_file = f.name

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        cert_file = f.name

    return key_file, cert_file

def register_audio_stream():
    zeroconf = Zeroconf()
    service_type = "_audio._tcp.local."
    name = "USB Audio Stream"
    port = AUDIO_PORT
    service_info = ServiceInfo(service_type, f"{name}.{service_type}", addresses=[socket.inet_aton(IP_ADDRESS)], port=port)
    zeroconf.register_service(service_info)
    return zeroconf, service_info

def register_video_stream():
    zeroconf = Zeroconf()
    service_type = "_video._tcp.local."
    name = "USB Video Stream"
    port = VIDEO_PORT
    service_info = ServiceInfo(service_type, f"{name}.{service_type}", addresses=[socket.inet_aton(IP_ADDRESS)], port=port)
    zeroconf.register_service(service_info)
    return zeroconf, service_info

def register_input_devices():
    zeroconf = Zeroconf()
    service_type = "_input._tcp.local."
    name = "USB Input Devices"
    port = INPUT_DEVICES_PORT
    service_info = ServiceInfo(service_type, f"{name}.{service_type}", addresses=[socket.inet_aton(IP_ADDRESS)], port=port)
    zeroconf.register_service(service_info)
    return zeroconf, service_info

# New function for registering the Samba share using Zeroconf
def register_samba_share():
    zeroconf = Zeroconf()
    service_type = "_smb._tcp.local."
    name = "USB Drive Share"
    port = SAMBA_PORT
    service_info = ServiceInfo(service_type, f"{name}.{service_type}", addresses=[socket.inet_aton(IP_ADDRESS)], port=port, properties={"path": "/media/usb"})
    zeroconf.register_service(service_info)

    return zeroconf, service_info

def transfer_audio_stream():
    # Set up audio stream
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=2,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024)

    # Create a secure socket for audio streaming
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((IP_ADDRESS, AUDIO_PORT))
    sock.listen(1)
    print(f"Listening for audio on {IP_ADDRESS}:{AUDIO_PORT}")

    conn, address = sock.accept()
    print(f"Accepted connection from {address}")

    conn = ssl.wrap_socket(conn, keyfile=KEY_FILE, certfile=CERT_FILE, server_side=True)

    # Stream audio to the connected client
    try:
        while True:
            data = stream.read(1024)
            conn.sendall(data)
    except (BrokenPipeError, ConnectionResetError, OSError):
        print("Audio stream disconnected")

    stream.stop_stream()
    stream.close()
    p.terminate()
    conn.close()
    sock.close()

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((IP_ADDRESS, INPUT_DEVICES_PORT))
    sock.listen(1)
    print(f"Listening for input devices on {IP_ADDRESS}:{INPUT_DEVICES_PORT}")

    conn, address = sock.accept()
    print(f"Accepted connection from {address}")

    conn = ssl.wrap_socket(conn, keyfile=KEY_FILE, certfile=CERT_FILE, server_side=True)

    def on_press(key):
        try:
            key_data = {'type': 'key', 'event': 'down', 'key_code': key.vk}
            conn.sendall(json.dumps(key_data).encode('utf-8') + b'\n')
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def on_release(key):
        try:
            key_data = {'type': 'key', 'event': 'up', 'key_code': key.vk}
            conn.sendall(json.dumps(key_data).encode('utf-8') + b'\n')
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def on_move(x, y):
        try:
            mouse_data = {'type': 'mouse', 'event': 'move', 'x': x, 'y': y}
            conn.sendall(json.dumps(mouse_data).encode('utf-8') + b'\n')
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def on_click(x, y, button, pressed):
        try:
            button_data = {'type': 'mouse', 'event': 'click', 'x': x, 'y': y, 'button': str(button), 'pressed': pressed}
            conn.sendall(json.dumps(button_data).encode('utf-8') + b'\n')
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def on_scroll(x, y, dx, dy):
        try:
            scroll_data = {'type': 'mouse', 'event': 'scroll', 'x': x, 'y': y, 'dx': dx, 'dy': dy}
            conn.sendall(json.dumps(scroll_data).encode('utf-8') + b'\n')
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    with keyboard.Listener(on_press=on_press, on_release=on_release) as keyboard_listener, mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as mouse_listener:
        keyboard_listener.join()
        mouse_listener.join()

    conn.close()
    sock.close()

def generate_self_signed_cert():
    CERT_FILE = "cert.pem"
    KEY_FILE = "key.pem"
    
def main():
    generate_self_signed_cert()

    # Register services
    zeroconf_audio, service_info_audio = register_audio_stream()
    zeroconf_video, service_info_video = register_video_stream()
    zeroconf_input, service_info_input = register_input_devices()

    # New line to register the Samba share
    zeroconf_samba, service_info_samba = register_samba_share()

    transfer_audio_stream()
    transfer_video_stream(0)
    transfer_input_devices()

    # Unregister services before exiting
    zeroconf_audio.unregister_service(service_info_audio)
    zeroconf_video.unregister_service(service_info_video)
    zeroconf_input.unregister_service(service_info_input)

    # New line to unregister the Samba share
    zeroconf_samba.unregister_service(service_info_samba)

    zeroconf_audio.close()
    zeroconf_video.close()
    zeroconf_input.close()
    zeroconf_samba.close()

if __name__ == '__main__':
    main()

