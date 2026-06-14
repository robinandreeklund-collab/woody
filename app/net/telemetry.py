"""Host-telemetri för en Jetson-slav (CPU/GPU/RAM/disk/temp/last).

Läser RIKTIGA värden ur /proc och /sys — gäller oavsett om skanner-HAL:en kör sim
eller real (Jetsonen är en riktig maskin). Inga extra beroenden. CPU-% mäts som
delta mellan anrop, så ``HostTelemetry`` hålls levande och ``collect()`` anropas
periodiskt av SlaveServer.
"""
from __future__ import annotations

import os
import shutil


def _read_cpu_times():
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()[1:]
        vals = [int(x) for x in parts]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)   # idle + iowait
        return idle, sum(vals)
    except Exception:
        return None


def _mem():
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])              # kB
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", info.get("MemFree", 0))
        used = max(0, total - avail)
        return used // 1024, total // 1024, (100.0 * used / total if total else 0.0)
    except Exception:
        return 0, 0, 0.0


def _temp_c():
    try:
        temps = []
        base = "/sys/class/thermal"
        for z in os.listdir(base):
            if z.startswith("thermal_zone"):
                try:
                    with open(f"{base}/{z}/temp") as f:
                        temps.append(int(f.read().strip()) / 1000.0)
                except Exception:
                    continue
        return round(max(temps), 1) if temps else None
    except Exception:
        return None


def _gpu_pct():
    # Jetson GPU-last (per mille) — sökväg varierar mellan moduler; prova några.
    for path in ("/sys/devices/gpu.0/load",
                 "/sys/devices/platform/gpu.0/load",
                 "/sys/devices/17000000.gpu/load"):
        try:
            with open(path) as f:
                return round(int(f.read().strip()) / 10.0, 1)   # 0–1000 → %
        except Exception:
            continue
    return None


def _uptime():
    try:
        with open("/proc/uptime") as f:
            return int(float(f.readline().split()[0]))
    except Exception:
        return None


class HostTelemetry:
    def __init__(self):
        self._prev = _read_cpu_times()

    def collect(self) -> dict:
        cpu_pct = None
        cur = _read_cpu_times()
        if cur and self._prev:
            d_idle = cur[0] - self._prev[0]
            d_total = cur[1] - self._prev[1]
            if d_total > 0:
                cpu_pct = round(100.0 * (1.0 - d_idle / d_total), 1)
        self._prev = cur or self._prev

        ram_used, ram_total, ram_pct = _mem()
        try:
            du = shutil.disk_usage("/")
            disk_used_gb = round(du.used / 1e9, 1)
            disk_total_gb = round(du.total / 1e9, 1)
            disk_pct = round(100.0 * du.used / du.total, 1) if du.total else 0.0
        except Exception:
            disk_used_gb = disk_total_gb = disk_pct = 0.0
        try:
            load1 = round(os.getloadavg()[0], 2)
        except Exception:
            load1 = None
        try:
            ncpu = os.cpu_count() or 1
        except Exception:
            ncpu = 1

        return {
            "cpu_pct": cpu_pct, "gpu_pct": _gpu_pct(),
            "ram_used_mb": ram_used, "ram_total_mb": ram_total, "ram_pct": round(ram_pct, 1),
            "disk_used_gb": disk_used_gb, "disk_total_gb": disk_total_gb, "disk_pct": disk_pct,
            "temp_c": _temp_c(), "load1": load1, "ncpu": ncpu, "uptime_s": _uptime(),
        }
