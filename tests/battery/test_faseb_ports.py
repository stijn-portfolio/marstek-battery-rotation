"""Test FaseB met verschillende port combinaties"""
import socket
import json
import time

IP = "192.168.6.213"

tests = [
    (30000, 28416, "bind 30000 send 28416"),
    (28416, 30000, "bind 28416 send 30000"),
    (28416, 28416, "bind 28416 send 28416"),
    (30000, 30000, "bind 30000 send 30000"),
]

request = {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
data = json.dumps(request).encode("utf-8")

print("="*60)
print(f" Testing FaseB (9a7d) - IP: {IP}")
print("="*60)

for bind_port, send_port, desc in tests:
    print(f"\n--- {desc} ---")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", bind_port))
        sock.settimeout(1.5)

        sock.sendto(data, (IP, send_port))
        resp, addr = sock.recvfrom(65535)
        response = json.loads(resp.decode("utf-8"))
        print(f"SUCCESS!")
        print(json.dumps(response, indent=2))
        sock.close()
        break
    except socket.timeout:
        print(f"TIMEOUT")
    except OSError as e:
        print(f"Socket Error: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        try:
            sock.close()
        except:
            pass
    time.sleep(0.5)

print("\n" + "="*60)
