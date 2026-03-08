# 🔧 Troubleshooting Guide

Veelvoorkomende problemen en oplossingen voor het Marstek Battery Rotation systeem.

---

## 📋 Quick Diagnostic Checklist

Voordat je begint met troubleshooting, check deze basis zaken:

- [ ] Is `input_boolean.battery_rotation_enabled` **ON**?
- [ ] Zijn alle batterij SOC sensors beschikbaar? (niet "unknown" of "unavailable")
- [ ] Is `sensor.p1_meter_power` beschikbaar en geeft valide data?
- [ ] Zijn alle button entities beschikbaar? (fasea/b/c auto/manual mode)
- [ ] Check Home Assistant logs: Settings → System → Logs (zoek "marstek" of "battery")
- [ ] Check automation traces: Settings → Automations → [Select automation] → Traces

---

## 🚨 Kritische Problemen

### ❌ PROBLEEM: Grid Consumption Tijdens Switch (30+ seconden)

**Symptoom:**
- Tijdens batterij switch: P1 meter springt naar +500W tot +2000W
- Duurt 30+ seconden voordat nieuwe batterij actief is
- Onnodige grid verbruik tijdens transitie

**Diagnose:**
```yaml
# Check automation trace:
Settings → Automations → "Marstek: Solar Excess - Switch to Emptiest" → Traces
# Kijk naar timing tussen actions
```

**Oorzaak:**
- **OUDE FOUTIEVE VOLGORDE** (vóór fix):
  1. Zet A & B naar Manual (10-20 sec)
  2. Wacht 2 seconden
  3. Zet C naar Auto (5-10 sec)
  4. **Totaal: 17-32 sec ZONDER actieve batterij!**

**Oplossing:**
Gebruik de **gefixte configuratie** (v1.0.0+):
```yaml
action:
  # STAP 1: Activeer nieuwe batterij EERST
  - service: button.press
    target:
      entity_id: button.fasec_geen_deb8_auto_mode

  # STAP 2: Wacht op stabilisatie
  - delay:
      seconds: 5

  # STAP 3: Deactiveer andere batterijen (maakt niet uit, C is al actief)
  - service: button.press
    target:
      entity_id:
        - button.fasea_schuin_d828_manual_mode
        - button.faseb_plat_v3_9a7d_manual_mode
```

**Verificatie:**
1. Trigger een switch (bijv. manueel script draaien)
2. Monitor P1 power realtime
3. Zou GEEN spike mogen zien (max 5-10 sec kleine dip)

**Als het probleem blijft:**
- Check of je de nieuwste configuratie hebt (config/packages/battery-rotation.yaml:47262)
- Verifieer automation order in traces
- Post issue op GitHub met trace screenshots

---

### ❌ PROBLEEM: Automation Triggert Niet

**Symptoom:**
- Zonoverschot of netverbruik, maar geen batterij switch
- Automation staat in traces maar wordt niet triggered
- Batterij blijft hele dag op Fase A

#### **Diagnose Stap 1: Check Automation Enabled**
```yaml
Settings → Automations → Zoek "Marstek"
# Alle 3 automations moeten "Enabled" zijn:
- Marstek: Morning Battery A Start ✅
- Marstek: Solar Excess - Switch to Emptiest ✅
- Marstek: Grid Consumption - Switch to Fullest ✅
```

#### **Diagnose Stap 2: Check System Enabled**
```yaml
Developer Tools → States → Zoek "input_boolean.battery_rotation_enabled"
# Moet "on" zijn, anders is systeem UIT
```

**Oplossing als UIT:**
```yaml
Settings → Devices & Services → Helpers → "Batterij Rotatie Systeem" → Toggle ON
```

#### **Diagnose Stap 3: Check P1 Power Sensor**
```yaml
Developer Tools → States → sensor.p1_meter_power
# Moet een getal zijn (positief of negatief)
# NIET: unknown, unavailable, null
```

**Voorbeeld valide data:**
- `-1200` = 1200W teruglevering (zonoverschot) ✅
- `+350` = 350W netverbruik ✅
- `unknown` = PROBLEEM ❌

**Oplossing als unknown:**
1. Check P1 meter integratie: Settings → Devices & Services → DSMR
2. Restart DSMR integratie
3. Check USB verbinding P1 meter
4. Hernoem je sensor in automation als deze anders heet:
   ```yaml
   # In automation triggers, vervang:
   entity_id: sensor.p1_meter_power
   # Met jouw sensor naam (check in States)
   ```

