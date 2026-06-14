# Multi-huvud: delad encoder/motor + fusion över hela brädan

## Riggens fysik (LÅST logik)
Vid flera Jetson-läshuvuden finns **EN** encoder + **EN** motordrivare (RoboClaw) för
hela transporten — de är **INTE** separata per huvud. Brädan matas förbi alla huvuden
av samma band/motor, och samma encoder ger den gemensamma matningskoordinaten.

```
   matning →   [ Huvud A ]   [ Huvud B ]   [ Huvud C ]      en bräda, ett band
                cameras       cameras       cameras
                   │             │             │
                   └──── delad encoder-position (samma koordinat) ────┘
                                 │
                          EN RoboClaw (motor + encoder) på LEAD-noden
```

## Roller (data/head.json per Jetson)
| Fält | Roll |
|---|---|
| `has_conveyor: true` | **LEAD** — äger RoboClaw (motor + encoder). Exakt EN nod. |
| `has_conveyor: false` | **SENSOR-huvud** — bygger ingen egen RoboClaw; får matnings-positionen från lead. |
| `label`, `start_mm`, `end_mm` | vilken **sektion** av brädan huvudet täcker (för fusion). |

I koden: `RealScanner` läser `head.json` → lead bygger `RoboClawConveyor`, sensor-huvud
bygger `SharedConveyorClient` (set_speed = no-op, position matas från lead). Master-GUI:t
visar **LEAD**-badge på conveyor-ägaren och positionssektion per nod.

## Demo-riggen
Ett enda huvud (`has_conveyor: true`) över hela 500 mm-brädan → samma kod, ingen
stitch behövs (en sektion = hela brädan). Multi-huvud är en ren utbyggnad av samma logik.

## Synk + fusion över hela brädan
1. **Radklocka:** linjekamerans rader triggas av encodern (hårdvara, Line0) → alla
   huvuden samplar mot **samma** matningsposition. Profilkamerorna förvärvar mot samma
   koordinat.
2. **Position-distribution:** lead-noden känner absolut matningsposition (RoboClaw-
   encoder). Sensor-huvuden får den via `SharedConveyorClient.set_feed_position()`
   (matas av lead-sync — encoderns HW-trigg + lead-positionen i samma koordinat).
3. **Stitch:** varje huvud producerar sin sektions höjd/tjocklek-profil [start_mm,end_mm].
   `app/processing/stitch.py:stitch_sections()` resamplar in alla sektioner på ett
   gemensamt rutnät och medlar överlapp → **en hel-bräds-profil**. Sen kör samma
   `fusion`/`grade` som idag på hela brädan.

## Status / nästa steg
- ✅ Roller (lead/sensor) + position per nod, data-drivet, exponerat till master-GUI:t.
- ✅ `SharedConveyorClient` så sensor-huvuden inte dubblerar motor/encoder.
- ✅ `stitch_sections()` (testad) för fusion över sektioner.
- ⏳ **Nät-sync av matningsposition** lead→sensor (idag: stub `set_feed_position`).
  Lägg ett `feed_position`-event/ström i master/slave-protokollet (lead broadcastar
  position; sensor-huvuden + master konsumerar) så stitch får live-koordinaten.
- ⏳ **Master-orkestrering**: "skanna alla" — lead startar bandet, alla huvuden samlar
  sina sektioner, master kör `stitch_sections` → en bräda → gradering.
