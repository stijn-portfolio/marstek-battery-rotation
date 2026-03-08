#!/usr/bin/env python3
"""
Test script voor Venus V3 (192.168.6.213)
Test alle API methods om te zien welke werken.
"""

import socket
import json
import time
from datetime import datetime

# Target battery
BATTERY_IP = "192.168.6.213"
BATTERY_PORT = 30000
TIMEOUT = 5.0  # seconds

# Alle mogelijke API methods met verschillende parameter variaties
API_METHODS = [
    # Meest basic - zou altijd moeten werken
    ("Marstek.GetDevice", {"ble_mac": "0"}),
    ("Marstek.GetDevice", {}),

    # Energy System Mode - vaak stabiel
    ("ES.GetMode", {"id": 0}),
    ("ES.GetMode", {}),

    # Energy System Status - problematisch op V3
    ("ES.GetStatus", {"id": 0}),
    ("ES.GetStatus", {}),
    ("ES.GetStatus", {"ble_mac": "0"}),

    # BLE Status
    ("BLE.GetStatus", {"id": 0}),
    ("BLE.GetStatus", {}),

    # Battery Status
    ("Bat.GetStatus", {"id": 0}),
    ("Bat.GetStatus", {}),

    # WiFi Status
    ("Wifi.GetStatus", {"id": 0}),
    ("Wifi.GetStatus", {}),

    # Energy Meter (CT) Status
    ("EM.GetStatus", {"id": 0}),
    ("EM.GetStatus", {}),

    # PV Status (waarschijnlijk niet beschikbaar op Venus E)
    ("PV.GetStatus", {"id": 0}),
]

def create_socket():
    """Create and configure UDP socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", BATTERY_PORT))
    sock.settimeout(TIMEOUT)
    return sock

def send_request(sock, method, params, request_id):
    """Send API request and collect responses."""
    request = {
        "id": request_id,
        "method": method,
        "params": params
    }

    data = json.dumps(request).encode("utf-8")

    try:
        sock.sendto(data, (BATTERY_IP, BATTERY_PORT))
    except Exception as e:
        return None, f"Send error: {e}"

    # Collect responses
    packets = []
    start_time = time.time()

    while time.time() - start_time < TIMEOUT:
        try:
            resp, addr = sock.recvfrom(65535)
            packets.append((resp, addr))

            # Check if we have a valid response (not echo)
            try:
                response = json.loads(resp.decode('utf-8'))
                if response != request and ("result" in response or "error" in response):
                    break  # Got a real response
            except:
                pass

        except socket.timeout:
            break
        except Exception as e:
            return None, f"Receive error: {e}"

    if not packets:
        return None, "TIMEOUT - no response"

    # Filter out echo and find real response
    for resp, addr in packets:
        try:
            response = json.loads(resp.decode('utf-8'))

            # Skip echo
            if response == request:
                continue

            # Return result or error
            if "result" in response:
                return response["result"], None
            elif "error" in response:
                return None, f"API Error: {response['error']}"

        except json.JSONDecodeError:
            continue

    return None, "TIMEOUT - only echo received"

def test_all_methods():
    """Test all API methods and report results."""
    print("=" * 70)
    print(f"VENUS V3 API TEST - {BATTERY_IP}:{BATTERY_PORT}")
    print(f"Tijd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    results = {
        "success": [],
        "timeout": [],
        "error": []
    }

    request_id = 1

    for method, params in API_METHODS:
        print(f"\nTest {request_id}: {method}")
        print(f"  Params: {params}")

        try:
            # Create fresh socket for each request
            sock = create_socket()

            result, error = send_request(sock, method, params, request_id)

            sock.close()

            if result is not None:
                print(f"  ✅ SUCCESS!")
                print(f"  Result: {json.dumps(result, indent=4)}")
                results["success"].append({
                    "method": method,
                    "params": params,
                    "result": result
                })
            elif error:
                if "TIMEOUT" in error:
                    print(f"  ⏱️  {error}")
                    results["timeout"].append({
                        "method": method,
                        "params": params,
                        "error": error
                    })
                else:
                    print(f"  ❌ {error}")
                    results["error"].append({
                        "method": method,
                        "params": params,
                        "error": error
                    })

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results["error"].append({
                "method": method,
                "params": params,
                "error": str(e)
            })

        request_id += 1
        time.sleep(0.5)  # Small delay between requests

    # Print summary
    print("\n")
    print("=" * 70)
    print("SAMENVATTING")
    print("=" * 70)

    print(f"\n✅ WERKENDE METHODS ({len(results['success'])}):")
    if results["success"]:
        for item in results["success"]:
            print(f"   - {item['method']} (params: {item['params']})")
    else:
        print("   Geen")

    print(f"\n⏱️  TIMEOUTS ({len(results['timeout'])}):")
    if results["timeout"]:
        for item in results["timeout"]:
            print(f"   - {item['method']} (params: {item['params']})")
    else:
        print("   Geen")

    print(f"\n❌ ERRORS ({len(results['error'])}):")
    if results["error"]:
        for item in results["error"]:
            print(f"   - {item['method']}: {item['error']}")
    else:
        print("   Geen")

    # Firmware info if available
    print("\n")
    print("=" * 70)
    print("DEVICE INFO")
    print("=" * 70)

    for item in results["success"]:
        if item["method"] == "Marstek.GetDevice":
            result = item["result"]
            print(f"  Device: {result.get('device', 'Unknown')}")
            print(f"  Firmware: v{result.get('ver', 'Unknown')}")
            print(f"  BLE MAC: {result.get('ble_mac', 'Unknown')}")
            print(f"  WiFi MAC: {result.get('wifi_mac', 'Unknown')}")
            print(f"  IP: {result.get('ip', 'Unknown')}")
            print(f"  WiFi: {result.get('wifi_name', 'Unknown')}")
            break
    else:
        print("  Geen device info beschikbaar (Marstek.GetDevice faalde)")

    return results

if __name__ == "__main__":
    try:
        results = test_all_methods()
    except KeyboardInterrupt:
        print("\n\nTest onderbroken door gebruiker.")
    except Exception as e:
        print(f"\n\nFout: {e}")