#### **Diagnose Stap 4: Check Hysteresis & Delays**
```yaml
Developer Tools → States
# Check configuratie:
input_number.battery_switch_hysteresis_solar: 500  # Is P1 wel < -500W?
input_number.battery_switch_hysteresis_grid: 200   # Is P1 wel > +200W?
input_number.trigger_delay_solar: 2                # Is waarde al 2 min stabiel?
input_number.trigger_delay_grid: 2                 # Is waarde al 2 min stabiel?
```

**Voorbeeld situatie:**
- P1 power: -300W (teruglevering)
- Hysteresis: -500W
- **Probleem:** -300W is NIET onder -500W → Geen trigger!

**Oplossing:**
Verlaag hysteresis naar -200W:
```yaml
Settings → Devices & Services → Helpers → "Switch Hysteresis - Zon" → 200
```

#### **Diagnose Stap 5: Check Switch Delay**
```yaml
Developer Tools → States → input_datetime.last_battery_switch
# Kijk naar laatste switch tijd

# Voorbeeld: Laatste switch was 10:30, nu is het 10:33
# Switch delay: 5 minuten
# Probleem: (10:33 - 10:30) = 3 min < 5 min → GEBLOKKEERD!
```

**Oplossing:**
- Wacht tot 5 min voorbij is, OF
- Verlaag switch delay tijdelijk voor testen:
  ```yaml
  Settings → Helpers → "Min Tijd Tussen Switches" → 1 minuut
  ```

#### **Diagnose Stap 6: Check SOC Limieten**
```yaml
# Scenario: Solar Excess trigger
sensor.battery_emptiest = "none"  # Alle batterijen te vol!

# Check SOC van batterijen:
sensor.marstek_venuse_d828_state_of_charge: 92%         # Fase A
sensor.marstek_venuse_3_0_9a7d_state_of_charge: 91%     # Fase B
sensor.marstek_venuse_state_of_charge: 89%              # Fase C

# Max SOC Laden: 90%
# Probleem: Alle batterijen boven 90% → Geen selecteerbaar!
```

**Oplossing:**
- Verhoog max SOC laden naar 95%:
  ```yaml
  Settings → Helpers → "Max SOC Laden" → 95
  ```
- OF wacht tot batterijen ontladen

#### **Diagnose Stap 7: Check Automation Traces**
```yaml
Settings → Automations → "Marstek: Solar Excess..." → Traces
# Klik op laatste trace (of "Run" om te forceren)

# Kijk naar:
1. Trigger: Heeft deze gefired? (groen vinkje)
2. Conditions: Welke condition faalt? (rood kruisje)
3. Actions: Worden deze uitgevoerd?

# Veel voorkomende condition failures:
- "System not enabled" → input_boolean.battery_rotation_enabled = off
- "Switch delay not met" → Te kort geleden geswitched
- "No valid battery available" → Alle batterijen buiten SOC limieten
- "Trigger delay not met" → Waarde niet lang genoeg stabiel
```

**Voorbeeld trace output:**
```
✅ Trigger: numeric_state sensor.p1_meter_power below 0
❌ Condition: System enabled (FAILED - input_boolean is OFF)
⏸️  Actions: (skipped due to failed condition)
```

**Oplossing:** Turn system ON!

---

### ❌ PROBLEEM: Button Press Fails

**Symptoom:**
- Automation draait, maar button press werkt niet
- Error in logs: "Entity not found" of "Service call failed"
- Batterij mode wijzigt niet

#### **Diagnose Stap 1: Check Button Entities**
```yaml
Developer Tools → States → Zoek "button.fasea"
# Je moet zien (voor elke batterij):
button.fasea_schuin_d828_auto_mode       # Fase A Auto
button.fasea_schuin_d828_manual_mode     # Fase A Manual
button.faseb_plat_v3_9a7d_auto_mode      # Fase B Auto
button.faseb_plat_v3_9a7d_manual_mode    # Fase B Manual
button.fasec_geen_deb8_auto_mode         # Fase C Auto
button.fasec_geen_deb8_manual_mode       # Fase C Manual
```

**Als entities niet bestaan:**
1. Check Marstek Local API integratie: Settings → Devices & Services → Marstek Local API
2. Zijn alle batterijen gevonden?
3. Restart integratie
4. Hernoem entities in configuratie als jouw entities anders heten

#### **Diagnose Stap 2: Test Button Handmatig**
```yaml
Developer Tools → Services
# Service: button.press
# Target: button.fasea_schuin_d828_auto_mode
# Press "Call Service"

# Check of batterij naar Auto mode gaat
# Als dit werkt: Automation configuratie is fout
# Als dit NIET werkt: Probleem met Marstek Local API integratie
```

