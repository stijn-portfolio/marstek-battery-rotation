# 🏗️ Architecture & technical design

Technische documentatie over hoe het Marstek Battery Rotation systeem werkt.

---

## 📐 System overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    HOME ASSISTANT                               │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  BATTERY ROTATION SYSTEM (Package)                        │ │
│  │                                                           │ │
│  │  ┌─────────────┐      ┌──────────────┐      ┌─────────┐ │ │
│  │  │  Template   │────▶ │  Automations │────▶ │ Scripts │ │ │
│  │  │  Sensors    │      │              │      │         │ │ │
│  │  │             │      │  1. Morning  │      │ Fase A  │ │ │
│  │  │ - Emptiest  │      │  2. Solar    │      │ Fase B  │ │ │
│  │  │ - Fullest   │      │  3. Grid     │      │ Fase C  │ │ │
│  │  └─────────────┘      │  4. Night    │      │ All Man │ │ │
│  │                       │  5. Day      │      └─────────┘ │ │
│  │  ┌─────────────┐      └──────────────┘                  │ │
│  │  │   Input     │                                        │ │
│  │  │   Helpers   │                                        │ │
│  │  │             │                                        │ │
│  │  │ - Booleans  │      ┌──────────────┐                │ │
│  │  │ - Numbers   │      │  Dashboard   │                │ │
│  │  │ - DateTime  │      │    Card      │                │ │
│  │  │ - Text      │      └──────────────┘                │ │
│  │  └─────────────┘                                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────┐              ┌──────────────────┐          │
│  │ Marstek Local │              │  DSMR / P1 Meter │          │
│  │ API Integration│              │  Integration     │          │
│  └───────┬───────┘              └────────┬─────────┘          │
└──────────┼──────────────────────────────┼────────────────────┘
           │                              │
           │ WiFi (UDP JSON-RPC)         │ USB Serial
           │ Port 30000                  │
           │                              │
           ▼                              ▼
    ┌──────────────┐             ┌──────────────┐
    │  Marstek     │             │  P1 Smart    │
    │  Batteries   │             │  Meter       │
    │              │             │              │
    │  - Fase A    │             │ Grid Power   │
    │  - Fase B    │             │ Consumption  │
    │  - Fase C    │             │              │
    └──────────────┘             └──────────────┘
```

---

## 🔄 System components

### 1. Template sensors

Template sensors berekenen dynamisch welke batterij leeg/vol is.

#### `sensor.battery_emptiest`

**Doel:** Vind de leegste batterij die beschikbaar is voor laden.

**Logic:**
```python
batteries = [
    {'name': 'fase_a', 'soc': get_soc('fase_a')},
    {'name': 'fase_b', 'soc': get_soc('fase_b')},
    {'name': 'fase_c', 'soc': get_soc('fase_c')}
]

max_soc_charge = 90  # Configureerbaar

# Filter batterijen die vol zijn
available = [b for b in batteries if b['soc'] < max_soc_charge]

if available:
    # Sort oplopend op SOC (laagste eerst)
    emptiest = sorted(available, key=lambda x: x['soc'])[0]
    return emptiest['name']
else:
    return 'none'  # Alle batterijen te vol
```

**YAML Implementatie:**
```yaml
template:
  - sensor:
      - name: "Battery Emptiest"
        state: >
          {% set batteries = [
            {'name': 'fase_a', 'soc': states('sensor.marstek_venuse_d828_state_of_charge')|float(0)},
            {'name': 'fase_b', 'soc': states('sensor.marstek_venuse_3_0_9a7d_state_of_charge')|float(0)},
            {'name': 'fase_c', 'soc': states('sensor.marstek_venuse_state_of_charge')|float(0)}
          ] %}
          {% set max_soc = states('input_number.battery_max_soc_charge')|float(90) %}
          {% set valid_batteries = batteries | selectattr('soc', '<', max_soc) | list %}
          {{ (valid_batteries | sort(attribute='soc') | first).name if valid_batteries else 'none' }}
```

**Update Trigger:**
- Elke keer dat een SOC sensor wijzigt
- Elke keer dat `input_number.battery_max_soc_charge` wijzigt

**Attributes:**
```yaml
attributes:
  fase_a_soc: 80
  fase_b_soc: 45
  fase_c_soc: 15
  max_charge_limit: 90
  available_batteries: ['fase_a', 'fase_b', 'fase_c']
  reason: "fase_c selected (15% SOC, lowest)"
```

---

#### `sensor.battery_fullest`

**Doel:** Vind de volste batterij die beschikbaar is voor ontladen.

**Logic:**
```python
batteries = [...]  # Zelfde als emptiest

