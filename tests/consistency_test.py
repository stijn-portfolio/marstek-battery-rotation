#!/usr/bin/env python3 -u
"""
Consistentie test: dezelfde test elke 5 minuten herhalen.
Test: verse socket + 0.5s pauze tussen requests.
"""

import socket
import json
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

BATTERIES = [
    {"name": "A", "ip": "192.168.6.80"},
    {"name": "B", "ip": "192.168.6.213"},
    {"name": "C", "ip": "192.168.6.144"},
]
PORT = 30000
ROUNDS_PER_RUN = 10
PAUSE_BETWEEN_REQUESTS = 0.5
PAUSE_BETWEEN_RUNS = 300  # 5 minuten
TOTAL_RUNS = 5

def test(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(3.0)
    try:
        sock.bind(("0.0.0.0", PORT))
    except:
        time.sleep(0.3)
        try:
            sock.bind(("0.0.0.0", PORT))
        except:
            sock.close()
            return False

    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, _ = sock.recvfrom(65535)
        sock.close()
        response = json.loads(data.decode())
        return "result" in response
    except:
        sock.close()
        return False

def run_test():
    """Run één complete test (10 rounds x 3 batterijen)."""
    results = {"A": 0, "B": 0, "C": 0}

    for round_num in range(ROUNDS_PER_RUN):
        for bat in BATTERIES:
            ok = test(bat["ip"])
            if ok:
                results[bat["name"]] += 1
            time.sleep(PAUSE_BETWEEN_REQUESTS)

    return results

print("=" * 70)
print("CONSISTENTIE TEST")
print(f"Config: verse socket + {PAUSE_BETWEEN_REQUESTS}s pauze")
print(f"Per run: {ROUNDS_PER_RUN} rounds x 3 batterijen = {ROUNDS_PER_RUN * 3} tests")
print(f"Totaal: {TOTAL_RUNS} runs met {PAUSE_BETWEEN_RUNS}s (5 min) ertussen")
print("=" * 70)

all_results = []

for run in range(TOTAL_RUNS):
    print(f"\n[RUN {run+1}/{TOTAL_RUNS}] Start: {datetime.now().strftime('%H:%M:%S')}")

    results = run_test()

    pct_a = 100 * results["A"] / ROUNDS_PER_RUN
    pct_b = 100 * results["B"] / ROUNDS_PER_RUN
    pct_c = 100 * results["C"] / ROUNDS_PER_RUN
    total = (results["A"] + results["B"] + results["C"]) / (ROUNDS_PER_RUN * 3) * 100

    print(f"  A: {results['A']}/{ROUNDS_PER_RUN} ({pct_a:.0f}%)  "
          f"B: {results['B']}/{ROUNDS_PER_RUN} ({pct_b:.0f}%)  "
          f"C: {results['C']}/{ROUNDS_PER_RUN} ({pct_c:.0f}%)  "
          f"-> TOTAAL: {total:.0f}%")

    all_results.append({"A": pct_a, "B": pct_b, "C": pct_c, "total": total})

    if run < TOTAL_RUNS - 1:
        print(f"  Wachten 5 minuten tot volgende run...")
        for remaining in range(PAUSE_BETWEEN_RUNS, 0, -60):
            print(f"    ... {remaining}s ({datetime.now().strftime('%H:%M:%S')})")
            time.sleep(min(60, remaining))

print("\n" + "=" * 70)
print("SAMENVATTING ALLE RUNS")
print("=" * 70)
print(f"{'Run':<6} {'Fase A':<10} {'Fase B':<10} {'Fase C':<10} {'Totaal':<10}")
print("-" * 46)
for i, r in enumerate(all_results):
    print(f"{i+1:<6} {r['A']:.0f}%{'':<6} {r['B']:.0f}%{'':<6} {r['C']:.0f}%{'':<6} {r['total']:.0f}%")

avg_a = sum(r["A"] for r in all_results) / len(all_results)
avg_b = sum(r["B"] for r in all_results) / len(all_results)
avg_c = sum(r["C"] for r in all_results) / len(all_results)
avg_total = sum(r["total"] for r in all_results) / len(all_results)

print("-" * 46)
print(f"{'AVG':<6} {avg_a:.0f}%{'':<6} {avg_b:.0f}%{'':<6} {avg_c:.0f}%{'':<6} {avg_total:.0f}%")
print("=" * 70)

# Consistentie check
std_a = (sum((r["A"] - avg_a)**2 for r in all_results) / len(all_results)) ** 0.5
std_b = (sum((r["B"] - avg_b)**2 for r in all_results) / len(all_results)) ** 0.5
std_c = (sum((r["C"] - avg_c)**2 for r in all_results) / len(all_results)) ** 0.5

print(f"\nConsistentie (std dev):")
print(f"  Fase A: {std_a:.1f}%  Fase B: {std_b:.1f}%  Fase C: {std_c:.1f}%")
if max(std_a, std_b, std_c) < 15:
    print("  -> CONSISTENT (std dev < 15%)")
else:
    print("  -> NIET CONSISTENT (std dev >= 15%)")
