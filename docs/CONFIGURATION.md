# ⚙️ Configuratie handleiding

Uitgebreide uitleg van alle configureerbare parameters in het Marstek Battery Rotation systeem.

---

## 📍 Waar vind je de instellingen?

**Home Assistant → Instellingen → Apparaten en diensten → Helpers**

Zoek naar "Battery" of "Batterij" om alle gerelateerde helpers te vinden.

**OF via het Dashboard:**
Onderaan het Battery Rotation dashboard card staat de "Instellingen" sectie met alle configureerbare parameters.

---

## 🎛️ Alle configureerbare parameters

### 1. Switch Hysteresis - Zon (`input_number.battery_switch_hysteresis_solar`)

**Default:** 500W
**Bereik:** 100W - 3000W
**Eenheid:** Watt (W)

#### Wat doet dit?
Minimale teruglevering (negatief vermogen op P1 meter) voordat het systeem overweegt om te switchen naar de leegste batterij.

#### Technische werking
```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.p1_meter_power
    below: 0  # Teruglevering (negatief)

condition:
  - condition: template
    value_template: >
      {{ states('sensor.p1_meter_power')|float(0) <
         (states('input_number.battery_switch_hysteresis_solar')|float(500) * -1) }}
```

#### Praktische voorbeelden

**Scenario 1: Stabiel Weer (Default: 500W)**
- Zonnepanelen leveren constant 2000W
- Huis verbruikt 800W
- P1 meter: -1200W (teruglevering)
- ✅ Trigger: -1200W < -500W → Switch naar leegste batterij

**Scenario 2: Wisselvallig Weer (Verhoog naar 1000W)**
- Zonnepanelen fluctueren tussen 500W en 2500W (wolken)
- Huis verbruikt 800W
- P1 meter varieert van -300W tot -1700W
- ❌ Bij -300W: geen trigger (niet onder -1000W)
- ✅ Bij -1700W: trigger → Switch naar leegste batterij
- **Effect:** Voorkomt te veel switches bij wisselvallig weer

**Scenario 3: Winter met Weinig Zon (Verlaag naar 200W)**
- Zonnepanelen leveren slechts 400W
- Huis verbruikt 100W
- P1 meter: -300W
- ✅ Trigger: -300W < -200W → Switch naar leegste batterij
- **Effect:** Maakt gebruik van elke kleine hoeveelheid zonoverschot

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Stabiel zonnig weer | 500W (default) | Balanced, goede efficiency |
| Wisselvallig weer | 800-1000W | Voorkom te veel switches |
| Winter (weinig zon) | 200-300W | Maximaliseer gebruik van beperkte zon |
| Grote PV installatie (>10kWp) | 1000-1500W | Hogere drempel past bij grotere fluctuaties |
| Kleine PV installatie (<3kWp) | 200-400W | Lagere drempel om alle zon te benutten |

#### Gevolgen van instelling

**Te Laag (< 200W):**
- ⚠️ Veel switches bij kleine fluctuaties
- ⚠️ Batterij slijtage door te veel switches
- ⚠️ Mogelijk grid bounce (kort van net trekken tijdens switch)

**Te Hoog (> 1500W):**
- ⚠️ Gemiste kansen om zonoverschot op te slaan
- ⚠️ Teruglevering naar net i.p.v. opslag in batterij
- ⚠️ Niet optimaal gebruik van batterijen

---

### 2. Switch Hysteresis - Net (`input_number.battery_switch_hysteresis_grid`)

**Default:** 200W
**Bereik:** 50W - 2000W
**Eenheid:** Watt (W)

#### Wat doet dit?
Minimale netverbruik (positief vermogen op P1 meter) voordat het systeem overweegt om te switchen naar de volste batterij.

#### Technische werking
```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.p1_meter_power
    above: 0  # Netverbruik (positief)

condition:
  - condition: template
    value_template: >
      {{ states('sensor.p1_meter_power')|float(0) >
         states('input_number.battery_switch_hysteresis_grid')|float(200) }}
```

#### Praktische voorbeelden

**Scenario 1: Normale Dag (Default: 200W)**
- Zonnepanelen: 0W (bewolkt)
- Huis verbruikt: 500W
- P1 meter: +500W
- ✅ Trigger: +500W > +200W → Switch naar volste batterij

**Scenario 2: Koffiezetapparaat (1800W)**
- Apparaat start → P1 springt naar +2000W
- Na 3 minuten klaar → P1 terug naar +100W
- Met trigger delay van 2 min:
  - ❌ Switch gebeurt NIET (duurt maar 3 min, drempel 2 min wordt net gehaald maar apparaat al uit)
  - ✅ Voorkomt onnodige switch voor korte piek

**Scenario 3: Wasmachine Draait (Verhoog naar 500W)**
- Wasmachine verbruikt 300-400W voor 2 uur
- P1 meter: +300W (onder drempel van 500W)
- ❌ Geen trigger → blijft op huidige batterij
- **Gebruik:** Als je kleine verbruikers wilt negeren en alleen grote apparaten wilt dekken met batterij

