#!/usr/bin/env python3
"""
Test: Socket recyclen na elke request (maar op dezelfde port).
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

def single_request_recycle(ip, request_id, timeout=3.0):
    """Maak nieuwe socket, stuur request, ontvang antwoord, sluit socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    try:
        sock.bind(("0.0.0.0", PORT))
    except OSError as e:
        # Wacht even en probeer opnieuw
        time.sleep(0.2)
        try:
            sock.bind(("0.0.0.0", PORT))
        except OSError:
            sock.close()
            return None, "PORT_BUSY"

    request = {"id": request_id, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    start = time.time()
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, addr = sock.recvfrom(65535)
        elapsed = (time.time() - start) * 1000
        response = json.loads(data.decode())
        sock.close()
        return elapsed, response
    except socket.timeout:
        sock.close()
        return None, "TIMEOUT"
    except Exception as e:
        sock.close()
        return None, str(e)

print("=" * 60)
print("SOCKET RECYCLE TEST")
print("Nieuwe socket per request, minimale pauze")
print("=" * 60)

request_id = 0
results = {"A": [], "B": [], "C": []}

for round_num in range(5):
    print(f"\n--- Round {round_num + 1} ---")

    for i, bat in enumerate(BATTERIES):
        request_id += 1
        latency, result = single_request_recycle(bat["ip"], request_id)

        key = ["A", "B", "C"][i]
        if latency is not None and "result" in result:
            print(f"{bat['name']}: OK ({latency:.0f}ms)")
            results[key].append(True)
        else:
            print(f"{bat['name']}: FAIL")
            results[key].append(False)

        time.sleep(0.1)  # Minimale pauze

    time.sleep(0.5)

print("\n" + "=" * 60)
print("SAMENVATTING:")
for key in ["A", "B", "C"]:
    success = sum(results[key])
    total = len(results[key])
    print(f"  Fase {key}: {success}/{total} ({100*success//total}%)")
print("=" * 60)
