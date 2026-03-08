"""Test nieuwe IP 192.168.6.231"""
import socket
import json
import time

NEW_IP = "192.168.6.231"
BATTERY_PORT = 30000

def test_battery(ip):
    """Test batterij op nieuw IP"""
    print(f"Testing {ip}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", BATTERY_PORT))
    sock.settimeout(3.0)

    # Test methods met correcte parameters
    test_methods = [
        {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
        {"id": 2, "method": "ES.GetStatus", "params": {"id": 0}},
        {"id": 3, "method": "ES.GetMode", "params": {"id": 0}},
        {"id": 4, "method": "Bat.GetStatus", "params": {"id": 0}},
        {"id": 5, "method": "BLE.GetStatus", "params": {"id": 0}},
    ]

    for request in test_methods:
        data = json.dumps(request).encode("utf-8")
        method = request["method"]

        try:
            sock.sendto(data, (ip, BATTERY_PORT))

            try:
                resp, addr = sock.recvfrom(65535)
                response = json.loads(resp.decode('utf-8'))

                if "result" in response:
                    print(f"\n[OK] {method}")
                    print(f"     Result: {json.dumps(response['result'], indent=2)}")
                elif "error" in response:
                    print(f"\n[ERROR] {method}: {response['error']['message']}")

            except socket.timeout:
                print(f"\n[TIMEOUT] {method}")

        except Exception as e:
            print(f"\n[ERROR] {method}: {e}")

        time.sleep(0.3)

    sock.close()

if __name__ == "__main__":
    print("="*60)
    print(f" Testing New IP: {NEW_IP}")
    print("="*60)
    test_battery(NEW_IP)
