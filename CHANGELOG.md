# Changelog

Alle belangrijke wijzigingen in dit project worden gedocumenteerd in dit bestand.

Het formaat is gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/1.0.0/),
en dit project volgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2024-11-20

### Toegevoegd

#### Core functionaliteit
- ✨ Intelligente batterij rotatie systeem voor 3 Marstek Venus E batterijen
- ✨ Automatische batterij selectie op basis van P1 meter metingen
- ✨ Template sensors voor leegste en volste batterij detectie
- ✨ 3 automations voor dagelijkse rotatie, zonoverschot en netverbruik
- ✨ 5 scripts voor manuele batterij controle

#### Configuratie via UI
- ✨ Configureerbare hysteresis drempels (zon/net) via input_number helpers
- ✨ Configureerbare trigger delays via input_number helpers (0.5-10 min)
- ✨ Configureerbare nacht/dag tijden via input_datetime helpers
- ✨ Configureerbare SOC limieten (min ontladen, max laden)
- ✨ Configureerbare switch delay (minimale tijd tussen switches)
- ✨ Emergency stop toggle (battery_rotation_enabled)

#### Night/Day mode
- ✨ Automatische nachtmodus (01:00-07:00 default, configureerbaar)
- ✨ Automatische dagmodus (07:00 start, Fase A actief)
- ✨ Integratie met bestaande night charging automations

#### Safety features
- ✨ Anti-flapping bescherming (hysteresis + delays)
- ✨ SOC limieten (15% min ontladen, 90% max laden)
- ✨ Minimum 5 minuten tussen switches
- ✨ Configureerbare trigger delays om korte pieken te negeren
- ✨ Notifications bij elke switch

#### Dashboard
- ✨ Real-time SOC gauges voor elke batterij
- ✨ Automatische selectie info (leegste/volste batterij)
- ✨ Manuele batterij activatie knoppen (Fase A/B/C)
- ✨ Emergency stop button
- ✨ Configureerbare instellingen via UI
- ✨ Status overzicht met actieve batterij en P1 power
- ✨ Laatste switch tijd weergave

#### Documentatie
- ✨ README.md met features, quick start, configuratie overzicht
- ✨ INSTALLATION.md met stap-voor-stap instructies (packages + split config)
- ✨ CONFIGURATION.md met uitgebreide parameter uitleg
- ✨ TROUBLESHOOTING.md met veelvoorkomende problemen
- ✨ ARCHITECTURE.md met technische werking
- ✨ Example configuratie files (configuration.yaml, automations, shell_commands)

#### Testing
- ✨ API test scripts (apiTest.py, apiTest_advanced.py, etc.)
- ✨ Battery test scripts (test_all_batteries.py, test_battery.py)
- ✨ Entity verification script (verify-entities.py)

### Gewijzigd

#### Kritische fixes
- 🔧 **Switch volgorde omgedraaid** - Nieuwe batterij wordt nu EERST geactiveerd voordat oude worden gedeactiveerd
  - Elimineert gap tijdens switches (voorheen 30+ seconden netverbruik)
  - Nieuwe volgorde: Activeer nieuwe → Wacht 5 sec → Deactiveer oude
- 🔧 **Trigger delay workaround** - Home Assistant `for:` parameter niet compatibel met templates
  - Oplossing: `last_changed` attribute check in conditions
  - Maakt configureerbare trigger delays mogelijk
- 🔧 **Dashboard datetime picker fix** - Input datetime te breed voor card
  - Verplaatst naar Settings sectie
  - Relatieve tijd in header toegevoegd

#### Verbeteringen
- 🔧 Button entity names aangepast naar custom namen (fasea_schuin, faseb_plat, fasec_geen)
- 🔧 Package filename fix (underscores i.p.v. dashes voor HA slug compatibility)
- 🔧 Stabilisatie delay verhoogd van 2 naar 5 seconden
- 🔧 Default trigger delays ingesteld op 2 minuten
- 🔧 Folder structuur georganiseerd voor GitHub

### Technische details

#### Entity names
- Fase A (schuin - d828): `button.fasea_schuin_d828_*`
- Fase B (plat - 9a7d): `button.faseb_plat_v3_9a7d_*`
- Fase C (geen - deb8): `button.fasec_geen_deb8_*`

#### Default waarden
- Hysteresis Zon: 500W
- Hysteresis Net: 200W
- Trigger Delay Zon: 2 min
- Trigger Delay Net: 2 min
- Switch Delay: 5 min
- Min SOC Ontladen: 15%
- Max SOC Laden: 90%
- Nachtmodus Start: 01:00
- Dagmodus Start: 07:00

#### Folder structuur
```
marstekAPI/
├── config/
│   ├── packages/
│   │   └── battery-rotation.yaml (25KB main config)
│   └── examples/
│       ├── configuration.yaml
│       ├── automations_examples.yaml
│       └── shell_commands.yaml
├── dashboards/
│   └── battery-rotation-card.yaml
├── docs/
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── TROUBLESHOOTING.md
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── tests/
│   ├── api/
│   ├── battery/
│   └── verify-entities.py
├── .archive/ (oude versies)
├── README.md
├── CHANGELOG.md
└── LICENSE
```

### Bekende issues
- Geen bekende issues in v1.0.0

### Breaking changes
- Geen - dit is de eerste release

### Upgrade instructies
- N/A - eerste release

---

## [Unreleased]

### Geplande features (zie ROADMAP.md)
- MQTT Bridge voor multi-batterij monitoring
- Dynamic power allocation
- Weersvoorspelling integratie
- Energy price optimization
- Web UI voor configuratie

---

## Versie geschiedenis

**[1.0.0]** - 2024-11-20
- Eerste stabiele release met volledige batterij rotatie functionaliteit
- Alle features getest en werkend
- Volledige documentatie beschikbaar