#### **Diagnose Stap 3: Check Marstek Local API Logs**
```yaml
Settings → System → Logs → Filter "marstek"
# Zoek naar errors zoals:
- "Connection timeout"
- "Device not reachable"
- "API call failed"
```

**Mogelijke oorzaken:**
- Batterij IP adres gewijzigd
- Batterij offline/uit
- Local API disabled op batterij
- Netwerk probleem

**Oplossing:**
1. Ping batterij: `ping 192.168.6.80` (Fase A IP)
2. Check batterij WiFi verbinding
3. Reconfigure Marstek Local API integratie met correcte IP
4. Enable Local API op batterij (via BLE 0x28 command)

#### **Diagnose Stap 4: Check Entity Namen in Config**
```yaml
# Open config/packages/battery-rotation.yaml
# Zoek naar button entities in scripts (regel ~407)

# Jouw entity names MOETEN matchen met States!
# Voorbeeld mismatch:
# Config zegt: button.marstek_venuse_auto_mode  ❌
# States heeft: button.fasea_schuin_d828_auto_mode  ✅
```

**Oplossing:**
Edit `battery-rotation.yaml` en vervang alle button entities met correcte namen.

---

### ❌ PROBLEEM: Te Veel Switches (Flapping)

**Symptoom:**
- 20+ switches per dag
- Batterijen switchen heen en weer
- Veel notificaties
- Inefficiënt, batterij slijtage

#### **Diagnose:**
```yaml
Developer Tools → Logbook → Filter "battery_rotation"
# Kijk naar switch frequentie
# Normaal: 3-8 switches per dag
# Probleem: >15 switches per dag
```

**Mogelijke Oorzaken:**

#### **Oorzaak 1: Hysteresis Te Laag**
```yaml
# Settings:
battery_switch_hysteresis_solar: 100W  # TE LAAG!
battery_switch_hysteresis_grid: 50W    # TE LAAG!

# Gevolg: Elk kleine fluctuatie triggert switch
# P1 wisselt tussen -120W en +80W → Constant switches!
```

**Oplossing:**
Verhoog hysteresis:
```yaml
battery_switch_hysteresis_solar: 500-800W
battery_switch_hysteresis_grid: 200-500W
```

#### **Oorzaak 2: Trigger Delay Te Kort**
```yaml
# Settings:
trigger_delay_solar: 0.5 min  # TE KORT!
trigger_delay_grid: 0.5 min   # TE KORT!

# Gevolg: Korte pieken/dips triggeren al switches
# Waterkoker (3 min) triggert switch, maar is al snel klaar
```

**Oplossing:**
Verhoog trigger delays:
```yaml
trigger_delay_solar: 5 min
trigger_delay_grid: 5 min
```

#### **Oorzaak 3: Switch Delay Te Kort**
```yaml
# Settings:
battery_switch_delay_minutes: 1 min  # TE KORT!

# Gevolg: Switches kunnen snel achter elkaar gebeuren
# 10:00: Zon → Fase B
# 10:02: Wolk → Fase A
# 10:04: Zon → Fase B (PING-PONG!)
```

**Oplossing:**
Verhoog switch delay:
```yaml
battery_switch_delay_minutes: 10-15 min
```

#### **Oorzaak 4: Wisselvallig Weer**
```yaml
# Situatie: Wolken passeren om de 2-3 minuten
# P1 wisselt: -800W → +200W → -900W → +150W
# Met trigger delay van 2 min: Te kort voor dit weer!
```

**Oplossing - Complete Anti-Flapping Configuratie:**
```yaml
battery_switch_hysteresis_solar: 1000W      # Hoge drempel
battery_switch_hysteresis_grid: 500W        # Hoge drempel
trigger_delay_solar: 5 min                  # Lange stabilisatie
trigger_delay_grid: 5 min                   # Lange stabilisatie
battery_switch_delay_minutes: 15 min        # Lange cooldown
```

**Effect:** Max 4 switches per uur, zeer stabiel systeem.

---

## ⚠️ Configuratie Problemen

### ❌ PROBLEEM: Entities Not Found na Installatie

**Symptoom:**
- Na restart: Veel "Entity not found" errors
- Template sensors bestaan niet
- Input helpers ontbreken

#### **Diagnose:**
```yaml
Developer Tools → States → Zoek "battery"
# Verwacht:
sensor.battery_emptiest        ❌ Niet gevonden
sensor.battery_fullest         ❌ Niet gevonden
input_boolean.battery_rotation_enabled  ❌ Niet gevonden
```