min_soc_discharge = 15  # Configureerbaar

# Filter batterijen die te leeg zijn
available = [b for b in batteries if b['soc'] > min_soc_discharge]

if available:
    # Sort aflopend op SOC (hoogste eerst)
    fullest = sorted(available, key=lambda x: x['soc'], reverse=True)[0]
    return fullest['name']
else:
    return 'none'  # Alle batterijen te leeg
```

---

### 2. Input helpers

Input helpers zijn configureerbare parameters die via UI kunnen worden aangepast.

#### Boolean helpers

**`input_boolean.battery_rotation_enabled`**
- **Doel:** Master enable/disable switch
- **Effect:** Alle automations checken deze voordat ze triggeren
- **Default:** OFF (veilig, manual enable vereist)

#### Number helpers

| Helper | Type | Bereik | Default | Eenheid |
|--------|------|--------|---------|---------|
| `battery_switch_hysteresis_solar` | slider | 100-3000 | 500 | W |
| `battery_switch_hysteresis_grid` | slider | 50-2000 | 200 | W |
| `trigger_delay_solar` | slider | 0.5-10 | 2 | min |
| `trigger_delay_grid` | slider | 0.5-10 | 2 | min |
| `battery_switch_delay_minutes` | slider | 1-30 | 5 | min |
| `battery_min_soc_discharge` | slider | 5-50 | 15 | % |
| `battery_max_soc_charge` | slider | 50-100 | 90 | % |

**Icon Mapping:**
- Hysteresis: `mdi:gauge`
- Delays: `mdi:timer-outline`
- SOC: `mdi:battery-outline`

#### DateTime helpers

**`input_datetime.night_mode_start_time`**
- **Format:** HH:MM (24-hour)
- **Default:** 01:00
- **Icon:** `mdi:weather-night`

**`input_datetime.day_mode_start_time`**
- **Format:** HH:MM (24-hour)
- **Default:** 07:00
- **Icon:** `mdi:weather-sunny`

**`input_datetime.last_battery_switch`**
- **Format:** Full datetime
- **Purpose:** Track laatste switch tijd voor switch delay check
- **Icon:** `mdi:clock-outline`

#### Text helpers

**`input_text.active_battery_fase`**
- **Options:** fase_a, fase_b, fase_c
- **Purpose:** Track welke batterij momenteel actief is
- **Used in:** Dashboard display, notifications

---

### 3. Automations

#### 3.1 morning battery a start

**Trigger:**
```yaml
- platform: time
  at: input_datetime.day_mode_start_time  # Default 07:00
```

**Conditions:**
```yaml
# Geen conditions - altijd activeren
# Reden: Na night charging willen we altijd bekend state
```

**Actions:**
```yaml
1. Enable system:
   input_boolean.battery_rotation_enabled → ON

2. Activeer Fase A:
   button.fasea_schuin_d828_auto_mode → PRESS

3. Wait 5 seconden (stabilisatie)

4. Deactiveer Fase B & C:
   button.faseb_plat_v3_9a7d_manual_mode → PRESS
   button.fasec_geen_deb8_manual_mode → PRESS

5. Update tracking:
   input_text.active_battery_fase → "fase_a"
   input_datetime.last_battery_switch → NOW
```

**Flow Diagram:**
```
07:00 Trigger
    ↓
Enable System (ON)
    ↓
Fase A → AUTO MODE (Actief!)
    ↓
Wait 5 sec
    ↓
Fase B → MANUAL MODE
Fase C → MANUAL MODE
    ↓
Update Tracking
    ↓
Done ✅
```

---

#### 3.2 solar excess - switch to emptiest

**Trigger:**
```yaml
- platform: numeric_state
  entity_id: sensor.p1_meter_power
  below: 0  # Teruglevering (negatief)
```

**Conditions:**
```yaml
1. System enabled:
   input_boolean.battery_rotation_enabled == ON

2. Hysteresis check:
   P1 power < (hysteresis_solar * -1)
   # Bijv: -1200W < -500W ✅

3. Trigger delay check:
   (now - last_changed_p1_power) >= trigger_delay_solar * 60
   # Bijv: 2.5 min >= 2 min ✅

4. Switch delay check:
   (now - last_battery_switch) >= switch_delay_minutes * 60
   # Bijv: 6 min >= 5 min ✅

5. Valid battery available:
   sensor.battery_emptiest != "none"
   # Minimaal 1 batterij onder max_soc_charge