**Scenario 4: Nachttarief Laden (Verlaag naar 50W)**
- Tijdens nacht: batterij rotatie UIT (night mode)
- Maar overdag: wil je ELKE Watt dekken met batterij
- P1 meter: +80W (standby verbruik)
- ✅ Trigger: +80W > +50W → Switch naar volste batterij
- **Effect:** Maximale self-consumption, minimaal grid verbruik

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Normale situatie | 200W (default) | Dekt meeste verbruik, negeert standby |
| Veel korte pieken (waterkoker, etc) | 500-800W | Voorkom switches voor korte apparaten |
| Maximale self-consumption | 50-100W | Dek zelfs standby verbruik met batterij |
| Night charging actief | 0W (of systeem UIT) | Laat night charging automation het overnemen |
| Grote verbruikers (airco, etc) | 1000-1500W | Switch alleen voor grote apparaten |

#### Gevolgen van instelling

**Te Laag (< 100W):**
- ⚠️ Veel switches bij kleine verbruiksschommelingen
- ⚠️ Mogelijk switch voor standby verbruik (<50W)
- ✅ Maximale batterij benutting
- ✅ Minimaal grid verbruik

**Te Hoog (> 800W):**
- ⚠️ Kleine tot middelgrote verbruikers worden niet gedekt
- ⚠️ Meer grid verbruik
- ✅ Minder switches
- ✅ Batterij wordt gespaard voor grote verbruikers

---

### 3. Trigger Delay - Zon (`input_number.trigger_delay_solar`)

**Default:** 2 minuten
**Bereik:** 0.5 - 10 minuten
**Eenheid:** Minuten

#### Wat doet dit?
Hoe lang de teruglevering (zonoverschot) moet aanhouden BOVEN de hysteresis drempel voordat er wordt geswitcht naar de leegste batterij.

#### Technische werking
```yaml
condition:
  - condition: template
    value_template: >
      {% set delay_seconds = states('input_number.trigger_delay_solar')|float(2) * 60 %}
      {{ (as_timestamp(now()) - as_timestamp(states.sensor.p1_meter_power.last_changed))
         >= delay_seconds }}
```

**Belangrijk:** Home Assistant `for:` parameter ondersteunt geen templates, dus we gebruiken `last_changed` attribute check.

#### Praktische voorbeelden

**Scenario 1: Waterkoker (2000W, 3 minuten)**
- T=0min: Waterkoker start → P1: -2500W (zonoverschot door PV 4500W - verbruik 2000W)
- T=0min: Hysteresis check: -2500W < -500W ✅
- T=0min: Delay check: 0 min < 2 min ❌ → Geen switch
- T=2min: Delay check: 2 min >= 2 min ✅ → **Zou nu switchen...**
- T=3min: Waterkoker uit → P1 wijzigt → last_changed reset → Delay check: 0 min < 2 min ❌
- **Resultaat:** GEEN switch! Waterkoker was te kort actief.

**Scenario 2: Middagzon (Stabiel 5 uur)**
- T=12:00: Zon komt vrij → P1: -1500W
- T=12:00: last_changed = 12:00
- T=12:01: Delay check: 1 min < 2 min ❌
- T=12:02: Delay check: 2 min >= 2 min ✅ → **Switch naar leegste batterij**
- T=12:02-17:00: Batterij laadt gedurende 5 uur
- **Resultaat:** Correcte switch, lange laadperiode

**Scenario 3: Wisselvallige Wolken**
- T=0min: P1: -800W (zonoverschot)
- T=1min: Wolk → P1: +100W (verbruik) → **last_changed reset!**
- T=2min: Zon terug → P1: -900W → **last_changed reset naar T=2min!**
- T=3min: Delay check: 1 min < 2 min ❌ (sinds laatste wijziging)
- T=4min: Delay check: 2 min >= 2 min ✅ → Switch
- **Resultaat:** Delay voorkomt switch tijdens instabiele periode

**Scenario 4: Verhoog naar 5 minuten (zeer wisselvallig weer)**
- Wolken passeren elke 3-4 minuten
- P1 wisselt tussen -1000W en +200W
- Delay van 5 min betekent: teruglevering moet 5 min stabiel blijven
- **Effect:** Alleen switchen bij echt stabiele zonoverschot periodes

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Stabiel weer | 2 min (default) | Goede balans tussen snelheid en stabiliteit |
| Wisselvallig weer | 5-10 min | Voorkom switches tijdens wolkenperiodes |
| Grote PV installatie | 1-2 min | Snelle reactie op overschot |
| Test fase | 0.5-1 min | Snelle feedback tijdens testen |
| Zomer (veel zon) | 1-2 min | Snelle reactie, zon blijft toch lang |
| Lente/herfst (wisselvallig) | 3-5 min | Voorkom flapping |

#### Gevolgen van instelling

**Te Kort (< 1 min):**
- ⚠️ Te veel switches bij korte zonnige periodes
- ⚠️ Flapping bij wisselvallig weer
- ✅ Snelle reactie op echt zonoverschot

**Te Lang (> 5 min):**
- ⚠️ Gemiste kansen (zonoverschot wordt teruggeleverd i.p.v. opgeslagen)
- ⚠️ Batterij switch komt te laat
- ✅ Zeer stabiel, geen onnodige switches

---

### 4. Trigger Delay - Net (`input_number.trigger_delay_grid`)

**Default:** 2 minuten
**Bereik:** 0.5 - 10 minuten
**Eenheid:** Minuten

#### Wat doet dit?
Hoe lang het netverbruik moet aanhouden BOVEN de hysteresis drempel voordat er wordt geswitcht naar de volste batterij.

#### Praktische voorbeelden

