from __future__ import annotations

from enum import Enum


class Branch(str, Enum):
    FOOTBALL = "Futbol"
    BASKETBALL = "Basketbol"
    VOLLEYBALL = "Voleybol"


class Difficulty(str, Enum):
    EASY = "Kolay"
    MEDIUM = "Orta"


class FeatureMode(str, Enum):
    RANDOM = "Sistem Rastgele Secer"
    USER_CHOICE = "Kullanici Secer"


BRANCH_SEQUENCE = [
    Branch.FOOTBALL,
    Branch.BASKETBALL,
    Branch.VOLLEYBALL,
]

BRANCH_FEATURES: dict[Branch, list[str]] = {
    Branch.FOOTBALL: ["penalti", "serbest_vurus", "kaleci_karsi_karsiya"],
    Branch.BASKETBALL: ["ucluk", "ikilik", "serbest_atis"],
    Branch.VOLLEYBALL: ["servis", "blok", "smac"],
}

FEATURE_LABELS = {
    "penalti": "Penalti",
    "serbest_vurus": "Serbest Vurus",
    "kaleci_karsi_karsiya": "Kaleci Karsi Karsiya",
    "ucluk": "Ucluk",
    "ikilik": "Ikilik",
    "serbest_atis": "Serbest Atis",
    "servis": "Servis",
    "blok": "Blok",
    "smac": "Smac",
    "ozel_yetenek_katsayisi": "Ozel Yetenek Katsayisi",
    "dayaniklilik": "Dayaniklilik",
}

INITIAL_MORALE = 60
SPECIAL_ABILITY_WIN_POINTS = 15
NORMAL_WIN_POINTS = 10
FORFEIT_WIN_POINTS = 8
LOW_ENERGY_BONUS_POINTS = 5
LEVEL_UP_FIRST_WIN_BONUS = 5
CLUTCH_WIN_BONUS = 5
THREE_STREAK_BONUS = 10
FIVE_STREAK_BONUS = 20
