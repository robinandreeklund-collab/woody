# Jetson Orin Nano — bänk-setup & inställningar (att inte glömma)

Prototypbänken körs på en **NVIDIA Jetson Orin Nano Super Dev Kit** (ARM64 / aarch64,
Ubuntu/L4T). Det här dokumentet samlar drivrutiner, kritiska OS-inställningar och
kopplingar så vi inte tappar bort dem. Räkna med det här när riggen ska sättas upp.

> Verifierat i kod: `python tools/verify_jetson_io.py` (portar, bandbredd, keep-up,
> drivrutiner) och `python tools/verify_optics.py` (mount/gänga + optik).

---

## 1. Kameror — drivrutiner / SDK på ARM64

Båda kamerorna följer **vendor-neutrala standarder** (GenICam), så vi är aldrig
låsta till en enda SDK.

| Kamera | Standard | Drivs på Jetson via |
|---|---|---|
| **Profilkameror** Hikrobot MV-CS050-10UM (×2, USB3) | USB3 Vision + GenICam | **Hikrobot MVS SDK — aarch64 `.deb`** (libs i `/opt/MVS/lib/aarch64`) |
| **Ytkamera** Huateng 4K färg (GigE) | GigE Vision V1.2 + GenICam | vendor-SDK (Linux) **eller Aravis** |

- **Universal reserv:** [Aravis](https://github.com/AravisProject/aravis) (open source)
  driver **både** GigE Vision och USB3 Vision på aarch64 — bekräftat på Orin Nano
  (Aravis 0.8.34). Om en vendor-SDK krånglar täcker Aravis båda kameratyperna.
- Hikrobot MVS laddas från <https://www.hikrobotics.com/en/machinevision/service/download/>.

### Testa att kamerorna hittas (när hårdvaran är på plats)
```bash
sudo apt install aravis-tools
arv-tool-0.8            # listar anslutna GigE/USB3 Vision-kameror
arv-viewer             # live-bild (eller vendor-viewer / MVS Viewer)
```
Ser du kameran listad och får en bild → den funkar.

---

## 2. KRITISKA OS-inställningar (annars droppar/hänger strömmarna)

### USB3 (profilkameror) — höj usbfs-minnesgränsen
Default-gränsen i Linux är för låg för högupplösta USB3-kameror → tappade ramar.
```bash
# temporärt:
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'
# permanent: lägg till i kernel-cmdline (extlinux.conf APPEND ...):
#   usbcore.usbfs_memory_mb=1000
```
Kör de **två profilkamerorna på skilda USB3-portar/kontroller** (undvik delad
hubb-flaskhals).

### GigE (ytkamera) — jumbo frames + samma subnät
```bash
# sätt Jetsons GbE på samma subnät som kameran och aktivera jumbo frames:
sudo ip link set eth0 mtu 9000
# samt höj rx-buffrar vid behov (sysctl net.core.rmem_max).
```

---

## 3. Enhetskarta — vad kopplas var

| Enhet | Jetson-port | Not |
|---|---|---|
| Profilkamera RÖD | USB3 #1 | ~307 MB/s (ROI) |
| Profilkamera GRÖN | USB3 #2 | egen kontroller om möjligt |
| Ytkamera 4K färg | GbE (RJ45) | GigE direkt, ingen switch |
| 3× punktlaser LR400 | USB (Waveshare USB→4CH RS-485) | **1 LR400/kanal** → samtidig avläsning, ingen Modbus-adressering |
| 2× Jrk G2 (motorer) | I²C (el. USB/UART) | motorns Hall → Jrk frekvens-FB |
| Röd/grön laser-enable | GPIO (MOSFET) | röd 5 V, grön 24 V |
| Ingångslaser (fotocell) | GPIO | brädstart + nollning |
| Vitt LED-ljus (yta) | GPIO/flash-ut | färg i 1 pass |
| NVMe SSD | M.2 Key-M | OS + dataset + modeller |

**Ingen analog in behövs** — LR400 ger avstånd digitalt via RS-485 (ingen ADC/MCP3008).

---

## 4. Programvaru-arkitektur — så att inget HÄNGER

Hårdvaran räcker med marginal (compute ~few % vid 60 brädor/min), men det avgörs
av mjukvaran. Tre regler:

1. **Laserstripe-extraktion på GPU/CUDA** (el. NVIDIA VPI) — *inte* en naiv
   pixel-för-pixel Python-loop. Det är det enda sättet att få det att hänga.
2. **Pipelina stegen:** capture-trådar ∥ GPU-bearbetning ∥ U-Net-inferens
   (inte en blockande loop).
3. **Profilkameror på skilda USB3-portar** (se §2).

---

## 5. Snabb sanity-check före köp/idrifttagning
```bash
python tools/verify_jetson_io.py   # portar, bandbredd, keep-up @ 60/min, drivrutiner
python tools/verify_optics.py      # C-mount + M30.5-filter, FOV/WD, laser 45°, precision
```

---

## Referenser
- Hikrobot MVS SDK (aarch64/Jetson): <https://www.hikrobotics.com/en/machinevision/service/download/>
- Hikrobot MVS ROS-drivrutin (aarch64-exempel): <https://github.com/luckyluckydadada/HIKROBOT-MVS-CAMERA-ROS>
- Aravis (GenICam, GigE+USB3 Vision): <https://github.com/AravisProject/aravis>
- camera_aravis2 (ROS2-drivrutin): <https://github.com/FraunhoferIOSB/camera_aravis2>
