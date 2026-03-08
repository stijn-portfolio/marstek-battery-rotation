import socket
import json
import time

# Correcte IP gevonden via broadcast discovery!
BATTERY_IP = "192.168.0.111"  # Was 192.168.0.108
BATTERY_PORT = 30000

def test_marstek_api():
    """Test Marstek Local API met correcte IP"""

    # Belangrijk: source en destination port moeten hetzelfde zijn!
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', BATTERY_PORT))
    sock.settimeout(5.0)

    # Correcte JSON-RPC requests volgens Marstek API
    test_methods = [
        {"id": 1, "method": "Marstek.GetDevice", "params": {}},
        {"id": 2, "method": "Bat.GetStatus", "params": {}},
        {"id": 3, "method": "ES.GetStatus", "params": {}},
        {"id": 4, "method": "ES.GetMode", "params": {}},
        {"id": 5, "method": "Wifi.GetStatus", "params": {}},
        {"id": 6, "method": "EM.GetStatus", "params": {}},
    ]

    print(f"=== Testing Marstek Local API at {BATTERY_IP}:{BATTERY_PORT} ===\n")

    results = []
    for request in test_methods:
        data = json.dumps(request).encode("utf-8")
        method = request["method"]

        try:
            print(f"[>>] {method}")
            sock.sendto(data, (BATTERY_IP, BATTERY_PORT))

            resp, addr = sock.recvfrom(65535)
            response = json.loads(resp.decode('utf-8'))

            # Check if this is a real response or just an echo
            if response == request:
                print(f"     [ECHO] Received echo of request (not a real response)")
                results.append((method, "ECHO"))
            else:
                print(f"     [OK] Response:")
                print(f"     {json.dumps(response, indent=6)}")
                results.append((method, "SUCCESS"))

        except socket.timeout:
            print(f"     [TIMEOUT]")
            results.append((method, "TIMEOUT"))
        except json.JSONDecodeError as e:
            print(f"     [ERROR] Invalid JSON: {e}")
            results.append((method, "JSON_ERROR"))
        except Exception as e:
            print(f"     [ERROR] {e}")
            results.append((method, "ERROR"))

        print()

    sock.close()

    # Summary
    print("="*60)
    print("SAMENVATTING:")
    print("="*60)
    for method, status in results:
        print(f"{method:25} {status}")

    success_count = sum(1 for _, status in results if status == "SUCCESS")
    if success_count > 0:
        print(f"\n[SUCCESS] {success_count}/{len(results)} methods werkten!")
    else:
        print(f"\n[FAILED] Geen succesvolle API calls")
        print("\nMogelijke oorzaken:")
        print("- Local API is ingeschakeld maar de batterij stuurt alleen echo's")
        print("- Mogelijk is een System Reset nodig via de BLE tool")
        print("- Mogelijk werkt het protocol anders dan gedocumenteerd")

    return success_count > 0

if __name__ == "__main__":
    test_marstek_api()
