#!/usr/bin/env python3
"""
Gedetailleerde test voor Fase A die ES.SetMode timeout geeft.
"""

import socket
import json
import time

FASE_A_IP = "192.168.6.80"
PORT = 30000
TIMEOUT = 5.0

def send_and_wait(sock, method, params, request_id, description):
    """Stuur command en wacht op response."""
    request = {
        "id": request_id,
        "method": method,
        "params": params
    }

    print(f"\n[{request_id}] {description}")
    print(f"    Method: {method}")
    print(f"    Params: {json.dumps(params)[:100]}...")

    message = json.dumps(request).encode('utf-8')
    sock.sendto(message, (FASE_A_IP, PORT))

    responses = []
    start = time.time()

    # Wacht langer en verzamel alle responses
    while time.time() - start < TIMEOUT:
        try:
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(65535)
            elapsed = time.time() - start
            response = json.loads(data.decode())
            responses.append(response)
            print(f"    Response ({elapsed:.2f}s) from {addr[0]}: id={response.get('id')}", end="")
            if "result" in response:
                print(f" -> SUCCESS")
            elif "error" in response:
                err = response["error"]
                print(f" -> ERROR {err.get('code')}: {err.get('message')}")
            else:
                print(f" -> {response}")
        except socket.timeout:
            continue

    if not responses:
        print(f"    -> NO RESPONSE (timeout)")

    return responses

def main():
    print("="*60)
    print("FASE A (VenusE v156) DETAILED TEST")
    print(f"IP: {FASE_A_IP}:{PORT}")
    print("="*60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))

    rid = 0

    # Test 1: Device info
    rid += 1
    send_and_wait(sock, "Marstek.GetDevice", {"ble_mac": "0"}, rid, "Device discovery")
    time.sleep(0.5)

    # Test 2: ES.GetStatus
    rid += 1
    send_and_wait(sock, "ES.GetStatus", {"id": 0}, rid, "ES.GetStatus")
    time.sleep(0.5)

    # Test 3: ES.GetMode
    rid += 1
    send_and_wait(sock, "ES.GetMode", {"id": 0}, rid, "ES.GetMode")
    time.sleep(0.5)

    # Test 4: Bat.GetStatus
    rid += 1
    send_and_wait(sock, "Bat.GetStatus", {"id": 0}, rid, "Bat.GetStatus")
    time.sleep(0.5)

    # Test 5: ES.SetMode Manual
    rid += 1
    send_and_wait(sock, "ES.SetMode", {
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
    }, rid, "ES.SetMode (Manual)")
    time.sleep(0.5)

    # Test 6: ES.SetMode Auto
    rid += 1
    send_and_wait(sock, "ES.SetMode", {
        "id": 0,
        "config": {
            "mode": "Auto",
            "auto_cfg": {"enable": 1}
        }
    }, rid, "ES.SetMode (Auto)")
    time.sleep(0.5)

    # Test 7: Probe met langere timeout
    print("\n" + "="*60)
    print("EXTENDED WAIT (10s) voor ES.SetMode...")
    print("="*60)

    rid += 1
    request = {
        "id": rid,
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

    sock.sendto(json.dumps(request).encode(), (FASE_A_IP, PORT))

    start = time.time()
    while time.time() - start < 10.0:
        try:
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(65535)
            elapsed = time.time() - start
            response = json.loads(data.decode())
            print(f"Response ({elapsed:.2f}s) from {addr[0]}: {response}")
        except socket.timeout:
            print(".", end="", flush=True)

    print("\n")
    sock.close()

    print("="*60)
    print("CONCLUSIE")
    print("="*60)
    print("""
Als Fase A geen response geeft op ES.SetMode:
1. Deze methode is mogelijk niet ondersteund op oudere Venus E (v156)
2. OF er is een bug in de firmware
3. OF de batterij staat in een mode die SetMode blokkeert

Opties:
- Firmware update voor Fase A
- Alternatief: BLE protocol gebruiken
""")

if __name__ == "__main__":
    main()