**Scenario 1: Wasmachine (400W, 90 minuten)**
- T=0min: Wasmachine start → P1: +600W
- T=0min: Hysteresis check: +600W > +200W ✅
- T=0min: Delay check: 0 min < 2 min ❌
- T=2min: Delay check: 2 min >= 2 min ✅ → **Switch naar volste batterij**
- T=2-90min: Volste batterij levert 400W
- **Resultaat:** Correcte switch, batterij dekt wasmachine

**Scenario 2: Koffiezetapparaat (1800W, 5 minuten)**
- T=0min: Koffie start → P1: +2000W
- T=2min: Delay check: 2 min >= 2 min ✅ → **Switch gestart...**
- T=2min: Switch duurt 10-15 seconden
- T=5min: Koffie klaar → P1: +50W → **last_changed reset**
- **Probleem:** Switch gebeurde, maar koffie al bijna klaar!
- **Oplossing:** Verhoog delay naar 3-5 min voor korte apparaten

**Scenario 3: Delay 5 minuten - Koffiezetapparaat**
- T=0min: Koffie start → P1: +2000W
- T=5min: Koffie al klaar (duurt maar 5 min) → P1: +50W
- Delay check: nooit 5 min stabiel gebleven
- **Resultaat:** GEEN switch! Koffie was te kort, switch niet de moeite waard

**Scenario 4: Airco (2500W, 3 uur)**
- T=0min: Airco start → P1: +2800W
- T=2min: Delay check: 2 min >= 2 min ✅ → Switch naar volste batterij
- T=2min-3uur: Batterij levert 2500W
- **Resultaat:** Perfecte use case voor batterij ontlading

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Normale situatie | 2 min (default) | Dekt meeste langdurige verbruikers |
| Veel korte verbruikers | 5-10 min | Negeer waterkoker, koffie, etc |
| Vooral lange verbruikers | 1-2 min | Snelle batterij inzet |
| Test fase | 0.5-1 min | Snelle feedback |
| Airco/verwarming | 1-2 min | Deze draaien lang, snelle reactie gewenst |

#### Gevolgen van instelling

**Te Kort (< 1 min):**
- ⚠️ Switch voor korte verbruikers (waterkoker, etc)
- ⚠️ Batterij switch voor 5 min verbruik (inefficiënt)
- ✅ Snelle batterij inzet bij grote verbruikers

**Te Lang (> 5 min):**
- ⚠️ Grid verbruik tijdens wachttijd (eerste 5 min komt van net)
- ⚠️ Gemiste kansen voor batterij ontlading
- ✅ Alleen lange, stabiele verbruikers worden gedekt

---

### 5. Min Tijd Tussen Switches (`input_number.battery_switch_delay_minutes`)

**Default:** 5 minuten
**Bereik:** 1 - 30 minuten
**Eenheid:** Minuten

#### Wat doet dit?
Minimale tijd die moet verstrijken tussen twee batterij switches. Anti-flapping bescherming.

#### Technische werking
```yaml
condition:
  - condition: template
    value_template: >
      {% set last_switch = states('input_datetime.last_battery_switch') %}
      {% set delay_min = states('input_number.battery_switch_delay_minutes')|float(5) %}
      {{ (as_timestamp(now()) - as_timestamp(last_switch)) / 60 >= delay_min }}
```

#### Praktische voorbeelden

**Scenario 1: Zon → Verbruik → Zon (Wisselvallig)**
- T=10:00: Zonoverschot → Switch naar leegste batterij (Fase B, 30%)
- T=10:02: Switch compleet, last_battery_switch = 10:02
- T=10:05: Wolk → Netverbruik +300W
  - Hysteresis: +300W > +200W ✅
  - Trigger delay: 2 min ✅
  - **Switch delay check:** (10:07 - 10:02) = 5 min >= 5 min ✅
  - → Switch naar volste batterij (Fase A, 80%)
- **Resultaat:** Switch toegestaan, minimale tijd verstreken

**Scenario 2: Snel Wisselend Weer (Default 5 min beschermt)**
- T=10:00: Zon → Switch naar Fase B (leegste)
- T=10:02: Switch compleet, last_battery_switch = 10:02
- T=10:04: Wolk → Netverbruik
- T=10:06: Netverbruik trigger delay compleet (2 min)
  - **Switch delay check:** (10:06 - 10:02) = 4 min < 5 min ❌
  - → Switch GEBLOKKEERD!
- T=10:07: Zon terug → Zonoverschot (maar vorige switch nog geen 5 min geleden)
  - → Blijft op huidige batterij (Fase B)
- **Resultaat:** Voorkomt ping-pong switches

**Scenario 3: Verhoog naar 15 min (Extra Bescherming)**
- Zeer wisselvallig weer met constant wisseling zon/wolk
- Switch delay van 15 min betekent: max 4 switches per uur
- **Effect:** Batterij slijtage minimaliseren, stabiliteit maximaliseren

**Scenario 4: Verlaag naar 2 min (Agressieve Switching)**
- Grote batterij installatie (3x5kWh = 15kWh totaal)
- Wil maximaal reageren op elke situatie
- **Risico:** Meer switches, meer slijtage
- **Voordeel:** Optimale batterij benutting

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Normale situatie | 5 min (default) | Goede balans slijtage/efficiency |
| Zeer wisselvallig weer | 10-15 min | Extra bescherming tegen flapping |
| Stabiel weer | 3-5 min | Kan sneller switchen |
| Test fase | 1-2 min | Snelle feedback |
| Batterij levensduur maximaliseren | 15-30 min | Minimaliseer aantal switches |
| Optimale efficiency | 3-5 min | Snelle aanpassing aan situatie |

