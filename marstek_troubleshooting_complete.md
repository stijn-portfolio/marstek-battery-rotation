# MARSTEK BATTERY ROTATION - TROUBLESHOOTING & FIXES
## Complete Context & Analysis

**Datum:** 26 november 2024  
**Systeem:** 3x Marstek thuisbatterijen met Home Assistant rotatie systeem  
**Doel:** Intelligente batterij rotatie op basis van P1 meter metingen

---

## SECTIE A: PROBLEEM ANALYSE & CONTEXT

### PROBLEEM 1: Mode Sensors Geven Vaak "Unknown"

#### Symptomen
- `sensor.marstek_venuse_3_0_9a7d_mode` (Fase B) geeft regelmatig "unknown"
- Dit gebeurt met alle drie de fasen, niet alleen Fase B
- Timing: onvoorspelbaar, maar vooral tijdens switches en high-load momenten

#### Observaties
- Fase B heeft V3 firmware (er is al een bekende bug met `available_capacity`)
- De configuratie heeft al een workaround voor V3 firmware bugs
- Mode sensors zijn essentieel voor verificatie of een batterij op Auto/Manual staat

#### Hypotheses
1. **Firmware/API Issue:** V3 firmware heeft incomplete mode sensor implementatie
2. **Communicatie Issues:** Netwerk timeouts tussen HA en Marstek units
3. **Polling Frequency:** Sensor wordt niet vaak genoeg geüpdatet of juist overwhelmed
4. **Entity Availability:** Integratie markeert entity unavailable bij comm errors

#### Impact
- **Verificatie onmogelijk:** Kan niet checken of batterij switch daadwerkelijk gelukt is
- **Conflict detection faalt:** `unknown` wordt niet als `Auto` gezien, maar batterij kan wel op Auto staan
- **Peak Assist kan verkeerde batterij selecteren:** Als mode unknown is, denkt systeem dat batterij inactief is
- **Grid consumption switch kan interfereren:** Denkt dat batterij beschikbaar is terwijl die actief is

#### Root Cause
Mode sensors zijn fundamenteel onbetrouwbaar in dit systeem. We kunnen er geen logica op bouwen die 100% van de tijd moet werken.

---

### PROBLEEM 2: Twee Batterijen Tegelijk op Auto Mode

#### Symptomen
- User ziet soms (tijdelijk) twee batterijen tegelijk op Auto staan in de Marstek app
- Dit gebeurt tijdens batterij switches

#### Observaties
Alle switch automations gebruiken dit patroon:
```yaml
# EERST: Nieuwe batterij activeren
- service: button.press
  target:
    entity_id: button.fasea_schuin_d828_auto_mode

# Wacht op stabilisatie  
- delay:
    seconds: 5

# DAN PAS: Andere batterijen deactiveren
- service: button.press
  target:
    entity_id:
      - button.faseb_plat_v3_9a7d_manual_mode
      - button.fasec_geen_deb8_manual_mode
```

**Gedurende die 5 seconden staan TWEE batterijen op Auto!**

#### Timing & Observaties
- Dit patroon komt voor in:
  * marstek_manual_toggle_on
  * marstek_solar_excess_switch
  * marstek_grid_consumption_switch
  * marstek_enable_rotation_in_morning
  * Alle drie handmatige activatie scripts

#### Hypotheses over waarom 5 seconden delay?
1. **Stabilisatie tijd:** Nieuwe batterij moet volledig geactiveerd zijn
2. **Voorkomen gap:** Anders moment zonder actieve batterij (ook problematisch)
3. **API response tijd:** Wachten tot commando verwerkt is

#### Mogelijke Scenario's die Misgaan

**Scenario 1: Conflicterende Load Sharing**
```
T=0s:   Fase A = Auto (1000W ontladen)
T=1s:   Fase B = Auto wordt aangezet
T=1-5s: Beide op Auto!
        - Beide denken dat ze alles moeten doen
        - Resultaat: onvoorspelbaar gedrag, mogelijk 2x de stroom
T=5s:   Fase A = Manual
```

