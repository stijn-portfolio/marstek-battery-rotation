# 🔋 Marstek Battery Rotation System

**Intelligente batterij rotatie voor Home Assistant op basis van P1 meter metingen**

Automatisch wisselen tussen 3 Marstek Venus E batterijen om:
- ☀️ Zonoverschot op te slaan in de leegste batterij
- ⚡ Netverbruik te dekken met de volste batterij
- 🌙 Nacht laden toe te staan zonder interferentie
- 📊 Batterij levensduur te maximaliseren

---

## ✨ Features

### Automatische Batterij Rotatie
- **Solar Excess**: Bij zonoverschot wordt de leegste batterij actief om op te laden
- **Grid Consumption**: Bij netverbruik wordt de volste batterij actief om te ontladen
- **Smart Switching**: Altijd een actieve batterij (geen gap), snelle switches (5-10 sec)

### Configureerbaar via UI
Alle instellingen aanpasbaar zonder YAML te editen:
- Hysteresis drempels (zon/net)
- Trigger delays (hoe lang waarde moet aanhouden)
- Switch delay (minimale tijd tussen switches)
- SOC limieten (min/max)
- Nacht/dag tijden

### Night Mode
- Automatisch UIT tussen 01:00-07:00 voor night charging
- Configureerbare tijden via UI
- Voorkomt conflict met bestaande night charging automations

### Safety Features
- Anti-flapping (hysteresis + delays)
- SOC limieten (niet te leeg/vol)
- Emergency stop button
- Notifications bij elke switch

---

## 📋 Vereisten

### Hardware
- 3x Marstek Venus E batterijen
- P1 meter (DSMR integratie)
- Home Assistant installatie

### Software
- Home Assistant 2023.1 of nieuwer
- MQTT Broker (bijv. Mosquitto)
- P1 meter integratie (bijv. DSMR)

---

## ⚠️ Belangrijk: MQTT Poller (Aanbevolen)

De standaard Marstek Local API integratie heeft **timeout problemen** op veel batterijen. Wij bieden een **lightweight MQTT poller** die alleen de werkende API method (`ES.GetMode`) gebruikt.

### Waarom MQTT Poller?
| Aspect | HA Integratie | MQTT Poller |
|--------|:-------------:|:-----------:|
| ES.GetStatus | ❌ Timeout | N/A |
| ES.GetMode | ✅ | ✅ |
| Batterij lockups | ⚠️ Risico | ✅ Geen |
| SOC sensor | ✅ | ✅ |

**Zie [MQTT Poller Documentatie](docs/MQTT_POLLER.md)** voor installatie.

---

## 🚀 Quick Start

### Optie A: Met MQTT Poller (Aanbevolen)

#### 1. Installeer MQTT Poller
```bash
cd poller
sudo ./install.sh
sudo nano /opt/marstek-poller/config.yaml  # Pas IPs aan
sudo systemctl restart marstek-poller
```

#### 2. Ga verder met stap 2 hieronder

### Optie B: Met HA Integratie (Als het werkt)

#### 1. Installeer Marstek Local API
Volg de instructies op: https://github.com/jaapp/ha-marstek-local-api

**Let op:** Test eerst of `ES.GetStatus` werkt op jouw batterijen!

### 2. Enable Packages
Voeg toe aan `configuration.yaml`:
```yaml
homeassistant:
  packages: !include_dir_named packages
```

### 3. Clone Repo & Maak Symlink
```bash
# Clone de repo naar je HA machine
cd /homeassistant
git clone https://github.com/SDBeu/marstek-battery-rotation.git

# Maak packages folder aan (als deze niet bestaat)
mkdir -p /homeassistant/packages

# Maak symlink (config blijft automatisch in sync na git pull)
ln -s /homeassistant/marstek-battery-rotation/config/packages/battery-rotation.yaml /homeassistant/packages/battery-rotation.yaml
```

### 4. Updates Binnenhalen
Na een `git pull` wordt de config automatisch bijgewerkt via de symlink:
```bash
cd /homeassistant/marstek-battery-rotation
git pull
# Daarna in HA: Developer Tools → YAML → Reload All YAML
```

### 5. Pas Button Entity Names Aan
Edit `battery-rotation.yaml` en vervang de button entity names met jouw batterijen:
```yaml
# Vind jouw entity names in Developer Tools → States
# Zoek naar: button.*marstek*
```

### 6. Restart Home Assistant
```
Developer Tools → YAML → Restart
```

### 7. Configureer Settings
Ga naar **Instellingen → Apparaten en diensten → Helpers** en pas aan:
- Nachtmodus Start (bijv. 01:00)
- Dagmodus Start (bijv. 07:00)
- Switch delay (min. tijd tussen switches)

