"""Nordisk utseendesortering A/B/C/D — gränsvärden som DATA (ruleset).

Representativa, publicerade värden enligt STRUKTUREN i Nordic Timber ("Blå boken")
och EN 1611-1 (G4-0..G4-4). De EXAKTA certifierade talen är upphovsrättsskyddade —
köp standarden (SIS SS-EN 1611-1 / Nordic Timber) och ersätt talen nedan för
certifierad/deklarerbar sortering. STRUKTUREN och MOTORN är kompletta; endast de
numeriska gränserna ska finjusteras (och kalibreras mot referensbrädor).

Princip (EN 1611-1 / Nordic Timber):
  * Bedöms per sida; **sämsta enskilda defekten avgör graden** (worst governs).
  * Varje gräns = MAX tillåtet för att FÅ den graden. Klarar man inte ens D → "V" (vrak).
  * Grader bäst→sämst: A (US/G4-0..1) · B (kvinta/G4-2) · C (bygg/G4-3) · D (formvirke/G4-4).

Se docs/grading-nordic.md för fullständig analys + källor.
"""
from __future__ import annotations

# Skevhetsgränser uttrycks per 2 m brädlängd; uppmätt skevhet skalas till detta.
WARP_REF_MM = 2000.0

NORDIC_ABCD: dict = {
    "order": ["A", "B", "C", "D"],          # bäst → sämst; sämre än D = "V"
    "meta": {                                # (titel, GUI-färg)
        "A": ("Klass A · A-virke (US/G4-0–1)", "#34e6b5"),
        "B": ("Klass B · kvinta (G4-2)",       "#27d3e0"),
        "C": ("Klass C · bygg (G4-3)",         "#ffb33d"),
        "D": ("Klass D · formvirke (G4-4)",    "#d98a3d"),
        "V": ("Vrak · under D",                "#ff4d5e"),
    },
    # --- gränser PER GRAD (värdet måste vara ≤ gränsen för att få graden) ---
    # Kvist: största kvistens diameter / sidans bredd. (Frisk kvist; torr/lös/röt
    # är strängare i standarden — läggs till när kvist-TYP klassas, se docs.)
    "knot_frac_width":  {"A": 0.20, "B": 0.35, "C": 0.55, "D": 0.85},
    # Vankant: djup / tjocklek
    "wane_frac_thick":  {"A": 0.05, "B": 0.20, "C": 0.40, "D": 0.75},
    # Vankant: längd / brädlängd
    "wane_frac_len":    {"A": 0.05, "B": 0.15, "C": 0.35, "D": 0.80},
    # Spricka: längd / brädlängd  (genomgående spricka = strängare, ej modellerat än)
    "crack_frac_len":   {"A": 0.05, "B": 0.15, "C": 0.33, "D": 0.80},
    # Blånad: total area / brädyta
    "stain_frac_area":  {"A": 0.00, "B": 0.05, "C": 0.20, "D": 0.60},
    # Röta: total area / brädyta  (allvarligt → tillåts först från C)
    "rot_frac_area":    {"A": 0.00, "B": 0.00, "C": 0.05, "D": 0.20},
    # Hål: antal
    "hole_count":       {"A": 0,    "B": 0,    "C": 2,    "D": 6},
    # Skevhet (mm per 2 m):
    "bow_mm_2m":        {"A": 8.0,  "B": 12.0, "C": 20.0, "D": 40.0},   # flatböj
    "spring_mm_2m":     {"A": 6.0,  "B": 10.0, "C": 16.0, "D": 30.0},   # kantkrok
    "twist_mm_2m":      {"A": 4.0,  "B": 8.0,  "C": 12.0, "D": 20.0},   # vridning
    # Kupa: pildjup / bredd
    "cup_frac_width":   {"A": 0.01, "B": 0.02, "C": 0.04, "D": 0.08},
}

# Läsbara namn för "styrande defekt"-rapportering.
FEATURE_LABEL = {
    "knot_frac_width": "kvist", "wane_frac_thick": "vankant (djup)",
    "wane_frac_len": "vankant (längd)", "crack_frac_len": "spricka",
    "stain_frac_area": "blånad", "rot_frac_area": "röta", "hole_count": "hål",
    "bow_mm_2m": "flatböj", "spring_mm_2m": "kantkrok", "twist_mm_2m": "vridning",
    "cup_frac_width": "kupa",
}
