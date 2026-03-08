"""
Finale vergelijking van alle 3 batterijen
Test welke methods werken per firmware versie
"""
import socket
import json
import time

BATTERIES = [
    {"ip": "192.168.6.80", "name": "FaseA (d828)", "fw": "v155"},
    {"ip": "192.168.6.213", "name": "FaseB (9a7d)", "fw": "v139"},
    {"ip": "192.168.6.144", "name": "FaseC (deb8)", "fw": "v155"},
]

PORT = 30000

METHODS = [
    ("Marstek.GetDevice", {"ble_mac": "0"}),
    ("ES.GetStatus", {"id": 0}),
    ("ES.GetMode", {"id": 0}),
    ("Bat.GetStatus", {"id": 0}),
    ("BLE.GetStatus", {"id": 0}),
    ("Wifi.GetStatus", {"id": 0}),
]

def test_battery(ip, name, fw):
    """Test one battery"""
    print(f"\n{'='*70}")
    print(f" {name} - Firmware {fw}")
    print(f" IP: {ip}:{PORT}")
    print(f"{'='*70}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(2.0)

    results = {}

    for method, params in METHODS:
        request = {"id": 1, "method": method, "params": params}
        data = json.dumps(request).encode("utf-8")

        try:
            sock.sendto(data, (ip, PORT))
            resp, addr = sock.recvfrom(65535)
            response = json.loads(resp.decode("utf-8"))

            if "result" in response:
                results[method] = "OK"
                print(f"  [{method:20s}] OK")
            elif "error" in response:
                results[method] = f"ERROR: {response['error']['message']}"
                print(f"  [{method:20s}] ERROR: {response['error']['message']}")
        except socket.timeout:
            results[method] = "TIMEOUT"
            print(f"  [{method:20s}] TIMEOUT")
        except Exception as e:
            results[method] = f"EXCEPTION: {e}"
            print(f"  [{method:20s}] EXCEPTION: {e}")

        time.sleep(0.3)

    sock.close()
    return results

def main():
    print("\n")
    print("="*70)
    print(" FINAL COMPARISON TEST - All 3 Batteries")
    print("="*70)

    all_results = {}

    for battery in BATTERIES:
        results = test_battery(battery["ip"], battery["name"], battery["fw"])
        all_results[battery["name"]] = {
            "fw": battery["fw"],
            "results": results
        }
        time.sleep(1)

    # Summary Table
    print(f"\n\n{'='*70}")
    print(" SUMMARY - Method Support by Firmware Version")
    print(f"{'='*70}\n")

    print(f"{'Method':<25} {'FaseA (v155)':<15} {'FaseB (v139)':<15} {'FaseC (v155)':<15}")
    print("-"*70)

    for method, _ in METHODS:
        row = f"{method:<25}"
        for battery in BATTERIES:
            name = battery["name"]
            result = all_results[name]["results"].get(method, "N/A")
            status = "OK" if result == "OK" else "FAIL"
            row += f" {status:<15}"
        print(row)

    print("\n" + "="*70)
    print(" WORKING DATA SOURCES PER BATTERY:")
    print("="*70)

    for battery in BATTERIES:
        name = battery["name"]
        fw = all_results[name]["fw"]
        results = all_results[name]["results"]

        working = [m for m, r in results.items() if r == "OK"]

        print(f"\n{name} ({fw}):")
        if working:
            for method in working:
                print(f"  - {method}")
        else:
            print("  (None working!)")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
