"""
MQTT Test Script - Verifieert Home Assistant MQTT connectie
"""
import json
import time
import socket
import random

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[WARNING] paho-mqtt niet geïnstalleerd!")
    print("          Installeer met: pip install paho-mqtt")

# Configuration
MQTT_BROKER = "192.168.0.139"  # Of "homeassistant.local" als hostname werkt
MQTT_PORT = 1883
MQTT_USER = "your_mqtt_username"  # Vul in als je authenticatie hebt
MQTT_PASSWORD = "your_mqtt_password"  # Vul in als je authenticatie hebt

# Test sensor configuratie
DEVICE_NAME = "marstek_test"
SENSOR_NAME = "test_sensor"


def resolve_hostname(hostname):
    """Probeer hostname op te lossen naar IP"""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"[OK] Hostname '{hostname}' resolved naar {ip}")
        return ip
    except socket.gaierror:
        print(f"[WARNING] Kon '{hostname}' niet resolven")
        print("          Probeer IP adres in plaats van hostname")
        return None


def on_connect(client, userdata, flags, rc):
    """Callback wanneer verbonden met MQTT broker"""
    if rc == 0:
        print("[OK] Verbonden met MQTT broker!")
        print(f"     Broker: {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"[ERROR] Connectie mislukt met code: {rc}")
        print("     0: Succes")
        print("     1: Verkeerde protocol versie")
        print("     2: Client ID geweigerd")
        print("     3: Server onbereikbaar")
        print("     4: Verkeerde username/password")
        print("     5: Niet geautoriseerd")


def on_publish(client, userdata, mid):
    """Callback wanneer bericht gepubliceerd is"""
    print(f"     > Bericht {mid} gepubliceerd")


def on_disconnect(client, userdata, rc):
    """Callback bij disconnect"""
    if rc != 0:
        print(f"[WARNING] Onverwachte disconnect: {rc}")


def test_mqtt_connection():
    """Test basis MQTT connectie"""
    print("="*60)
    print(" MQTT Connection Test")
    print("="*60)
    print()

    if not MQTT_AVAILABLE:
        print("[ERROR] paho-mqtt library niet beschikbaar")
        print("        Installeer met: pip install paho-mqtt")
        return False

    # Probeer hostname te resolven
    print(f"[>>] Resolving hostname...")
    resolve_hostname(MQTT_BROKER)
    print()

    # Maak client met unieke ID
    client_id = f"marstek_mqtt_test_{random.randint(1000, 9999)}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect

    # Authenticatie (als nodig)
    if MQTT_USER and MQTT_PASSWORD:
        print(f"[>>] Username/password authenticatie ingesteld")
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    try:
        print(f"[>>] Verbinden met {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(2)  # Wacht op connectie

        if not client.is_connected():
            print("\n[FAILED] Kon niet verbinden met MQTT broker")
            print("\nMogelijke oplossingen:")
            print("1. Check of Mosquitto add-on draait in Home Assistant")
            print("   > Settings > Add-ons > Mosquitto broker")
            print("2. Check of MQTT integratie geconfigureerd is")
            print("   > Settings > Devices & Services > MQTT")
            print("3. Verifieer hostname/IP adres klopt")
            print(f"   > Probeer: ping {MQTT_BROKER}")
            print("4. Check firewall instellingen (port 1883)")
            print("5. MQTT broker vereist mogelijk authenticatie")
            print("   > Stel MQTT_USER en MQTT_PASSWORD in bovenaan script")
            client.loop_stop()
            return False

        print()
        return client

    except Exception as e:
        print(f"[ERROR] {e}")
        print(f"\nMogelijke oorzaak: {type(e).__name__}")
        return False


def test_simple_publish(client):
    """Test simpel bericht publiceren"""
    print("\n" + "="*60)
    print(" Test 1: Simpel Bericht")
    print("="*60)
    print()

    topic = "marstek/test/message"
    payload = "Hello from Marstek API!"

    print(f"[>>] Publiceren naar topic: {topic}")
    print(f"     Payload: {payload}")

    result = client.publish(topic, payload)
    time.sleep(0.5)

    if result.rc == 0:
        print("[OK] Bericht succesvol gepubliceerd!")
        print(f"\nCheck in Home Assistant Developer Tools > MQTT:")
        print(f"   - Listen to: {topic}")
        print(f"   - Je zou het bericht moeten zien verschijnen")
        return True
    else:
        print(f"[ERROR] Publiceren mislukt: {result.rc}")
        return False


def test_autodiscovery_sensor(client):
    """Test Home Assistant MQTT autodiscovery"""
    print("\n" + "="*60)
    print(" Test 2: Home Assistant Autodiscovery")
    print("="*60)
    print()

    # Discovery topic volgens HA conventie
    discovery_topic = f"homeassistant/sensor/{DEVICE_NAME}/{SENSOR_NAME}/config"
    state_topic = f"marstek/{DEVICE_NAME}/{SENSOR_NAME}/state"

    # Discovery payload
    discovery_payload = {
        "name": "Marstek Test Sensor",
        "unique_id": f"{DEVICE_NAME}_{SENSOR_NAME}",
        "state_topic": state_topic,
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:battery",
        "device": {
            "identifiers": [DEVICE_NAME],
            "name": "Marstek Test Device",
            "manufacturer": "Marstek",
            "model": "Venus E",
            "sw_version": "Test v1.0"
        }
    }

    print(f"[>>] Publishing autodiscovery config...")
    print(f"     Topic: {discovery_topic}")

    result = client.publish(
        discovery_topic,
        json.dumps(discovery_payload),
        retain=True
    )

    if result.rc != 0:
        print(f"[ERROR] Discovery publiceren mislukt: {result.rc}")
        return False

    time.sleep(0.5)
    print("[OK] Discovery config gepubliceerd!")
    time.sleep(1)

    # Publiceer test waarde
    print(f"\n[>>] Publishing test values...")
    print(f"     Topic: {state_topic}")
    print()

    for i in range(5):
        test_value = 100 + (i * 50)  # 100, 150, 200, 250, 300 W
        print(f"     [{i+1}/5] Waarde: {test_value} W")

        result = client.publish(state_topic, test_value)

        if result.rc != 0:
            print(f"[ERROR] State publiceren mislukt: {result.rc}")
            return False

        time.sleep(2)

    print()
    print("[OK] Test waardes gepubliceerd!")
    print()
    print("="*60)
    print("Check in Home Assistant:")
    print("="*60)
    print("1. Ga naar Settings > Devices & Services > MQTT")
    print("2. Klik op 'X devices' (onder Mosquitto broker)")
    print("3. Zoek naar 'Marstek Test Device'")
    print("4. Je zou een sensor moeten zien: 'Marstek Test Sensor'")
    print("5. De waarde zou moeten zijn: 300 W")
    print()
    print("Of voeg toe aan dashboard:")
    print("- Type: Entity")
    print("- Entity: sensor.marstek_test_sensor")

    return True


def cleanup_test_sensor(client):
    """Verwijder test sensor uit Home Assistant"""
    print("\n" + "="*60)
    print(" Cleanup: Test Sensor Verwijderen")
    print("="*60)
    print()

    discovery_topic = f"homeassistant/sensor/{DEVICE_NAME}/{SENSOR_NAME}/config"

    print("[>>] Verwijderen van test sensor...")
    print(f"     Topic: {discovery_topic}")

    # Lege payload met retain=True verwijdert de discovery
    result = client.publish(discovery_topic, "", retain=True)
    time.sleep(0.5)

    if result.rc == 0:
        print("[OK] Test sensor verwijderd uit Home Assistant")
        print("     (kan 1-2 minuten duren voordat verdwenen in UI)")
    else:
        print(f"[ERROR] Verwijderen mislukt: {result.rc}")


if __name__ == "__main__":
    print("\n")
    print("="*60)
    print("    Marstek Venus - Home Assistant MQTT Test")
    print("="*60)
    print()

    if not MQTT_AVAILABLE:
        print("\n[STOP] Installeer eerst paho-mqtt:")
        print("       pip install paho-mqtt")
        print()
        exit(1)

    # Test 1: Verbinding
    client = test_mqtt_connection()
    if not client:
        print("\n[FAILED] MQTT connectie test mislukt. Stop hier.")
        print()
        exit(1)

    time.sleep(1)

    # Test 2: Simpel bericht
    if not test_simple_publish(client):
        print("\n[FAILED] Simpel bericht test mislukt.")
        client.disconnect()
        client.loop_stop()
        exit(1)

    time.sleep(1)

    # Test 3: Autodiscovery
    if test_autodiscovery_sensor(client):
        print("\n[SUCCESS] Alle tests geslaagd! ✓")

        # Vraag of sensor verwijderd moet worden
        print("\n" + "="*60)
        try:
            input("\nDruk op Enter om de test sensor te verwijderen (of Ctrl+C om te stoppen)...")
            cleanup_test_sensor(client)
        except KeyboardInterrupt:
            print("\n\n[>>] Test sensor blijft staan in Home Assistant")
            print("     Verwijder handmatig via MQTT integration")

    # Disconnect
    time.sleep(1)
    print("\n[>>] Disconnecting...")
    client.disconnect()
    client.loop_stop()

    print("\n✓ MQTT test voltooid!\n")