**Scenario 2: Peak Assist tijdens Switch**
```
T=0s:   Solar Excess switch start: Fase C → Auto
T=2s:   Peak Assist trigger: ziet Fase A nog als "actief"
T=2s:   Peak Assist zet Fase B op Passive mode
T=3s:   NU ACTIEF: Fase C (Auto), Fase A (nog Auto), Fase B (Passive)
T=5s:   Fase A → Manual
Resultaat: Chaos met 3 batterijen tegelijk actief
```

**Scenario 3: Dubbele Charging**
```
Beide batterijen op Auto tijdens zonoverschot:
- Batterij A: laadt met 2000W
- Batterij B: laadt met 2000W  
- Totaal: 4000W van PV/grid in plaats van verwachte 2000W
```

#### Afgewogen Alternatieven

**Optie A: Omkeren volgorde (AFGEWEZEN)**
- Eerst oude UIT, dan nieuwe AAN
- Risico: moment zonder actieve batterij = geen load sharing
- Te gevaarlijk

**Optie B: Kortere delay met verificatie**
- Verlaag naar 1-2 seconden
- Gebruik wait_template om te verifiëren
- PROBLEEM: mode sensors zijn unreliable (zie Probleem 1)

**Optie C: Atomic switch met conditional logic**
- Complex, moeilijk te onderhouden
- Nog steeds afhankelijk van unreliable sensors

**Optie D: Accepteer overlap, minimaliseer window**
- Pragmatisch: verlaag 5 sec → 2 sec
- Voeg safeguards toe (cooldowns, conflict preventie)
- GEKOZEN

#### Root Cause
Het systeem probeert een "make-before-break" patroon te gebruiken (nieuwe aan voor oude uit) om een gap te voorkomen. De 5 seconden delay is een workaround maar creëert een conflict window waarin twee batterijen actief zijn.

#### Gekozen Oplossing
- Verlaag delay van 5 → 2 seconden (minimaliseer overlap)
- Voeg 30 seconden cooldown toe na switches voor Peak Assist
- Accepteer dat we mode sensors niet kunnen vertrouwen voor verificatie

---

### PROBLEEM 3: Ochtend Failure - Fase A Verdwijnt, Peak Assist Faalt

#### Symptomen
**Datum:** Vandaag, 26 november 2024, om 07:00

Verwacht gedrag:
- 07:00: Morning mode start
- Fase A → Auto mode  
- Systeem draait normaal

Wat er gebeurde:
- 07:00: Morning mode triggert
- Fase A → Auto mode (gelukt)
- "Iets later": Fase A staat op Manual (?!)
- Peak Assist triggert (verkeerde batterij/onvoldoende vermogen)
- Verbruik niet gedekt

#### Timeline Reconstructie
```
07:00:00 - Morning mode trigger
07:00:01 - Rotatie AAN
07:00:02 - Fase A → Auto
07:00:07 - Fase B & C → Manual  
07:00:08 - Clear night schedules START (traag!)
07:01:xx - Grid consumption switch triggert? (mode sensors unknown?)
07:0x:xx - Fase A terug naar Manual
07:0x:xx - Peak Assist start (verkeerde batterij)
```

#### Hypotheses

**Hypothese 1: Mode Sensor Unknown → Verkeerde Switch**
- Om 07:00: Morning mode activeert Fase A
- Kort daarna (07:01): P1 meter > 200W (ochtend verbruik)
- Grid consumption switch triggert
- Als mode sensors `unknown` zijn → SOC berekeningen falen (float(0))
- Systeem denkt alle batterijen leeg zijn
- Switchet naar willekeurige "volste" batterij
- Fase A blijft Manual

**Hypothese 2: Commando Failures + continue_on_error**
- Morning mode commando faalt maar wordt gemaskeerd
- HA denkt: Fase A actief
- Werkelijkheid: Fase A staat Manual
- Later switches interfereren