**Oorzaak 1: Package Niet Geladen**
```yaml
# Check configuration.yaml:
homeassistant:
  packages: !include_dir_named packages  # Staat deze regel er?
```

**Oplossing:**
1. Voeg packages regel toe aan configuration.yaml
2. Developer Tools → YAML → Check Configuration
3. Developer Tools → YAML → Restart

**Oorzaak 2: Package Filename Fout**
```yaml
# Fout: config/packages/ha-marstek-battery-rotation.yaml
# Error: "invalid slug ha-marstek-battery-rotation"
# Reden: Dashes niet toegestaan in package namen!
```

**Oplossing:**
Hernoem naar:
```bash
mv ha-marstek-battery-rotation.yaml battery_rotation.yaml
# Of: ha_marstek_battery_rotation.yaml (underscores OK!)
```

**Oorzaak 3: YAML Syntax Error**
```yaml
# Check logs:
Settings → System → Logs → Filter "yaml" of "configuration"

# Veel voorkomende errors:
- "expected <block end>, but found '-'" → Indentation fout
- "mapping values are not allowed here" → : op verkeerde plaats
- "found undefined alias" → Entity naam bestaat niet
```

**Oplossing:**
1. Developer Tools → YAML → Check Configuration
2. Lees error message zorgvuldig (geeft regel nummer!)
3. Fix YAML indentation (gebruik spaces, GEEN tabs!)
4. Valideer YAML online: http://www.yamllint.com/

---

### ❌ PROBLEEM: Template Sensor Errors

**Symptoom:**
- `sensor.battery_emptiest` of `sensor.battery_fullest` = "unknown"
- Error in logs: "Template error"
- Automation triggert niet (condition faalt)

#### **Diagnose:**
```yaml
Developer Tools → Template
# Test template:
{% set batteries = [
  {'name': 'fase_a', 'soc': states('sensor.marstek_venuse_d828_state_of_charge')|float(0)},
  {'name': 'fase_b', 'soc': states('sensor.marstek_venuse_3_0_9a7d_state_of_charge')|float(0)},
  {'name': 'fase_c', 'soc': states('sensor.marstek_venuse_state_of_charge')|float(0)}
] %}
{{ batteries }}

# Output verwacht:
[
  {'name': 'fase_a', 'soc': 80.0},
  {'name': 'fase_b', 'soc': 45.0},
  {'name': 'fase_c', 'soc': 15.0}
]

# Als output is:
[
  {'name': 'fase_a', 'soc': 0.0},  # PROBLEEM!
  {'name': 'fase_b', 'soc': 0.0},
  {'name': 'fase_c', 'soc': 0.0}
]
# Dan bestaan de SOC sensors niet of hebben geen data
```

**Oorzaak: SOC Sensor Namen Verkeerd**
```yaml
# In template staat:
states('sensor.marstek_venuse_d828_state_of_charge')

# Maar jouw sensor heet misschien:
sensor.battery_a_soc  # Anders!
```

**Oplossing:**
1. Check exacte sensor namen in Developer Tools → States
2. Edit battery-rotation.yaml, zoek naar template sensors (regel ~30)
3. Vervang sensor namen met jouw entity names
4. Reload: Developer Tools → YAML → Reload Template Entities

---

### ❌ PROBLEEM: Night Mode Werkt Niet

**Symptoom:**
- Om 01:00: Rotatie blijft actief (zou UIT moeten gaan)
- Om 07:00: Fase A wordt niet actief
- Night charging en rotatie interfereren

#### **Diagnose Stap 1: Check Automations Enabled**
```yaml
Settings → Automations → Zoek:
- "Marstek: Disable Rotation at Night" → Moet ENABLED zijn ✅
- "Marstek: Enable Rotation at Day" → Moet ENABLED zijn ✅
```

#### **Diagnose Stap 2: Check Tijd Configuratie**
```yaml
Developer Tools → States
input_datetime.night_mode_start_time: "01:00:00"  # Correct format?
input_datetime.day_mode_start_time: "07:00:00"    # Correct format?

# Fout formaat voorbeelden:
"1:00"     ❌ Moet "01:00:00" zijn
"1:00 AM"  ❌ Moet 24-uur formaat zijn
```

**Oplossing:**
Settings → Helpers → Zoek datetime helpers → Set correct tijd in HH:MM formaat

#### **Diagnose Stap 3: Check Automation Traces**
```yaml
Settings → Automations → "Marstek: Disable Rotation at Night" → Traces
# Heeft deze getriggerd om 01:00?
# Zo nee: Automation is niet gelopen
# Zo ja: Check of action succesvol was
```

