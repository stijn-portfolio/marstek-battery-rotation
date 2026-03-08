# MQTT Poller voor Marstek Batterijen

Lightweight Python service die Marstek batterijen pollt via de **enige betrouwbare API method** (`ES.GetMode`) en de data publiceert naar MQTT met Home Assistant auto-discovery.

---

## Waarom Deze Poller?

### Het Probleem

De standaard Marstek Local API Home Assistant integratie gebruikt `ES.GetStatus` om batterij data op te halen. **Dit faalt op veel Marstek batterijen** (inclusief Venus E v3):

| Method | Fase A (v155) | Fase B V3 (v139) | Fase C (v155) |
|--------|:-------------:|:----------------:|:-------------:|
| ES.GetStatus | ❌ TIMEOUT | ❌ TIMEOUT | ❌ TIMEOUT |
| ES.GetMode | ✅ | ✅ | ✅ |

**Gevolgen van timeouts:**
- Elke timeout duurt 15 sec x 3 retries = 45 seconden per batterij
- Dit veroorzaakt stress op de batterij
- Kan leiden tot batterij lockups (batterij wordt onbereikbaar)
- HA krijgt geen SOC data → battery rotation werkt niet

### De Oplossing

Deze poller gebruikt **alleen ES.GetMode** - de enige method die betrouwbaar werkt op alle geteste batterijen.

`ES.GetMode` geeft:
- `bat_soc` - State of Charge (%)
- `mode` - Huidige modus (Auto/Manual/AI/Passive)
- `ongrid_power` - Grid power (W)
- `offgrid_power` - Off-grid power (W)

Dit is **alles wat nodig is** voor battery rotation!

---

