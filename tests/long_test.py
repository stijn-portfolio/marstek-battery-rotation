#!/usr/bin/env python3 -u
"""
Lange test met 5 minuten pauze tussen batterijen.
Test elke batterij 5x geïsoleerd.
"""

import socket
import json
import time
import sys
from datetime import datetime

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80"},
    {"name": "Fase B", "ip": "192.168.6.213"},
    {"name": "Fase C", "ip": "192.168.6.144"},
]
PORT = 30000
PAUSE_BETWEEN_BATTERIES = 300  # 5 minuten
TESTS_PER_BATTERY = 5
PAUSE_BETWEEN_TESTS = 2  # 2 seconden tussen tests naar dezelfde batterij

def test(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(5.0)
    try:
        sock.bind(("0.0.0.0", PORT))
    except:
        time.sleep(0.5)
        try:
            sock.bind(("0.0.0.0", PORT))
        except:
            sock.close()
            return False, 0

    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    start = time.time()
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, _ = sock.recvfrom(65535)
        elapsed = (time.time() - start) * 1000
        sock.close()
        response = json.loads(data.decode())
        return "result" in response, elapsed
    except:
        sock.close()
        return False, 0

def countdown(seconds, message):
    """Countdown timer met updates."""
    print(f"\n{message}")
    for remaining in range(seconds, 0, -30):
        print(f"  ... {remaining} seconden remaining ({datetime.now().strftime('%H:%M:%S')})")
        time.sleep(min(30, remaining))

print("=" * 70)
print(f"LANGE GEÏSOLEERDE TEST - Start: {datetime.now().strftime('%H:%M:%S')}")
print(f"Pauze tussen batterijen: {PAUSE_BETWEEN_BATTERIES}s (5 min)")
print(f"Tests per batterij: {TESTS_PER_BATTERY}")
print("=" * 70)

results = {}

for bat in BATTERIES:
    print(f"\n{'='*70}")
    print(f"TESTING: {bat['name']} ({bat['ip']})")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    successes = 0
    latencies = []

    for i in range(TESTS_PER_BATTERY):
        ok, latency = test(bat["ip"])
        if ok:
            successes += 1
            latencies.append(latency)
            print(f"  Test {i+1}/{TESTS_PER_BATTERY}: OK ({latency:.0f}ms)")
        else:
            print(f"  Test {i+1}/{TESTS_PER_BATTERY}: FAIL")

        if i < TESTS_PER_BATTERY - 1:
            time.sleep(PAUSE_BETWEEN_TESTS)

    rate = 100 * successes / TESTS_PER_BATTERY
    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    results[bat["name"]] = {"success": successes, "total": TESTS_PER_BATTERY, "rate": rate, "avg_lat": avg_lat}

    print(f"\n  RESULTAAT {bat['name']}: {successes}/{TESTS_PER_BATTERY} ({rate:.0f}%) avg={avg_lat:.0f}ms")

    # Wacht 5 minuten voor volgende batterij (behalve na de laatste)
    if bat != BATTERIES[-1]:
        countdown(PAUSE_BETWEEN_BATTERIES, f"Wachten {PAUSE_BETWEEN_BATTERIES}s voor volgende batterij...")

print("\n" + "=" * 70)
print(f"EINDRESULTAAT - {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)
for name, data in results.items():
    print(f"  {name}: {data['success']}/{data['total']} ({data['rate']:.0f}%) avg={data['avg_lat']:.0f}ms")

total_success = sum(d["success"] for d in results.values())
total_tests = sum(d["total"] for d in results.values())
print(f"\n  TOTAAL: {total_success}/{total_tests} ({100*total_success/total_tests:.0f}%)")
print("=" * 70)