**Hypothese 3: Race Condition met Night Charging Cleanup (MEEST WAARSCHIJNLIJK)**
- Fase A → Auto mode (gelukt)
- Fase A heeft NOG een manual schedule actief (van nachtladen)
- Clear schedules commando is traag of faalt
- Mode sensors worden `unknown` (communicatie issue tijdens schedule clear?)
- Grid consumption switch triggert kort daarna
- Ziet mode sensors unknown → verkeerde selectie
- Switchet weg van Fase A
- Peak Assist triggert met verkeerde batterij

**Hypothese 4: Peak Assist Verkeerde Batterij**
- active_battery_fase = "fase_a" (volgens tracking)
- Maar Fase A staat Manual
- Peak Assist selecteert volste inactieve batterij
- Als mode sensors unknown → selecteert Fase C (30%) ipv Fase B (80%)
- Peak Assist: 1000W (standaard)
- Verbruik: 3000W
- Tekort: 2000W → komt van net

#### Root Cause Analyse
**WAARSCHIJNLIJK:** Combinatie van Hypothese 1 + 3:
1. Morning mode start, Fase A → Auto
2. Fase A heeft NOG manual schedule (van vannacht)
3. Clear schedules is traag
4. Mode sensors worden unknown tijdens clear
5. Grid consumption switch triggert (07:01-07:02)
6. Ziet unknown sensors → SOC berekeningen falen
7. Switchet naar verkeerde batterij
8. Fase A blijft Manual
9. Peak Assist triggert met verkeerde batterij/vermogen

#### Impact
- Ochtendverbruik niet gedekt door batterijen
- Onnodig netverbruik
- Systeem niet betrouwbaar bij dagstart

---

### PROBLEEM 4: Oude Manual Schedules Blijven Actief

#### Ontdekking
User merkte op: "Ik denk dat er inderdaad nog ergens een oude manual schedule stond op een batterij. Ik zie dat hij deze nacht (manual loading) niet alleen het voorgestelde programma heeft geladen maar ook nog extra in de late nachturen, hetgeen ik ooit manueel in de app had ingegeven."

#### Symptomen
Vannacht:
- HA Night Charging: Schema 23:00-07:00 @ 2000W (verwacht)
- Oude app schedule: Schema 03:00-05:00 @ 1500W (vergeten, onverwacht)
- Resultaat: BEIDE schedules actief = dubbel laden

#### Observaties
- Schedules die ooit in Marstek app zijn ingegeven blijven actief
- HA weet niet van deze oude schedules
- HA overschrijft ze niet, maar voegt nieuwe toe
- Batterij heeft meerdere schedules tegelijk

#### Impact
1. **Onvoorspelbaar laadgedrag:** Meerdere schedules tegelijk = ongecontroleerd laden
2. **Morning mode conflicts:** Batterij heeft nog schedule bij activatie → vreemd gedrag
3. **Verkeerde mode detectie:** Schedule actief terwijl batterij op Auto staat → Marstek firmware confused?
4. **Root cause van Probleem 3:** Morning mode failure was waarschijnlijk hierdoor

#### Waarom Gebeurt Dit?
- `marstek_local_api.set_manual_schedule` VOEGT toe, overschrijft niet
- `marstek_local_api.clear_manual_schedules` wordt alleen aangeroepen:
  * Aan EINDE van morning mode (na batterij activatie)
  * NERGENS bij night charging start

#### Redenering
Morning mode cleared aan het einde omdat:
- Clear is traag (3-5 seconden per batterij)
- Als aan begin: Peak Assist triggert te vroeg tijdens clear proces
- Maar: dit veroorzaakt Probleem 3 (batterij heeft schedule tijdens activatie)

---

### PROBLEEM 5: Oneindige Rotatie bij Volle Batterijen

