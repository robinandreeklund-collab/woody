# GPIO fält-IO (laser-enable, LED, fotocell) — idrifttagning + säkerhet

Jetsons 40-pin header styr fält-IO enligt `prototype-pinout.svg` (`gpio_io.py`):

| Pin | Roll | Not |
|---|---|---|
| 7 | Anhåll-fotocell IN | GTRIC LSZ-S30N1, NPN, **aktiv LÅG** (bräda laddad) |
| 16 | Linjelaser RÖD enable | 650 nm, 5 V, klass 3B |
| 18 | Linjelaser GRÖN enable | 520 nm, 24 V, klass 3B |
| 13 + 15 | Vitt LED ×2 enable | 24 V list |

## ⚠️ Lasersäkerhet — kodlåst arm-grind
Laser-enable är **klass 3B**. `GpioEnable(requires_arm=True)` (lasrarna) **VÄGRAR**
`set(True)` tills `arm(confirm=True)` anropats — det representerar människo-interlock
(rum låst, dörrinterlock, skyddsglasögon HM326-C). Ingen kalibrering eller drift-rutin
kan tända lasern av misstag; auto-rutinerna tänder den **aldrig** själva.

- Drift: `RealScanner.arm_lasers(confirm=True)` (GUI ska anropa det från en **explicit
  bekräftelse-kontroll** med säkerhets-checklista) → `new_board()`/`begin_stream()` kan
  tända lasrarna. Utan arm skannas utan laserprofil + tydlig säkerhets-hint i loggen.
- `disarm_lasers()` och varje `close()` släcker + avarmar (säkert läge).
- LED (`requires_arm=False`) tänds direkt — ofarligt.

## Kalibrering (GUI: Sensorer → enhet → Kalibrering)
| Enhet | Metod | AUTO | Vad |
|---|---|---|---|
| LED | `uniform` | ✅ | Tänd LED (ofarligt) → mät belysningsjämnhet längs FOV → ojämnhet + rekommendation. |
| Fotocell | `trigger` | ✅ | Räkna laddnings-flanker (pin 7) medan operatören laddar bräda 10× → detektioner + dubbeltrigg/debounce. |
| Laser RÖD/GRÖN | `straight` | ✅ grindat | Linjerakhet (bow) via profilkameran — **kräver att lasern redan är tänd** (operatör + interlock); tänder aldrig själv. |
| Laser RÖD/GRÖN | `width` | ✅ grindat | Stripe-bredd (FWHM) — samma grind. |
| Laser RÖD/GRÖN | `power` | ⛔ guidat | Enable & effekt-test — det ÄR tändnings-testet → görs via explicit interlock-bekräftelse. |

"Grindat" = auto-mätningen körs bara om lasern redan är tänd; annars returneras
`"tänd lasern via interlock-kontrollen först (klass 3B)"`.

## Idrifttagning
1. `bash tools/jetson_bootstrap.sh` (Jetson.GPIO + udev). Användaren i `gpio`-gruppen
   (redan) → ingen sudo för GPIO.
2. `python tools/jetson_selftest.py` → sektion 5: GPIO-bibliotek + pin-karta +
   fotocellens momentanstatus (utgångar rörs ALDRIG av selftestet — lasersäkerhet).
3. **Fotocell:** kör `photocell.trigger` (GUI) → ladda bräda mot anhållet 10× →
   verifiera 10/10 detektioner, inga dubbeltriggar.
4. **LED:** kör `led_white.uniform` med vit yta i FOV → ojämnhet (< 30 % = flat-field räcker).
5. **Laser (interlock!):** säkra rummet, ta på glasögon, bekräfta interlock i GUI →
   `arm_lasers(confirm=True)` → kör `power` (effekt), sen `straight`/`width` (auto).
   Avarma (`disarm_lasers`) när klart.

## Felsökning
- **Laser tänds inte:** ej armad — kör interlock-bekräftelsen (`arm_lasers(confirm=True)`).
- **Fotocell triggar inte / inverterat:** NPN aktiv-låg på pin 7 — kontrollera pull-up
  och polaritet; `read()` ska bli True när bräda skymmer strålen.
- **Dubbeltriggar:** öka debounce (bouncetime) eller kontrollera mekaniskt glapp.
- **"GPIO channel not set up":** `open()` ej körd på enheten (HAL gör det i probe/drift).
