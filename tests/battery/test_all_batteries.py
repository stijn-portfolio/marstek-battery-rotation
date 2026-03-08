"""Test alle 3 Marstek Venus batterijen"""
import socket
import json
import time

BATTERIES = [
    {"ip": "192.168.6.80", "name": "FaseA (schuin - d828)"},
    {"ip": "192.168.6.213", "name": "FaseB (plat - 9a7d)"},
    {"ip": "192.168.6.144", "name": "FaseC (geen - deb8)"},
]

BATTERY_PORT = 30000

def test_battery(ip, name):
    """Test één batterij"""
    print(f"\n{'='*60}")
    print(f" Testing {name} - {ip}")
    print(f"{'='*60}\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", BATTERY_PORT))
    sock.settimeout(5.0)

    # Test belangrijkste methods
    test_methods = [
        {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
        {"id": 2, "method": "ES.GetStatus", "params": {"id": 0}},
        {"id": 3, "method": "Bat.GetStatus", "params": {"id": 0}},
    ]

    results = {}

    for request in test_methods:
        data = json.dumps(request).encode("utf-8")
        method = request["method"]

        try:
            sock.sendto(data, (ip, BATTERY_PORT))

            # Collect response
            try:
                resp, addr = sock.recvfrom(65535)
                response = json.loads(resp.decode('utf-8'))

                if "result" in response:
                    results[method] = response["result"]
                    print(f"[OK] {method}")

                    # Print key info
                    if method == "Marstek.GetDevice":
                        result = response["result"]
                        print(f"     Device: {result.get('device')}")
                        print(f"     Firmware: v{result.get('ver')}")
                        print(f"     BLE MAC: {result.get('ble_mac')}")
                    elif method == "ES.GetStatus":
                        result = response["result"]
                        print(f"     SOC: {result.get('bat_soc')}%")
                        print(f"     Capacity: {result.get('bat_cap')} Wh")
                        print(f"     Grid Power: {result.get('ongrid_power')} W")
                    elif method == "Bat.GetStatus":
                        result = response["result"]
                        print(f"     SOC: {result.get('soc')}%")
                        print(f"     Temp: {result.get('bat_temp')}°C")
                        print(f"     Current Cap: {result.get('bat_capacity')} Wh")
                elif "error" in response:
                    print(f"[ERROR] {method}: {response['error']['message']}")

            except socket.timeout:
                print(f"[TIMEOUT] {method}")

        except Exception as e:
            print(f"[ERROR] {method}: {e}")

        time.sleep(0.5)  # Kleine pauze tussen requests

    sock.close()
    return results


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "Multi-Battery Test" + " "*25 + "║")
    print("╚" + "="*58 + "╝")

    all_results = {}

    for battery in BATTERIES:
        results = test_battery(battery["ip"], battery["name"])
        all_results[battery["name"]] = results
        time.sleep(2)  # Pauze tussen batterijen

    # Summary
    print(f"\n\n{'='*60}")
    print(" SUMMARY - All Batteries")
    print(f"{'='*60}\n")

    total_soc = 0
    total_capacity = 0
    total_rated = 0
    online_count = 0

    for battery in BATTERIES:
        name = battery["name"]
        results = all_results.get(name, {})

        print(f"{name} ({battery['ip']}):")

        if "ES.GetStatus" in results:
            online_count += 1
            es = results["ES.GetStatus"]
            soc = es.get("bat_soc", 0)
            cap = es.get("bat_cap", 0)
            grid = es.get("ongrid_power", 0)

            total_soc += soc
            total_rated += cap

            if "Bat.GetStatus" in results:
                bat = results["Bat.GetStatus"]
                current_cap = bat.get("bat_capacity", 0)
                total_capacity += current_cap

            print(f"  ✓ Online - SOC: {soc}%, Capacity: {cap} Wh, Grid: {grid} W")
        else:
            print(f"  ✗ Offline or No Response")
        print()

    if online_count > 0:
        print(f"{'='*60}")
        print(f"TOTALS ({online_count}/{len(BATTERIES)} batteries online):")
        print(f"  Average SOC: {total_soc // online_count}%")
        print(f"  Total Rated Capacity: {total_rated} Wh")
        print(f"  Total Current Capacity: {total_capacity:.0f} Wh")
        print(f"{'='*60}\n")
    else:
        print("[FAILED] No batteries responded!\n")

if __name__ == "__main__":
    main()
