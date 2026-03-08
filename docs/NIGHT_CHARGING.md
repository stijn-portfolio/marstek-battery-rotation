# Intelligent Night Charging Feature

> **Status**: Gepland
> **Datum**: November 2024

## Doel

Automatisch laden tijdens nachtmodus (goedkoop tarief) om een gewenste totale capaciteit te bereiken bij dagstart.

## Voorbeeld Scenario

```
Gewenste capaciteit bij dagstart: 10 kWh
Huidige totale capaciteit:         7 kWh
Te laden:                          3 kWh
Nachtmodus:                        01:00 - 07:00 (6 uur)
Benodigd laadvermogen:             3000 Wh / 6h = 500W
Doelbatterij:                      Leegste batterij
```

---

## Marstek API Capabilities

### Beschikbare Modes

| Mode | Functie | Laadt van net? |
|------|---------|----------------|
| **Auto** | Automatisch op basis van zon | Nee |
| **AI** | Intelligent mode | ? |
| **Manual** | Met schema's en power limits | Ja (met schema) |
| **Passive** | Direct power control met duratie | Ja |

### Cruciale Services

#### 1. `marstek_local_api.set_manual_schedule`

Schema instellen voor laden/ontladen:

```yaml
service: marstek_local_api.set_manual_schedule
data:
  device_id: "abc123"       # Batterij device ID
  time_num: 0               # Slot 0-9
  start_time: "01:00"
  end_time: "07:00"
  days: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
  power: -2000              # NEGATIEF = LADEN (2000W)
  enabled: true
```

#### 2. `marstek_local_api.set_passive_mode`

Direct laden/ontladen met duratie:

```yaml
service: marstek_local_api.set_passive_mode
data:
  device_id: "abc123"
  power: -2000              # NEGATIEF = LADEN
  duration: 21600           # Seconden (6 uur)
```

#### 3. `marstek_local_api.clear_manual_schedules`

Alle schema's wissen:

```yaml
service: marstek_local_api.clear_manual_schedules
data:
  device_id: "abc123"
```

### Power Conventie

- **Negatief = LADEN** (bijv. -2000 = laden met 2000W)
- **Positief = ONTLADEN** (bijv. 800 = ontladen met 800W)
- **Nul = Geen limiet**

---

## Implementatie Plan

### Stap 1: Input Helpers Toevoegen

```yaml
input_number:
  desired_total_capacity:
    name: "Gewenste Totale Capaciteit"
    min: 0
    max: 15
    step: 0.5
    initial: 10
    unit_of_measurement: "kWh"
    icon: mdi:battery-charging-high
```

### Stap 2: Template Sensors Toevoegen

```yaml
template:
  - sensor:
      - name: "Marstek Capacity Deficit"
        unique_id: marstek_capacity_deficit
        unit_of_measurement: "kWh"
        state: >
          {% set desired = states('input_number.desired_total_capacity')|float(10) %}
          {% set current = states('sensor.marstek_system_total_remaining_capacity_2')|float(0) %}
          {{ [0, desired - current]|max|round(2) }}
        icon: mdi:battery-alert

      - name: "Marstek Night Hours"
        unique_id: marstek_night_hours
        unit_of_measurement: "h"
        state: >
          {% set night_start = states('input_datetime.night_mode_start_time') %}
          {% set day_start = states('input_datetime.day_mode_start_time') %}
          {% if night_start and day_start %}
            {% set ns = strptime(night_start, '%H:%M:%S') %}
            {% set ds = strptime(day_start, '%H:%M:%S') %}
            {% set night_minutes = ns.hour * 60 + ns.minute %}
            {% set day_minutes = ds.hour * 60 + ds.minute %}
            {% if day_minutes > night_minutes %}
              {{ ((day_minutes - night_minutes) / 60)|round(1) }}
            {% else %}
              {{ ((1440 - night_minutes + day_minutes) / 60)|round(1) }}
            {% endif %}
          {% else %}
            6
          {% endif %}
        icon: mdi:clock-time-eight

      - name: "Marstek Required Charging Power"
        unique_id: marstek_required_charging_power
        unit_of_measurement: "W"
        state: >
          {% set deficit = states('sensor.marstek_capacity_deficit')|float(0) %}
          {% set hours = states('sensor.marstek_night_hours')|float(6) %}
          {% if hours > 0 %}
            {{ ((deficit / hours) * 1000)|round(0) }}
          {% else %}
            0
          {% endif %}
        icon: mdi:flash
```

### Stap 3: Nachtmodus Automation Aanpassen

