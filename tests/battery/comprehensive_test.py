"""Comprehensive test van alle batterijen met correcte parameters"""
import socket
import json
import time

# Alle bekende IPs
IPS_TO_TEST = [
    ("192.168.6.80", "FaseA (schuin - d828)"),
    ("192.168.6.144", "FaseC (geen - deb8)"),
    ("192.168.6.213", "FaseB (plat - 9a7d) - OUD IP"),
    ("192.168.6.231", "NIEUW IP (broadcast discovery)"),
]

BATTERY_PORT = 30000

def test_ip(ip, name):
    """Test één IP adres"""
    print(f"\n{'='*70}")
    print(f" {name}")
    print(f" IP: {ip}")
    print(f"{'='*70}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", BATTERY_PORT))
    sock.settimeout(2.0)

    # Test methods met CORRECTE parameters
    tests = [
        ("Marstek.GetDevice", {"ble_mac": "0"}),
        ("ES.GetStatus", {"id": 0}),
        ("ES.GetMode", {"id": 0}),
        ("Bat.GetStatus", {"id": 0}),
        ("BLE.GetStatus", {"id": 0}),
    ]

    results = {}

    for i, (method, params) in enumerate(tests):
        request = {"id": i+1, "method": method, "params": params}
        data = json.dumps(request).encode("utf-8")

        try:
            sock.sendto(data, (ip, BATTERY_PORT))

            try:
                resp, addr = sock.recvfrom(65535)
                response = json.loads(resp.decode('utf-8'))

                # Check if echo (request sent back)
                if response == request:
                    print(f"  [{method:20s}] ⚠️  ECHO (request returned)")
                    continue

                if "result" in response:
                    results[method] = response["result"]
                    print(f"  [{method:20s}] ✅ OK")

                    # Print key details
                    result = response["result"]
                    if method == "Marstek.GetDevice":
                        print(f"      Device: {result.get('device')}, Firmware: v{result.get('ver')}, BLE MAC: {result.get('ble_mac')}")
                    elif method == "ES.GetStatus":
                        print(f"      SOC: {result.get('bat_soc')}%, Capacity: {result.get('bat_cap')} Wh, Grid: {result.get('ongrid_power')} W")
                    elif method == "ES.GetMode":
                        print(f"      Mode: {result.get('mode')}, SOC: {result.get('bat_soc')}%")
                    elif method == "Bat.GetStatus":
                        print(f"      SOC: {result.get('soc')}%, Temp: {result.get('bat_temp')}°C")

                elif "error" in response:
                    error = response["error"]
                    print(f"  [{method:20s}] ❌ ERROR: {error['message']} (code {error['code']})")

            except socket.timeout:
                print(f"  [{method:20s}] ⏱️  TIMEOUT")

        except Exception as e:
            print(f"  [{method:20s}] ❌ EXCEPTION: {e}")

        time.sleep(0.2)

    sock.close()
    return results


def main():
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "COMPREHENSIVE BATTERY TEST" + " "*27 + "║")
    print("╚" + "="*68 + "╝")

    all_results = {}

    for ip, name in IPS_TO_TEST:
        results = test_ip(ip, name)
        all_results[ip] = {"name": name, "results": results}
        time.sleep(1)

    # Summary
    print(f"\n\n{'='*70}")
    print(" SUMMARY")
    print(f"{'='*70}\n")

    working_batteries = []

    for ip, name in IPS_TO_TEST:
        data = all_results.get(ip, {})
        results = data.get("results", {})

        if "Marstek.GetDevice" in results or "ES.GetStatus" in results:
            working_batteries.append((ip, name, results))
            print(f"✅ {name} ({ip})")
            if "Marstek.GetDevice" in results:
                dev = results["Marstek.GetDevice"]
                print(f"    Device: {dev.get('device')}, FW: v{dev.get('ver')}, MAC: {dev.get('ble_mac')}")
            if "ES.GetStatus" in results:
                es = results["ES.GetStatus"]
                print(f"    SOC: {es.get('bat_soc')}%, Mode working: ✅")
        else:
            print(f"❌ {name} ({ip}) - NO RESPONSE")
        print()

    print(f"{'='*70}")
    print(f"Working Batteries: {len(working_batteries)}/{len(IPS_TO_TEST)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
