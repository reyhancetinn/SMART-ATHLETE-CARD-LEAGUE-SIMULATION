from __future__ import annotations

import random
from abc import ABC, abstractmethod

from .constants import BRANCH_FEATURES, Branch
from .models import ComputerPlayer, SportCard


class CardSelectionStrategy(ABC):
    @abstractmethod
    def select_card(
        self,
        computer: ComputerPlayer,
        branch: Branch,
        game_state: dict[str, object] | None = None,
    ) -> SportCard | None:
        raise NotImplementedError


class EasyStrategy(CardSelectionStrategy):
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def select_card(
        self,
        computer: ComputerPlayer,
        branch: Branch,
        game_state: dict[str, object] | None = None,
    ) -> SportCard | None:
        cards = computer.available_cards(branch)
        if not cards:
            return None
        return self.rng.choice(cards)


class MediumStrategy(CardSelectionStrategy):
    def select_card(
        self,
        computer: ComputerPlayer,
        branch: Branch,
        game_state: dict[str, object] | None = None,
    ) -> SportCard | None:
        cards = computer.available_cards(branch)
        if not cards:
            return None
        if game_state is None:
            return max(cards, key=lambda card: sum(card.base_attributes().values()))

        round_number = int(game_state["round_number"])
        total_expected_rounds = int(game_state["total_expected_rounds"])
        opponent = game_state["opponent"]

        def average_performance(card: SportCard) -> float:
            branch_card_count = computer.branch_card_count(branch)
            same_team_support = computer.same_team_branch_support(card)
            totals = []
            for attribute in BRANCH_FEATURES[branch]:
                opponent_base = max(
                    (
                        enemy_card.base_attributes()[attribute]
                        for enemy_card in opponent.available_cards(branch)
                    ),
                    default=0,
                )
                breakdown = card.calculate_performance(
                    attribute_name=attribute,
                    player_morale=computer.morale,
                    round_number=round_number,
                    total_expected_rounds=total_expected_rounds,
                    owner_player_name=computer.player_name,
                    owner_branch_card_count=branch_card_count,
                    same_team_branch_support=same_team_support,
                    opponent_attribute_base=opponent_base,
                )
                totals.append(breakdown.total)
            return sum(totals) / len(totals)

        return max(cards, key=average_performance)


class KartSecmeStratejisi(CardSelectionStrategy):
    """Dokumandaki strateji sinifi adi icin uyumluluk katmani."""


class KolayStrateji(EasyStrategy):
    """Kolay mod: uygun branstan rastgele kart secer."""


class OrtaStrateji(MediumStrategy):
    """Orta mod: guncel ortalama performansi en yuksek karti secer."""


__all__ = [
    "CardSelectionStrategy",
    "EasyStrategy",
    "MediumStrategy",
    "KartSecmeStratejisi",
    "KolayStrateji",
    "OrtaStrateji",
]