```

**Actions:**
```yaml
1. Choose based on sensor.battery_emptiest:

   IF fase_a:
     - Activate Fase A (Auto)
     - Wait 5 sec
     - Deactivate Fase B & C (Manual)
     - Set active_battery_fase = "fase_a"

   ELIF fase_b:
     - Activate Fase B (Auto)
     - Wait 5 sec
     - Deactivate Fase A & C (Manual)
     - Set active_battery_fase = "fase_b"

   ELIF fase_c:
     - Activate Fase C (Auto)
     - Wait 5 sec
     - Deactivate Fase A & B (Manual)
     - Set active_battery_fase = "fase_c"

2. Update last_battery_switch = NOW

3. Send notification (optioneel):
   "Batterij switch: {{ emptiest }} actief voor laden (SOC: {{ soc }}%)"
```

**Timing Analysis:**
```
T=0:00  P1: -1200W (teruglevering)
T=0:00  Trigger fires (P1 < 0)
T=0:00  ❌ Trigger delay: 0 sec < 120 sec
T=0:30  ❌ Trigger delay: 30 sec < 120 sec
T=2:00  ✅ Trigger delay: 120 sec >= 120 sec
T=2:00  ✅ Hysteresis: -1200W < -500W
T=2:00  ✅ Switch delay: (now - last) >= 5 min
T=2:00  ✅ Valid battery: fase_c (15% SOC)
T=2:00  ACTION START
T=2:00  Activate Fase C (Auto) → API call (5-10 sec)
T=2:08  Wait 5 sec
T=2:13  Deactivate Fase A & B (Manual) → API calls (parallel, 5-10 sec)
T=2:21  Update tracking
T=2:21  ACTION COMPLETE
```

**Total Duration:** ~21 seconds, but NO GAP! Fase C active from T=2:08.

---

#### 3.3 grid consumption - switch to fullest

**Trigger:**
```yaml
- platform: numeric_state
  entity_id: sensor.p1_meter_power
  above: 0  # Netverbruik (positief)
```

**Conditions:**
```yaml
# Zelfde structuur als Solar Excess, maar:

1. System enabled ✅

2. Hysteresis check:
   P1 power > hysteresis_grid
   # Bijv: +350W > +200W ✅

3. Trigger delay check:
   (now - last_changed_p1_power) >= trigger_delay_grid * 60

4. Switch delay check:
   (now - last_battery_switch) >= switch_delay_minutes * 60

5. Valid battery available:
   sensor.battery_fullest != "none"
   # Minimaal 1 batterij boven min_soc_discharge
```

**Actions:**
```yaml
# Identiek aan Solar Excess, maar:
# - Uses sensor.battery_fullest (hoogste SOC)
# - Purpose: Ontladen i.p.v. laden
# - Notification: "... actief voor ontladen"
```

---

#### 3.4 disable rotation at night

**Trigger:**
```yaml
- platform: time
  at: input_datetime.night_mode_start_time  # Default 01:00
```

**Actions:**
```yaml
1. Disable system:
   input_boolean.battery_rotation_enabled → OFF

2. Notification (optioneel):
   "Batterij rotatie UIT (night mode)"
```

**Purpose:**
- Voorkom conflict met night charging automation
- Night charging kan batterijen A & B laden zonder interferentie
- Fase C blijft leeg (voor ochtend solar excess)

---

#### 3.5 enable rotation at day

**Trigger:**
```yaml
- platform: time
  at: input_datetime.day_mode_start_time  # Default 07:00