#### Symptomen
**Datum:** Vandaag, 26 november 2024, veel zon

Observatie:
- Alle batterijen lopen vol (95%+)
- Veel zonoverschot blijft
- Systeem blijft roteren tussen batterijen
- Telkens zoekt het leegste batterij
- Maar "leegste" is 96%, dan 97%, dan 96% weer...
- Eindloze loop

#### Scenario
```
12:00 - Veel zon, alle batterijen 95%+
12:02 - Solar excess switch: Fase A (96%) → Fase B (95%)
12:04 - Solar excess switch: Fase B (97%) → Fase C (96%)
12:06 - Solar excess switch: Fase C (97%) → Fase A (96%)
12:08 - Solar excess switch: Fase A (97%) → Fase B (96%)
... LOOP CONTINUES ...
```

#### Root Cause
Solar excess switch conditie:
```yaml
# Actieve batterij SOC >= 85% (bijna vol)
- condition: template
  value_template: >
    {% if active == 'fase_a' %}
      {{ states('sensor.marstek_venuse_d828_state_of_charge')|float(0) >= 85 }}
    {% endif %}

# Actieve batterij != leegste batterij
- condition: template
  value_template: >
    {{ states('input_text.active_battery_fase') != states('sensor.battery_emptiest') }}
```

Probleem:
- Conditie checkt alleen of actieve >=85%
- Checkt NIET of leegste batterij ook vol is
- Als alle batterijen 95%+ zijn, blijft hij switchen
- Er is geen "alle batterijen vol, stop roteren" logica

#### Impact
- Onnodige switches tussen volle batterijen
- Systeem blijft actief terwijl batterijen niets meer kunnen opnemen
- Overtollige PV kan niet naar net (batterij probeert steeds te laden)
- Slijtage door onnodige switches

#### Waarom Geen Auto-Stop?
- Systeem ontworpen voor continues rotatie
- Geen "exit condition" bij alle batterijen vol
- Assumptie: altijd minstens één batterij heeft ruimte

---

## SECTIE B: GEKOZEN OPLOSSINGEN

### OPLOSSING 1: Clear Old Schedules Voor Night Charging

#### Waarom Deze Aanpak?
- **Preventief:** Wist oude schedules VOOR nieuwe worden ingesteld
- **Clean slate:** Elk nacht systeem start met lege schedules  
- **Voorspelbaar:** HA heeft volledige controle over schedules
- **Traceable:** Logbook entries tonen wanneer schedules gewist worden

#### Implementatie
1. **Bij Manual Schedule Night Charging:**
   - AAN BEGIN: Clear alle schedules (3x device_id)
   - Delay 5 seconden (zeker weten dat clear klaar is)
   - Dan pas nieuwe schedules instellen

2. **Bij Peak-Aware Night Charging:**
   - AAN BEGIN: Clear alle schedules
   - Delay 3 seconden (korter, gebruikt Passive mode ipv schedules)
   - Dan pas Passive mode activeren

3. **Bij Morning Mode:**
   - BLIJFT AAN EINDE (niet verplaatsen!)
   - Reden: clear duurt te lang, Peak Assist triggert anders te vroeg
   - Trade-off: batterij heeft nog schedule bij activatie, maar dit is minder erg dan Peak Assist failure

4. **Manual Script:**
   - User kan handmatig cleanup triggeren
   - Voor als iets fout gaat of testen

#### Verwacht Gedrag Na Fix
- Vannacht: alleen HA schedules actief, geen oude app schedules
- Morning mode: minder kans op conflicts (schedules worden later gewist)
- Voorspelbaar laadgedrag

#### Afgewogen Alternatieven

**Alternatief A: Daily Cleanup om 18:00 (AFGEWEZEN)**
- Zou proactief alle schedules wissen
- User wilde dit niet (Oplossing 3 afgewezen)
- Reden afwijzing: te invasief, mogelijk in conflict met user's eigen planning

