"""Host-telemetri för en Jetson-slav — ALLT som går att läsa ur /proc + /sys.

Riktiga värden oavsett om skanner-HAL:en kör sim eller real. Inga extra beroenden.
CPU-% och nät-genomflöde mäts som delta mellan anrop → ``HostTelemetry`` hålls
levande och ``collect()`` anropas periodiskt av SlaveServer. Allt är best-effort:
saknas en källa returneras None för det fältet (övriga påverkas inte).
"""
from __future__ import annotations

import glob
import os
import shutil
import time


def _read_all_cpu() -> dict:
    """{'cpu': (idle,total), 'cpu0': (...), ...} ur /proc/stat."""
    out = {}
    try:
        with open("/proc/stat") as f:
            for line in f:
                if not line.startswith("cpu"):
                    break
                p = line.split()
                vals = [int(x) for x in p[1:]]
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                out[p[0]] = (idle, sum(vals))
    except Exception:
        pass
    return out


def _pct(prev, cur):
    if not prev or not cur:
        return None
    d_idle = cur[0] - prev[0]
    d_total = cur[1] - prev[1]
    return round(100.0 * (1.0 - d_idle / d_total), 1) if d_total > 0 else None


def _mem():
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])               # kB
    except Exception:
        return {}
    return info


def _temps():
    """{zon-typ: °C} för alla thermal zones."""
    out = {}
    for zdir in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            with open(f"{zdir}/temp") as f:
                t = int(f.read().strip()) / 1000.0
            try:
                with open(f"{zdir}/type") as f:
                    name = f.read().strip()
            except Exception:
                name = os.path.basename(zdir)
            out[name] = round(t, 1)
        except Exception:
            continue
    return out


def _cpu_freq_mhz():
    freqs = []
    for fp in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
        try:
            with open(fp) as f:
                freqs.append(int(f.read().strip()) / 1000.0)   # kHz → MHz
        except Exception:
            continue
    return round(max(freqs)) if freqs else None


def _gpu():
    load = freq = None
    for path in ("/sys/devices/gpu.0/load", "/sys/devices/platform/gpu.0/load",
                 "/sys/devices/17000000.gpu/load"):
        try:
            with open(path) as f:
                load = round(int(f.read().strip()) / 10.0, 1)
                break
        except Exception:
            continue
    for fp in glob.glob("/sys/class/devfreq/*.gpu/cur_freq") + glob.glob("/sys/devices/*.gpu/devfreq/*/cur_freq"):
        try:
            with open(fp) as f:
                freq = round(int(f.read().strip()) / 1e6)      # Hz → MHz
                break
        except Exception:
            continue
    return load, freq


def _fan_rpm():
    for fp in glob.glob("/sys/class/hwmon/*/fan1_input") + glob.glob("/sys/devices/*/hwmon/*/rpm"):
        try:
            with open(fp) as f:
                return int(f.read().strip())
        except Exception:
            continue
    return None


def _power_w():
    """Jetson INA3221 total effekt (W) — sökvägar varierar mellan JetPack-versioner."""
    candidates = (glob.glob("/sys/bus/i2c/drivers/ina3221*/*/hwmon/*/in_power*_input")
                  + glob.glob("/sys/bus/i2c/drivers/ina3221/*/hwmon/*/power*_input")
                  + glob.glob("/sys/bus/i2c/devices/*/hwmon/*/in_power*_input"))
    tot = 0.0
    found = False
    for fp in candidates:
        try:
            with open(fp) as f:
                tot += int(f.read().strip()) / 1000.0          # mW → W
                found = True
        except Exception:
            continue
    return round(tot, 1) if found else None


def _net_bytes():
    rx = tx = 0
    try:
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                iface, rest = line.split(":", 1)
                if iface.strip() == "lo":
                    continue
                cols = rest.split()
                rx += int(cols[0]); tx += int(cols[8])
    except Exception:
        return None
    return rx, tx


def _model():
    for fp in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        try:
            with open(fp) as f:
                return f.read().strip().strip("\x00")
        except Exception:
            continue
    return None


class HostTelemetry:
    def __init__(self):
        self._prev_cpu = _read_all_cpu()
        self._prev_net = _net_bytes()
        self._prev_t = time.monotonic()
        self._model = _model()

    def collect(self) -> dict:
        cur_cpu = _read_all_cpu()
        cpu_pct = _pct(self._prev_cpu.get("cpu"), cur_cpu.get("cpu"))
        per_core = []
        i = 0
        while f"cpu{i}" in cur_cpu:
            per_core.append(_pct(self._prev_cpu.get(f"cpu{i}"), cur_cpu.get(f"cpu{i}")))
            i += 1
        self._prev_cpu = cur_cpu or self._prev_cpu

        m = _mem()
        ram_total = m.get("MemTotal", 0) // 1024
        ram_avail = m.get("MemAvailable", m.get("MemFree", 0)) // 1024
        ram_used = max(0, ram_total - ram_avail)
        swap_total = m.get("SwapTotal", 0) // 1024
        swap_used = max(0, swap_total - m.get("SwapFree", 0) // 1024)

        try:
            du = shutil.disk_usage("/")
            disk = (round(du.used / 1e9, 1), round(du.total / 1e9, 1),
                    round(100.0 * du.used / du.total, 1) if du.total else 0.0)
        except Exception:
            disk = (0.0, 0.0, 0.0)

        # nät-genomflöde (MB/s) ur delta
        now = time.monotonic()
        dt = max(1e-3, now - self._prev_t)
        net = _net_bytes()
        rx_mbps = tx_mbps = None
        if net and self._prev_net:
            rx_mbps = round((net[0] - self._prev_net[0]) / dt / 1e6, 2)
            tx_mbps = round((net[1] - self._prev_net[1]) / dt / 1e6, 2)
        self._prev_net = net or self._prev_net
        self._prev_t = now

        gpu_load, gpu_freq = _gpu()
        try:
            la = os.getloadavg()
            load = [round(x, 2) for x in la]
        except Exception:
            load = [None, None, None]
        try:
            procs = len(glob.glob("/proc/[0-9]*"))
        except Exception:
            procs = None

        temps = _temps()
        temp_max = round(max(temps.values()), 1) if temps else None

        return {
            "model": self._model,
            "cpu_pct": cpu_pct, "per_core": per_core, "cpu_freq_mhz": _cpu_freq_mhz(),
            "ncpu": os.cpu_count() or len(per_core) or 1,
            "gpu_pct": gpu_load, "gpu_freq_mhz": gpu_freq,
            "ram_used_mb": ram_used, "ram_total_mb": ram_total,
            "ram_pct": round(100.0 * ram_used / ram_total, 1) if ram_total else 0.0,
            "swap_used_mb": swap_used, "swap_total_mb": swap_total,
            "disk_used_gb": disk[0], "disk_total_gb": disk[1], "disk_pct": disk[2],
            "temp_c": temp_max, "temps": temps,
            "fan_rpm": _fan_rpm(), "power_w": _power_w(),
            "net_rx_mbps": rx_mbps, "net_tx_mbps": tx_mbps,
            "load1": load[0], "load5": load[1], "load15": load[2],
            "procs": procs, "uptime_s": _uptime(),
        }


def _uptime():
    try:
        with open("/proc/uptime") as f:
            return int(float(f.readline().split()[0]))
    except Exception:
        return None
