# 🔋 Marstek batterij rotatie - installatie voor jouw setup

Je hebt **2 opties**. Optie 1 is het makkelijkst!

---

## ✅ OPTIE 1: packages (AANBEVOLEN - 5 minuten)

### Stap 1: pas configuration.yaml aan

Voeg deze regel toe aan het **einde** van je `configuration.yaml`:

```yaml
# ============================================================================
# PACKAGES - Modulaire configuratie
# ============================================================================
homeassistant:
  packages: !include_dir_named packages
```

**OF** gebruik de kant-en-klare versie:
```bash
# Backup maken
cp /config/configuration.yaml /config/configuration.yaml.backup

# Nieuwe versie gebruiken
cp configuration_with_packages.yaml /config/configuration.yaml
```

### Stap 2: kopieer de batterij rotatie configuratie

```bash
# Maak packages folder aan
mkdir -p /config/packages

# Kopieer configuratie
cp ha-marstek-battery-rotation.yaml /config/packages/marstek_battery_rotation.yaml
```

### Stap 3: check & restart

1. **Developer Tools → YAML → Check Configuration**
2. Zou moeten zeggen: "Configuration valid!"
3. **Developer Tools → YAML → Restart**

### Stap 4: verify na restart

Ga naar **Developer Tools → States** en zoek naar:
- ✅ `sensor.battery_emptiest`
- ✅ `sensor.battery_fullest`
- ✅ `input_boolean.battery_rotation_enabled`

Als deze bestaan → **SUCCESS!** Ga naar "Eerste Test" hieronder.

---

## 🔧 OPTIE 2: split configuratie (15 minuten, complexer)

Als je liever geen packages gebruikt, moet je de configuratie handmatig splitsen.

### Stap 1: pas configuration.yaml aan

Voeg deze regels toe:

```yaml
# Template sensors
template: !include template.yaml

# Input helpers
input_text: !include input_text.yaml
input_number: !include input_number.yaml
input_datetime: !include input_datetime.yaml
input_boolean: !include input_boolean.yaml
```

Je **configuration.yaml** wordt dan:

```yaml
# Loads default set of integrations. Do not remove.
default_config:

# Load frontend themes from the themes folder
frontend:
  themes: !include_dir_merge_named themes

automation: !include automations.yaml
script: !include scripts.yaml
scene: !include scenes.yaml

# shell commands
shell_command: !include shell_command.yaml

# Template sensors
template: !include template.yaml

# Input helpers
input_text: !include input_text.yaml
input_number: !include input_number.yaml
input_datetime: !include input_datetime.yaml
input_boolean: !include input_boolean.yaml
```

### Stap 2: maak de nieuwe files

Ik ga de configuratie voor je splitsen. Run dit script:

```bash
cd /config
python3 /path/to/split_config.py
```

### Stap 3: voeg automations toe

Open `automations.yaml` en voeg de 3 automations toe (zie ha-marstek-battery-rotation.yaml regels 155-402).

### Stap 4: voeg scripts toe

Open `scripts.yaml` en voeg de 5 scripts toe (zie ha-marstek-battery-rotation.yaml regels 407-511).

---

## 🧪 EERSTE TEST (Na installatie)

### Test 1: check entities

**Developer Tools → Template:**
```jinja2
Leegste: {{ states('sensor.battery_emptiest') }}
Volste: {{ states('sensor.battery_fullest') }}
Systeem: {{ states('input_boolean.battery_rotation_enabled') }}
```

Moet geldige waardes geven (niet "unknown").

### Test 2: test script - activeer fase a

**Developer Tools → Services:**
```yaml
service: script.marstek_activate_fase_a
```

**Check:**
1. Fase A button → Auto mode
2. Fase B & C buttons → Manual mode
3. Geen errors in logs

### Test 3: test script - emergency stop

**Developer Tools → Services:**
```yaml
service: script.marstek_all_batteries_manual
```

**Check:**
Alle 3 batterijen → Manual mode

### Test 4: check automations

Ga naar **Instellingen → Automations & Scenes**

Je moet zien:
- ✅ Marstek: Morning Battery A Start
- ✅ Marstek: Solar Excess - Switch to Emptiest
- ✅ Marstek: Grid Consumption - Switch to Fullest

---

## ⚙️ ENABLE SYSTEEM

### Zet rotatie AAN

1. Ga naar **Instellingen → Apparaten en diensten → Helpers**
2. Zoek **"Batterij Rotatie Systeem"**
3. Toggle **ON** ✅

### Of via developer tools:

