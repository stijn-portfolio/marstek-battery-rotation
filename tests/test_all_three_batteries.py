#!/usr/bin/env python3
"""
Test script voor alle 3 batterijen
Vergelijkt welke API methods werken per batterij.
"""

import socket
import json
import time
from datetime import datetime

# Alle batterijen
BATTERIES = [
    ("Fase A (d828)", "192.168.6.80"),
    ("Fase B V3 (9a7d)", "192.168.6.213"),
    ("Fase C (deb8)", "192.168.6.144"),
]

BATTERY_PORT = 30000
TIMEOUT = 3.0  # Kortere timeout voor snellere test

# Alleen de meest relevante methods testen
API_METHODS = [
    ("Marstek.GetDevice", {"ble_mac": "0"}),
    ("ES.GetStatus", {"id": 0}),
    ("ES.GetMode", {"id": 0}),
    ("Bat.GetStatus", {"id": 0}),
    ("BLE.GetStatus", {"id": 0}),
    ("Wifi.GetStatus", {}),
    ("Wifi.GetStatus", {"id": 0}),
]

def send_request(ip, method, params, request_id):
    """Send API request and collect responses."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", BATTERY_PORT))
    sock.settimeout(TIMEOUT)

    request = {
        "id": request_id,
        "method": method,
        "params": params
    }

    data = json.dumps(request).encode("utf-8")

    try:
        sock.sendto(data, (ip, BATTERY_PORT))
    except Exception as e:
        sock.close()
        return None, f"Send error: {e}"

    # Collect responses
    start_time = time.time()
    result = None
    error = "TIMEOUT"

    while time.time() - start_time < TIMEOUT:
        try:
            resp, addr = sock.recvfrom(65535)
            response = json.loads(resp.decode('utf-8'))

            # Skip echo
            if response == request:
                continue

            if "result" in response:
                result = response["result"]
                error = None
                break
            elif "error" in response:
                error = f"Error {response['error'].get('code', '?')}"
                break

        except socket.timeout:
            break
        except Exception as e:
            error = str(e)
            break

    sock.close()
    return result, error

def test_battery(name, ip):
    """Test one battery with all methods."""
    print(f"\n{'='*60}")
    print(f"  {name} - {ip}")
    print(f"{'='*60}")

    results = {}
    request_id = 1

    for method, params in API_METHODS:
        method_key = f"{method} {params}"
        result, error = send_request(ip, method, params, request_id)

        if result is not None:
            results[method_key] = {"status": "OK", "data": result}

            # Show key data
            if method == "Marstek.GetDevice":
                print(f"  ✅ {method}: device={result.get('device')}, ver={result.get('ver')}")
            elif method == "ES.GetStatus":
                print(f"  ✅ {method}: soc={result.get('bat_soc')}%, pv={result.get('pv_power')}W")
            elif method == "ES.GetMode":
                print(f"  ✅ {method}: soc={result.get('bat_soc')}%, mode={result.get('mode')}")
            elif method == "Bat.GetStatus":
                print(f"  ✅ {method}: soc={result.get('soc')}%, temp={result.get('bat_temp')}")
            elif method == "BLE.GetStatus":
                print(f"  ✅ {method}: mac={result.get('ble_mac')}")
            elif method == "Wifi.GetStatus":
                print(f"  ✅ {method} {params}: ssid={result.get('ssid')}, rssi={result.get('rssi')}")
        else:
            results[method_key] = {"status": "FAIL", "error": error}
            print(f"  ❌ {method} {params}: {error}")

        request_id += 1
        time.sleep(0.3)

    return results

def main():
    print("="*60)
    print("  MARSTEK BATTERIJ VERGELIJKING")
    print(f"  Tijd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    all_results = {}

    for name, ip in BATTERIES:
        all_results[name] = test_battery(name, ip)

    # Comparison table
    print("\n")
    print("="*80)
    print("  VERGELIJKINGSTABEL")
    print("="*80)

    # Header
    print(f"\n{'Method':<35} | ", end="")
    for name, _ in BATTERIES:
        short_name = name.split()[0] + " " + name.split()[1]
        print(f"{short_name:<12} | ", end="")
    print()
    print("-"*80)

    # Data rows
    for method, params in API_METHODS:
        method_key = f"{method} {params}"
        short_method = method.replace("Marstek.", "M.").replace(".GetStatus", ".Status").replace(".GetMode", ".Mode")
        if params == {}:
            short_method += " {}"
        elif params == {"id": 0}:
            short_method += " id:0"
        elif params == {"ble_mac": "0"}:
            short_method += " ble:0"

        print(f"{short_method:<35} | ", end="")

        for name, _ in BATTERIES:
            if name in all_results:
                res = all_results[name].get(method_key, {})
                status = res.get("status", "?")
                if status == "OK":
                    # Show key value
                    data = res.get("data", {})
                    if "bat_soc" in data:
                        print(f"✅ {data['bat_soc']}%".ljust(12) + " | ", end="")
                    elif "soc" in data:
                        print(f"✅ {data['soc']}%".ljust(12) + " | ", end="")
                    elif "ver" in data:
                        print(f"✅ v{data['ver']}".ljust(12) + " | ", end="")
                    elif "ble_mac" in data:
                        print(f"✅ {data['ble_mac'][-4:]}".ljust(12) + " | ", end="")
                    elif "ssid" in data:
                        print(f"✅".ljust(12) + " | ", end="")
                    else:
                        print(f"✅".ljust(12) + " | ", end="")
                else:
                    err = res.get("error", "?")
                    if "TIMEOUT" in str(err):
                        print(f"⏱️ TIMEOUT".ljust(12) + " | ", end="")
                    else:
                        print(f"❌ {err[:8]}".ljust(12) + " | ", end="")
            else:
                print(f"?".ljust(12) + " | ", end="")
        print()

    print("-"*80)

    # SOC Summary
    print("\n")
    print("="*60)
    print("  SOC BRONNEN PER BATTERIJ")
    print("="*60)

    for name, ip in BATTERIES:
        print(f"\n{name}:")
        results = all_results.get(name, {})

        soc_sources = []

        # Check ES.GetStatus
        es_status = results.get("ES.GetStatus {'id': 0}", {})
        if es_status.get("status") == "OK":
            soc = es_status["data"].get("bat_soc")
            soc_sources.append(f"  ✅ ES.GetStatus: {soc}%")
        else:
            soc_sources.append(f"  ❌ ES.GetStatus: {es_status.get('error', 'N/A')}")

        # Check ES.GetMode
        es_mode = results.get("ES.GetMode {'id': 0}", {})
        if es_mode.get("status") == "OK":
            soc = es_mode["data"].get("bat_soc")
            soc_sources.append(f"  ✅ ES.GetMode: {soc}%")
        else:
            soc_sources.append(f"  ❌ ES.GetMode: {es_mode.get('error', 'N/A')}")

        # Check Bat.GetStatus
        bat_status = results.get("Bat.GetStatus {'id': 0}", {})
        if bat_status.get("status") == "OK":
            soc = bat_status["data"].get("soc")
            soc_sources.append(f"  ✅ Bat.GetStatus: {soc}%")
        else:
            soc_sources.append(f"  ❌ Bat.GetStatus: {bat_status.get('error', 'N/A')}")

        for src in soc_sources:
            print(src)

    print("\n")
    print("="*60)
    print("  AANBEVELING")
    print("="*60)

    # Count working methods
    all_work_es_status = all(
        all_results.get(name, {}).get("ES.GetStatus {'id': 0}", {}).get("status") == "OK"
        for name, _ in BATTERIES
    )
    all_work_es_mode = all(
        all_results.get(name, {}).get("ES.GetMode {'id': 0}", {}).get("status") == "OK"
        for name, _ in BATTERIES
    )
    all_work_bat_status = all(
        all_results.get(name, {}).get("Bat.GetStatus {'id': 0}", {}).get("status") == "OK"
        for name, _ in BATTERIES
    )

    print(f"\n  ES.GetStatus werkt op alle batterijen: {'✅ JA' if all_work_es_status else '❌ NEE'}")
    print(f"  ES.GetMode werkt op alle batterijen:   {'✅ JA' if all_work_es_mode else '❌ NEE'}")
    print(f"  Bat.GetStatus werkt op alle batterijen: {'✅ JA' if all_work_bat_status else '❌ NEE'}")

    if all_work_es_mode:
        print("\n  📌 AANBEVELING: Gebruik ES.GetMode voor SOC (werkt op alle batterijen)")
    elif all_work_bat_status:
        print("\n  📌 AANBEVELING: Gebruik Bat.GetStatus voor SOC")
    else:
        print("\n  ⚠️  Geen universele methode gevonden!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest onderbroken.")
    except Exception as e:
        print(f"\n\nFout: {e}")
        import traceback
        traceback.print_exc()