```

**Actions:**
```yaml
# Identiek aan "Morning Battery A Start"
# Reden: Zelfde logic (enable + activate Fase A)
```

---

### 4. Scripts

Scripts zijn herbruikbare actions voor manuele batterij controle.

#### 4.1 `script.marstek_activate_fase_a`

**Purpose:** Manueel Fase A activeren

**Sequence:**
```yaml
1. Press button.fasea_schuin_d828_auto_mode
2. Delay 5 sec
3. Press button.faseb_plat_v3_9a7d_manual_mode
4. Press button.fasec_geen_deb8_manual_mode
5. Set input_text.active_battery_fase = "fase_a"
6. Set input_datetime.last_battery_switch = NOW
```

**Mode:** `single` (prevent overlapping runs)

---

#### 4.2 `script.marstek_activate_fase_b`

Identiek aan Fase A, maar met Fase B active.

---

#### 4.3 `script.marstek_activate_fase_c`

Identiek aan Fase A, maar met Fase C active.

---

#### 4.4 `script.marstek_all_batteries_manual`

**Purpose:** Emergency stop - alle batterijen naar Manual mode

**Sequence:**
```yaml
1. Press button.fasea_schuin_d828_manual_mode
2. Press button.faseb_plat_v3_9a7d_manual_mode
3. Press button.fasec_geen_deb8_manual_mode
4. Set input_text.active_battery_fase = "none"
5. Notification: "Alle batterijen Manual mode"
```

**Use Case:**
- Emergency stop
- Maintenance
- Testing
- System misbehaving

---

### 5. Dashboard

Dashboard biedt visualisatie en manuele controle.

**Components:**

1. **Status Header (Markdown)**
   - Actieve batterij naam
   - P1 meter power (realtime)
   - Laatste switch tijd (relatief)

2. **System Toggle (Entities)**
   - `input_boolean.battery_rotation_enabled`

3. **Battery SOC Gauges (Horizontal Stack)**
   - 3x Gauge cards (Fase A, B, C)
   - Min: 0, Max: 100
   - Kleur gradient (rood → groen)

4. **Automatische Selectie (Entities)**
   - `sensor.battery_emptiest`
   - `sensor.battery_fullest`

5. **Manuele Controle (Horizontal Stack)**
   - 3x Button cards (Fase A, B, C)
   - Tap action → call script.marstek_activate_fase_*

6. **Emergency Stop (Button)**
   - Tap action → call script.marstek_all_batteries_manual
   - Rood, prominent

7. **Instellingen (Entities, Collapsed)**
   - Alle 9 configureerbare parameters
   - Hysteresis drempels
   - Trigger delays
   - SOC limieten
   - Night/day tijden

---

## 🔁 Decision flow

### Solar excess scenario

```
☀️ Solar Panels: 4500W
🏠 House Load: 800W
📊 P1 Meter: -3700W (teruglevering)

    ↓ Trigger fires (P1 < 0)

Condition Checks:
├─ System enabled?
│  ├─ ✅ YES → Continue
│  └─ ❌ NO → STOP
│
├─ Hysteresis met?
│  ├─ -3700W < -500W?
│  │  ├─ ✅ YES → Continue
│  │  └─ ❌ NO → STOP
│
├─ Trigger delay met?
│  ├─ last_changed >= 2 min?
│  │  ├─ ✅ YES → Continue
│  │  └─ ❌ NO → STOP
│
├─ Switch delay met?
│  ├─ (now - last_switch) >= 5 min?
│  │  ├─ ✅ YES → Continue
│  │  └─ ❌ NO → STOP
│
└─ Valid battery available?
   ├─ sensor.battery_emptiest != "none"?
   │  ├─ ✅ YES (fase_c, 15% SOC) → ACTIVATE
   │  └─ ❌ NO → STOP

Action:
┌─────────────────────────────────────┐
│ 1. Activate Fase C (Auto)          │
│    └─ API call → 5-10 sec          │
│    └─ Batterij ACTIVE!              │
│                                      │
│ 2. Wait 5 sec (stabilisatie)       │
│                                      │
│ 3. Deactivate Fase A & B (Manual)  │
│    └─ Parallel API calls            │
│                                      │
│ 4. Update tracking                  │
│    ├─ active_battery_fase = "fase_c"│
│    └─ last_battery_switch = NOW    │
└─────────────────────────────────────┘

Result:
🔋 Fase C actief, laadt met 3700W
⏱️  Total duration: ~21 sec, NO GAP!
```

---

### Grid consumption scenario

```
☁️ Solar Panels: 0W (bewolkt)
🏠 House Load: 2500W (airco draait)
📊 P1 Meter: +2500W (netverbruik)

    ↓ Trigger fires (P1 > 0)

Condition Checks:
├─ System enabled? ✅
├─ Hysteresis: +2500W > +200W? ✅
├─ Trigger delay: >= 2 min? ✅
├─ Switch delay: >= 5 min? ✅
└─ Valid battery: fase_a (80% SOC)? ✅

Action:
┌─────────────────────────────────────┐
│ Activate Fase A (volste, 80%)      │
│ └─ Batterij ontlaadt 2500W         │
│ └─ Grid consumption → 0W!           │
└─────────────────────────────────────┘

Result:
🔋 Fase A ontlaadt, dekt airco volledig
⚡ Grid: 0W (self-consumption)
```

---

## ⏱️ Timing & delays

### Multi-Layer anti-Flapping

**Layer 1: Hysteresis Drempels**
```
Purpose: Filter kleine fluctuaties
Effect: P1 moet boven/onder drempel zijn
Example:
  - P1: -300W → Hysteresis: -500W → ❌ No trigger
  - P1: -800W → Hysteresis: -500W → ✅ Potential trigger
