#!/usr/bin/env python3
"""
Marstek MQTT Poller

Lightweight poller die ES.GetMode gebruikt (de enige betrouwbare API method)
en SOC/mode data publiceert naar MQTT met Home Assistant auto-discovery.

Gebruik:
    python marstek_poller.py [--config config.yaml]

Author: Marstek Battery Rotation Project
License: MIT
"""

import socket
import json
import time
import signal
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Optional imports
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("WARNING: paho-mqtt not installed. Install with: pip install paho-mqtt")

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("WARNING: PyYAML not installed. Install with: pip install pyyaml")


# Default configuration
DEFAULT_CONFIG = {
    "batteries": [
        {
            "name": "Fase A",
            "ip": "192.168.6.80",
            "entity_id": "marstek_venuse_d828_state_of_charge",
            "device_id": "marstek_fasea_d828"
        },
        {
            "name": "Fase B",
            "ip": "192.168.6.213",
            "entity_id": "marstek_venuse_3_0_9a7d_state_of_charge",
            "device_id": "marstek_faseb_9a7d"
        },
        {
            "name": "Fase C",
            "ip": "192.168.6.144",
            "entity_id": "marstek_venuse_state_of_charge",
            "device_id": "marstek_fasec_deb8"
        }
    ],
    "mqtt": {
        "host": "localhost",
        "port": 1883,
        "username": "",
        "password": "",
        "discovery_prefix": "homeassistant",
        "state_topic_prefix": "marstek"
    },
    "polling": {
        "interval_seconds": 30,
        "timeout_seconds": 3
    },
    "api": {
        "port": 30000
    },
    "logging": {
        "level": "INFO"
    }
}