#### Gevolgen van instelling

**Te Kort (< 3 min):**
- ⚠️ Veel batterij switches
- ⚠️ Verhoogde slijtage
- ⚠️ Mogelijk flapping bij wisselvallig weer
- ✅ Snelle aanpassing aan wijzigende situaties

**Te Lang (> 15 min):**
- ⚠️ Suboptimale batterij benutting
- ⚠️ Gemiste kansen (verkeerde batterij actief)
- ⚠️ Mogelijk grid verbruik/teruglevering tijdens wachttijd
- ✅ Minimale batterij slijtage
- ✅ Zeer stabiel systeem

---

### 6. Min SOC Ontladen (`input_number.battery_min_soc_discharge`)

**Default:** 15%
**Bereik:** 5% - 50%
**Eenheid:** Procent (%)

#### Wat doet dit?
Voorkomt dat een batterij geselecteerd wordt voor ontlading (grid consumption) als de SOC onder deze waarde zit.

#### Technische werking
```yaml
# In sensor.battery_fullest template
{% set batteries = [
  {'name': 'fase_a', 'soc': states('sensor.marstek_venuse_d828_state_of_charge')|float(0)},
  {'name': 'fase_b', 'soc': states('sensor.marstek_venuse_3_0_9a7d_state_of_charge')|float(0)},
  {'name': 'fase_c', 'soc': states('sensor.marstek_venuse_state_of_charge')|float(0)}
] %}
{% set min_soc = states('input_number.battery_min_soc_discharge')|float(15) %}
{% set valid_batteries = batteries | selectattr('soc', '>', min_soc) | list %}
{{ (valid_batteries | sort(attribute='soc', reverse=true) | first).name if valid_batteries else 'none' }}
```

#### Praktische voorbeelden

**Scenario 1: Normale Situatie (Default 15%)**
- Fase A: 80% SOC → ✅ Beschikbaar voor ontlading
- Fase B: 45% SOC → ✅ Beschikbaar voor ontlading
- Fase C: 12% SOC → ❌ Te laag, niet selecteerbaar
- Netverbruik trigger → Volste batterij = Fase A (80%)

**Scenario 2: Alle Batterijen Leeg (Edge Case)**
- Fase A: 10% SOC → ❌ Onder 15%
- Fase B: 8% SOC → ❌ Onder 15%
- Fase C: 12% SOC → ❌ Onder 15%
- Netverbruik trigger → sensor.battery_fullest = "none"
- **Automation conditie blokkeert:** Geen switch!
- **Resultaat:** Huidige batterij blijft actief (of grid neemt over)

**Scenario 3: BMS Bescherming (5%)**
- Marstek Venus E BMS cut-off: ~5%
- Als je min_soc_discharge op 5% zet:
  - Batterij wordt ontladen tot 5%
  - BMS gaat in bescherming
  - Mogelijke foutmeldingen
- **Aanbeveling:** Houd minimaal 10-15% marge boven BMS cut-off

**Scenario 4: Batterij Levensduur (30%)**
- Li-ion batterijen: Diepste ontlading = meeste slijtage
- DoD (Depth of Discharge) beperken tot 70% (30%-100%)
- **Effect:** 2-3x langere levensduur
- **Nadeel:** 30% capaciteit ongebruikt

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Normale situatie | 15% (default) | BMS bescherming + kleine marge |
| Maximale levensduur | 30-40% | Minimaliseer dieptontlading |
| Maximale capaciteit | 10% | Gebruik bijna volledige capaciteit |
| Nood situaties (stroomuitval) | 20-30% | Houd reserve voor nood |
| Test fase | 20% | Extra veiligheid tijdens testen |

#### Gevolgen van instelling

**Te Laag (< 10%):**
- ⚠️ Risico op BMS cut-off
- ⚠️ Verhoogde batterij slijtage
- ⚠️ Mogelijke foutmeldingen
- ✅ Maximale capaciteit benutting

**Te Hoog (> 30%):**
- ⚠️ 30-40% capaciteit ongebruikt
- ⚠️ Suboptimale ROI
- ✅ Maximale levensduur
- ✅ Reserve voor noodsituaties

#### Relatie met SOC sensors
```yaml
# Check huidige SOC waardes:
sensor.marstek_venuse_d828_state_of_charge         # Fase A
sensor.marstek_venuse_3_0_9a7d_state_of_charge     # Fase B
sensor.marstek_venuse_state_of_charge              # Fase C
```

---

### 7. Max SOC Laden (`input_number.battery_max_soc_charge`)

**Default:** 90%
**Bereik:** 50% - 100%
**Eenheid:** Procent (%)

#### Wat doet dit?
Voorkomt dat een batterij geselecteerd wordt voor laden (solar excess) als de SOC boven deze waarde zit.

#### Technische werking
```yaml
# In sensor.battery_emptiest template
{% set batteries = [...] %}
{% set max_soc = states('input_number.battery_max_soc_charge')|float(90) %}
{% set valid_batteries = batteries | selectattr('soc', '<', max_soc) | list %}
{{ (valid_batteries | sort(attribute='soc') | first).name if valid_batteries else 'none' }}
```