```yaml
service: input_boolean.turn_on
target:
  entity_id: input_boolean.battery_rotation_enabled
```

---

## 📊 MONITORING

### Dashboard card (Optioneel)

Voeg dit toe aan je dashboard voor live monitoring:

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # 🔋 Batterij Rotatie
      **Actief:** {{ states('input_text.active_battery_fase')|replace('fase_a','Fase A')|replace('fase_b','Fase B')|replace('fase_c','Fase C') }}
      **P1:** {{ states('sensor.p1_meter_power') }}W

  - type: entities
    entities:
      - input_boolean.battery_rotation_enabled

  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.marstek_venuse_d828_state_of_charge
        name: Fase A
        min: 0
        max: 100
      - type: gauge
        entity: sensor.marstek_venuse_3_0_9a7d_state_of_charge
        name: Fase B
        min: 0
        max: 100
      - type: gauge
        entity: sensor.marstek_venuse_state_of_charge
        name: Fase C
        min: 0
        max: 100

  - type: entities
    title: Automatische Selectie
    entities:
      - sensor.battery_emptiest
      - sensor.battery_fullest

  - type: horizontal-stack
    cards:
      - type: button
        name: Fase A
        tap_action:
          action: call-service
          service: script.marstek_activate_fase_a
      - type: button
        name: Fase B
        tap_action:
          action: call-service
          service: script.marstek_activate_fase_b
      - type: button
        name: Fase C
        tap_action:
          action: call-service
          service: script.marstek_activate_fase_c

  - type: button
    name: 🛑 STOP
    tap_action:
      action: call-service
      service: script.marstek_all_batteries_manual
```

---

## 🎯 GEDRAG

Na installatie gebeurt automatisch:

**07:00u 's morgens**
→ Fase A wordt actief (Auto mode)
→ B en C gaan naar Manual mode

**Bij zonoverschot (P1 < -500W)**
→ Leegste batterij wordt actief (om op te laden)
→ Andere gaan naar Manual

**Bij netverbruik (P1 > +200W)**
→ Volste batterij wordt actief (om te ontladen)
→ Andere gaan naar Manual

**Safety features:**
- Min 5 minuten tussen switches
- Laad niet boven 90% SOC
- Ontlaad niet onder 15% SOC
- Configureerbare hysteresis

---

## ⚙️ CONFIGURATIE AANPASSEN

Alle instellingen zijn configureerbaar via **Helpers**:

| Helper | Default | Omschrijving |
|--------|---------|--------------|
| Switch Hysteresis - Zon | 500W | Min teruglevering voor switch |
| Switch Hysteresis - Net | 200W | Min verbruik voor switch |
| Min Tijd Tussen Switches | 5 min | Anti-flapping |
| Min SOC Ontladen | 15% | Ontlaad niet onder deze SOC |
| Max SOC Laden | 90% | Laad niet boven deze SOC |

---

## 🔍 TROUBLESHOOTING

### ❌ Automation triggert niet

**Check:**
1. Is `input_boolean.battery_rotation_enabled` **ON**?
2. Is P1 power boven/onder drempel? (check sensor.p1_meter_power)
3. Is laatste switch langer dan 5 min geleden?
4. Kijk in automation traces: **Settings → Automations → [Select] → Traces**

### ❌ Entities not found

**Check:**
1. Developer Tools → YAML → Check Configuration
2. Check logs: Settings → System → Logs
3. Zoek naar "marstek" of "battery"

### ❌ Button press fails

**Check:**
1. Zijn alle buttons beschikbaar in Developer Tools → States?
2. Test handmatig: Developer Tools → Services → button.press
3. Check Marstek Local API integration logs

### ⚠️ Te veel switches (flapping)

**Verhoog:**
- `input_number.battery_switch_hysteresis_solar` → 1000W
- `input_number.battery_switch_hysteresis_grid` → 500W
- `input_number.battery_switch_delay_minutes` → 10 min

---

## 🛑 EMERGENCY STOP

**Altijd beschikbaar:**
```yaml
service: script.marstek_all_batteries_manual
```

Of zet het systeem uit:
```yaml
service: input_boolean.turn_off
target:
  entity_id: input_boolean.battery_rotation_enabled
```

---

## 📝 VOLGENDE STAPPEN

1. ✅ Kies Optie 1 of 2
2. ✅ Installeer configuratie
3. ✅ Test alle scripts
4. ✅ Enable systeem
5. ✅ Monitor 24u
6. ✅ Fine-tune instellingen
7. ✅ Geniet van automatische rotatie! 🎉

**Welke optie kies je? Optie 1 (packages) of Optie 2 (split)?**