```yaml
automation:
  - id: marstek_night_charging
    alias: "Marstek: Night Charging"
    description: "Laad leegste batterij tijdens nachtmodus"
    trigger:
      - platform: time
        at: input_datetime.night_mode_start_time
    action:
      # Bereken benodigd vermogen
      - variables:
          deficit: "{{ states('sensor.marstek_capacity_deficit')|float(0) }}"
          power_needed: "{{ states('sensor.marstek_required_charging_power')|int(0) }}"
          # Cap op max 2500W per batterij
          power_capped: "{{ [power_needed, 2500]|min }}"
          emptiest: "{{ states('sensor.battery_emptiest') }}"
          night_end: "{{ states('input_datetime.day_mode_start_time') }}"

      # Alleen laden als deficit > 0
      - condition: template
        value_template: "{{ deficit > 0 }}"

      # Zet rotatie uit
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.battery_rotation_enabled

      # Bepaal device_id van leegste batterij
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ emptiest == 'fase_a' }}"
            sequence:
              # Set charging schedule voor Fase A
              - service: marstek_local_api.set_manual_schedule
                data:
                  device_id: "FASE_A_DEVICE_ID"  # TODO: vervang met echte ID
                  time_num: 0
                  start_time: "{{ states('input_datetime.night_mode_start_time')[:5] }}"
                  end_time: "{{ night_end[:5] }}"
                  power: "{{ -power_capped }}"  # Negatief voor laden
                  enabled: true
              # Andere batterijen naar Manual
              - service: button.press
                target:
                  entity_id:
                    - button.faseb_plat_v3_9a7d_manual_mode
                    - button.fasec_geen_deb8_manual_mode
                continue_on_error: true

          # Herhaal voor fase_b en fase_c...

      # Notificatie
      - service: notify.persistent_notification
        data:
          title: "Marstek - Nachtladen"
          message: >
            Laden: {{ deficit }} kWh @ {{ power_capped }}W
            Batterij: {{ emptiest }}
```

### Stap 4: Dagmodus Automation Aanpassen

```yaml
automation:
  - id: marstek_enable_rotation_in_morning
    alias: "Marstek: Enable Rotation in Morning"
    trigger:
      - platform: time
        at: input_datetime.day_mode_start_time
    action:
      # Clear charging schedules
      - service: marstek_local_api.clear_manual_schedules
        data:
          device_id: "FASE_A_DEVICE_ID"
        continue_on_error: true
      - service: marstek_local_api.clear_manual_schedules
        data:
          device_id: "FASE_B_DEVICE_ID"
        continue_on_error: true
      - service: marstek_local_api.clear_manual_schedules
        data:
          device_id: "FASE_C_DEVICE_ID"
        continue_on_error: true

      # Zet rotatie aan
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.battery_rotation_enabled

      # Activeer Fase A
      - service: button.press
        target:
          entity_id: button.fasea_schuin_d828_auto_mode
        continue_on_error: true

      # ... rest van dagmodus logic
```

### Stap 5: Dashboard Uitbreiden

```yaml
# In Instellingen sectie toevoegen:
- entity: input_number.desired_total_capacity
  name: Gewenste Capaciteit bij Dagstart

- type: divider

- entity: sensor.marstek_capacity_deficit
  name: Te Laden (deficit)

- entity: sensor.marstek_required_charging_power
  name: Benodigd Laadvermogen
```

---

## Risico's & Overwegingen

### Technisch
- Max laadvermogen per batterij: ~2500W
- Als deficit te groot voor nachturen → maximaal vermogen gebruiken
- Batterij kan vol raken voor einde nacht

### Mogelijke Uitbreidingen
1. **Rotatie tijdens nacht**: Als leegste batterij vol → switch naar volgende
2. **Dynamisch tarief**: Integratie met energieprijzen API
3. **Weersverwachting**: Minder laden als veel zon verwacht

---

## Device IDs Mapping

> **TODO**: Vul de echte device IDs in

| Batterij | Entity Prefix | Device ID |
|----------|---------------|-----------|
| Fase A (schuin) | `marstek_venuse_d828` | `???` |
| Fase B (plat) | `marstek_venuse_3_0_9a7d` | `???` |
| Fase C (geen) | `marstek_venuse` | `???` |

Om device IDs te vinden:
1. Developer Tools → Services
2. Selecteer `marstek_local_api.set_manual_schedule`
3. Kies een batterij → device_id wordt getoond

---

## Checklist Implementatie

- [ ] Input helper toevoegen
- [ ] Template sensors toevoegen
- [ ] Device IDs ophalen
- [ ] Nachtmodus automation aanpassen
- [ ] Dagmodus automation aanpassen
- [ ] Dashboard uitbreiden
- [ ] Testen met lage power waarde
- [ ] Documentatie bijwerken
