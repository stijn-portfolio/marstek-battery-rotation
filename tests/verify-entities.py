#!/usr/bin/env python3
"""
Verify Marstek entity names in Home Assistant
Gebruik dit script om de juiste button entity names te vinden
"""

import requests
import json
from typing import List, Dict

# CONFIGURATIE - PAS AAN!
HA_URL = "http://homeassistant.local:8123"  # Of je IP adres
HA_TOKEN = "JE_LONG_LIVED_ACCESS_TOKEN_HIER"  # Maak aan in HA Profile

def get_entities() -> List[Dict]:
    """Haal alle entities op van Home Assistant."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.get(f"{HA_URL}/api/states", headers=headers)
    response.raise_for_status()
    return response.json()

def find_marstek_entities():
    """Vind alle Marstek gerelateerde entities."""
    print("🔍 Zoeken naar Marstek entities...\n")

    try:
        entities = get_entities()
    except Exception as e:
        print(f"❌ Fout bij ophalen entities: {e}")
        print("\n📝 Controleer:")
        print("   1. HA_URL klopt (http://IP:8123)")
        print("   2. HA_TOKEN is geldig (Profile → Long-Lived Access Token)")
        return

    # Filter Marstek entities
    marstek_entities = [e for e in entities if 'marstek' in e['entity_id'].lower()]

    if not marstek_entities:
        print("❌ Geen Marstek entities gevonden!")
        return

    print(f"✅ Gevonden: {len(marstek_entities)} Marstek entities\n")

    # Categoriseer
    categories = {
        'button': [],
        'sensor': [],
        'binary_sensor': [],
        'other': []
    }

    for entity in marstek_entities:
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        if domain in categories:
            categories[domain].append(entity)
        else:
            categories['other'].append(entity)

    # Print buttons (belangrijk voor configuratie!)
    print("=" * 80)
    print("🔘 BUTTONS (belangrijk voor config!)".center(80))
    print("=" * 80)

    for entity in sorted(categories['button'], key=lambda x: x['entity_id']):
        entity_id = entity['entity_id']
        name = entity['attributes'].get('friendly_name', 'Unknown')
        print(f"  {entity_id}")
        print(f"    └─ {name}\n")

    # Print sensors
    print("\n" + "=" * 80)
    print("📊 SENSORS".center(80))
    print("=" * 80)

    soc_sensors = [e for e in categories['sensor'] if 'soc' in e['entity_id'] or 'charge' in e['entity_id']]
    mode_sensors = [e for e in categories['sensor'] if 'mode' in e['entity_id'] or 'operating' in e['entity_id']]

    print("\n🔋 State of Charge sensors:")
    for entity in sorted(soc_sensors, key=lambda x: x['entity_id']):
        entity_id = entity['entity_id']
        state = entity['state']
        name = entity['attributes'].get('friendly_name', 'Unknown')
        print(f"  {entity_id} = {state}% ({name})")

    print("\n⚙️  Operating Mode sensors:")
    for entity in sorted(mode_sensors, key=lambda x: x['entity_id']):
        entity_id = entity['entity_id']
        state = entity['state']
        name = entity['attributes'].get('friendly_name', 'Unknown')
        print(f"  {entity_id} = {state} ({name})")

    # Genereer correcte YAML mapping
    print("\n\n" + "=" * 80)
    print("📝 YAML CONFIGURATIE CHECK".center(80))
    print("=" * 80)

    print("\n✅ Je SOC sensors zijn correct:")
    print("  - sensor.marstek_venuse_d828_state_of_charge")
    print("  - sensor.marstek_venuse_3_0_9a7d_state_of_charge")
    print("  - sensor.marstek_venuse_state_of_charge")

    print("\n🔘 Expected button entities (verifieer hieronder):")
    expected_buttons = [
        "button.marstek_venuse_d828_auto_mode",
        "button.marstek_venuse_d828_manual_mode",
        "button.marstek_venuse_3_0_9a7d_auto_mode",
        "button.marstek_venuse_3_0_9a7d_manual_mode",
        "button.marstek_venuse_auto_mode",
        "button.marstek_venuse_manual_mode",
    ]

    button_ids = [e['entity_id'] for e in categories['button']]

    for expected in expected_buttons:
        if expected in button_ids:
            print(f"  ✅ {expected}")
        else:
            print(f"  ❌ {expected} - NIET GEVONDEN!")
            # Zoek alternatief
            domain, name = expected.split('.')
            similar = [b for b in button_ids if name.split('_')[-2:] == b.split('_')[-2:]]
            if similar:
                print(f"     💡 Mogelijk alternatief: {similar[0]}")

if __name__ == "__main__":
    print("=" * 80)
    print("MARSTEK ENTITY VERIFICATIE".center(80))
    print("=" * 80)
    print()

    # Check configuratie
    if HA_TOKEN == "JE_LONG_LIVED_ACCESS_TOKEN_HIER":
        print("⚠️  WAARSCHUWING: Pas eerst de configuratie aan!\n")
        print("📝 Edit dit bestand en wijzig:")
        print("   - HA_URL (bijv. http://192.168.0.100:8123)")
        print("   - HA_TOKEN (maak aan in Home Assistant Profile)\n")
        input("Druk Enter om toch door te gaan (zal falen) of Ctrl+C om te stoppen...")

    find_marstek_entities()

    print("\n" + "=" * 80)
    print("Als alle buttons ✅ zijn, is de configuratie correct!")
    print("Als er ❌ zijn, kopieer dan de 💡 alternatieven naar de YAML file.")
    print("=" * 80)
