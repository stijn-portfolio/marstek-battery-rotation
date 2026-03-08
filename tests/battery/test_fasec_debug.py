import socket
import json
import time

BATTERY_IP = "192.168.0.108"
BATTERY_PORT = 30000

print(f"=== Debug Test FaseC at {BATTERY_IP}:{BATTERY_PORT} ===\n")

# Create socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", BATTERY_PORT))
sock.settimeout(5.0)

# Simple request
request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
data = json.dumps(request).encode("utf-8")

print(f"Sending request: {request}")
print(f"To: {BATTERY_IP}:{BATTERY_PORT}")
print(f"From port: {BATTERY_PORT}")
print(f"Request size: {len(data)} bytes\n")

try:
    # Send
    sent_bytes = sock.sendto(data, (BATTERY_IP, BATTERY_PORT))
    print(f"[OK] Sent {sent_bytes} bytes")

    # Receive with multiple attempts
    print("Waiting for response...")
    responses = []

    for i in range(5):
        try:
            resp, addr = sock.recvfrom(65535)
            print(f"\n[OK] Received packet {i+1} from {addr}")
            print(f"  Size: {len(resp)} bytes")
            print(f"  Raw: {resp[:100]}")

            try:
                parsed = json.loads(resp.decode('utf-8'))
                print(f"  Parsed: {json.dumps(parsed, indent=2)}")
                responses.append(parsed)
            except:
                print(f"  Could not parse as JSON")

        except socket.timeout:
            if i == 0:
                print("\n[TIMEOUT] No response received")
            break

    if responses:
        print(f"\n[SUCCESS] Got {len(responses)} response(s)")
    else:
        print("\n[FAILED] No responses")
        print("\nTroubleshooting:")
        print("1. Check Local API is enabled in BLE tool")
        print("2. Verify IP address is correct (check in BLE tool)")
        print("3. Check port is 30000 (check in BLE tool)")
        print("4. Try System Reset in BLE tool")
        print("5. Check firewall is not blocking UDP port 30000")

except Exception as e:
    print(f"\n[ERROR] {e}")

finally:
    sock.close()