```

**Layer 2: Trigger Delay**
```
Purpose: Waarde moet stabiel aanhouden
Effect: last_changed attribute check
Example:
  - P1 < -500W voor 1 min → Delay: 2 min → ❌ Wait
  - P1 < -500W voor 3 min → Delay: 2 min → ✅ Trigger
```

**Layer 3: Switch Delay**
```
Purpose: Cooldown tussen switches
Effect: Minimale tijd tussen batterij wijzigingen
Example:
  - Laatste switch: 10:30, Nu: 10:33 → Delay: 5 min → ❌ Too soon
  - Laatste switch: 10:30, Nu: 10:36 → Delay: 5 min → ✅ OK
```

**Combined Effect:**
```
Scenario: Waterkoker (2000W, 3 minuten)

T=0:00  Waterkoker start → P1: +2200W
T=0:00  ✅ Hysteresis: +2200W > +200W
T=0:00  ❌ Trigger delay: 0 sec < 120 sec → WAIT
T=2:00  ✅ Trigger delay: 120 sec >= 120 sec
T=2:00  ✅ Switch delay: OK
T=2:00  🚀 ACTION WOULD START... maar:
T=3:00  Waterkoker uit → P1: +50W
T=3:00  ❌ Hysteresis: +50W < +200W
T=3:00  last_changed RESET!
T=3:00  ❌ Trigger delay: 0 sec < 120 sec → STOP

Result: GEEN switch! (Waterkoker te kort, delay voorkomt)
```

---

## 🔐 Safety mechanisms

### 1. SOC limieten

**Min SOC Discharge (15% default):**
```yaml
Purpose: Bescherm batterij tegen diepte ontlading
Effect: Batterijen onder limiet worden niet geselecteerd voor ontladen
BMS Protection: ~5% (hardware cut-off)
Safety Margin: 10% (15% limit - 5% BMS = 10% buffer)

Example:
  Fase A: 80% → ✅ Selecteerbaar voor ontladen
  Fase B: 12% → ❌ Te laag, skip
  Fase C: 15% → ✅ Exact op limiet, selecteerbaar
```

**Max SOC Charge (90% default):**
```yaml
Purpose: Bescherm batterij tegen overmatig laden
Effect: Batterijen boven limiet worden niet geselecteerd voor laden
BMS Protection: ~100% (hardware protection)
Safety Margin: 10% (100% BMS - 90% limit = 10% buffer)
Li-ion Sweet Spot: 20-80% (maximale levensduur)

Example:
  Fase A: 91% → ❌ Te vol, skip
  Fase B: 89% → ✅ Selecteerbaar voor laden
  Fase C: 30% → ✅ Selecteerbaar voor laden
```

### 2. Switch order (Critical!)

**OLD WRONG ORDER (vóór fix):**
```yaml
1. Set Fase A & B → Manual (10-20 sec)
2. Wait 2 sec
3. Set Fase C → Auto (5-10 sec)

Problem:
├─ T=0-20s: GEEN actieve batterij!
├─ Grid consumption: Huis trekt van net
└─ Power gap: 20-30 seconden
```

**NEW CORRECT ORDER (v1.0.0+):**
```yaml
1. Set Fase C → Auto (5-10 sec) ✅ IMMEDIATELY ACTIVE!
2. Wait 5 sec (stabilisatie)
3. Set Fase A & B → Manual (parallel, 5-10 sec)

Advantage:
├─ T=8s: Fase C ACTIVE!
├─ Grid consumption: 0W (Fase C dekt alles)
└─ No gap: Continue batterij coverage
```

**Stabilization Wait:**
```yaml
Purpose: Allow battery mode transition to complete
Duration: 5 seconds
Reason:
  - API call: 2-3 sec
  - Mode switch: 1-2 sec
  - Power ramp: 1-2 sec
  - Total: ~5 sec buffer
```

### 3. Night mode protection

**Purpose:** Voorkom conflict met night charging automation

**Timeline:**
```
23:00 → Rotatie ACTIEF (normale werking)
01:00 → Night Mode START
        ├─ input_boolean.battery_rotation_enabled → OFF
        └─ Alle automations disabled (condition faalt)

01:00 → Night Charging START (externe automation)
        ├─ Fase A laadt tot 5kWh (~90%)
        ├─ Fase B laadt tot 5kWh (~90%)
        └─ Fase C: NIET laden (blijft leeg, ~15%)

07:00 → Day Mode START
        ├─ input_boolean.battery_rotation_enabled → ON
        ├─ Fase A → Auto (vol, 90%)
        ├─ Fase B → Manual (vol, 90%)
        ├─ Fase C → Manual (leeg, 15%)
        └─ Klaar voor dag rotatie!