**Mogelijke problemen:**
- Automation disabled
- Tijd format verkeerd
- Condition blokkeert (als je er een hebt toegevoegd)

#### **Diagnose Stap 4: Handmatig Testen**
```yaml
# Force trigger night mode NU:
Developer Tools → Services
service: automation.trigger
target:
  entity_id: automation.marstek_disable_rotation_at_night

# Check:
input_boolean.battery_rotation_enabled → Moet OFF zijn
```

---

## 🔋 Batterij Specifieke Problemen

### ❌ PROBLEEM: Batterij Reageert Niet op Mode Switch

**Symptoom:**
- Button press succesvol, maar batterij blijft in oude mode
- Mode switch duurt >30 seconden
- Batterij display toont geen wijziging

#### **Diagnose Stap 1: Check Batterij Status**
```yaml
# Check batterij reachability:
Settings → Devices & Services → Marstek Local API
# Klik op device (bijv. "FaseA schuin d828")
# Check "Last seen" → Recent? (< 5 min)
```

**Als "Last seen" oud is (>1 uur):**
- Batterij mogelijk offline
- WiFi verbinding verbroken
- Local API disabled

#### **Diagnose Stap 2: Ping Batterij**
```bash
# Windows CMD / PowerShell:
ping 192.168.6.80    # Fase A
ping 192.168.6.213   # Fase B
ping 192.168.6.144   # Fase C

# Verwacht: Reply from 192.168.6.80: bytes=32 time<10ms
# Probleem: Request timed out → Batterij niet bereikbaar
```

**Oplossing als unreachable:**
1. Check batterij power (staat deze AAN?)
2. Check WiFi LED op batterij (brandt deze?)
3. Reboot batterij (power cycle)
4. Check router: Is batterij verbonden?

#### **Diagnose Stap 3: Test API Direct**
```bash
# Windows PowerShell (zorg dat je in de juiste map zit):
cd C:\Dev\marstekAPI\tests\api
python apiTest.py

# Verwacht output:
"ES.GetStatus: Success"
"ES.GetMode: Success"

# Probleem output:
"Timeout" → Local API niet bereikbaar
"Connection refused" → Local API disabled
```

**Oplossing:**
Enable Local API via BLE command 0x28 (zie docs/ARCHITECTURE.md voor details)

#### **Diagnose Stap 4: Check Mode Mismatch**
```yaml
# Scenario: Je drukt Auto, maar batterij blijft Manual
# Mogelijke oorzaak: Batterij BMS in beschermingsmodus

# Check SOC:
sensor.marstek_venuse_d828_state_of_charge: 5%  # TE LAAG!
# BMS blokkeert mogelijk Auto mode onder 10%

# Of:
sensor.marstek_venuse_d828_state_of_charge: 98%  # TE HOOG!
# BMS blokkeert mogelijk laden boven 95%
```

**Oplossing:**
- Wacht tot SOC in normaal bereik (15-90%)
- Of: Gebruik Passive mode voor directe controle (geavanceerd!)

---

### ❌ PROBLEEM: Batterij SOC Sensor "Unknown"

**Symptoom:**
- `sensor.marstek_venuse_*_state_of_charge` = "unknown" of "unavailable"
- Template sensors werken niet (battery_emptiest/fullest)
- Automation kondities falen

#### **Diagnose:**
```yaml
Developer Tools → States → Zoek "state_of_charge"
# Check alle 3 batterijen:
sensor.marstek_venuse_d828_state_of_charge         # Fase A
sensor.marstek_venuse_3_0_9a7d_state_of_charge     # Fase B
sensor.marstek_venuse_state_of_charge              # Fase C

# Status:
- Getal (bijv. 75): ✅ OK
- "unknown": ❌ Sensor bestaat maar geen data
- "unavailable": ❌ Sensor offline/integratie probleem
- Niet gevonden: ❌ Entity bestaat niet
```

**Oplossing unknown:**
1. Wacht 5 minuten (integratie update interval)
2. Check Marstek Local API logs
3. Restart Marstek Local API integratie

**Oplossing unavailable:**
1. Check batterij WiFi verbinding (ping test)
2. Restart Home Assistant
3. Reconfigure Marstek Local API integratie

**Oplossing niet gevonden:**
1. Check entity namen in Marstek Local API integratie
2. Pas battery-rotation.yaml aan met correcte entity namen
3. Reload template entities

---

## 📡 Netwerk & Communicatie Problemen

### ❌ PROBLEEM: P1 Meter Data "Unknown"

**Symptoom:**
- `sensor.p1_meter_power` = "unknown"
- Automation triggert nooit (conditie faalt)
- Dashboard toont geen power data

