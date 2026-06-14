# Master/slave — styr alla Jetson-läshuvuden från desktopen

Varje **Jetson = en slave** (ett läshuvud med sina sensorer). Din **desktop = master**
som ansluter till alla noder och styr var och en på distans (sensorstatus +
kalibrering) i samma GUI.

```
   desktop (MASTER)                       Jetson A (SLAVE)        Jetson B (SLAVE)
 ┌──────────────────┐  TCP JSON-lines   ┌────────────────┐     ┌────────────────┐
 │  python -m app   │◄────8765─────────►│ app.net.slave  │     │ app.net.slave  │
 │     --master     │◄──────────────────│ DeviceManager  │     │ DeviceManager  │
 │  NodeManager     │   8765            │  + scanner+HAL │     │  + scanner+HAL │
 │   RemoteNode ×N  │                   └────────────────┘     └────────────────┘
 └──────────────────┘
```

## Transport
Qt Network (QTcpServer/QTcpSocket), **JSON-lines** — ett JSON-objekt per rad.
Inga extra beroenden (inbyggt i PySide6). Tre meddelandeformer (`app/net/protocol.py`):
begäran `{id,cmd,args}`, svar `{id,ok,result|error}`, event `{event,data}` (oombett,
för live-status). Slaven broadcastar event när enhetsstatus/kalibrering ändras →
mastern uppdateras utan polling.

## Den eleganta delen
`RemoteNode` (master) speglar **exakt** `DeviceManager`:s QML-gränssnitt (devices,
methodsFor, startCalibration, calib*-properties + signaler). Därför driver den
**befintliga** `CalibrationView` en fjärrnod oförändrad — bara `dm` byts från lokal
`devmgr` till en `RemoteNode`. Nät-anrop är asynkrona: methodsFor returnerar cache +
begär uppdatering; kalibreringsprogress strömmar via event.

## Köra

### På varje Jetson (slave)
```bash
python -m app.net.slave --mode real --name "RÖD-huvud" --port 8765
# sim utan hårdvara:  python -m app.net.slave --mode sim --name testhuvud
```
Headless (QCoreApplication). Lyssnar på 0.0.0.0:8765. Ett läshuvud per Jetson.

### På desktopen (master)
1. Skapa `data/nodes.json` med dina läshuvuden:
   ```json
   [
     {"name": "RÖD-huvud",  "host": "100.64.0.11",     "port": 8765},
     {"name": "GRÖN-huvud", "host": "woody-gron.local", "port": 8765}
   ]
   ```
   `host` = IP eller hostname (LAN **eller** Tailscale — funkar över subnät).
2. Starta master-GUI:t:
   ```bash
   python -m app --master
   ```
3. Vänster: alla läshuvuden med live anslutning/läge/kalibreringsstatus. Klicka en
   nod → styr dess sensorer + kalibrering på distans (samma AUTO/guidat-flöde som
   lokalt). "Arma lasrar" kräver fortfarande interlock-bekräftelse per nod (klass 3B).

## Kommandon (master → slave)
`hello`, `status`, `devices`, `methods{dev}`, `start_calibration{dev,method}`,
`cancel_calibration`, `calib_state`, `refresh`, `arm_lasers{confirm}`, `disarm_lasers`.
Event (slave → master): `devices_changed`, `methods_changed`, `calib_changed`, `hello`.

## Säkerhet
- **Laser (klass 3B):** arm-grinden gäller även på distans — `arm_lasers{confirm}`
  motsvarar människo-interlock vid den fysiska riggen. Fjärrstyrning tänder aldrig
  lasern utan bekräftelse, och slavens `close()` släcker alltid.
- **Nät:** kör helst över **Tailscale** (krypterat, ingen öppen LAN-port). På öppet
  LAN — lägg bakom brandvägg. (Token-auth kan läggas till i protokollet vid behov.)

## Filer
`app/net/`: `protocol.py` (inramning), `command_handler.py` (kommando→DeviceManager),
`slave_server.py` + `slave.py` (Jetson-sidan), `remote_node.py` + `node_manager.py`
(master-sidan), `nodes_config.py` (data/nodes.json). GUI: `app/ui/qml/MasterMain.qml`.
Tester: `app/tests/test_net.py` (protokoll, kommandohanterare, full loopback).