```

**Why This Works:**
- Night charging: Volledige controle over batterijen (rotatie uit)
- Morning state: Bekend (A vol, B vol, C leeg)
- Day start: A actief (vol voor ontlading)
- Solar excess: C actief (leeg voor laden)

### 4. Entity validation

**Template Sensor Validation:**
```yaml
# sensor.battery_emptiest:
{% set batteries = [...] %}
{% set valid_batteries = batteries | selectattr('soc', '<', max_soc) | list %}

IF valid_batteries:
  return emptiest
ELSE:
  return "none"  # Automation condition will fail safely
```

**Automation Condition:**
```yaml
condition:
  - condition: template
    value_template: "{{ states('sensor.battery_emptiest') != 'none' }}"

Effect:
  - "none" → Condition fails → No action → Safe!
  - Valid battery → Condition passes → Action runs
```

---

## 📡 Communication layer

### Marstek local API integration

**Protocol:** UDP JSON-RPC
**Port:** 30000
**Format:** UTF-8 JSON

**Button Entity Mapping:**
```yaml
button.fasea_schuin_d828_auto_mode:
  API Call: ES.SetMode
  Params: {id: 0, mode: "Auto"}
  Target: 192.168.6.80:30000
  Response Time: 2-8 sec

button.fasea_schuin_d828_manual_mode:
  API Call: ES.SetMode
  Params: {id: 0, mode: "Manual"}
  Target: 192.168.6.80:30000
  Response Time: 2-8 sec
```

**Example API Transaction:**
```json
// Request (from HA to battery):
{
  "id": 1,
  "method": "ES.SetMode",
  "params": {
    "id": 0,
    "mode": "Auto"
  }
}

// Response (from battery to HA):
{
  "id": 1,
  "src": "VenusE-acd92968deb8",
  "result": {
    "id": 0,
    "mode": "Auto"
  }
}

// Error Response:
{
  "id": 1,
  "src": "VenusE-acd92968deb8",
  "error": {
    "code": -32602,
    "message": "Invalid params"
  }
}
```

**SOC Sensor Update:**
```yaml
Entity: sensor.marstek_venuse_d828_state_of_charge
API Call: ES.GetStatus
Poll Interval: 30-60 sec (configurable in integration)
Response:
  {
    "bat_soc": 75,        ← Used for sensor
    "bat_cap": 5120,
    "pv_power": 1200,
    ...
  }
```

---

### P1 meter integration

**Protocol:** DSMR (Dutch Smart Meter Requirements)
**Interface:** USB Serial
**Format:** ASCII telegram (OBIS codes)

**Example Telegram:**
```
/ISk5\2MT382-1000

1-0:1.8.1(123456.789*kWh)    # Import tariff 1
1-0:2.8.1(012345.678*kWh)    # Export tariff 1
1-0:1.7.0(01.234*kW)         # Current import ← Used!
1-0:2.7.0(00.000*kW)         # Current export ← Used!
```

**Sensor Mapping:**
```yaml
sensor.p1_meter_power:
  Calculation: (import - export)
  Example 1: Import=0.000kW, Export=1.234kW → -1234W (teruglevering)
  Example 2: Import=2.345kW, Export=0.000kW → +2345W (verbruik)
  Update Interval: ~1 sec (realtime)
```

---

## 🧮 Template logic deep dive

### Battery selection algorithm

**Pseudo-code:**
```python
def get_emptiest_battery():
    batteries = [
        Battery("fase_a", soc=80),
        Battery("fase_b", soc=45),
        Battery("fase_c", soc=15)
    ]

    max_soc_charge = 90  # Config parameter

    # Filter: Remove batteries too full
    available = [b for b in batteries if b.soc < max_soc_charge]
    # Result: [fase_a(80), fase_b(45), fase_c(15)]

    if not available:
        return "none"  # All batteries too full

    # Sort ascending by SOC (lowest first)
    sorted_batteries = sorted(available, key=lambda b: b.soc)
    # Result: [fase_c(15), fase_b(45), fase_a(80)]

    # Select first (lowest SOC)
    emptiest = sorted_batteries[0]
    # Result: fase_c

    return emptiest.name
```

**Edge Cases:**

**Case 1: All Batteries Full**
```python
batteries = [
    Battery("fase_a", soc=91),
    Battery("fase_b", soc=92),
    Battery("fase_c", soc=89)
]
max_soc_charge = 90

