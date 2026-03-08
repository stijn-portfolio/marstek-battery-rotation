#!/usr/bin/env python3
"""
Test de "wake-up" theorie: eerste request wekt de batterij,
tweede request krijgt antwoord.
"""

import socket
import json
import time

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80"},
    {"name": "Fase B", "ip": "192.168.6.213"},
    {"name": "Fase C", "ip": "192.168.6.144"},
]
PORT = 30000

def test_with_wakeup(name, ip):
    """Test met wake-up request."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)  # Korte timeout voor wake-up
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))

    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    message = json.dumps(request).encode()

    # Wake-up request (verwacht geen antwoord)
    print(f"\n{name} ({ip}):")
    print("  [1] Wake-up request...", end=" ")
    sock.sendto(message, (ip, PORT))

    try:
        data, _ = sock.recvfrom(65535)
        print(f"ANTWOORD (onverwacht!)")
        wakeup_worked = True
    except socket.timeout:
        print("timeout (verwacht)")
        wakeup_worked = False

    # Wacht even
    time.sleep(0.3)

    # Echte request
    sock.settimeout(3.0)
    request["id"] = 2
    print("  [2] Echte request...", end=" ")
    start = time.time()
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, _ = sock.recvfrom(65535)
        elapsed = (time.time() - start) * 1000
        response = json.loads(data.decode())
        if "result" in response:
            print(f"SUCCESS ({elapsed:.0f}ms) - {response['result'].get('device')}")
            real_worked = True
        else:
            print(f"ERROR: {response}")
            real_worked = False
    except socket.timeout:
        print("TIMEOUT")
        real_worked = False

    sock.close()
    return wakeup_worked, real_worked

print("=" * 60)
print("WAKE-UP THEORIE TEST")
print("=" * 60)
print("Theorie: eerste request wekt batterij, tweede krijgt antwoord")

# Wacht eerst 10 seconden zodat batterijen in idle gaan
print("\nWachten 10 seconden zodat batterijen in idle gaan...")
time.sleep(10)

print("\nTest na lange idle periode:")
for bat in BATTERIES:
    wakeup, real = test_with_wakeup(bat["name"], bat["ip"])
    time.sleep(1)

print("\n" + "-" * 60)
print("Direct opnieuw testen (batterijen nu wakker):")
for bat in BATTERIES:
    wakeup, real = test_with_wakeup(bat["name"], bat["ip"])
    time.sleep(1)

print("\n" + "=" * 60)