#### **Diagnose:**
```yaml
Developer Tools → States → sensor.p1_meter_power
# Status:
- Getal (bijv. -1200 of +350): ✅ OK
- "unknown": ❌ DSMR integratie probleem
- "unavailable": ❌ P1 meter niet bereikbaar
- Niet gevonden: ❌ Sensor bestaat niet (verkeerde naam?)
```

**Mogelijke Sensor Namen:**
```yaml
# Verschillende DSMR integraties gebruiken verschillende namen:
sensor.p1_meter_power
sensor.dsmr_power_usage
sensor.power_consumption
sensor.electricity_power_usage
sensor.current_power_usage

# Check welke jij hebt:
Developer Tools → States → Zoek "power"
```

**Oplossing:**
1. Check DSMR integratie: Settings → Devices & Services → DSMR
2. Test P1 USB verbinding (reconnect cable)
3. Restart DSMR integratie
4. Update sensor naam in battery-rotation.yaml als anders

---

### ❌ PROBLEEM: "Connection Timeout" Errors

**Symptoom:**
- Logs vol met "Connection timeout to 192.168.6.x"
- Button presses falen sporadisch
- Batterij mode switches langzaam (>20 sec)

#### **Diagnose:**
```bash
# Test netwerk latency:
ping 192.168.6.80 -n 100

# Check statistieken:
# Packets: Sent = 100, Received = 100, Lost = 0 (0% loss)
# RTT: Minimum = 1ms, Maximum = 5ms, Average = 2ms

# Probleem signalen:
# Lost > 5% → Slechte WiFi verbinding
# Average > 50ms → Congestie of interference
# Maximum > 200ms → Packet loss / retry
```

**Oplossing WiFi Problemen:**
1. Verplaats batterijen dichter bij router/AP
2. Check 2.4GHz congestie (wissel naar minder druk kanaal)
3. Gebruik WiFi analyzer app om signaal sterkte te checken
4. Overweeg WiFi extender of mesh systeem

**Oplossing Netwerk Congestie:**
1. Zet batterijen op vaste IP (DHCP reservatie)
2. Configureer QoS in router (prioriteit voor batterij traffic)
3. Check voor grote downloads die bandbreedte opeten

---

## 🐛 Software & Integratie Problemen

### ❌ PROBLEEM: "Invalid Slug" Error bij Package

**Symptoom:**
```
Configuration invalid!
invalid slug ha-marstek-battery-rotation (try ha_marstek_battery_rotation)
```

**Oorzaak:**
Package filenames mogen geen dashes bevatten, alleen underscores.

**Oplossing:**
```bash
# Hernoem bestand:
cd /config/packages
mv ha-marstek-battery-rotation.yaml battery_rotation.yaml
# Of:
mv ha-marstek-battery-rotation.yaml ha_marstek_battery_rotation.yaml

# Restart:
Developer Tools → YAML → Restart
```

---

### ❌ PROBLEEM: Automations Verdwijnen na Restart

**Symptoom:**
- Automation working, restart HA → automation weg
- Entities blijven bestaan, maar automations niet
- Settings → Automations toont geen Marstek automations

**Oorzaak:**
Als je `automation: !include automations.yaml` hebt EN automations in package:
→ Conflict! HA laadt alleen automations.yaml.

**Oplossing 1: Gebruik Packages (AANBEVOLEN)**
```yaml
# configuration.yaml:
homeassistant:
  packages: !include_dir_named packages

# Verwijder deze regels:
# automation: !include automations.yaml
# automation: !include_dir_merge_list automations/
```

**Oplossing 2: Gebruik Split Config**
Volg INSTALLATION.md Optie 2 en verplaats automations naar automations.yaml.

---

### ❌ PROBLEEM: Template Sensor Update Vertraging

**Symptoom:**
- Battery SOC wijzigt, maar `sensor.battery_emptiest` update pas na 5+ minuten
- Automation switch komt te laat
- Dashboard toont oude waarden

**Oorzaak:**
Template sensors updaten alleen als hun dependencies wijzigen. Als SOC sensor langzaam update, dan ook template sensor langzaam.

**Diagnose:**
```yaml
Developer Tools → States
# Check last_changed:
sensor.marstek_venuse_d828_state_of_charge
  state: 75
  last_changed: 2024-11-20 10:15:00  # 10 minuten geleden!

# Marstek Local API poll interval is te lang
```

**Oplossing:**
Verlaag Marstek Local API scan interval:
1. Settings → Devices & Services → Marstek Local API → Configure
2. Scan Interval: 30 seconden (was 5 minuten)
3. Save & Restart integratie