#### Praktische voorbeelden

**Scenario 1: Normale Situatie (Default 90%)**
- Fase A: 92% SOC → ❌ Te vol, niet selecteerbaar voor laden
- Fase B: 65% SOC → ✅ Beschikbaar voor laden
- Fase C: 30% SOC → ✅ Beschikbaar voor laden
- Zonoverschot trigger → Leegste batterij = Fase C (30%)

**Scenario 2: Alle Batterijen Vol (Zonnige Dag)**
- Fase A: 95% SOC → ❌ Boven 90%
- Fase B: 91% SOC → ❌ Boven 90%
- Fase C: 88% SOC → ✅ Beschikbaar
- Zonoverschot trigger → Leegste batterij = Fase C
- **Fase C laadt verder tot 90%**
- Volgende trigger → sensor.battery_emptiest = "none"
- **Resultaat:** Geen switch meer, zonoverschot gaat naar net

**Scenario 3: Batterij Levensduur (80% Max)**
- Li-ion sweet spot: 20%-80% SOC
- Voorkom volledig laden (stress op cellen)
- **Effect:** 2-3x langere levensduur
- **Nadeel:** 20% capaciteit ongebruikt

**Scenario 4: Maximale Opslag (100%)**
- Zomer, verwacht hoog verbruik 's avonds
- Wil maximale capaciteit benutten
- Max SOC = 100%
- **Risico:** Verhoogde slijtage bij frequent vol laden

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Normale situatie | 90% (default) | Goede balans capaciteit/levensduur |
| Maximale levensduur | 80% | Li-ion sweet spot |
| Maximale capaciteit | 95-100% | Gebruik volledige capaciteit |
| Zomer (veel zon) | 85-90% | Batterijen toch vaak vol |
| Winter (weinig zon) | 95-100% | Elke kWh telt |
| Voor lang weekend weg | 100% | Maximale buffer |

#### Gevolgen van instelling

**Te Laag (< 80%):**
- ⚠️ 20-30% capaciteit ongebruikt
- ⚠️ Sneller vol, vaker teruglevering naar net
- ✅ Maximale levensduur
- ✅ Minimale stress op cellen

**Te Hoog (= 100%):**
- ⚠️ Verhoogde batterij slijtage
- ⚠️ Stress op cellen bij hoge SOC
- ✅ Maximale capaciteit benutting
- ✅ Meer energie beschikbaar

#### BMS balancing
**Belangrijk:** Batterijen hebben BMS balancing nodig!
- BMS balanceert cellen bij ~95-100% SOC
- Aanbeveling: Elke 1-2 weken volledig laden (100%)
- Of: Gebruik night charging om periodiek 100% te bereiken

**Gebalanceerde Strategie:**
- Dagelijks: Max SOC 85-90% (levensduur)
- Wekelijks: Max SOC 100% (balancing)
- Oplossing: Automation die elke zondag max_soc_charge tijdelijk op 100% zet

---

### 8. Nachtmodus Start (`input_datetime.night_mode_start_time`)

**Default:** 01:00
**Format:** HH:MM (24-uur)

#### Wat doet dit?
Tijdstip waarop het batterij rotatie systeem automatisch wordt uitgeschakeld om conflict met night charging automations te voorkomen.

#### Technische werking
```yaml
- id: marstek_disable_rotation_at_night
  alias: "Marstek: Disable Rotation at Night"
  trigger:
    - platform: time
      at: input_datetime.night_mode_start_time
  action:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.battery_rotation_enabled
```

#### Praktische voorbeelden

**Scenario 1: Nachttarief 23:00-07:00 (Pas aan naar 23:00)**
- Je nachttarief: 23:00-07:00
- Je night charging automation start: 23:00
- **Probleem met default (01:00):**
  - 23:00-01:00: Batterij rotatie ACTIEF
  - Rotatie kan batterijen switchen
  - Night charging laadt verkeerde batterij
- **Oplossing:**
  - Zet night_mode_start_time op 22:30 (vóór night charging)
  - 22:30: Rotatie UIT
  - 23:00: Night charging start (geen interferentie)

**Scenario 2: Dubbeltarief 01:00-07:00 (Default)**
- Nachttarief: 01:00-07:00
- Night charging: 01:00-07:00
- Default night_mode_start_time: 01:00 ✅
- **Resultaat:** Perfect afgestemd

**Scenario 3: Weekend (Geen Nachttarief)**
- Alleen doordeweeks goedkoop tarief
- Weekend: Geen night charging
- **Optie 1:** Laat night mode gewoon lopen (rotatie gaat uit, maar doet geen kwaad)
- **Optie 2:** Extra automation om night mode alleen ma-vr te doen:
  ```yaml
  condition:
    - condition: time
      weekday:
        - mon
        - tue
        - wed
        - thu
        - fri
  ```

**Scenario 4: Variabel Tarief (Nordpool/Tibber)**
- Goedkope uren variëren per dag
- **Oplossing:** Automation die night_mode_start_time dynamisch aanpast:
  ```yaml
  - service: input_datetime.set_datetime
    target:
      entity_id: input_datetime.night_mode_start_time
    data:
      time: "{{ states('sensor.cheapest_hour_today') }}"
  ```

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Nachttarief 01:00-07:00 | 01:00 (default) | Perfecte afstemming |
| Nachttarief 23:00-07:00 | 22:30-22:45 | Start vóór night charging |
| Nachttarief 00:00-06:00 | 23:30-23:45 | Start vóór night charging |
| Variabel tarief | Dynamisch | Automation aanpassen |
| Geen nachttarief | 01:00 (of disable night mode) | Niet relevant, maar safe |

