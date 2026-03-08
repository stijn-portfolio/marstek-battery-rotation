#!/usr/bin/env python3
"""Quick connectivity test voor alle batterijen."""

import socket
import json
import time

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80"},
    {"name": "Fase B", "ip": "192.168.6.213"},
    {"name": "Fase C", "ip": "192.168.6.144"},
]
PORT = 30000

def test_battery(name, ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind(("0.0.0.0", PORT))
    except:
        pass

    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, _ = sock.recvfrom(65535)
        response = json.loads(data.decode())
        if "result" in response:
            r = response["result"]
            print(f"{name} ({ip}): OK - {r.get('device')} v{r.get('ver')}")
            return True
        elif "error" in response:
            print(f"{name} ({ip}): ERROR - {response['error']}")
            return False
    except socket.timeout:
        print(f"{name} ({ip}): TIMEOUT - niet bereikbaar")
        return False
    finally:
        sock.close()

print("Connectivity test...")
print("-" * 50)
for bat in BATTERIES:
    test_battery(bat["name"], bat["ip"])
    time.sleep(0.5)