**Trade-off:**
- Lagere interval = snellere updates, maar meer batterij WiFi traffic
- 30-60 seconden is goede balans

---

## 🎛️ Dashboard Problemen

### ❌ PROBLEEM: Gauge Charts Tonen Geen Data

**Symptoom:**
- Dashboard battery gauges leeg of "Unknown"
- Entities bestaan wel in States
- Andere dashboard cards werken

**Diagnose:**
```yaml
# Check dashboard YAML:
type: gauge
entity: sensor.marstek_venuse_d828_state_of_charge
min: 0
max: 100

# Test entity in Developer Tools → States:
sensor.marstek_venuse_d828_state_of_charge: 75  # Heeft waarde!
```

**Mogelijke Oorzaken:**

**Oorzaak 1: Entity Naam Fout**
```yaml
# Dashboard YAML:
entity: sensor.battery_a_soc  # Verkeerde naam!

# Correcte naam:
entity: sensor.marstek_venuse_d828_state_of_charge
```

**Oplossing:** Fix entity naam in dashboard YAML.

**Oorzaak 2: Gauge Min/Max Verkeerd**
```yaml
# Fout:
min: 0
max: 10  # Moet 100 zijn!

# SOC is 75 → Buiten range (0-10) → Geen weergave
```

**Oplossing:** Zet max: 100

**Oorzaak 3: Entity Type Incompatibel**
```yaml
# Gauge verwacht numeric sensor
# Maar entity is:
sensor.battery_status: "Charging"  # String, niet getal!
```

**Oplossing:** Gebruik correct entity (SOC = getal).

---

### ❌ PROBLEEM: DateTime Picker Te Breed

**Symptoom:**
- `input_datetime.last_battery_switch` picker komt uit card
- Layout broken op mobiel
- Tijdslot selector te groot

**Oplossing:**
Gebruik relatieve tijd i.p.v. datetime picker:
```yaml
# In markdown card:
**Laatste Switch:** {{ as_timestamp(states('input_datetime.last_battery_switch')) | timestamp_custom('%H:%M', true) }}

# Verplaats datetime picker naar Settings sectie (onderaan dashboard)
# Of gebruik collapsed entities card
```

Zie dashboards/battery-rotation-card.yaml voor correcte implementatie.

---

## 🧪 Testing & Debugging

### Tool 1: Manual Trigger Test

Test automation zonder te wachten op conditions:

```yaml
Developer Tools → Services
service: automation.trigger
target:
  entity_id: automation.marstek_solar_excess_switch_to_emptiest
data:
  skip_condition: true  # Forceer trigger, negeer conditions

# Check:
1. Wordt automation uitgevoerd? (check traces)
2. Worden buttons pressed? (check battery modes)
3. Zijn er errors in logs?
```

### Tool 2: Template Testing

Test template logic realtime:

```yaml
Developer Tools → Template

# Test battery selection:
{% set batteries = [
  {'name': 'fase_a', 'soc': states('sensor.marstek_venuse_d828_state_of_charge')|float(0)},
  {'name': 'fase_b', 'soc': states('sensor.marstek_venuse_3_0_9a7d_state_of_charge')|float(0)},
  {'name': 'fase_c', 'soc': states('sensor.marstek_venuse_state_of_charge')|float(0)}
] %}
{% set max_soc = 90 %}
{% set valid = batteries | selectattr('soc', '<', max_soc) | list %}
Leegste: {{ (valid | sort(attribute='soc') | first).name if valid else 'none' }}

# Output:
Leegste: fase_c  # Correct!
```

### Tool 3: Automation Trace Analysis

Diepgaande analyse van automation gedrag:

```yaml
Settings → Automations → [Select automation] → Traces → [Select trace]

# Kijk naar:
1. Trigger Details: Welke waarde triggerde? Timestamp?
2. Condition Results: Welke conditions passed/failed? Waarom?
3. Action Timeline: Hoe lang duurde elke actie? Errors?
4. Changed States: Welke entities wijzigden?

# Nuttige info:
- Last triggered: Wanneer was laatste trigger?
- Execution time: Hoe lang duurde de run?
- Trace count: Hoeveel runs in history?
```

### Tool 4: Entity History

Visualiseer entity wijzigingen over tijd:

```yaml
Developer Tools → States → [Select entity] → History tab

# Nuttig voor:
- Battery SOC trajecten (zijn deze logisch?)
- P1 power fluctuaties (is trigger hysteresis goed?)
- Switch frequentie (te veel/weinig switches?)
- Mode changes (switchen batterijen correct?)
```

### Tool 5: Log Filtering