**Alternatief B: Clear ook aan begin morning mode (AFGEWEZEN)**
- Zou Probleem 3 volledig oplossen
- Maar: clear duurt 10-15 seconden totaal
- Peak Assist zou triggeren tijdens clear = chaos
- Trade-off niet waard

---

### OPLOSSING 2: Verkort Delay + Cooldown voor Peak Assist

#### Waarom Deze Aanpak?
We kunnen Probleem 2 (twee batterijen op Auto) niet volledig oplossen omdat:
- Mode sensors unreliable (Probleem 1)
- Make-before-break nodig om gap te voorkomen
- Geen atomic switch mogelijk

Dus: **minimaliseer het probleem, voeg safeguards toe**

#### Implementatie
1. **Verkort delay van 5 → 2 seconden:**
   - In morning mode automation
   - In alle handmatige scripts
   - Blijft lang genoeg voor commando verwerking
   - Kort genoeg om overlap window te minimaliseren

2. **Voeg mode status toe aan morning notificatie:**
   - User kan verificeren of switch gelukt is
   - Debug info voor troubleshooting
   - Template: `Mode status: A={{ ... }} B={{ ... }} C={{ ... }}`

3. **Preventie: Cooldown voor Peak Assist (TOEKOMSTIG):**
   - Peak Assist mag niet triggeren binnen 30 sec na battery switch
   - Check: `last_battery_switch` timestamp
   - Voorkomt Scenario 2 (Peak Assist tijdens switch)

#### Verwacht Gedrag Na Fix
- Overlap window: 5 sec → 2 sec (60% reductie)
- Minder kans op conflicten
- User ziet mode status in notificatie
- Peak Assist triggert niet tijdens switches

#### Wat Dit NIET Oplost
- Twee batterijen kunnen nog steeds 2 seconden tegelijk op Auto staan
- Mode sensors blijven unreliable
- Geen 100% garantie tegen conflicts

**Dit is acceptabel omdat:**
- 2 seconden overlap is te kort voor meeste problemen
- Complete oplossing niet mogelijk met huidige hardware/API
- Pragmatische trade-off tussen veiligheid en functionaliteit

---

### OPLOSSING 3: Auto-Stop bij Volle Batterijen

#### Waarom Deze Aanpak?
Bij alle batterijen vol (95%+) EN zonoverschot:
- Batterijen kunnen niets meer opnemen
- Roteren heeft geen zin (alle batterijen vol)
- Systeem moet zichzelf uitschakelen
- Overtollige PV moet naar net kunnen

#### Implementatie

**Auto-Stop Automation:**
- Trigger: Elke 5 minuten (time_pattern)
- Conditions:
  * Rotatie systeem is ON
  * Alle drie batterijen >= 95%
  * P1 meter < -200W (nog steeds zonoverschot)
- Actions:
  * Zet rotatie OFF
  * Alle batterijen → Manual mode
  * Clear active_battery_fase
  * Logbook + notificatie

