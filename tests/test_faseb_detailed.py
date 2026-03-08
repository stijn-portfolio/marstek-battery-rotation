#!/usr/bin/env python3
"""
Gedetailleerde test om te begrijpen waarom HA faalt maar direct UDP werkt.
"""

import socket
import json
import time

FASE_B_IP = "192.168.6.213"
PORT = 30000
TIMEOUT = 5.0

def send_and_receive_all(sock, method, params, request_id):
    """Stuur command en verzamel ALLE responses (inclusief echos)."""
    request = {
        "id": request_id,
        "method": method,
        "params": params
    }

    message = json.dumps(request).encode('utf-8')
    print(f"\n>>> SENDING to {FASE_B_IP}:{PORT}")
    print(f"    Payload: {message.decode()}")

    sock.sendto(message, (FASE_B_IP, PORT))

    responses = []
    start = time.time()

    while time.time() - start < TIMEOUT:
        try:
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(65535)
            elapsed = time.time() - start
            response = data.decode('utf-8')
            print(f"<<< RECEIVED from {addr[0]}:{addr[1]} after {elapsed:.2f}s")
            print(f"    Raw: {response}")
            try:
                parsed = json.loads(response)
                responses.append(parsed)
                print(f"    Parsed ID: {parsed.get('id')}, has result: {'result' in parsed}, has error: {'error' in parsed}")
                if "error" in parsed:
                    err = parsed["error"]
                    print(f"    ERROR: code={err.get('code')}, msg={err.get('message')}")
            except:
                print(f"    (Could not parse as JSON)")
        except socket.timeout:
            continue

    return responses

def main():
    print("="*70)
    print("FASE B DETAILED API TEST")
    print("="*70)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind(("0.0.0.0", PORT))
        print(f"Bound to port {PORT}")
    except OSError as e:
        print(f"Could not bind to {PORT}: {e}")
        # Try ephemeral port
        sock.bind(("0.0.0.0", 0))
        local_port = sock.getsockname()[1]
        print(f"Using ephemeral port {local_port}")

    # Test 1: Exact HA button payload
    print("\n" + "="*70)
    print("TEST 1: Exact payload zoals HA button.py het stuurt")
    print("="*70)

    # Dit is wat de HA integratie stuurt (button.py line 205-209 + api.py line 807-809)
    ha_payload = {
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

    responses = send_and_receive_all(sock, "ES.SetMode", ha_payload, 1)

    if not responses:
        print("\n!!! GEEN RESPONSE - Dit verklaart de timeout in HA")
    else:
        for r in responses:
            if "error" in r:
                print(f"\n!!! ERROR RESPONSE GEVONDEN: {r['error']}")
            elif "result" in r:
                print(f"\n>>> SUCCESS: {r['result']}")

    time.sleep(1)

    # Test 2: Simpeler formaat
    print("\n" + "="*70)
    print("TEST 2: Config direct in params (zoals mijn eerste test)")
    print("="*70)

    simple_payload = {
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

    responses = send_and_receive_all(sock, "ES.SetMode", simple_payload, 2)

    time.sleep(1)

    # Test 3: Auto mode (simpeler config)
    print("\n" + "="*70)
    print("TEST 3: Auto mode (simpeler)")
    print("="*70)

    auto_payload = {
        "id": 0,
        "config": {
            "mode": "Auto",
            "auto_cfg": {"enable": 1}
        }
    }

    responses = send_and_receive_all(sock, "ES.SetMode", auto_payload, 3)

    time.sleep(1)

    # Test 4: Check current mode
    print("\n" + "="*70)
    print("TEST 4: ES.GetMode om huidige mode te zien")
    print("="*70)

    responses = send_and_receive_all(sock, "ES.GetMode", {"id": 0}, 4)

    sock.close()

    print("\n" + "="*70)
    print("ANALYSE")
    print("="*70)
    print("""
Als ES.SetMode hier werkt maar in HA faalt met 'Method not found':
1. Check of HA dezelfde socket port gebruikt (moet 30000 zijn)
2. Check of er firewall issues zijn
3. Check de HA logs voor de exacte payload die verstuurd wordt
4. Mogelijk is er een race condition met meerdere devices
""")

if __name__ == "__main__":
    main()
