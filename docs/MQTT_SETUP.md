# Home Assistant MQTT Setup Instructies

## Probleem Gevonden

MQTT broker geeft error code 5: **"Niet geautoriseerd"**

Dit betekent dat de Mosquitto broker authenticatie vereist, maar we hebben geen credentials opgegeven.

---

## Oplossing: MQTT Gebruiker Aanmaken

### Stap 1: Ga naar Mosquitto Add-on Settings

1. Open Home Assistant: http://homeassistant.local:8123
2. Ga naar **Settings** > **Add-ons**
3. Klik op **Mosquitto broker**
4. Klik op tabblad **Configuration**

### Stap 2: Gebruiker Aanmaken

Scroll naar beneden naar de sectie **"Logins"**

Je ziet iets als:
```yaml
logins: []
```

**Wijzig dit naar**:
```yaml
logins:
  - username: marstek
    password: jouw_wachtwoord_hier
```

**Belangrijk**:
- Kies een sterk wachtwoord
- Onthoud deze credentials (je hebt ze nodig voor de Python scripts)

### Stap 3: Save & Restart

1. Klik op **SAVE** (rechtsboven)
2. Ga naar tabblad **Info**
3. Klik op **RESTART** om Mosquitto opnieuw op te starten

Wacht ~10 seconden tot de broker weer draait.

---

## Alternatief: Home Assistant User Gebruiken

Als je al een Home Assistant user hebt, kun je die ook gebruiken:

1. Ga naar **Settings** > **People**
2. Klik op een bestaande user (of maak nieuwe aan)
3. Scroll naar beneden
4. Bij **"Allow person to login"** zorg dat dit aanstaat
5. Gebruik dezelfde username/password voor MQTT

**Let op**: Niet alle HA users werken automatisch met MQTT. De Mosquitto add-on heeft vaak specifieke logins nodig (methode hierboven).

---

## Stap 4: Update Python Script

Na het aanmaken van de MQTT user, update het `mqtt_test.py` script:

Open `mqtt_test.py` en wijzig bovenaan:

```python
MQTT_USER = "marstek"  # Of jouw gekozen username
MQTT_PASSWORD = "jouw_wachtwoord_hier"
```

---

## Stap 5: Test Opnieuw

Run het test script opnieuw:

```bash
python mqtt_test.py
```

Je zou nu moeten zien:
```
[OK] Verbonden met MQTT broker!
```

---

## Troubleshooting

### Error code 4: "Verkeerde username/password"
- Check of username en password correct zijn
- Let op hoofdletters/kleine letters
- Verifieer dat Mosquitto is gerestart na het toevoegen van de user

### Error code 3: "Server onbereikbaar"
- Check of Mosquitto add-on draait (Settings > Add-ons > Mosquitto broker)
- Probeer `ping homeassistant.local` in command prompt
- Probeer IP adres 192.168.0.139 in plaats van homeassistant.local

### Error code 5: "Niet geautoriseerd" (blijft)
- Verifieer dat MQTT integratie is geconfigureerd in HA
- Ga naar Settings > Devices & Services
- Zoek naar "MQTT" en check of het is ingesteld
- Probeer Mosquitto add-on volledig te stoppen en starten

---

## Beveiligingsnote

**BELANGRIJK**: Bewaar MQTT credentials veilig!

Voor productie gebruik:
1. Gebruik een configuratie bestand (niet hardcoded in Python)
2. Gebruik environment variables:
   ```python
   import os
   MQTT_USER = os.getenv("MQTT_USER", "")
   MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
   ```
3. Voeg config bestand toe aan `.gitignore`
