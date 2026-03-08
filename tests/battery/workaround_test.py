"""
Workaround test: Gebruik ES.GetMode i.p.v. ES.GetStatus

ES.GetStatus faalt op firmware v155, maar ES.GetMode werkt wel en geeft:
- mode (Auto/Manual/AI/Passive)
- bat_soc (%)
- ongrid_power (W)
- offgrid_power (W)
"""
import socket
import json
import time

BATTERIES = [
    {"ip": "192.168.6.80", "name": "FaseA (schuin - d828)"},
    {"ip": "192.168.6.144", "name": "FaseC (geen - deb8)"},
    {"ip": "192.168.6.213", "name": "FaseB (plat - 9a7d)"},  # Mogelijk offline
]

BATTERY_PORT = 30000

def get_battery_data(ip, name):
    """Haal batterij data op met ES.GetMode workaround"""
    print(f"\n{'='*60}")
    print(f" {name}")
    print(f" IP: {ip}")
    print(f"{'='*60}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", BATTERY_PORT))
    sock.settimeout(2.0)

    data = {}

    # 1. Get Device Info
    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    try:
        sock.sendto(json.dumps(request).encode("utf-8"), (ip, BATTERY_PORT))
        resp, addr = sock.recvfrom(65535)
        response = json.loads(resp.decode('utf-8'))
        if "result" in response:
            data["device"] = response["result"]
            print(f"  Device Info: ✅")
            print(f"    Type: {data['device'].get('device')}")
            print(f"    Firmware: v{data['device'].get('ver')}")
            print(f"    BLE MAC: {data['device'].get('ble_mac')}")
        else:
            print(f"  Device Info: ❌ {response.get('error', {}).get('message', 'Error')}")
    except socket.timeout:
        print(f"  Device Info: ⏱️  TIMEOUT")
    except Exception as e:
        print(f"  Device Info: ❌ {e}")

    time.sleep(0.2)

    # 2. Get Mode + SOC (WORKAROUND voor ES.GetStatus)
    request = {"id": 2, "method": "ES.GetMode", "params": {"id": 0}}
    try:
        sock.sendto(json.dumps(request).encode("utf-8"), (ip, BATTERY_PORT))
        resp, addr = sock.recvfrom(65535)
        response = json.loads(resp.decode('utf-8'))
        if "result" in response:
            data["status"] = response["result"]
            print(f"  Battery Status: ✅ (via ES.GetMode workaround)")
            print(f"    Mode: {data['status'].get('mode')}")
            print(f"    SOC: {data['status'].get('bat_soc')}%")
            print(f"    Grid Power: {data['status'].get('ongrid_power', 0)} W")
            print(f"    Offgrid Power: {data['status'].get('offgrid_power', 0)} W")
        else:
            print(f"  Battery Status: ❌ {response.get('error', {}).get('message', 'Error')}")
    except socket.timeout:
        print(f"  Battery Status: ⏱️  TIMEOUT")
    except Exception as e:
        print(f"  Battery Status: ❌ {e}")

    sock.close()
    return data


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "WORKAROUND TEST: ES.GetMode" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    print("\nUsing ES.GetMode instead of ES.GetStatus (firmware v155 bug)")
    print()

    all_data = {}

    for battery in BATTERIES:
        data = get_battery_data(battery["ip"], battery["name"])
        all_data[battery["name"]] = data
        time.sleep(1)

    # Summary
    print(f"\n\n{'='*60}")
    print(" SUMMARY - Battery Status via ES.GetMode")
    print(f"{'='*60}\n")

    online_count = 0
    total_soc = 0

    for battery in BATTERIES:
        name = battery["name"]
        data = all_data.get(name, {})

        if "status" in data:
            online_count += 1
            status = data["status"]
            soc = status.get("bat_soc", 0)
            mode = status.get("mode", "Unknown")
            total_soc += soc

            print(f"✅ {name}")
            print(f"    SOC: {soc}% | Mode: {mode}")
        else:
            print(f"❌ {name} - OFFLINE")
        print()

    if online_count > 0:
        print(f"{'='*60}")
        print(f"Online: {online_count}/{len(BATTERIES)} batteries")
        print(f"Average SOC: {total_soc // online_count}%")
        print(f"{'='*60}\n")
        print("✅ WORKAROUND SUCCESVOL!")
        print("   ES.GetMode kan gebruikt worden i.p.v. ES.GetStatus")
    else:
        print("[FAILED] No batteries responded!\n")


if __name__ == "__main__":
    main()