## Architectuur

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │ marstek_poller.py│ ──UDP──►│ 3x Marstek       │             │
│  │                  │◄────────│ Batteries        │             │
│  │ ES.GetMode ONLY  │         │                  │             │
│  │ Timeout: 3 sec   │         │ - 192.168.6.80   │             │
│  │ Interval: 30 sec │         │ - 192.168.6.213  │             │
│  └────────┬─────────┘         │ - 192.168.6.144  │             │
│           │                   └──────────────────┘             │
│           │ MQTT publish                                        │
│           ▼                                                     │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │ MQTT Broker      │────────►│ Home Assistant   │             │
│  │ (Mosquitto)      │         │                  │             │
│  │                  │         │ Auto-discovery:  │             │
│  │ Topics:          │         │ - sensor.marstek_│             │
│  │ marstek/*/state  │         │   venuse_*_soc   │             │
│  └──────────────────┘         └──────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Installatie

### Vereisten

- Python 3.8+
- MQTT Broker (bijv. Mosquitto) - meestal al aanwezig op HA
- Netwerk toegang tot Marstek batterijen (UDP port 30000)

### Optie 1: Automatische Installatie (Linux/HA OS)

```bash
# Download of clone repository
git clone https://github.com/SDBeu/marstek-battery-rotation.git
cd marstek-battery-rotation/poller

# Installeer als systemd service
sudo ./install.sh

# Pas configuratie aan
sudo nano /opt/marstek-poller/config.yaml

# Herstart service
sudo systemctl restart marstek-poller
```

### Optie 2: Handmatige Installatie

```bash
# 1. Installeer dependencies
pip3 install paho-mqtt pyyaml

# 2. Kopieer bestanden
mkdir -p /opt/marstek-poller
cp marstek_poller.py /opt/marstek-poller/
cp config.yaml /opt/marstek-poller/

# 3. Pas config aan
nano /opt/marstek-poller/config.yaml

# 4. Test
python3 /opt/marstek-poller/marstek_poller.py --test

# 5. Installeer service (optioneel)
cp marstek-poller.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable marstek-poller
systemctl start marstek-poller
```

### Optie 3: Draaien op Windows (voor testen)

```powershell
# Installeer dependencies
pip install paho-mqtt pyyaml

# Pas config aan
notepad config.yaml

# Test modus
python marstek_poller.py --test

# Draai poller
python marstek_poller.py --config config.yaml
```

---

## Configuratie

### config.yaml

```yaml
# Batterij Configuratie
batteries:
  - name: "Fase A"
    ip: "192.168.6.80"
    # BELANGRIJK: entity_id moet matchen met battery-rotation.yaml!
    entity_id: "marstek_venuse_d828_state_of_charge"
    device_id: "marstek_fasea_d828"

  - name: "Fase B"
    ip: "192.168.6.213"
    entity_id: "marstek_venuse_3_0_9a7d_state_of_charge"
    device_id: "marstek_faseb_9a7d"

  - name: "Fase C"
    ip: "192.168.6.144"
    entity_id: "marstek_venuse_state_of_charge"
    device_id: "marstek_fasec_deb8"

# MQTT Broker
mqtt:
  host: "192.168.6.1"    # IP van je MQTT broker (of "localhost")
  port: 1883
  username: "mqtt_user"   # Leeg laten als geen auth
  password: "mqtt_pass"
  discovery_prefix: "homeassistant"
  state_topic_prefix: "marstek"

# Polling
polling:
  interval_seconds: 30    # Elke 30 seconden pollen
  timeout_seconds: 3      # 3 sec timeout (voorkomt lockups!)

# Logging
logging:
  level: "INFO"           # DEBUG voor troubleshooting
```

### Entity ID Matching

**Belangrijk:** De `entity_id` in config.yaml moet matchen met de entity names in `battery-rotation.yaml`!

De battery rotation template sensors gebruiken:
```yaml
states('sensor.marstek_venuse_d828_state_of_charge')      # Fase A
states('sensor.marstek_venuse_3_0_9a7d_state_of_charge')  # Fase B
states('sensor.marstek_venuse_state_of_charge')           # Fase C
```

Door dezelfde entity_id te gebruiken in de poller, werkt battery rotation **zonder aanpassingen**!

---

## Home Assistant Integratie

### Automatische Sensors (via MQTT Discovery)

De poller publiceert auto-discovery configs naar MQTT. Na starten verschijnen automatisch:

**Per batterij:**
- `sensor.marstek_venuse_*_state_of_charge` - SOC (%)
- `sensor.marstek_*_mode` - Modus (Auto/Manual/AI/Passive)
- `sensor.marstek_*_power` - Power (W)

### MQTT Topics

```
# State topics (JSON payload)
marstek/marstek_fasea_d828/state
marstek/marstek_faseb_9a7d/state
marstek/marstek_fasec_deb8/state

# Availability topics
marstek/marstek_fasea_d828/availability  (online/offline)
marstek/marstek_faseb_9a7d/availability
marstek/marstek_fasec_deb8/availability

# Discovery topics (auto-discovery configs)
homeassistant/sensor/marstek_fasea_d828_soc/config
homeassistant/sensor/marstek_fasea_d828_mode/config
homeassistant/sensor/marstek_fasea_d828_power/config
# etc...
```

### State Payload Voorbeeld

```json
{
  "soc": 75,
  "mode": "Auto",
  "ongrid_power": 1200,
  "offgrid_power": 0,
  "timestamp": "2024-11-21T20:15:00"
}
```

---

## Gebruik

### Service Commando's

```bash
# Status bekijken
sudo systemctl status marstek-poller

# Logs bekijken (live)
sudo journalctl -u marstek-poller -f

# Logs bekijken (laatste 100 regels)
sudo journalctl -u marstek-poller -n 100

# Herstarten
sudo systemctl restart marstek-poller

# Stoppen
sudo systemctl stop marstek-poller

# Uitschakelen (niet starten bij boot)
sudo systemctl disable marstek-poller
```

### Test Modus

Test de verbinding met batterijen zonder MQTT:

```bash
python3 marstek_poller.py --test
```

Output:
```
=== TEST MODE ===

Testing Fase A (192.168.6.80)...
  ✅ SOC: 45%, Mode: Manual
Testing Fase B (192.168.6.213)...
  ✅ SOC: 100%, Mode: Auto
Testing Fase C (192.168.6.144)...
  ✅ SOC: 67%, Mode: Manual

=== TEST COMPLETE ===
```

### Debug Logging

Voor meer details, zet log level op DEBUG in config.yaml:

```yaml
logging:
  level: "DEBUG"
```

Herstart de service:
```bash
sudo systemctl restart marstek-poller
```

---

## Troubleshooting

### Probleem: Geen MQTT verbinding

**Symptoom:** Logs tonen "MQTT connection failed"

**Oplossingen:**
1. Check MQTT broker draait: `sudo systemctl status mosquitto`
2. Check IP/port in config.yaml
3. Check credentials (username/password)
4. Test met `mosquitto_sub -h localhost -t "marstek/#" -v`

### Probleem: Batterij timeout

**Symptoom:** Logs tonen "No response" voor een batterij

**Oplossingen:**
1. Ping batterij: `ping 192.168.6.80`
2. Check firewall: UDP port 30000 moet open zijn
3. Check batterij IP (kan gewijzigd zijn na DHCP)
4. Local API moet enabled zijn op batterij

### Probleem: Sensors verschijnen niet in HA

**Symptoom:** Na starten poller, geen nieuwe sensors in HA

**Oplossingen:**
1. Check MQTT integratie in HA is geconfigureerd
2. Check discovery prefix matcht: `homeassistant` (default)
3. Bekijk MQTT Explorer of `mosquitto_sub` voor berichten
4. Restart HA na eerste discovery

### Probleem: SOC sensor heeft verkeerde entity_id

**Symptoom:** Battery rotation vindt de sensor niet

**Oplossing:**
1. Check `entity_id` in config.yaml
2. Moet exact matchen met battery-rotation.yaml
3. Na wijziging: herstart poller EN HA (discovery opnieuw)

---

## Vergelijking met HA Integratie

| Aspect | HA Integratie | MQTT Poller |
|--------|---------------|-------------|
| API Method | ES.GetStatus (faalt vaak) | ES.GetMode (werkt altijd) |
| Timeout | 15 sec x 3 retries | 3 sec (configureerbaar) |
| Batterij stress | Hoog (lange timeouts) | Laag (snelle timeout) |
| SOC sensor | ✅ | ✅ |
| Mode sensor | ✅ | ✅ |
| Power sensor | ✅ | ✅ |
| Energy counters | ✅ | ❌ (niet nodig voor rotation) |
| Mode control | ✅ (buttons) | ❌ (gebruik shell_commands) |
| Setup complexiteit | Makkelijk | Medium |
| Betrouwbaarheid | Laag (timeouts) | Hoog |

**Aanbeveling:** Gebruik de MQTT poller voor SOC sensors, en bestaande shell_commands voor mode control.

---

## Mode Control (ES.SetMode)

De poller is alleen voor **lezen** van data. Voor mode control (Auto/Manual switching) gebruik je de bestaande shell_commands:

```yaml
# In shell_commands.yaml
marstek_fasea_auto: "python test_tool.py --ip 192.168.6.80 set-mode auto"
marstek_fasea_manual: "python test_tool.py --ip 192.168.6.80 set-mode manual"
# etc...
```

Deze werken al en hoeven niet gewijzigd te worden!

---

## Migratie van HA Integratie

### Stap 1: Disable HA Integratie

1. Ga naar **Settings → Devices & Services → Marstek Local API**
2. Klik op de 3 dots → **Delete**
3. Herstart HA

### Stap 2: Installeer MQTT Poller

Volg de installatie instructies hierboven.

### Stap 3: Verify Sensors

Na installatie, check in HA:
- **Developer Tools → States**
- Zoek naar `sensor.marstek_venuse_*`
- Sensors moeten zelfde naam hebben als voorheen

### Stap 4: Test Battery Rotation

1. Enable battery rotation: `input_boolean.battery_rotation_enabled` → ON
2. Check of automations triggeren
3. Check logs voor fouten

---

## Geavanceerd

### Meerdere Instances

Als je batterijen op verschillende netwerken hebt, kun je meerdere instances draaien:

```bash
# Instance 1 - Lokale batterijen
python3 marstek_poller.py --config /opt/marstek-poller/config-local.yaml

# Instance 2 - Remote batterijen
python3 marstek_poller.py --config /opt/marstek-poller/config-remote.yaml
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY marstek_poller.py .
COPY config.yaml .
CMD ["python", "marstek_poller.py", "--config", "config.yaml"]
```

```bash
docker build -t marstek-poller .
docker run -d --name marstek-poller --network host marstek-poller
```

### Custom MQTT Topics

Als je andere topic structuur wilt, pas `state_topic_prefix` aan:

```yaml
mqtt:
  state_topic_prefix: "home/energy/batteries"
```

Topics worden dan:
- `home/energy/batteries/marstek_fasea_d828/state`
- etc.

---

## Zie Ook

- [README.md](../README.md) - Project overzicht
- [INSTALLATION.md](INSTALLATION.md) - Battery rotation installatie
- [CONFIGURATION.md](CONFIGURATION.md) - Configuratie parameters
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Algemene troubleshooting

---

**Vragen of problemen? [Open een issue](https://github.com/SDBeu/marstek-battery-rotation/issues)!**