available = [b for b in batteries if b.soc < 90]
# Result: [fase_c(89)] ← Only Fase C available!

return "fase_c"  # Still works!
```

**Case 2: All Batteries TOO Full**
```python
batteries = [
    Battery("fase_a", soc=91),
    Battery("fase_b", soc=92),
    Battery("fase_c", soc=93)
]
max_soc_charge = 90

available = [b for b in batteries if b.soc < 90]
# Result: [] ← Empty list!

return "none"  # Automation condition will fail, no switch
```

**Case 3: Tie (Equal SOC)**
```python
batteries = [
    Battery("fase_a", soc=50),
    Battery("fase_b", soc=50),  # TIE!
    Battery("fase_c", soc=60)
]

sorted_batteries = sorted(batteries, key=lambda b: b.soc)
# Result: [fase_a(50), fase_b(50), fase_c(60)]
#          ↑ First in list wins

return "fase_a"  # Deterministic: alfabetische volgorde bij tie
```

---

### Trigger delay logic (last_changed workaround)

**Problem:** Home Assistant `for:` parameter doesn't support templates

**Naive Approach (DOESN'T WORK):**
```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.p1_meter_power
    below: 0
    for:
      minutes: "{{ states('input_number.trigger_delay_solar') }}"  # ❌ NOT SUPPORTED!
```

**Working Solution:**
```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.p1_meter_power
    below: 0
    # NO 'for:' parameter here!

condition:
  - condition: template
    value_template: >
      {% set delay_seconds = states('input_number.trigger_delay_solar')|float(2) * 60 %}
      {{ (as_timestamp(now()) - as_timestamp(states.sensor.p1_meter_power.last_changed)) >= delay_seconds }}
```

**How It Works:**
```python
# Example:
now = "2024-11-20 10:05:00"  # Current time
last_changed = "2024-11-20 10:02:30"  # Last time sensor value changed
delay_config = 2  # Minutes from input_number

# Convert to seconds:
delay_seconds = 2 * 60 = 120

# Calculate time elapsed since last change:
elapsed = as_timestamp(now) - as_timestamp(last_changed)
# 1730289900 - 1730289750 = 150 seconds

# Check if elapsed >= delay:
150 >= 120  # ✅ TRUE → Condition passes

# If P1 value changes:
# last_changed resets to NOW
# elapsed = 0 seconds
# 0 >= 120  # ❌ FALSE → Condition fails
```

**Key Insight:**
- `last_changed` attribute resets elke keer dat de sensor VALUE wijzigt
- Niet elke keer dat sensor UPDATE (state change vs value change)
- Perfect voor "stable value for X minutes" check

---

## 🎯 Performance optimization

### Template sensor update frequency

**Current:** Updates wanneer dependency wijzigt (reactive)

**Optimization:** Add scan_interval voor periodic fallback
```yaml
template:
  - sensor:
      - name: "Battery Emptiest"
        state: ...
        scan_interval: 60  # Force update elke 60 sec als fallback
```

**Trade-off:**
- Pro: Garanteerde updates, geen stale data
- Con: Extra CPU, meer state changes in recorder

---

### Automation parallelization

**Current:** Sequential button presses na nieuwe batterij actief

**Optimization:** Parallelize deactivation calls
```yaml
- service: button.press
  target:
    entity_id:
      - button.faseb_plat_v3_9a7d_manual_mode
      - button.fasec_geen_deb8_manual_mode
  # Both calls happen simultaneously!
```

**Effect:**
- Sequential: 5 sec + 5 sec = 10 sec
- Parallel: max(5 sec, 5 sec) = 5 sec
- Savings: 5 sec per switch

---

## 📊 Data flow diagram

```
┌──────────────┐
│  P1 Meter    │
│  -1200W      │
└──────┬───────┘
       │ USB Serial
       │ Update: ~1 sec
       ▼
┌──────────────────────┐
│ sensor.p1_meter_power│
│ State: -1200         │
│ last_changed: 10:03  │
└──────┬───────────────┘
       │ State change event
       ▼
┌────────────────────────────────┐
│ Automation Trigger             │
│ numeric_state below 0          │
└──────┬─────────────────────────┘
       │ Trigger fires
       ▼
┌────────────────────────────────┐
│ Condition Checks               │
│ 1. System enabled? ✅          │
│ 2. Hysteresis? ✅              │
│ 3. Trigger delay? ✅           │
│ 4. Switch delay? ✅            │
│ 5. Valid battery? ✅           │
└──────┬─────────────────────────┘
       │ All conditions pass
       ▼