### 8. Installeer Dashboard (Optioneel)
Kopieer `dashboards/battery-rotation-card.yaml` naar je Lovelace dashboard.

---

## 📖 Documentatie

- **[MQTT Poller](docs/MQTT_POLLER.md)** - Aanbevolen: Betrouwbare SOC polling
- **[Installation Guide](docs/INSTALLATION.md)** - Uitgebreide installatie instructies
- **[Configuration Guide](docs/CONFIGURATION.md)** - Uitleg van alle instellingen
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Veelvoorkomende problemen
- **[Architecture](docs/ARCHITECTURE.md)** - Hoe het systeem werkt
- **[Roadmap](docs/ROADMAP.md)** - Geplande features

---

## ⚙️ Configuratie Overzicht

### Belangrijkste Instellingen

| Setting | Default | Beschrijving |
|---------|---------|--------------|
| **Drempel Teruglevering** | -200W | Trigger bij teruglevering > 200W |
| **Drempel Verbruik** | +200W | Trigger bij verbruik > 200W |
| **Trigger Delay** | 2 min | Hoe lang drempel moet aanhouden |
| **Switch Delay** | 5 min | Min tijd tussen switches (instelbaar) |
| **Nachtmodus Start** | 01:00 | Wanneer rotatie uitgaat |
| **Dagmodus Start** | 07:00 | Wanneer rotatie aangaat |

Zie [Configuration Guide](docs/CONFIGURATION.md) voor details.

---

## 🎯 Hoe Het Werkt

### Dagelijkse Timeline

```
23:00  → Rotatie actief (intelligente switching)
01:00  → 🌙 Nachtmodus: Rotatie UIT
        → Jouw night charging automation start
        → Batterijen A en B laden ongestoord
07:00  → ☀️ Dagmodus: Rotatie AAN
        → Fase A wordt actief
        → Intelligente rotatie start
```

### Switching Logic

**Bij Zonoverschot (P1 < -500W voor 2 min):**
```
1. Bepaal leegste batterij
2. Activeer leegste batterij (Auto mode)
3. Wacht 5 seconden (stabilisatie)
4. Deactiveer andere batterijen (Manual mode)
```

**Bij Netverbruik (P1 > +200W voor 2 min):**
```
1. Bepaal volste batterij
2. Activeer volste batterij (Auto mode)
3. Wacht 5 seconden (stabilisatie)
4. Deactiveer andere batterijen (Manual mode)
```

---

## 📊 Dashboard

Het optionele dashboard biedt:
- Real-time SOC gauges voor elke batterij
- Automatische selectie info (leegste/volste)
- Manuele batterij activatie knoppen
- Emergency stop button
- Configureerbare instellingen
- Status overzicht

![Dashboard Screenshot](docs/images/dashboard.png)

---

## 🧪 Testen

### Unit Tests
```bash
cd tests/api
python apiTest.py
```

### Battery Tests
```bash
cd tests/battery
python test_all_batteries.py
```

### Entity Verification
```bash
cd tests
python verify-entities.py
```

---

## 🤝 Bijdragen

Bijdragen zijn welkom! Zie [CONTRIBUTING.md](CONTRIBUTING.md) voor details.

### Development Setup
```bash
git clone https://github.com/SDBeu/marstek-battery-rotation.git
cd marstek-battery-rotation
# Edit config/packages/battery-rotation.yaml
```

---

## 📝 Changelog

Zie [CHANGELOG.md](CHANGELOG.md) voor volledige versie geschiedenis.

### v1.0.0 (2024-11-20)
- ✨ Intelligente batterij rotatie op basis van P1 meter
- ✨ Configureerbare trigger delays via UI
- ✨ Night/day mode met configureerbare tijden
- ✨ Dashboard card met real-time monitoring
- ✨ Safety features (anti-flapping, SOC limieten)
- ✨ Emergency stop functionaliteit

---

## 🐛 Issues & Support

Problemen gevonden? [Open een issue](https://github.com/SDBeu/marstek-battery-rotation/issues)

---

## 📄 License

MIT License - zie [LICENSE](LICENSE) voor details.

---

## 🙏 Credits

- **Marstek Local API**: [jaapp/ha-marstek-local-api](https://github.com/jaapp/ha-marstek-local-api)
- **Protocol Documentatie**: [rweijnen.github.io](https://rweijnen.github.io/marstek-venus-monitor/)
- **Community**: Home Assistant Community Forum

---

## ⭐ Star History

Als dit project je helpt, geef het een ⭐ op GitHub!

---

**Made with ❤️ for the Home Assistant community**
