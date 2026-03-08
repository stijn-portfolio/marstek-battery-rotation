#!/usr/bin/env python3
"""
Uitgebreide verificatie van de hypothese:
1. Verse socket + pauze = 100% success
2. Verse socket + geen pauze = lager success
3. Persistent socket = laagste success

Test elke configuratie 10 keer per batterij.
"""

import socket
import json
import time
import select
from datetime import datetime

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80"},
    {"name": "Fase B", "ip": "192.168.6.213"},
    {"name": "Fase C", "ip": "192.168.6.144"},
]
PORT = 30000
TESTS_PER_CONFIG = 10

def fresh_socket_request(ip, timeout=3.0):
    """Verse socket per request."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    try:
        sock.bind(("0.0.0.0", PORT))
    except OSError:
        time.sleep(0.3)
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

class PersistentSocket:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", PORT))
        self.sock.setblocking(False)
        self.request_id = 0

    def drain(self):
        while True:
            ready, _, _ = select.select([self.sock], [], [], 0.01)
            if not ready:
                break
            try:
                self.sock.recvfrom(65535)
            except:
                break

    def request(self, ip, timeout=3.0):
        self.drain()
        self.request_id += 1
        request = {"id": self.request_id, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
        start = time.time()
        self.sock.sendto(json.dumps(request).encode(), (ip, PORT))

        while time.time() - start < timeout:
            ready, _, _ = select.select([self.sock], [], [], 0.1)
            if ready:
                try:
                    data, addr = self.sock.recvfrom(65535)
                    response = json.loads(data.decode())
                    if response.get("id") == self.request_id and addr[0] == ip:
                        elapsed = (time.time() - start) * 1000
                        return "result" in response, elapsed
                except:
                    pass
        return False, 0

    def close(self):
        self.sock.close()

def run_test_config(name, test_func, pause_between):
    """Run een test configuratie."""
    print(f"\n{'='*60}")
    print(f"CONFIG: {name}")
    print(f"{'='*60}")

    results = {bat["name"]: {"success": 0, "total": 0, "latencies": []} for bat in BATTERIES}

    for round_num in range(TESTS_PER_CONFIG):
        print(f"  Round {round_num + 1}/{TESTS_PER_CONFIG}: ", end="", flush=True)
        round_results = []

        for bat in BATTERIES:
            success, latency = test_func(bat["ip"])
            results[bat["name"]]["total"] += 1
            if success:
                results[bat["name"]]["success"] += 1
                results[bat["name"]]["latencies"].append(latency)
                round_results.append("OK")
            else:
                round_results.append("--")

            if pause_between > 0:
                time.sleep(pause_between)

        print(f"A={round_results[0]} B={round_results[1]} C={round_results[2]}")
        time.sleep(0.2)  # Kleine pauze tussen rounds

    # Samenvatting
    print(f"\n  RESULTAAT {name}:")
    total_success = 0
    total_tests = 0
    for bat_name, data in results.items():
        rate = 100 * data["success"] / data["total"] if data["total"] > 0 else 0
        avg_lat = sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0
        print(f"    {bat_name}: {data['success']}/{data['total']} ({rate:.0f}%) avg={avg_lat:.0f}ms")
        total_success += data["success"]
        total_tests += data["total"]

    overall_rate = 100 * total_success / total_tests if total_tests > 0 else 0
    print(f"    TOTAAL: {total_success}/{total_tests} ({overall_rate:.0f}%)")

    return overall_rate

def main():
    print("=" * 60)
    print(f"HYPOTHESE VERIFICATIE - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    print(f"Tests per configuratie: {TESTS_PER_CONFIG} rounds x 3 batterijen")

    results = {}

    # Config 1: Verse socket + 0.5s pauze (verwacht: ~100%)
    results["Fresh+Pause"] = run_test_config(
        "Verse socket + 0.5s pauze",
        fresh_socket_request,
        pause_between=0.5
    )

    time.sleep(2)

    # Config 2: Verse socket + geen pauze (verwacht: ~60-80%)
    results["Fresh+NoPause"] = run_test_config(
        "Verse socket + GEEN pauze",
        fresh_socket_request,
        pause_between=0
    )

    time.sleep(2)

    # Config 3: Persistent socket + 0.5s pauze (verwacht: ~60-80%)
    ps = PersistentSocket()
    results["Persistent+Pause"] = run_test_config(
        "Persistent socket + 0.5s pauze",
        ps.request,
        pause_between=0.5
    )
    ps.close()

    time.sleep(2)

    # Config 4: Persistent socket + geen pauze (verwacht: ~40-60%)
    ps = PersistentSocket()
    results["Persistent+NoPause"] = run_test_config(
        "Persistent socket + GEEN pauze",
        ps.request,
        pause_between=0
    )
    ps.close()

    # Eindconclusie
    print("\n" + "=" * 60)
    print("EINDRESULTAAT")
    print("=" * 60)
    for config, rate in results.items():
        bar = "#" * int(rate / 5) + "." * (20 - int(rate / 5))
        print(f"  {config:20s}: [{bar}] {rate:.0f}%")

    print("\n" + "=" * 60)
    print("HYPOTHESE VERIFICATIE:")

    if results["Fresh+Pause"] > 90:
        print("  [OK] Verse socket + pauze geeft hoge success rate")
    else:
        print("  [??] Verse socket + pauze gaf NIET de verwachte hoge rate!")

    if results["Fresh+NoPause"] < results["Fresh+Pause"]:
        print("  [OK] Zonder pauze is success rate lager")
    else:
        print("  [??] Pauze lijkt geen effect te hebben")

    if results["Persistent+Pause"] < results["Fresh+Pause"]:
        print("  [OK] Persistent socket geeft lagere success rate")
    else:
        print("  [??] Socket type lijkt geen effect te hebben")

    print("=" * 60)

if __name__ == "__main__":
    main()
