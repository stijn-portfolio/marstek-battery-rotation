#!/usr/bin/env python3
"""
Systematische debug van connectivity problemen.
Test elke batterij meerdere keren en meet response tijden.
"""

import socket
import json
import time
from datetime import datetime

BATTERIES = [
    {"name": "Fase A", "ip": "192.168.6.80", "mac": "d828"},
    {"name": "Fase B", "ip": "192.168.6.213", "mac": "9a7d"},
    {"name": "Fase C", "ip": "192.168.6.144", "mac": "deb8"},
]
PORT = 30000
TIMEOUT = 3.0
TESTS_PER_BATTERY = 5

def create_socket():
    """Maak een nieuwe socket voor elke test."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Probeer te binden op port 30000
    try:
        sock.bind(("0.0.0.0", PORT))
        return sock, PORT
    except OSError as e:
        # Port in gebruik - probeer ephemeral port
        sock.bind(("0.0.0.0", 0))
        local_port = sock.getsockname()[1]
        return sock, local_port

def test_single(ip, request_id):
    """Test een enkele request naar een batterij."""
    sock, local_port = create_socket()

    request = {
        "id": request_id,
        "method": "Marstek.GetDevice",
        "params": {"ble_mac": "0"}
    }

    start = time.time()
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    result = {
        "local_port": local_port,
        "success": False,
        "latency": None,
        "error": None,
        "device": None,
        "response_port": None,
    }

    try:
        data, addr = sock.recvfrom(65535)
        elapsed = time.time() - start
        result["latency"] = round(elapsed * 1000, 1)  # ms
        result["response_port"] = addr[1]

        response = json.loads(data.decode())
        if "result" in response:
            result["success"] = True
            result["device"] = response["result"].get("device", "?")
        elif "error" in response:
            result["error"] = f"API error: {response['error']}"
    except socket.timeout:
        result["error"] = "TIMEOUT"
    except Exception as e:
        result["error"] = str(e)
    finally:
        sock.close()

    return result

def main():
    print("=" * 70)
    print(f"CONNECTIVITY DEBUG - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)
    print(f"Target port: {PORT}, Timeout: {TIMEOUT}s, Tests per battery: {TESTS_PER_BATTERY}")
    print()

    # Check of port 30000 vrij is
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        test_sock.bind(("0.0.0.0", PORT))
        print(f"[INFO] Port {PORT} is VRIJ - geen andere listener")
        test_sock.close()
    except OSError:
        print(f"[WARN] Port {PORT} is IN GEBRUIK - mogelijk HA integratie actief!")

    print()

    request_id = 0

    for bat in BATTERIES:
        print(f"\n--- {bat['name']} ({bat['ip']}) ---")
        successes = 0
        latencies = []

        for i in range(TESTS_PER_BATTERY):
            request_id += 1
            result = test_single(bat["ip"], request_id)

            status = "OK" if result["success"] else "FAIL"
            latency_str = f"{result['latency']}ms" if result["latency"] else "-"
            port_info = f"src:{result['local_port']}"

            if result["success"]:
                successes += 1
                latencies.append(result["latency"])
                print(f"  [{i+1}] {status} {latency_str:>8} ({port_info}) -> {result['device']}")
            else:
                print(f"  [{i+1}] {status} {result['error']:>20} ({port_info})")

            time.sleep(0.5)  # Korte pauze tussen tests

        # Samenvatting per batterij
        success_rate = (successes / TESTS_PER_BATTERY) * 100
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        print(f"  Summary: {successes}/{TESTS_PER_BATTERY} OK ({success_rate:.0f}%), avg latency: {avg_latency:.1f}ms")

    print("\n" + "=" * 70)
    print("CONCLUSIE")
    print("=" * 70)
    print("""
Als sommige tests falen met TIMEOUT:
1. Check of de HA integratie port 30000 bezet houdt
2. Check WiFi signaalsterkte op de batterijen
3. Check router/firewall instellingen

Als tests falen wanneer local_port != 30000:
-> De batterij antwoordt alleen naar port 30000 (known issue)
""")

if __name__ == "__main__":
    main()
