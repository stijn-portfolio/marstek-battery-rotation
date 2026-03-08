import socket
import json

BATTERY_PORT = 30000

def test_ip_and_port(ip, port):
    """Test een specifiek IP en poort"""
    print(f"\n{'='*60}")
    print(f"Testing {ip}:{port}")
    print('='*60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(2.0)

    request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
    data = json.dumps(request).encode("utf-8")

    try:
        print(f"Sending: {json.dumps(request)}")
        sock.sendto(data, (ip, port))

        # Verzamel alle responses
        responses = []
        while True:
            try:
                resp, addr = sock.recvfrom(65535)
                response = json.loads(resp.decode('utf-8'))
                responses.append((addr, response))
            except socket.timeout:
                break

        if responses:
            for addr, response in responses:
                print(f"\nResponse from {addr}:")
                if response == request:
                    print("  [ECHO - geen echte response]")
                else:
                    print(f"  {json.dumps(response, indent=2)}")
            return True
        else:
            print("  [TIMEOUT] Geen response")
            return False

    except Exception as e:
        print(f"  [ERROR] {e}")
        return False
    finally:
        sock.close()


if __name__ == "__main__":
    print("="*60)
    print(" Marstek API Debug - Testing verschillende IP/Port combinaties")
    print("="*60)

    # Test verschillende configuraties
    configs = [
        ("192.168.0.108", 30000),  # IP uit BLE Network Info
        ("192.168.0.111", 30000),  # IP uit broadcast discovery
        ("192.168.0.108", 28416),  # Alternatieve poort
        ("192.168.0.111", 28416),  # Alternatieve poort
    ]

    results = []
    for ip, port in configs:
        success = test_ip_and_port(ip, port)
        results.append((ip, port, success))

    # Samenvatting
    print(f"\n{'='*60}")
    print(" SAMENVATTING")
    print('='*60)
    for ip, port, success in results:
        status = "[OK]" if success else "[FAILED]"
        print(f"{status} {ip}:{port}")

    print(f"\n{'='*60}")
    print("DIAGNOSE:")
    print('='*60)
    print("De batterij stuurt alleen echo's terug.")
    print("Dit betekent dat de Local API:")
    print("  1. Wel luistert op poort 30000")
    print("  2. Maar niet correct is geactiveerd/geconfigureerd")
    print()
    print("Mogelijke oplossingen:")
    print("  - Doe een 'System Reset' via de BLE tool")
    print("  - Schakel Local API uit en weer in via BLE")
    print("  - Check firmware versie (dev_ver uit BLE)")
    print("  - Sommige firmware versies hebben bugs met Local API")