Vind relevante logs snel:

```yaml
Settings → System → Logs

# Filter opties:
- Zoek: "marstek" → Alle marstek-related logs
- Zoek: "battery_rotation" → Specifiek dit systeem
- Zoek: "error" + "marstek" → Alleen errors
- Level: Warning/Error → Zie alleen problemen

# Nuttige log patterns:
[automation.marstek_*] → Automation runs
[template.*battery*] → Template sensor updates
[button.fasea_*] → Button press events
```

---

## 🆘 Emergency Procedures

### 🛑 Emergency Stop

**Wanneer gebruiken:**
- System out of control (te veel switches)
- Verkeerde batterij actief
- Testing/debugging
- Maintenance

**Methode 1: Dashboard Button**
```yaml
# Klik op dashboard:
"🛑 STOP Rotatie" button

# Of via Services:
service: script.marstek_all_batteries_manual
```

**Methode 2: Disable System**
```yaml
service: input_boolean.turn_off
target:
  entity_id: input_boolean.battery_rotation_enabled
```

**Effect:**
- Alle automations stoppen met triggeren (condition faalt)
- Batterijen blijven in huidige mode (geen automatic changes)
- Je kunt manueel modes wijzigen

**Herstarten:**
```yaml
service: input_boolean.turn_on
target:
  entity_id: input_boolean.battery_rotation_enabled
```

---

### 🔄 Volledig Reset

**Wanneer gebruiken:**
- Systeem compleet fout geconfigureerd
- Wil opnieuw beginnen
- Na grote configuratie wijzigingen

**Stappen:**

1. **Stop Systeem**
   ```yaml
   service: input_boolean.turn_off
   target:
     entity_id: input_boolean.battery_rotation_enabled
   ```

2. **Zet Alle Batterijen Manueel**
   ```yaml
   service: script.marstek_all_batteries_manual
   ```

3. **Reset Configuratie naar Defaults**
   ```yaml
   # Via Helpers:
   battery_switch_hysteresis_solar: 500W
   battery_switch_hysteresis_grid: 200W
   trigger_delay_solar: 2 min
   trigger_delay_grid: 2 min
   battery_switch_delay_minutes: 5 min
   battery_min_soc_discharge: 15%
   battery_max_soc_charge: 90%
   night_mode_start_time: "01:00"
   day_mode_start_time: "07:00"
   ```

4. **Restart Home Assistant**
   ```yaml
   Developer Tools → YAML → Restart
   ```

5. **Verify Entities**
   ```bash
   cd C:\Dev\marstekAPI\tests
   python verify-entities.py
   ```

6. **Test Basic Functionality**
   ```yaml
   # Test 1: Activeer Fase A
   service: script.marstek_activate_fase_a

   # Test 2: Check sensor updates
   Developer Tools → States → sensor.battery_emptiest

   # Test 3: Enable systeem
   service: input_boolean.turn_on
   target:
     entity_id: input_boolean.battery_rotation_enabled
   ```

---

## 📞 Getting Help

### Before Reporting Issue

1. ✅ Check deze troubleshooting guide
2. ✅ Check CONFIGURATION.md voor parameter uitleg
3. ✅ Check automation traces
4. ✅ Check Home Assistant logs
5. ✅ Test met manual trigger
6. ✅ Verify alle entities bestaan

### Reporting Issue

Open issue op GitHub met:

**System Info:**
```yaml
Home Assistant Version: 2023.11.x
Marstek Local API Version: x.x.x
Battery Rotation Config Version: 1.0.0
```

**Probleem Beschrijving:**
- Wat probeer je te doen?
- Wat gebeurt er (verkeerd)?
- Wat verwacht je dat er gebeurt?

**Configuration:**
```yaml
# Copy relevante helpers:
battery_switch_hysteresis_solar: 500
trigger_delay_solar: 2
# etc...
```

**Logs:**
```
# Copy relevante errors uit Settings → System → Logs
```

**Traces:**
```
# Screenshot van automation trace
```

**Entities Status:**
```yaml
# Developer Tools → States:
sensor.battery_emptiest: fase_c
sensor.battery_fullest: fase_a
input_boolean.battery_rotation_enabled: on
# etc...
```

---

## 📚 Zie Ook

- **[CONFIGURATION.md](CONFIGURATION.md)** - Parameter uitleg en tuning
- **[INSTALLATION.md](INSTALLATION.md)** - Installatie instructies
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technische werking
- **[README.md](../README.md)** - Project overzicht

---

**Probleem niet opgelost? [Open een issue](https://github.com/jouw-username/marstek-battery-rotation/issues)!**
