#!/usr/bin/env python3
"""
Test met langere pauzes tussen requests.
"""

import socket
import json
import time
import select

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80"},
    {"name": "Fase B", "ip": "192.168.6.213"},
    {"name": "Fase C", "ip": "192.168.6.144"},
]
PORT = 30000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", PORT))
sock.setblocking(False)

def drain_buffer():
    while True:
        ready, _, _ = select.select([sock], [], [], 0.01)
        if not ready:
            break
        try:
            sock.recvfrom(65535)
        except:
            break

def send_and_receive(ip, request_id, timeout=5.0):
    drain_buffer()

    request = {"id": request_id, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    start = time.time()
    while time.time() - start < timeout:
        ready, _, _ = select.select([sock], [], [], 0.1)
        if ready:
            try:
                data, addr = sock.recvfrom(65535)
                response = json.loads(data.decode())
                if response.get("id") == request_id and addr[0] == ip:
                    elapsed = (time.time() - start) * 1000
                    return elapsed, response
            except:
                pass
    return None, "TIMEOUT"

print("=" * 60)
print("SLOW SEQUENCE TEST")
print("3 seconden pauze tussen elke request")
print("=" * 60)

request_id = 0

for round_num in range(2):
    print(f"\n--- Round {round_num + 1} ---")

    for bat in BATTERIES:
        request_id += 1
        print(f"Testing {bat['name']}...", end=" ", flush=True)
        latency, result = send_and_receive(bat["ip"], request_id)

        if latency is not None and "result" in result:
            print(f"OK ({latency:.0f}ms)")
        else:
            print(f"FAIL: {result if isinstance(result, str) else result}")

        print("   Waiting 3 seconds...")
        time.sleep(3)

sock.close()
print("\n" + "=" * 60)
