import socket
import json
import time

BATTERY_IP = "192.168.6.80"  # FaseA (d828) - testing v2 compatibility
BATTERY_PORT = 30000

def test_marstek_api():
    """Test Marstek Local API met correcte JSON-RPC formaat"""

    # Belangrijk: source en destination port moeten hetzelfde zijn!
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", BATTERY_PORT))  # Bind op 0.0.0.0 zoals werkende implementaties
    sock.settimeout(5.0)  # Langere timeout (batterij kan traag reageren na veel requests)

    # Correcte JSON-RPC requests volgens Marstek API
    # Gebaseerd op jaapp/ha-marstek-local-api implementatie:
    # - Marstek.GetDevice: {"ble_mac": "0"}
    # - Alle andere methods: {"id": 0}
    test_methods = [
        {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
        {"id": 2, "method": "Bat.GetStatus", "params": {"id": 0}},
        {"id": 3, "method": "ES.GetStatus", "params": {"id": 0}},
        {"id": 4, "method": "ES.GetMode", "params": {"id": 0}},
        {"id": 5, "method": "Wifi.GetStatus", "params": {"id": 0}},
        {"id": 6, "method": "BLE.GetStatus", "params": {"id": 0}},
        {"id": 7, "method": "EM.GetStatus", "params": {"id": 0}},
        {"id": 8, "method": "PV.GetStatus", "params": {"id": 0}},
    ]

    print(f"=== Testing Marstek Local API at {BATTERY_IP}:{BATTERY_PORT} ===\n")

    success = False
    for request in test_methods:
        data = json.dumps(request).encode("utf-8")
        method = request["method"]

        try:
            print(f"[>>] {method}")
            sock.sendto(data, (BATTERY_IP, BATTERY_PORT))

            # Verzamel meerdere pakketten (zoals werkende implementaties doen)
            packets = []
            while len(packets) < 16:  # Max 16 pakketten verzamelen
                try:
                    resp, addr = sock.recvfrom(65535)
                    packets.append((resp, addr))
                except socket.timeout:
                    break  # Geen meer pakketten

            if not packets:
                print(f"     [TIMEOUT] Geen response\n")
                continue

            # Proces alle ontvangen pakketten
            for i, (resp, addr) in enumerate(packets):
                try:
                    response = json.loads(resp.decode('utf-8'))

                    # Check if this is a real response or just an echo
                    if response == request:
                        if i == 0:  # Alleen eerste keer melden
                            print(f"     [ECHO] Batterij stuurt echo terug")
                    elif "result" in response or "error" in response:
                        print(f"     [OK] Packet {i+1}/{len(packets)}:")
                        print(f"     {json.dumps(response, indent=6)}")
                        success = True
                    else:
                        print(f"     [UNKNOWN] Packet {i+1} onverwacht formaat:")
                        print(f"     {json.dumps(response, indent=6)}")

                except json.JSONDecodeError as e:
                    print(f"     [ERROR] Packet {i+1} invalid JSON: {e}")
                    print(f"     Raw: {resp[:100]}")

            print()

        except Exception as e:
            print(f"     [ERROR] {e}\n")

    sock.close()

    if success:
        print("\n[SUCCESS] API communicatie succesvol!")
    else:
        print("\n[FAILED] Geen responses ontvangen.")
        print("Tips:")
        print("- Controleer dat Local API is ingeschakeld via BLE tool")
        print("- Controleer firewall instellingen")
        print("- Probeer een System Reset via de BLE tool")

    return success

if __name__ == "__main__":
    test_marstek_api()