#### Relatie met night charging

**Typische Night Charging Setup:**
```yaml
- alias: "Marstek: Night Charging (01:00-07:00)"
  trigger:
    - platform: time
      at: "01:00:00"
  condition:
    - condition: numeric_state
      entity_id: sensor.marstek_system_average_state_of_charge_2
      below: 80  # Alleen laden als onder 80%
  action:
    # Laad Fase A en B naar 5kWh, Fase C blijft leeg
    - service: shell_command.marstek_fasea_charge
      data:
        power: 2500
        duration: 21600  # 6 uur
    - service: shell_command.marstek_faseb_charge
      data:
        power: 2500
        duration: 21600
```

**Belangrijk:** Night charging moet Fase A en B laden, Fase C leeg laten (zoals je aangaf). Batterij rotatie moet UIT zijn om dit niet te verstoren.

---

### 9. Dagmodus Start (`input_datetime.day_mode_start_time`)

**Default:** 07:00
**Format:** HH:MM (24-uur)

#### Wat doet dit?
Tijdstip waarop het batterij rotatie systeem automatisch wordt ingeschakeld en Fase A wordt geactiveerd.

#### Technische werking
```yaml
- id: marstek_morning_battery_a_start
  alias: "Marstek: Morning Battery A Start"
  trigger:
    - platform: time
      at: input_datetime.day_mode_start_time
  action:
    # Enable systeem
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.battery_rotation_enabled

    # Activeer Fase A
    - service: button.press
      target:
        entity_id: button.fasea_schuin_d828_auto_mode
    - delay:
        seconds: 5
    # Deactiveer B en C
    - service: button.press
      target:
        entity_id:
          - button.faseb_plat_v3_9a7d_manual_mode
          - button.fasec_geen_deb8_manual_mode
```

#### Praktische voorbeelden

**Scenario 1: Nachttarief 01:00-07:00 (Default)**
- Night charging: 01:00-07:00
- Fase A en B geladen tot 5kWh (90%+)
- Fase C: leeg (15%)
- **07:00: Day mode start**
  - Batterij rotatie AAN
  - Fase A actief (vol, 90%)
  - Ready voor ontlading

**Scenario 2: Vroege Opstaan (05:30)**
- Je staat op om 05:30 (koffie, douche)
- Huis verbruik: 2000W
- Met day_mode_start 07:00:
  - 05:30-07:00: Rotatie UIT → Grid verbruik!
- **Oplossing:**
  - Zet day_mode_start_time op 05:00
  - 05:00: Fase A actief
  - 05:30: Ontbijt verbruik gedekt door batterij

**Scenario 3: Thuiswerken (Flexibel)**
- Sommige dagen vroeg op, andere dagen laat
- **Optie 1:** Vroegste tijd kiezen (bijv. 06:00)
- **Optie 2:** Automation + helper:
  ```yaml
  - alias: "Dynamic Day Mode Start"
    trigger:
      - platform: state
        entity_id: person.jij
        to: 'home'
        for:
          minutes: 5
    condition:
      - condition: time
        after: "05:00:00"
        before: "09:00:00"
    action:
      - service: input_boolean.turn_on
        entity_id: input_boolean.battery_rotation_enabled
  ```

**Scenario 4: Weekend Later (08:00)**
- Doordeweeks: 07:00 (default)
- Weekend: 08:00 (langer slapen)
- **Oplossing:** Conditional automation:
  ```yaml
  trigger:
    - platform: time
      at: input_datetime.day_mode_start_time_weekday
    - platform: time
      at: input_datetime.day_mode_start_time_weekend
  condition:
    - condition: template
      value_template: >
        {{
          (now().weekday() < 5 and trigger.entity_id == 'input_datetime.day_mode_start_time_weekday') or
          (now().weekday() >= 5 and trigger.entity_id == 'input_datetime.day_mode_start_time_weekend')
        }}
  ```

#### Wanneer aanpassen?

| Situatie | Aanbevolen Waarde | Reden |
|----------|-------------------|-------|
| Nachttarief eindigt 07:00 | 07:00 (default) | Perfecte afstemming |
| Vroeg opstaan | 05:00-06:00 | Dek ochtend verbruik met batterij |
| Laat opstaan | 08:00-09:00 | Pas relevant als je thuis bent |
| Thuiswerken | 06:00 | Vroeg klaar voor verbruik |
| Weekend anders | Conditional | Ma-vr: 07:00, Za-zo: 08:00 |

#### Relatie met night charging

**Typische Timeline:**
```
23:00  → Rotatie actief (intelligente switching)
01:00  → Nachtmodus: Rotatie UIT
        → Night charging automation start
        → Fase A: 30% → 90% (laden met 2500W)
        → Fase B: 40% → 90% (laden met 2500W)
        → Fase C: blijft 15% (niet laden)
07:00  → Dagmodus: Rotatie AAN
        → Fase A wordt actief (90%, vol)
        → Fase B en C naar Manual (90% en 15%)
        → Klaar voor ontlading
```

