#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script om slot 0 te clearen voor alle drie de Marstek batterijen."""

import asyncio
import json
import logging
import socket
import sys
import time

# Logging configuratie
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

# Batterij configuratie
BATTERIES = [
    {"name": "Fase A (schuin - d828)", "ip": "192.168.6.80"},
    {"name": "Fase B (plat - 9a7d)", "ip": "192.168.6.213"},
    {"name": "Fase C (geen - deb8)", "ip": "192.168.6.144"},
]

# API constanten
PORT = 30000
TIMEOUT = 2.0
MODE_MANUAL = "Manual"


class SimpleMarstekClient:
    """Eenvoudige UDP client voor Marstek batterijen."""

    def __init__(self, host: str, port: int = PORT):
        """Initialiseer de client."""
        self.host = host
        self.port = port
        self.sock = None
        self._msg_id = 0

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def connect(self):
        """Maak verbinding."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", PORT))
        self.sock.settimeout(TIMEOUT)
        _LOGGER.debug(f"Socket gebonden op 0.0.0.0:{PORT}")

    def disconnect(self):
        """Verbreek verbinding."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send_command(self, method: str, params: dict, max_retries: int = 3) -> dict | None:
        """Verstuur een command en wacht op response."""
        if not self.sock:
            raise RuntimeError("Niet verbonden")

        self._msg_id += 1
        payload = {
            "id": self._msg_id,
            "method": method,
            "params": params,
        }

        payload_str = json.dumps(payload)

        for attempt in range(max_retries):
            _LOGGER.debug(f"Verzenden naar {self.host}:{self.port} (poging {attempt+1}/{max_retries}): {payload_str}")

            # Verstuur command
            self.sock.sendto(payload_str.encode(), (self.host, self.port))

            # Wacht op response(s) - batterij kan meerdere packets sturen
            try:
                # Verzamel alle responses binnen timeout periode
                start_time = time.time()
                responses = []

                while time.time() - start_time < TIMEOUT:
                    try:
                        self.sock.settimeout(0.5)
                        resp_data, addr = self.sock.recvfrom(65535)

                        # Skip echo's (batterij stuurt soms request terug)
                        if resp_data.decode() == payload_str:
                            _LOGGER.debug("Echo ontvangen, negeren")
                            continue

                        response = json.loads(resp_data.decode())
                        responses.append(response)

                        # Check of dit de juiste response is
                        if response.get("id") == self._msg_id:
                            if "error" in response:
                                error = response["error"]
                                _LOGGER.error(f"API fout: {error}")
                                return None
                            if "result" in response:
                                _LOGGER.debug(f"Geldig antwoord ontvangen: {response}")
                                return response.get("result")

                    except socket.timeout:
                        continue
                    except json.JSONDecodeError as e:
                        _LOGGER.warning(f"JSON decode fout: {e}")
                        continue

                # Geen geldige response gevonden
                if responses:
                    _LOGGER.warning(f"Responses ontvangen maar geen match: {responses}")

                if attempt < max_retries - 1:
                    _LOGGER.info(f"Opnieuw proberen over 0.5s...")
                    time.sleep(0.5)

            except Exception as e:
                _LOGGER.error(f"Onverwachte fout: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)

        _LOGGER.error(f"Geen geldige response na {max_retries} pogingen van {self.host}")
        return None

    def set_es_mode(self, config: dict) -> bool:
        """Stel energy system mode in."""
        result = self.send_command(
            "ES.SetMode",
            {"id": 0, "config": config}
        )

        if result and result.get("set_result"):
            return True
        return False


def clear_slot_0(battery: dict) -> bool:
    """Clear slot 0 voor een batterij."""
    print(f"\n{'='*80}")
    print(f"Clearing slot 0 voor: {battery['name']}")
    print(f"IP adres: {battery['ip']}")
    print(f"{'='*80}")

    config = {
        "mode": MODE_MANUAL,
        "manual_cfg": {
            "time_num": 0,
            "start_time": "00:00",
            "end_time": "00:00",
            "week_set": 0,  # Geen dagen
            "power": 0,
            "enable": 0,  # Uitgeschakeld
        },
    }

    try:
        with SimpleMarstekClient(battery['ip']) as client:
            success = client.set_es_mode(config)

            if success:
                print(f"[OK] Slot 0 succesvol gecleared voor {battery['name']}")
                return True
            else:
                print(f"[FOUT] Batterij weigerde slot 0 te clearen voor {battery['name']}")
                return False

    except Exception as e:
        print(f"[FOUT] Fout bij clearen van slot 0 voor {battery['name']}: {e}")
        _LOGGER.exception("Uitgebreide fout informatie:")
        return False


def main():
    """Main functie."""
    print("Marstek Batterij - Clear Slot 0")
    print("=" * 80)
    print("Dit script cleared slot 0 voor alle drie de batterijen")
    print()

    results = {}
    for battery in BATTERIES:
        result = clear_slot_0(battery)
        results[battery['name']] = result

    # Samenvatting
    print(f"\n{'='*80}")
    print("SAMENVATTING")
    print(f"{'='*80}")

    for name, success in results.items():
        status = "[OK] Succesvol" if success else "[FOUT] Mislukt"
        print(f"{name}: {status}")

    # Exit code
    all_success = all(results.values())
    if all_success:
        print("\n[OK] Alle batterijen succesvol gecleared!")
        sys.exit(0)
    else:
        print("\n[WAARSCHUWING] Sommige batterijen konden niet worden gecleared")
        sys.exit(1)


if __name__ == "__main__":
    main()
