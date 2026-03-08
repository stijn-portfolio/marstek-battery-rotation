import socket
import json
import time

BATTERY_IP = "192.168.0.108"
BATTERY_PORT = 30000
BROADCAST_IP = "255.255.255.255"

def test_broadcast_discovery():
    """Test device discovery via UDP broadcast"""
    print("=== Test 1: UDP Broadcast Device Discovery ===\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', BATTERY_PORT))
    sock.settimeout(5.0)

    # Discovery request
    request = {"id": 1, "method": "Marstek.GetDevice", "params": {}}
    data = json.dumps(request).encode("utf-8")

    try:
        print(f"[>>] Broadcasting discovery to {BROADCAST_IP}:{BATTERY_PORT}")
        print(f"     Request: {json.dumps(request)}")
        sock.sendto(data, (BROADCAST_IP, BATTERY_PORT))

        # Luister naar meerdere responses
        print("\n[<<] Waiting for responses (5s)...")
        devices_found = []

        while True:
            try:
                resp, addr = sock.recvfrom(65535)
                response = json.loads(resp.decode('utf-8'))
                print(f"\n[OK] Response from {addr}:")
                print(f"     {json.dumps(response, indent=2)}")
                devices_found.append((addr, response))
            except socket.timeout:
                break

        if devices_found:
            print(f"\n[SUCCESS] Found {len(devices_found)} device(s)!")
            return True
        else:
            print("[TIMEOUT] No devices found via broadcast\n")
            return False

    except Exception as e:
        print(f"[ERROR] {e}\n")
        return False
    finally:
        sock.close()


def test_direct_unicast():
    """Test direct unicast communication"""
    print("\n=== Test 2: Direct Unicast to Known IP ===\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', BATTERY_PORT))
    sock.settimeout(5.0)

    test_methods = [
        {"id": 1, "method": "Marstek.GetDevice", "params": {}},
        {"id": 2, "method": "Bat.GetStatus", "params": {}},
        {"id": 3, "method": "ES.GetStatus", "params": {}},
    ]

    success = False
    for request in test_methods:
        data = json.dumps(request).encode("utf-8")
        method = request["method"]

        try:
            print(f"[>>] Sending to {BATTERY_IP}:{BATTERY_PORT}")
            print(f"     Method: {method}")
            print(f"     Request: {json.dumps(request)}")
            sock.sendto(data, (BATTERY_IP, BATTERY_PORT))

            resp, addr = sock.recvfrom(65535)
            response = json.loads(resp.decode('utf-8'))

            print(f"[OK] Response from {addr}:")
            print(f"     {json.dumps(response, indent=2)}")
            print()
            success = True

        except socket.timeout:
            print(f"[TIMEOUT] No response\n")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
            print(f"        Raw: {resp[:200]}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")

    sock.close()
    return success


def test_listen_only():
    """Just listen on port 30000 for any incoming traffic"""
    print("\n=== Test 3: Passive Listening (10 seconds) ===\n")
    print("Luistert op poort 30000 voor spontane berichten van de batterij...")
    print("(Sommige batterijen sturen periodiek updates)\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', BATTERY_PORT))
    sock.settimeout(10.0)

    try:
        while True:
            try:
                resp, addr = sock.recvfrom(65535)
                print(f"[<<] Received from {addr}:")
                try:
                    response = json.loads(resp.decode('utf-8'))
                    print(f"     {json.dumps(response, indent=2)}")
                except:
                    print(f"     Raw: {resp[:200]}")
            except socket.timeout:
                print("[TIMEOUT] No spontaneous messages received")
                break
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        sock.close()


def check_port_available():
    """Check if port 30000 is available"""
    print("=== Checking Port Availability ===\n")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', BATTERY_PORT))
        sock.close()
        print(f"[OK] Port {BATTERY_PORT} is beschikbaar\n")
        return True
    except OSError as e:
        print(f"[ERROR] Port {BATTERY_PORT} is in gebruik: {e}")
        print("Tip: Sluit andere applicaties die poort 30000 gebruiken\n")
        return False


if __name__ == "__main__":
    print("="*60)
    print(" Marstek Venus E - Local API Diagnostics")
    print("="*60)
    print()

    # Check port availability
    if not check_port_available():
        print("\n[FAILED] Kan poort 30000 niet gebruiken. Stop hier.")
        exit(1)

    # Test 1: Broadcast discovery
    discovered = test_broadcast_discovery()

    # Test 2: Direct unicast
    time.sleep(1)
    unicast_success = test_direct_unicast()

    # Test 3: Passive listening
    time.sleep(1)
    test_listen_only()

    # Summary
    print("\n" + "="*60)
    print(" SAMENVATTING")
    print("="*60)
    print(f"Broadcast Discovery: {'OK' if discovered else 'FAILED'}")
    print(f"Direct Unicast:      {'OK' if unicast_success else 'FAILED'}")
    print()

    if not discovered and not unicast_success:
        print("[DIAGNOSE]")
        print("- Local API is mogelijk niet ingeschakeld (controleer via BLE)")
        print("- Windows Firewall blokkeert mogelijk UDP poort 30000")
        print("- Batterij IP adres kan veranderd zijn (controleer 192.168.0.108)")
        print("- Probeer een System Reset via BLE tool")
        print()
        print("Test Windows Firewall:")
        print("  netsh advfirewall firewall add rule name=\"Marstek\" ")
        print("  dir=in action=allow protocol=UDP localport=30000")
    else:
        print("[SUCCESS] API communicatie werkt!")