#### Gevolgen van instelling

**Te Vroeg (< 06:00):**
- ⚠️ Mogelijk conflict met night charging (als die nog bezig is)
- ⚠️ Onnodige batterij activatie als je nog slaapt
- ✅ Batterij klaar voor vroeg verbruik

**Te Laat (> 08:00):**
- ⚠️ Ochtend verbruik (koffie, douche) komt van grid
- ⚠️ Gemiste kans voor batterij ontlading
- ✅ Geen onnodige activiteit als je niet thuis bent

---

## 🎯 Aanbevolen configuraties per scenario

### Scenario 1: normale situatie (Default)
```yaml
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

**Geschikt voor:**
- Gemiddeld PV systeem (4-8kWp)
- Stabiel tot licht wisselvallig weer
- Nachttarief 01:00-07:00
- Normale dagelijkse routine

---

### Scenario 2: maximale batterij levensduur
```yaml
battery_switch_hysteresis_solar: 800W
battery_switch_hysteresis_grid: 500W
trigger_delay_solar: 5 min
trigger_delay_grid: 5 min
battery_switch_delay_minutes: 15 min
battery_min_soc_discharge: 30%
battery_max_soc_charge: 80%
night_mode_start_time: "01:00"
day_mode_start_time: "07:00"
```

**Effect:**
- Minimale switches (max 4 per uur)
- SOC range: 30-80% (Li-ion sweet spot)
- Lange delays → zeer stabiel
- 2-3x langere batterij levensduur

**Nadeel:**
- 50% capaciteit ongebruikt (30-80% range)
- Meer grid verbruik/teruglevering

---

### Scenario 3: maximale efficiency (Wisselvallig weer)
```yaml
battery_switch_hysteresis_solar: 1000W
battery_switch_hysteresis_grid: 500W
trigger_delay_solar: 5 min
trigger_delay_grid: 3 min
battery_switch_delay_minutes: 10 min
battery_min_soc_discharge: 15%
battery_max_soc_charge: 90%
night_mode_start_time: "01:00"
day_mode_start_time: "07:00"
```

**Effect:**
- Hoge drempels → voorkom switches bij korte pieken
- Lange trigger delays → negeer wolkenperiodes
- 10 min switch delay → anti-flapping

**Geschikt voor:**
- Lente/herfst (wisselvallig weer)
- Gebied met veel wolken
- Batterij slijtage minimaliseren

---

### Scenario 4: maximale capaciteit benutting (Zomer)
```yaml
battery_switch_hysteresis_solar: 300W
battery_switch_hysteresis_grid: 100W
trigger_delay_solar: 1 min
trigger_delay_grid: 2 min
battery_switch_delay_minutes: 3 min
battery_min_soc_discharge: 10%
battery_max_soc_charge: 95%
night_mode_start_time: "01:00"
day_mode_start_time: "07:00"
```

**Effect:**
- Lage drempels → elk Watt telt
- Korte delays → snelle reactie
- Grote SOC range (10-95%)
- Agressieve switching

**Geschikt voor:**
- Zomer met stabiel weer
- Maximale ROI
- Test fase

**Nadeel:**
- Meer switches
- Verhoogde slijtage

---

### Scenario 5: grote PV installatie (>10kWp)
```yaml
battery_switch_hysteresis_solar: 1500W
battery_switch_hysteresis_grid: 800W
trigger_delay_solar: 2 min
trigger_delay_grid: 3 min
battery_switch_delay_minutes: 5 min
battery_min_soc_discharge: 15%
battery_max_soc_charge: 90%
night_mode_start_time: "01:00"
day_mode_start_time: "07:00"
```

**Effect:**
- Hoge drempels passen bij grote power swings
- Normale delays
- Alleen significante events triggeren switches

---

### Scenario 6: kleine PV installatie (<3kWp)
```yaml
battery_switch_hysteresis_solar: 200W
battery_switch_hysteresis_grid: 100W
trigger_delay_solar: 2 min
trigger_delay_grid: 2 min
battery_switch_delay_minutes: 5 min
battery_min_soc_discharge: 15%
battery_max_soc_charge: 95%
night_mode_start_time: "01:00"
day_mode_start_time: "07:00"
```

**Effect:**
- Lage drempels → benut elke Watt zon
- Max SOC 95% → maximale capaciteit
- Elk beetje zonoverschot wordt opgeslagen

---

### Scenario 7: nachttarief 23:00-07:00
```yaml
# ... andere settings normaal ...
night_mode_start_time: "22:45"  # Start VOOR night charging!
day_mode_start_time: "07:00"
```

**Belangrijk:**
- Night mode start 15 min vóór night charging
- Voorkom conflict tijdens transitie

---

### Scenario 8: variabel tarief (Nordpool/Tibber)
```yaml
# ... andere settings normaal ...
# Gebruik automation om tijden dynamisch aan te passen!
```

**Extra Automation Nodig:**
```yaml
- alias: "Set Night Mode Based on Cheapest Hours"
  trigger:
    - platform: time
      at: "00:00:00"  # Elke dag om middernacht
  action:
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.night_mode_start_time
      data:
        time: "{{ state_attr('sensor.cheapest_energy_window', 'start_time') }}"
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.day_mode_start_time
      data:
        time: "{{ state_attr('sensor.cheapest_energy_window', 'end_time') }}"
