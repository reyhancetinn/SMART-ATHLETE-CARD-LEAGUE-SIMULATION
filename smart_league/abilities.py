from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import ceil


@dataclass(slots=True)
class AbilityContext:
    round_number: int
    total_expected_rounds: int
    attribute_name: str
    owner_player_name: str
    owner_branch_card_count: int
    same_team_branch_support: int
    owner_energy: int
    opponent_attribute_base: int


class SpecialAbility(ABC):
    name = "Yok"
    description = "Ozel yetenek yoktur."
    single_use = False
    usage_rule = "Pasif"

    def __init__(self) -> None:
        self.used = False

    @abstractmethod
    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        raise NotImplementedError

    def modify_opponent_bonus(self, opponent_bonus: int, context: AbilityContext) -> int:
        return opponent_bonus

    def adjust_energy_loss(self, loss: int) -> int:
        return loss

    def mark_used_if_needed(self, bonus: int) -> None:
        if bonus > 0 and self.single_use:
            self.used = True

    def reset(self) -> None:
        self.used = False


class NoAbility(SpecialAbility):
    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        return 0


class ClutchPlayerAbility(SpecialAbility):
    name = "Clutch Player"
    description = "Son 3 turda +10 bonus verir."

    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        return 10 if context.round_number >= max(1, context.total_expected_rounds - 2) else 0


class CaptainAbility(SpecialAbility):
    name = "Captain"
    description = "Ayni takim ve bransta destek varsa +5 moral etkili bonus alir."

    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        return 5 if context.same_team_branch_support > 0 else 0


class LegendAbility(SpecialAbility):
    name = "Legend"
    description = "Bir mac boyunca bir kez secilen ozelligi iki kat etkiler."
    single_use = True
    usage_rule = "Bir macta bir kez"

    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        if self.used:
            return 0
        if base_attribute_value <= context.opponent_attribute_base:
            return base_attribute_value
        return 0


class DefenderAbility(SpecialAbility):
    name = "Defender"
    description = "Rakibin ozel yetenek bonusunu yariya indirir."

    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        return 0

    def modify_opponent_bonus(self, opponent_bonus: int, context: AbilityContext) -> int:
        return opponent_bonus // 2


class VeteranAbility(SpecialAbility):
    name = "Veteran"
    description = "Enerji kaybini yariya indirir."

    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        return 0

    def adjust_energy_loss(self, loss: int) -> int:
        return ceil(loss * 0.5)


class FinisherAbility(SpecialAbility):
    name = "Finisher"
    description = "Enerji 40'in altindaysa +8 bonus verir."

    def pre_round_bonus(self, base_attribute_value: int, context: AbilityContext) -> int:
        return 8 if context.owner_energy < 40 else 0


ABILITY_TYPES = {
    "Yok": NoAbility,
    "Clutch Player": ClutchPlayerAbility,
    "Captain": CaptainAbility,
    "Legend": LegendAbility,
    "Defender": DefenderAbility,
    "Veteran": VeteranAbility,
    "Finisher": FinisherAbility,
}


def create_ability(name: str | None) -> SpecialAbility:
    ability_cls = ABILITY_TYPES.get((name or "Yok").strip(), NoAbility)
    return ability_cls()