┌────────────────────────────────┐
│ Template Sensor Read           │
│ sensor.battery_emptiest        │
│ State: "fase_c"                │
└──────┬─────────────────────────┘
       │ Choose action: fase_c
       ▼
┌────────────────────────────────┐
│ API Call 1:                    │
│ button.fasec_geen_deb8_auto_   │
│ mode.press()                   │
│ → UDP to 192.168.6.144:30000   │
│ → ES.SetMode {mode: "Auto"}    │
└──────┬─────────────────────────┘
       │ Response: 5-10 sec
       │ Fase C: AUTO MODE ✅
       ▼
┌────────────────────────────────┐
│ Wait 5 seconds                 │
│ (stabilization)                │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ API Call 2 & 3 (Parallel):     │
│ button.fasea_*_manual.press()  │
│ button.faseb_*_manual.press()  │
│ → UDP to .80:30000 & .213:30000│
└──────┬─────────────────────────┘
       │ Responses: 5-10 sec
       │ Fase A & B: MANUAL ✅
       ▼
┌────────────────────────────────┐
│ Update Tracking                │
│ active_battery_fase = "fase_c" │
│ last_battery_switch = NOW      │
└────────────────────────────────┘
```

---

## 🔬 Testing architecture

### Unit tests

**Location:** `tests/api/`

**apiTest.py:**
```python
# Tests direct API communication
# Methods tested:
- Marstek.GetDevice
- ES.GetStatus
- ES.GetMode
- BLE.GetStatus

# Validates:
- Response format (JSON)
- Response time (<2 sec)
- Error handling (timeout, invalid response)
```

### Integration tests

**Location:** `tests/battery/`

**test_all_batteries.py:**
```python
# Tests all 3 batteries sequentially
# For each battery:
  1. Get current mode
  2. Switch to Auto
  3. Verify mode changed
  4. Switch to Manual
  5. Verify mode changed

# Validates:
- All batteries reachable
- Mode switching works
- API integration functional
```

### Entity verification

**Location:** `tests/verify-entities.py`

```python
# Checks HA entity existence
# Entities verified:
- sensor.battery_emptiest
- sensor.battery_fullest
- input_boolean.battery_rotation_enabled
- All button entities (6x)
- All SOC sensors (3x)
- All input_number helpers (7x)
- All input_datetime helpers (3x)

# Output:
- ✅ Entity found
- ❌ Entity missing (with suggestion)
```

---

## 🔮 Future architecture considerations

### Planned enhancements

**1. Dynamic Power Allocation**
```yaml
# Current: One battery active (Auto), others Manual
# Future: Multiple batteries active with power split

Example:
  Solar excess: 5000W
  Fase B: 30% SOC, charge at 2500W
  Fase C: 15% SOC, charge at 2500W
  Total: 5000W distributed

Implementation:
  - Use Passive mode with power parameter
  - Calculate power split based on SOC delta
  - Update every 5 minutes based on actual charging
```

**2. SOC Prediction**
```yaml
# Predict future SOC based on:
- Current power flow
- Historical patterns
- Weather forecast

Use Case:
  "Fase C will reach 90% in 2 hours at current rate"
  → Switch to different battery proactively
```

**3. Energy Price Optimization**
```yaml
# Integration with Nordpool/Tibber
# Optimize battery usage based on price:

Example:
  19:00-21:00: High price (€0.45/kWh)
  → Discharge batteries (sell expensive)

  02:00-04:00: Low price (€0.08/kWh)
  → Charge batteries (buy cheap)
```

**4. MQTT Bridge**
```yaml
# Publish battery data via MQTT
# Allows external monitoring/control

Topics:
  marstek/battery/a/soc → 80
  marstek/battery/a/power → -2500
  marstek/battery/a/mode → Auto
  marstek/system/active_battery → fase_a
```

---

## 📚 References

**Home Assistant Docs:**
- Template Sensors: https://www.home-assistant.io/integrations/template/
- Automations: https://www.home-assistant.io/docs/automation/
- Packages: https://www.home-assistant.io/docs/configuration/packages/

**Marstek Protocol:**
- BLE Protocol: https://rweijnen.github.io/marstek-venus-monitor/
- Local API: https://github.com/jaapp/ha-marstek-local-api

**P1 Meter:**
- DSMR Spec: https://www.netbeheernederland.nl/dossiers/slimme-meter-15
- HA Integration: https://www.home-assistant.io/integrations/dsmr/

---

**Vragen over de architectuur? Zie [TROUBLESHOOTING.md](TROUBLESHOOTING.md) of [open een issue](https://github.com/jouw-username/marstek-battery-rotation/issues)!**