```

---

## 🧪 Test procedure na aanpassing

Na het wijzigen van configuratie, volg deze test procedure:

### Stap 1: monitor gedrag (24 uur)
**Check:**
- Aantal switches per dag (Developer Tools → Logbook)
- P1 power tijdens switches (geen grid consumption spike)
- SOC trajecten van alle batterijen

**Acceptabel:**
- 3-8 switches per dag (afhankelijk van weer)
- Geen grid consumption tijdens switches
- Batterijen blijven binnen SOC limieten

**Probleem:**
- >15 switches per dag → Verhoog delays/hysteresis
- Grid consumption tijdens switches → Bug! (zou niet moeten)
- Batterijen buiten SOC limieten → Check template sensors

### Stap 2: check edge cases
**Test:**
1. Waterkoker (2000W, 3 min) → Zou NIET mogen triggeren
2. Wasmachine (400W, 90 min) → Zou WEL mogen triggeren
3. Wolk passeert (30 sec) → Zou NIET mogen triggeren
4. Alle batterijen vol → sensor.battery_emptiest = "none"
5. Alle batterijen leeg → sensor.battery_fullest = "none"

### Stap 3: fine-Tuning
**Te veel switches?**
- Verhoog trigger delays (+1 min)
- Verhoog switch delay (+5 min)
- Verhoog hysteresis (+200W)

**Te weinig switches?**
- Verlaag trigger delays (-0.5 min)
- Verlaag hysteresis (-100W)

**Batterijen te vaak vol/leeg?**
- Pas SOC limieten aan
- Check night charging configuratie

---

## 📊 Dashboard monitoring

Voeg deze sensors toe aan je dashboard voor monitoring:

```yaml
type: entities
title: "🔍 Configuration Monitor"
entities:
  # Huidige configuratie
  - entity: input_number.battery_switch_hysteresis_solar
  - entity: input_number.battery_switch_hysteresis_grid
  - entity: input_number.trigger_delay_solar
  - entity: input_number.trigger_delay_grid
  - entity: input_number.battery_switch_delay_minutes
  - entity: input_number.battery_min_soc_discharge
  - entity: input_number.battery_max_soc_charge
  - entity: input_datetime.night_mode_start_time
  - entity: input_datetime.day_mode_start_time

  # Status
  - type: section
    label: "Status"
  - entity: input_boolean.battery_rotation_enabled
  - entity: input_text.active_battery_fase
  - entity: input_datetime.last_battery_switch

  # Selectie
  - type: section
    label: "Automatische Selectie"
  - entity: sensor.battery_emptiest
  - entity: sensor.battery_fullest

  # Current SOC
  - type: section
    label: "Current SOC"
  - entity: sensor.marstek_venuse_d828_state_of_charge
    name: "Fase A (schuin)"
  - entity: sensor.marstek_venuse_3_0_9a7d_state_of_charge
    name: "Fase B (plat)"
  - entity: sensor.marstek_venuse_state_of_charge
    name: "Fase C (geen)"
```

---

## 🔍 Troubleshooting configuration issues

### Issue 1: "Te veel switches"
**Symptoom:** 20+ switches per dag

**Diagnose:**
1. Check automation traces: Settings → Automations → [Select] → Traces
2. Kijk naar trigger tijden → Zijn er snelle opeenvolgende triggers?

**Oplossing:**
- Verhoog `trigger_delay_solar` en `trigger_delay_grid` naar 5 min
- Verhoog `battery_switch_delay_minutes` naar 10-15 min
- Verhoog hysteresis drempels (+500W)

### Issue 2: "Geen switches, systeem reageert niet"
**Symptoom:** Batterij blijft hele dag op Fase A

**Diagnose:**
1. Check `input_boolean.battery_rotation_enabled` → Moet ON zijn
2. Check P1 power sensor → Geeft deze valide data?
3. Check automation conditions in traces

**Oplossing:**
- Verlaag hysteresis drempels (te hoog ingesteld)
- Verlaag trigger delays (te lang ingesteld)
- Check sensor.p1_meter_power beschikbaarheid

### Issue 3: "Batterij wordt niet geselecteerd"
**Symptoom:** sensor.battery_emptiest/fullest = "none"

**Diagnose:**
1. Check SOC van alle batterijen
2. Zijn alle batterijen buiten SOC limieten?

**Oplossing:**
- Pas `battery_min_soc_discharge` aan (te hoog?)
- Pas `battery_max_soc_charge` aan (te laag?)
- Check of batterij sensors valide data geven

### Issue 4: "Night mode werkt niet"
**Symptoom:** Rotatie blijft actief tijdens nacht

**Diagnose:**
1. Check automation "Marstek: Disable Rotation at Night" → Is deze enabled?
2. Check traces → Triggert deze om 01:00?

**Oplossing:**
- Check `input_datetime.night_mode_start_time` format (moet HH:MM zijn)
- Reload automations: Developer Tools → YAML → Reload Automations

---

## 📚 Gerelateerde documentatie

- **[INSTALLATION.md](INSTALLATION.md)** - Installatie instructies
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Veelvoorkomende problemen
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technische werking
- **[README.md](../README.md)** - Project overzicht

---

**Vragen? Check de [Troubleshooting Guide](TROUBLESHOOTING.md) of open een [issue](https://github.com/jouw-username/marstek-battery-rotation/issues)!**
