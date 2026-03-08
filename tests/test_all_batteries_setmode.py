#!/usr/bin/env python3
"""
Test ES.SetMode op alle 3 batterijen om te zien welke werkt en welke faalt.
"""

import socket
import json
import time

BATTERIES = [
    {"name": "Fase A (schuin - d828)", "ip": "192.168.6.80"},
    {"name": "Fase B (plat - 9a7d)", "ip": "192.168.6.213"},
    {"name": "Fase C (geen - deb8)", "ip": "192.168.6.144"},
]

PORT = 30000
TIMEOUT = 3.0

def test_setmode(name, ip):
    """Test ES.SetMode op een specifieke batterij."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"IP: {ip}")
    print("="*60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    try:
        # Marstek devices vereisen source port 30000!
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", PORT))
        print(f"Using source port: {PORT}")
    except Exception as e:
        print(f"Socket error: {e}")
        return

    # Eerst device info ophalen
    request = {
        "id": 1,
        "method": "Marstek.GetDevice",
        "params": {"ble_mac": "0"}
    }

    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, addr = sock.recvfrom(65535)
        device_info = json.loads(data.decode())
        if "result" in device_info:
            print(f"Device: {device_info['result'].get('device')}, FW: v{device_info['result'].get('ver')}")
        else:
            print(f"Device info response: {device_info}")
    except socket.timeout:
        print("GetDevice: TIMEOUT")
    except Exception as e:
        print(f"GetDevice error: {e}")

    time.sleep(0.5)

    # Nu ES.SetMode testen
    request = {
        "id": 2,
        "method": "ES.SetMode",
        "params": {
            "id": 0,
            "config": {
                "mode": "Manual",
                "manual_cfg": {
                    "time_num": 9,
                    "start_time": "00:00",
                    "end_time": "00:00",
                    "week_set": 0,
                    "power": 0,
                    "enable": 0
                }
            }
        }
    }

    print(f"\nSending ES.SetMode to {ip}...")
    sock.sendto(json.dumps(request).encode(), (ip, PORT))

    try:
        data, addr = sock.recvfrom(65535)
        response = json.loads(data.decode())

        if "result" in response:
            print(f"[OK] SUCCESS: {response['result']}")
        elif "error" in response:
            err = response['error']
            code = err.get('code', '?')
            msg = err.get('message', '?')
            print(f"[FAIL] ERROR {code}: {msg}")
            if code == -32601:
                print("   -> ES.SetMode is NOT SUPPORTED op dit device!")
        else:
            print(f"[?] UNKNOWN: {response}")

    except socket.timeout:
        print("[FAIL] TIMEOUT: Geen response ontvangen")
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")

    sock.close()
    return

def main():
    print("="*60)
    print("ES.SetMode TEST OP ALLE BATTERIJEN")
    print("="*60)

    for bat in BATTERIES:
        test_setmode(bat["name"], bat["ip"])
        time.sleep(1)

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