class MarstekPoller:
    """Polls Marstek batteries via ES.GetMode and publishes to MQTT."""

    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self.mqtt_client = None
        self.mqtt_connected = False
        self.request_id = 1

        # Setup logging
        log_level = config.get("logging", {}).get("level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger("marstek_poller")

    def setup_mqtt(self) -> bool:
        """Initialize MQTT connection."""
        if not MQTT_AVAILABLE:
            self.logger.error("MQTT not available. Install paho-mqtt.")
            return False

        mqtt_config = self.config.get("mqtt", {})

        # Use CallbackAPIVersion.VERSION2 to avoid deprecation warning
        try:
            self.mqtt_client = mqtt.Client(
                client_id="marstek_poller",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except (AttributeError, TypeError):
            # Fallback for older paho-mqtt versions
            self.mqtt_client = mqtt.Client(client_id="marstek_poller")

        # Set callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

        # Set credentials if provided
        username = mqtt_config.get("username", "")
        password = mqtt_config.get("password", "")
        if username:
            self.mqtt_client.username_pw_set(username, password)

        # Connect
        host = mqtt_config.get("host", "localhost")
        port = mqtt_config.get("port", 1883)

        try:
            self.logger.info(f"Connecting to MQTT broker at {host}:{port}")
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.loop_start()

            # Wait for connection
            for _ in range(10):
                if self.mqtt_connected:
                    return True
                time.sleep(0.5)

            self.logger.error("MQTT connection timeout")
            return False

        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            return False

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        """MQTT connect callback (VERSION2 compatible)."""
        # reason_code is 0 or ReasonCode object with value 0 on success
        rc_value = int(reason_code) if hasattr(reason_code, '__int__') else reason_code
        if rc_value == 0:
            self.mqtt_connected = True
            self.logger.info("Connected to MQTT broker")
            # Publish discovery configs
            self._publish_discovery()
        else:
            self.logger.error(f"MQTT connection failed with code {rc_value}")

    def _on_mqtt_disconnect(self, client, userdata, flags_or_rc, reason_code=None, properties=None):
        """MQTT disconnect callback (VERSION2 compatible)."""
        self.mqtt_connected = False
        # Handle both VERSION1 (rc as 3rd param) and VERSION2 (reason_code as 4th param)
        rc = reason_code if reason_code is not None else flags_or_rc
        self.logger.warning(f"Disconnected from MQTT broker (rc={rc})")

    def _publish_discovery(self):
        """Publish Home Assistant MQTT auto-discovery configs."""
        discovery_prefix = self.config.get("mqtt", {}).get("discovery_prefix", "homeassistant")
        state_prefix = self.config.get("mqtt", {}).get("state_topic_prefix", "marstek")

        for battery in self.config.get("batteries", []):
            device_id = battery.get("device_id", battery["name"].lower().replace(" ", "_"))
            entity_id = battery.get("entity_id", f"marstek_{device_id}_soc")
            name = battery.get("name", device_id)

            # SOC sensor discovery
            soc_config = {
                "name": f"{name} SOC",
                "state_topic": f"{state_prefix}/{device_id}/state",
                "value_template": "{{ value_json.soc }}",
                "unit_of_measurement": "%",
                "device_class": "battery",
                "state_class": "measurement",
                "unique_id": entity_id,
                "object_id": entity_id,
                "device": {
                    "identifiers": [device_id],
                    "name": f"Marstek {name}",
                    "manufacturer": "Marstek",
                    "model": "Venus E"
                },
                "availability": {
                    "topic": f"{state_prefix}/{device_id}/availability",
                    "payload_available": "online",
                    "payload_not_available": "offline"
                }
            }

            # Mode sensor discovery
            mode_entity_id = entity_id.replace("state_of_charge", "mode").replace("_soc", "_mode")
            mode_config = {
                "name": f"{name} Mode",
                "state_topic": f"{state_prefix}/{device_id}/state",
                "value_template": "{{ value_json.mode }}",
                "unique_id": mode_entity_id,
                "object_id": mode_entity_id,
                "icon": "mdi:battery-sync",
                "device": {
                    "identifiers": [device_id],
                    "name": f"Marstek {name}",
                    "manufacturer": "Marstek",
                    "model": "Venus E"
                }
            }

            # Power sensor discovery
            power_entity_id = entity_id.replace("state_of_charge", "power").replace("_soc", "_power")
            power_config = {
                "name": f"{name} Power",
                "state_topic": f"{state_prefix}/{device_id}/state",
                "value_template": "{{ value_json.ongrid_power }}",
                "unit_of_measurement": "W",
                "device_class": "power",
                "state_class": "measurement",
                "unique_id": power_entity_id,
                "object_id": power_entity_id,
                "device": {
                    "identifiers": [device_id],
                    "name": f"Marstek {name}",
                    "manufacturer": "Marstek",
                    "model": "Venus E"
                }
            }

            # Publish discovery configs
            self.mqtt_client.publish(
                f"{discovery_prefix}/sensor/{device_id}_soc/config",
                json.dumps(soc_config),
                retain=True
            )
            self.mqtt_client.publish(
                f"{discovery_prefix}/sensor/{device_id}_mode/config",
                json.dumps(mode_config),
                retain=True
            )
            self.mqtt_client.publish(
                f"{discovery_prefix}/sensor/{device_id}_power/config",
                json.dumps(power_config),
                retain=True
            )

            self.logger.info(f"Published discovery config for {name}")

    def query_battery(self, ip: str, sock: socket.socket = None) -> dict | None:
        """Query a single battery using ES.GetMode."""
        api_port = self.config.get("api", {}).get("port", 30000)
        timeout = self.config.get("polling", {}).get("timeout_seconds", 3)

        # Create request
        request = {
            "id": self.request_id,
            "method": "ES.GetMode",
            "params": {"id": 0}
        }
        self.request_id += 1

        own_socket = sock is None
        try:
            # Create UDP socket if not provided
            if own_socket:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, 'SO_REUSEPORT'):
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                sock.bind(("0.0.0.0", api_port))

            sock.settimeout(timeout)

            # Send request
            data = json.dumps(request).encode("utf-8")
            sock.sendto(data, (ip, api_port))

            # Receive response
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    resp, addr = sock.recvfrom(65535)
                    response = json.loads(resp.decode("utf-8"))

                    # Skip echo
                    if response == request:
                        continue

                    # Check for result
                    if "result" in response:
                        return response["result"]
                    elif "error" in response:
                        self.logger.warning(f"API error from {ip}: {response['error']}")
                        return None

                except socket.timeout:
                    break
                except json.JSONDecodeError:
                    continue

            return None

        except Exception as e:
            self.logger.error(f"Error querying {ip}: {e}")
            return None
        finally:
            if own_socket and sock:
                sock.close()

    def poll_all_batteries(self):
        """Poll all batteries and publish results."""
        state_prefix = self.config.get("mqtt", {}).get("state_topic_prefix", "marstek")
        api_port = self.config.get("api", {}).get("port", 30000)
        batteries = self.config.get("batteries", [])

        # Create one socket for all batteries
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(("0.0.0.0", api_port))

            for battery in batteries:
                name = battery.get("name", "Unknown")
                ip = battery.get("ip")
                device_id = battery.get("device_id", name.lower().replace(" ", "_"))

                if not ip:
                    self.logger.warning(f"No IP configured for {name}")
                    continue

                # Query battery using shared socket
                result = self.query_battery(ip, sock)

                availability_topic = f"{state_prefix}/{device_id}/availability"
                state_topic = f"{state_prefix}/{device_id}/state"

                if result:
                    # Publish state
                    state = {
                        "soc": result.get("bat_soc", 0),
                        "mode": result.get("mode", "Unknown"),
                        "ongrid_power": result.get("ongrid_power", 0),
                        "offgrid_power": result.get("offgrid_power", 0),
                        "timestamp": datetime.now().isoformat()
                    }

                    self.mqtt_client.publish(state_topic, json.dumps(state))
                    self.mqtt_client.publish(availability_topic, "online")

                    self.logger.debug(f"{name}: SOC={state['soc']}%, Mode={state['mode']}")
                else:
                    # Mark as offline
                    self.mqtt_client.publish(availability_topic, "offline")
                    self.logger.warning(f"{name} ({ip}): No response")

        except OSError as e:
            self.logger.error(f"Socket error: {e}")
        finally:
            if sock:
                sock.close()

    def run(self):
        """Main polling loop."""
        self.running = True
        interval = self.config.get("polling", {}).get("interval_seconds", 30)

        self.logger.info(f"Starting polling loop (interval: {interval}s)")

        while self.running:
            try:
                if self.mqtt_connected:
                    self.poll_all_batteries()
                else:
                    self.logger.warning("MQTT not connected, skipping poll")

            except Exception as e:
                self.logger.error(f"Polling error: {e}")

            # Sleep in small increments for faster shutdown
            for _ in range(interval * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def stop(self):
        """Stop the poller."""
        self.logger.info("Stopping poller...")
        self.running = False

        # Mark all batteries offline
        if self.mqtt_client and self.mqtt_connected:
            state_prefix = self.config.get("mqtt", {}).get("state_topic_prefix", "marstek")
            for battery in self.config.get("batteries", []):
                device_id = battery.get("device_id", battery["name"].lower().replace(" ", "_"))
                self.mqtt_client.publish(f"{state_prefix}/{device_id}/availability", "offline")

            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


def load_config(config_path: str | None) -> dict:
    """Load configuration from file or use defaults."""
    if config_path and Path(config_path).exists():
        if not YAML_AVAILABLE:
            print("ERROR: PyYAML required to load config file")
            sys.exit(1)

        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)

        # Merge with defaults
        config = DEFAULT_CONFIG.copy()
        for key, value in user_config.items():
            if isinstance(value, dict) and key in config:
                config[key].update(value)
            else:
                config[key] = value

        return config
    else:
        print("Using default configuration")
        return DEFAULT_CONFIG


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Marstek MQTT Poller")
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: poll once and exit"
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Create poller
    poller = MarstekPoller(config)

    # Setup signal handlers
    def signal_handler(signum, frame):
        poller.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Test mode
    if args.test:
        print("\n=== TEST MODE ===\n")
        for battery in config.get("batteries", []):
            name = battery.get("name")
            ip = battery.get("ip")
            print(f"Testing {name} ({ip})...")
            result = poller.query_battery(ip)
            if result:
                print(f"  ✅ SOC: {result.get('bat_soc')}%, Mode: {result.get('mode')}")
            else:
                print(f"  ❌ No response")
            # Delay between tests to allow socket port to be fully released
            time.sleep(1.0)
        print("\n=== TEST COMPLETE ===")
        return

    # Setup MQTT
    if not poller.setup_mqtt():
        print("Failed to connect to MQTT broker")
        sys.exit(1)

    # Run polling loop
    try:
        poller.run()
    finally:
        poller.stop()


if __name__ == "__main__":
    main()
