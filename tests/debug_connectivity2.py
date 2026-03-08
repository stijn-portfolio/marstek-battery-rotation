#!/usr/bin/env python3
"""
Debug met langere pauzes en grotere timeout.
"""

import socket
import json
import time
from datetime import datetime

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80"},
    {"name": "Fase B", "ip": "192.168.6.213"},
    {"name": "Fase C", "ip": "192.168.6.144"},
]
PORT = 30000
TIMEOUT = 5.0  # Langere timeout
PAUSE = 2.0    # Langere pauze tussen tests
TESTS = 3

def test_battery(name, ip, request_id):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))

    request = {"id": request_id, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    message = json.dumps(request).encode()

    # Stuur request
    start = time.time()
    sock.sendto(message, (ip, PORT))

    # Verzamel ALLE responses (soms komen er meerdere)
    responses = []
    while True:
        try:
            remaining = TIMEOUT - (time.time() - start)
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            data, addr = sock.recvfrom(65535)
            elapsed = (time.time() - start) * 1000
            responses.append({
                "data": data.decode(),
                "from": addr,
                "latency": elapsed
            })
        except socket.timeout:
            break

    sock.close()
    return responses

print("=" * 70)
print(f"CONNECTIVITY DEBUG v2 - {datetime.now().strftime('%H:%M:%S')}")
print(f"Timeout: {TIMEOUT}s, Pause: {PAUSE}s")
print("=" * 70)

request_id = 0

for bat in BATTERIES:
    print(f"\n=== {bat['name']} ({bat['ip']}) ===")

    for i in range(TESTS):
        request_id += 1
        print(f"\n  Test {i+1}:")
        responses = test_battery(bat["name"], bat["ip"], request_id)

        if not responses:
            print(f"    -> GEEN RESPONSE (timeout na {TIMEOUT}s)")
        else:
            for j, r in enumerate(responses):
                print(f"    Response {j+1} ({r['latency']:.0f}ms) from {r['from']}:")
                try:
                    parsed = json.loads(r['data'])
                    if "result" in parsed:
                        print(f"      SUCCESS: {parsed['result'].get('device')} v{parsed['result'].get('ver')}")
                    elif "error" in parsed:
                        print(f"      ERROR: {parsed['error']}")
                    else:
                        print(f"      UNKNOWN: {parsed}")
                except:
                    print(f"      RAW: {r['data'][:100]}")

        time.sleep(PAUSE)

print("\n" + "=" * 70)
