#!/usr/bin/env python3
"""
Test script om te controleren welke API methodes werken op Fase B (Venus E 3.0).
Dit helpt om te begrijpen waarom ES.SetMode faalt met "Method not found".
"""

import socket
import json
import time

# Fase B configuratie
FASE_B_IP = "192.168.6.213"
PORT = 30000
TIMEOUT = 3.0

def send_command(sock, method, params, request_id=1):
    """Stuur een UDP command en wacht op response."""
    request = {
        "id": request_id,
        "method": method,
        "params": params
    }

    message = json.dumps(request).encode('utf-8')
    sock.sendto(message, (FASE_B_IP, PORT))

    try:
        data, addr = sock.recvfrom(65535)
        return json.loads(data.decode('utf-8'))
    except socket.timeout:
        return {"error": "timeout"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}"}

def test_api_method(sock, method, params, description, request_id):
    """Test een API methode en print het resultaat."""
    print(f"\n{'='*60}")
    print(f"Testing: {method}")
    print(f"Description: {description}")
    print(f"Params: {params}")

    response = send_command(sock, method, params, request_id)

    if "error" in response and response["error"] == "timeout":
        print("Result: TIMEOUT (no response)")
    elif "error" in response:
        error = response["error"]
        if isinstance(error, dict):
            code = error.get("code", "?")
            msg = error.get("message", "?")
            print(f"Result: ERROR {code}: {msg}")
            if code == -32601:
                print("  -> Method NOT SUPPORTED op dit device!")
        else:
            print(f"Result: ERROR: {error}")
    elif "result" in response:
        print(f"Result: SUCCESS")
        print(f"  Response: {json.dumps(response['result'], indent=2)[:500]}")
    else:
        print(f"Result: UNKNOWN RESPONSE")
        print(f"  Raw: {response}")

    return response

def main():
    print("="*60)
    print("FASE B (Venus E 3.0) API Test")
    print(f"IP: {FASE_B_IP}:{PORT}")
    print("="*60)

    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    try:
        # Bind to source port 30000 (required for Marstek devices)
        sock.bind(("0.0.0.0", PORT))
        print(f"Socket bound to port {PORT}")
    except OSError as e:
        print(f"Warning: Could not bind to port {PORT}: {e}")
        print("Trying ephemeral port...")

    request_id = 0

    # Test 1: Device discovery (should always work)
    request_id += 1
    test_api_method(sock, "Marstek.GetDevice", {"ble_mac": "0"},
                    "Device discovery - verifies connection", request_id)
    time.sleep(0.5)

    # Test 2: ES.GetStatus (should work)
    request_id += 1
    test_api_method(sock, "ES.GetStatus", {"id": 0},
                    "Energy System status - basic read", request_id)
    time.sleep(0.5)

    # Test 3: ES.GetMode (should work but often returns unknown)
    request_id += 1
    test_api_method(sock, "ES.GetMode", {"id": 0},
                    "Get current operating mode", request_id)
    time.sleep(0.5)

    # Test 4: ES.SetMode - This is what fails!
    request_id += 1
    test_api_method(sock, "ES.SetMode", {
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
    }, "Set operating mode to Manual - THIS SHOULD FAIL", request_id)
    time.sleep(0.5)

    # Test 5: Alternative SetMode formats
    request_id += 1
    test_api_method(sock, "ES.SetMode", {
        "id": 0,
        "mode": "Manual",
        "manual_cfg": {
            "time_num": 9,
            "start_time": "00:00",
            "end_time": "00:00",
            "week_set": 0,
            "power": 0,
            "enable": 0
        }
    }, "SetMode with mode at top level (alt format)", request_id)
    time.sleep(0.5)

    # Test 6: Bat.GetStatus (often times out)
    request_id += 1
    test_api_method(sock, "Bat.GetStatus", {"id": 0},
                    "Battery status", request_id)
    time.sleep(0.5)

    # Test 7: BLE.GetStatus
    request_id += 1
    test_api_method(sock, "BLE.GetStatus", {"id": 0},
                    "Bluetooth status", request_id)

    sock.close()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("""
CONCLUSIE:
Als ES.SetMode faalt met -32601 (Method not found), dan ondersteunt
de Venus E 3.0 (firmware v143) deze methode niet of heeft een andere
API signature nodig.

MOGELIJKE OPLOSSINGEN:
1. Firmware update voor de Venus E 3.0
2. BLE protocol gebruiken (0x15/0x16 commands) ipv Local API
3. Cloud API gebruiken voor mode changes
""")

if __name__ == "__main__":
    main()
