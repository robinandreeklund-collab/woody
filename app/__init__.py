"""VIRKE kontrollsystem — huvudprogram (PySide6 + QML).

M0-skelett: native fönster, riggens geometri som en sanningskälla, simulerad HAL
som matar brädor, och en korrekt-proportionerad live-vy. Kör:

    python -m app.main --mode sim          # simulering (standard)
    python -m app.main --mode real         # fysisk hårdvara (Fas 4, ej klart)
"""
