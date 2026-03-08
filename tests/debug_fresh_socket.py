#!/usr/bin/env python3
"""
Test met verse socket per request - sluit socket direct na ontvangst.
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

def single_request(ip, timeout=3.0):
    """Eén request met verse socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind(("0.0.0.0", PORT))
    except OSError:
        # Port bezet, wacht en probeer opnieuw
        time.sleep(0.5)
        try:
            sock.bind(("0.0.0.0", PORT))
        except:
            sock.close()
            return None, "PORT_BUSY"

    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}

    start = time.time()
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, addr = sock.recvfrom(65535)
        elapsed = (time.time() - start) * 1000
        sock.close()
        return elapsed, json.loads(data.decode())
    except socket.timeout:
        sock.close()
        return None, "TIMEOUT"
    except Exception as e:
        sock.close()
        return None, str(e)

print("=" * 60)
print("FRESH SOCKET PER REQUEST TEST")
print("=" * 60)

for round_num in range(3):
    print(f"\n--- Round {round_num + 1} ---")

    for bat in BATTERIES:
        # Wacht even zodat socket vrijkomt
        time.sleep(0.3)

        latency, result = single_request(bat["ip"])

        if latency is not None:
            if "result" in result:
                device = result["result"].get("device", "?")
                print(f"{bat['name']}: OK ({latency:.0f}ms) - {device}")
            else:
                print(f"{bat['name']}: ERROR - {result}")
        else:
            print(f"{bat['name']}: {result}")

    # Pauze tussen rounds
    time.sleep(2)

print("\n" + "=" * 60)