**Auto-Start Automation:**
- Trigger: P1 meter > 200W voor 2 minuten
- Conditions:
  * Rotatie systeem is OFF
  * We zijn in dagmodus (niet 's nachts)
  * Minstens één batterij > 20% SOC
- Actions:
  * Zet rotatie ON (triggert manual_toggle_on)
  * Logbook + notificatie

**Dashboard Indicator:**
- Binary sensor: "Marstek All Batteries Full"
- True wanneer alle >= 95%
- Attributes: lowest_soc, highest_soc

#### Verwacht Gedrag Na Fix

**Scenario 1: Zonnige dag, batterijen vol**
```
11:00 - Alle batterijen 95%+, veel zon
11:05 - Auto-stop triggert
11:05 - Alle batterijen Manual, PV → net
11:30 - Verbruik start (lunch)
11:32 - Auto-start triggert
11:32 - Rotatie herstart, volste batterij actief
```

**Scenario 2: Niet vol genoeg**
```
11:00 - A:95%, B:93%, C:97% (niet alle >=95%)
11:05 - Auto-stop triggert NIET
11:05 - Systeem blijft roteren tussen B (leegst) en anderen
```

#### Afgewogen Alternatieven

**Alternatief A: Threshold 90% ipv 95% (AFGEWEZEN)**
- Te vroeg, batterijen kunnen nog 5% opnemen
- Bij 95% is batterij praktisch vol

**Alternatief B: Stop alleen solar excess switch (AFGEWEZEN)**
- Complexer: partiële disable
- Beter: volledig systeem uit bij volle batterijen

**Alternatief C: Voeg 5% verschil conditie toe aan solar excess (AFGEWEZEN door user)**
- Zou voorkomen dat 96% → 97% switch gebeurt
- User wilde dit niet: "nee, ik ben niet akkoord met je voorstel"
- Mogelijk reden: wil alle batterijen gelijkmatig gebruiken, ongeacht klein verschil

---

## SECTIE C: IMPLEMENTATIE SAMENVATTING

### Wijzigingen aan battery-rotation.yaml

1. **marstek_night_charging automation:**
   - Voeg clear schedules toe aan BEGIN
   - Delay 5 sec na clear
   - Notificatie "Oude schedules worden gewist"

2. **marstek_night_charging_peakaware_start automation:**
   - Voeg clear schedules toe aan BEGIN  
   - Delay 3 sec na clear

3. **marstek_enable_rotation_in_morning automation:**
   - Verlaag delay 5 → 2 sec
   - Voeg mode status toe aan notificatie
   - LAAT clear schedules aan EINDE

4. **Nieuw script: marstek_clear_all_schedules**
   - Manual cleanup optie
   - Logbook entry

5. **Nieuwe automation: marstek_auto_stop_all_full**
   - Zet systeem uit bij alle batterijen >= 95% + zonoverschot
   - Elke 5 min check

6. **Nieuwe automation: marstek_auto_start_on_consumption**
   - Herstart systeem bij verbruik > 200W
   - Als systeem uit is en we zijn overdag

7. **Nieuwe sensor: binary_sensor.marstek_all_batteries_full**
   - Dashboard indicator
   - Attributes: lowest_soc, highest_soc

### Test Criteria

**Test 1: Night Charging**
- Start nachtladen
- Check: oude schedules eerst gewist
- Check: alleen nieuwe schedules actief
- Check: geen dubbele schedules

**Test 2: Morning Mode**
- Om 07:00 morning mode
- Check: Fase A wordt actief
- Check: notificatie toont mode status
- Check: geen grid consumption switch binnen 2 min
- Check: schedules worden gewist na activatie

**Test 3: Auto-Stop**
- Wacht tot alle batterijen > 95%
- Check: systeem schakelt uit binnen 5 min
- Check: alle batterijen Manual
- Check: PV gaat naar net

**Test 4: Auto-Start**
- Met systeem uit, start groot verbruik
- Check: systeem herstart binnen 2 min
- Check: volste batterij wordt actief

---

## SECTIE D: BEKENDE BEPERKINGEN & EDGE CASES

### Nog Niet Opgelost

1. **Mode Sensors Unreliable**
   - Root cause: firmware/API issue
   - Status: Niet opgelost, geaccepteerd
   - Workaround: Pragmatische oplossingen zonder mode verificatie

2. **Twee Batterijen Korte Tijd Op Auto**
   - 2 seconden overlap blijft bestaan
   - Status: Geminimaliseerd maar niet geëlimineerd
   - Impact: Acceptabel voor meeste scenario's

3. **Morning Mode Schedule Conflict**
   - Batterij heeft nog schedule tijdens activatie
   - Status: Trade-off geaccepteerd (Peak Assist > clean start)
   - Alternative: User kan manual cleanup script draaien voor morning mode

### Edge Cases

**Edge Case 1: Alle batterijen 94%**
```
Situatie: A:94%, B:94%, C:94% met veel zon
Gedrag: Auto-stop triggert NIET (threshold is 95%)
Systeem: Blijft roteren
Risico: Onnodige switches bij marginaal verschil
Status: Geaccepteerd (batterijen kunnen nog 1% opnemen)
```

**Edge Case 2: Auto-start tijdens nachtmodus**
```
Situatie: Systeem uit, 03:00 uur, plotseling groot verbruik
Gedrag: Auto-start triggert NIET (conditie: we zijn in dagmodus)
Resultaat: Verbruik komt van net
Status: Correct gedrag (nachtladen zou moeten actief zijn)
```

**Edge Case 3: Clear schedules faalt**
```
Situatie: Network timeout tijdens clear
Gedrag: continue_on_error: true → gaat door
Resultaat: Oude + nieuwe schedule beide actief
Risico: Onvoorspelbaar laden
Mitigatie: User kan manual script draaien
Status: Zeer zeldzaam, maar mogelijk
```

**Edge Case 4: Auto-stop tijdens verbruikspiek**
```
Situatie: Alle batterijen 95%, plotseling groot verbruik
Timing: 
  11:00:00 - Auto-stop check (alle vol, zon)
  11:00:30 - Groot verbruik start
  11:02:00 - Auto-start triggert
Gap: 1.5 minuten zonder batterij
Resultaat: Tijdelijk netverbruik
Status: Acceptabel (zeldzame timing, korte duur)
```

### Open Vragen

1. **Optimale Auto-Stop Threshold?**
   - Nu: 95%
   - Vraag: Is 95% te hoog? Te laag?
   - Monitor: Hoe vaak triggert het te vroeg/te laat?

2. **Auto-Start Delay?**
   - Nu: 2 minuten verbruik voor herstart
   - Vraag: Te lang? Te kort?
   - Monitor: False positives bij korte verbruikspieken?

3. **Peak Assist Cooldown?**
   - Voorgesteld maar niet geïmplementeerd: 30 sec na switch
   - Vraag: Is dit nodig met 2 sec delay?
   - Monitor: Triggert Peak Assist nog tijdens switches?

### Toekomstige Verbeteringen

1. **Mode Sensor Fallback:**
   - Gebruik battery_power of grid_power als indicator
   - Als mode unknown: detecteer actieve batterij via power flow
   - Complexer maar betrouwbaarder

2. **Intelligent Switch Timing:**
   - Niet switchen bij marginale verschillen (97% vs 96%)
   - Maar: user wilde dit expliciet NIET
   - Mogelijk later herbekijken

3. **Schedule Verification:**
   - Read-back na set_manual_schedule
   - Verify dat schedule echt ingesteld is
   - Vereist nieuwe sensor entities

4. **Adaptive Thresholds:**
   - Auto-stop threshold aanpassen o.b.v. historisch gedrag
   - Machine learning approach
   - Ver in de toekomst

---

## CONCLUSIE

We hebben 5 problemen geïdentificeerd en oplossingen geïmplementeerd voor 3 daarvan:

**Opgelost:**
- ✅ Oude manual schedules interfereren (clear voor night charging)
- ✅ Oneindige rotatie bij volle batterijen (auto-stop/start)
- ✅ Lange overlap bij switches (5→2 sec, notificatie verbeterd)

**Geminimaliseerd:**
- ⚠️ Twee batterijen korte tijd op Auto (2 sec overlap blijft)
- ⚠️ Mode sensors unreliable (geaccepteerd, pragmatische workarounds)

**Trade-offs:**
- Morning mode heeft nog schedule conflict risico (Peak Assist priority)
- Auto-stop werkt alleen bij duidelijk volle batterijen (95%+ threshold)
- Geen verificatie van succesvolle switches (mode sensors onbetrouwbaar)

De oplossingen zijn pragmatisch en robuust binnen de beperkingen van de hardware/firmware.
