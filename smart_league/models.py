from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .abilities import AbilityContext, SpecialAbility, create_ability
from .constants import BRANCH_FEATURES, Branch, FEATURE_LABELS, INITIAL_MORALE


@dataclass(slots=True)
class PerformanceBreakdown:
    attribute_name: str
    base_value: int
    moral_bonus: int
    ability_bonus: int
    energy_penalty: int
    level_bonus: int
    energy_at_calculation: int
    total: int


@dataclass(slots=True)
class SportCard(ABC):
    card_id: int
    player_name: str
    team_name: str
    branch: Branch
    durability: int
    energy: int
    max_energy: int
    level: int = 1
    experience_points: int = 0
    usage_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    draw_count: int = 0
    used_in_league: bool = False
    just_leveled_up: bool = False
    ability_name: str = "Yok"
    special_ability_coefficient: int = 10
    image_path: str = ""
    special_ability: SpecialAbility = field(init=False)

    def __post_init__(self) -> None:
        self.special_ability = create_ability(self.ability_name)

    @abstractmethod
    def base_attributes(self) -> dict[str, int]:
        raise NotImplementedError

    def attribute_names(self) -> list[str]:
        return BRANCH_FEATURES[self.branch]

    def label(self) -> str:
        return f"{self.player_name} ({self.team_name})"

    @property
    def sporcuID(self) -> int:
        return self.card_id

    @property
    def sporcuAdi(self) -> str:
        return self.player_name

    @property
    def sporcuTakim(self) -> str:
        return self.team_name

    @property
    def maxEnerji(self) -> int:
        return self.max_energy

    @property
    def deneyimPuani(self) -> int:
        return self.experience_points

    @property
    def kartKullanildiMi(self) -> bool:
        return self.used_in_league

    @property
    def ozelYetenek(self) -> str:
        return self.ability_name

    def can_play(self) -> bool:
        return not self.used_in_league and self.energy > 0

    def is_critical(self) -> bool:
        return 0 < self.energy < 20

    def level_bonus(self) -> int:
        return {1: 0, 2: 5, 3: 10}[self.level]

    def morale_bonus(self, player_morale: int) -> int:
        if player_morale >= 90:
            return 10
        if player_morale >= 80:
            return 5
        if player_morale < 50:
            return -5
        return 0

    def energy_penalty(self, base_value: int) -> int:
        if self.energy > 70:
            return 0
        if 40 <= self.energy <= 70:
            return round(base_value * 0.10)
        if 0 < self.energy < 40:
            return round(base_value * 0.20)
        return base_value

    def build_ability_context(
        self,
        attribute_name: str,
        round_number: int,
        total_expected_rounds: int,
        owner_player_name: str,
        owner_branch_card_count: int,
        same_team_branch_support: int,
        opponent_attribute_base: int,
    ) -> AbilityContext:
        return AbilityContext(
            round_number=round_number,
            total_expected_rounds=total_expected_rounds,
            attribute_name=attribute_name,
            owner_player_name=owner_player_name,
            owner_branch_card_count=owner_branch_card_count,
            same_team_branch_support=same_team_branch_support,
            owner_energy=self.energy,
            opponent_attribute_base=opponent_attribute_base,
        )

    def calculate_performance(
        self,
        attribute_name: str,
        player_morale: int,
        round_number: int,
        total_expected_rounds: int,
        owner_player_name: str,
        owner_branch_card_count: int,
        same_team_branch_support: int,
        opponent_attribute_base: int,
    ) -> PerformanceBreakdown:
        base_value = self.base_attributes()[attribute_name]
        context = self.build_ability_context(
            attribute_name=attribute_name,
            round_number=round_number,
            total_expected_rounds=total_expected_rounds,
            owner_player_name=owner_player_name,
            owner_branch_card_count=owner_branch_card_count,
            same_team_branch_support=same_team_branch_support,
            opponent_attribute_base=opponent_attribute_base,
        )
        raw_ability_bonus = self.special_ability.pre_round_bonus(base_value, context)
        ability_bonus = round(raw_ability_bonus * (self.special_ability_coefficient / 10))
        self.special_ability.mark_used_if_needed(ability_bonus)
        moral_bonus = self.morale_bonus(player_morale)
        energy_penalty = self.energy_penalty(base_value)
        level_bonus = self.level_bonus()
        total = base_value + moral_bonus + ability_bonus - energy_penalty + level_bonus
        return PerformanceBreakdown(
            attribute_name=attribute_name,
            base_value=base_value,
            moral_bonus=moral_bonus,
            ability_bonus=ability_bonus,
            energy_penalty=energy_penalty,
            level_bonus=level_bonus,
            energy_at_calculation=self.energy,
            total=total,
        )

    def apply_energy_change(self, loss_amount: int) -> None:
        adjusted_loss = self.special_ability.adjust_energy_loss(loss_amount)
        self.energy = max(0, self.energy - adjusted_loss)
        if self.energy == 0:
            self.used_in_league = True

    def register_usage(self, decisive: bool) -> None:
        self.usage_count += 1
        if decisive:
            self.used_in_league = True

    def register_result(self, result: str) -> None:
        if result == "win":
            self.win_count += 1
            self.experience_points += 2
        elif result == "loss":
            self.loss_count += 1
        else:
            self.draw_count += 1
            self.experience_points += 1

    def level_up_if_needed(self) -> bool:
        target_level = self.level
        if self.level < 2 and (self.win_count >= 2 or self.experience_points >= 4):
            target_level = 2
        if self.level < 3 and (self.win_count >= 4 or self.experience_points >= 8):
            target_level = 3
        if target_level == self.level:
            return False

        while self.level < target_level:
            self.level += 1
            self.increase_all_attributes(5)
            self.max_energy += 10
            self.durability += 5
        self.just_leveled_up = True
        return True

    def consume_level_up_bonus(self) -> bool:
        if self.just_leveled_up:
            self.just_leveled_up = False
            return True
        return False

    def sporcuPuaniGoster(self) -> dict[str, int]:
        return self.base_attributes()

    def kartBilgisiYazdir(self) -> str:
        return "\n".join(self.detail_lines())

    def performansHesapla(self, *args, **kwargs) -> PerformanceBreakdown:
        return self.calculate_performance(*args, **kwargs)

    def enerjiGuncelle(self, kayip_miktari: int) -> None:
        self.apply_energy_change(kayip_miktari)

    def seviyeAtlaKontrol(self) -> bool:
        return self.level_up_if_needed()

    def ozelYetenekUygula(self, base_attribute_value: int, context: AbilityContext) -> int:
        raw_bonus = self.special_ability.pre_round_bonus(base_attribute_value, context)
        bonus = round(raw_bonus * (self.special_ability_coefficient / 10))
        self.special_ability.mark_used_if_needed(bonus)
        return bonus

    @abstractmethod
    def increase_all_attributes(self, amount: int) -> None:
        raise NotImplementedError

    def detail_lines(self) -> list[str]:
        attrs = ", ".join(
            f"{FEATURE_LABELS[name]}={value}" for name, value in self.base_attributes().items()
        )
        return [
            f"ID: {self.card_id}",
            f"Ad: {self.player_name}",
            f"Takim: {self.team_name}",
            f"Brans: {self.branch.value}",
            f"Seviye: {self.level}",
            f"Deneyim Puani: {self.experience_points}",
            f"Enerji: {self.energy}/{self.max_energy}",
            f"Dayaniklilik: {self.durability}",
            f"Ozel Yetenek Katsayisi: {self.special_ability_coefficient}",
            f"Ozel Yetenek: {self.ability_name}",
            f"Yetenek Kullanimi: {self.special_ability.usage_rule}",
            f"Gorsel: {'Var' if self.image_path else 'Yok'}",
            f"Yetenek Aciklamasi: {self.special_ability.description}",
            f"Kullanim: {self.usage_count}",
            f"Galibiyet/Maglubiyet/Beraberlik: {self.win_count}/{self.loss_count}/{self.draw_count}",
            f"Ozellikler: {attrs}",
        ]


@dataclass(slots=True)
class Footballer(SportCard):
    penalti: int = 0
    serbest_vurus: int = 0
    kaleci_karsi_karsiya: int = 0

    def base_attributes(self) -> dict[str, int]:
        return {
            "penalti": self.penalti,
            "serbest_vurus": self.serbest_vurus,
            "kaleci_karsi_karsiya": self.kaleci_karsi_karsiya,
        }

    def increase_all_attributes(self, amount: int) -> None:
        self.penalti += amount
        self.serbest_vurus += amount
        self.kaleci_karsi_karsiya += amount


@dataclass(slots=True)
class Basketballer(SportCard):
    ucluk: int = 0
    ikilik: int = 0
    serbest_atis: int = 0

    def base_attributes(self) -> dict[str, int]:
        return {
            "ucluk": self.ucluk,
            "ikilik": self.ikilik,
            "serbest_atis": self.serbest_atis,
        }

    def increase_all_attributes(self, amount: int) -> None:
        self.ucluk += amount
        self.ikilik += amount
        self.serbest_atis += amount


@dataclass(slots=True)
class Volleyballer(SportCard):
    servis: int = 0
    blok: int = 0
    smac: int = 0

    def base_attributes(self) -> dict[str, int]:
        return {
            "servis": self.servis,
            "blok": self.blok,
            "smac": self.smac,
        }

    def increase_all_attributes(self, amount: int) -> None:
        self.servis += amount
        self.blok += amount
        self.smac += amount


@dataclass(slots=True)
class Player(ABC):
    player_id: int
    player_name: str
    score: int = 0
    morale: int = INITIAL_MORALE
    cards: list[SportCard] = field(default_factory=list)
    win_streak: int = 0
    loss_streak: int = 0
    rounds_won: int = 0
    rounds_lost: int = 0
    draws: int = 0
    streak_bonus_count: int = 0
    series_count: int = 0
    special_ability_wins: int = 0
    branch_loss_streak: dict[Branch, int] = field(
        default_factory=lambda: {branch: 0 for branch in Branch}
    )

    @property
    def oyuncuID(self) -> int:
        return self.player_id

    @property
    def oyuncuAdi(self) -> str:
        return self.player_name

    @property
    def kartListesi(self) -> list[SportCard]:
        return self.cards

    @property
    def galibiyetSerisi(self) -> int:
        return self.win_streak

    @property
    def kaybetmeSerisi(self) -> int:
        return self.loss_streak

    def available_cards(self, branch: Branch | None = None) -> list[SportCard]:
        cards = [card for card in self.cards if card.can_play()]
        if branch is not None:
            cards = [card for card in cards if card.branch == branch]
        return cards

    def branch_card_count(self, branch: Branch) -> int:
        return len(self.available_cards(branch))

    def same_team_branch_support(self, card: SportCard) -> int:
        return sum(
            1
            for teammate in self.available_cards(card.branch)
            if teammate is not card and teammate.team_name == card.team_name
        )

    def apply_morale_delta(self, delta: int) -> None:
        self.morale = max(0, min(100, self.morale + delta))

    def register_round_result(self, result: str, branch: Branch) -> None:
        if result == "win":
            self.rounds_won += 1
            self.win_streak += 1
            self.loss_streak = 0
            self.branch_loss_streak[branch] = 0
            if self.win_streak == 2:
                self.series_count += 1
                self.apply_morale_delta(10)
            elif self.win_streak == 3:
                self.apply_morale_delta(15)
        elif result == "loss":
            self.rounds_lost += 1
            self.loss_streak += 1
            self.win_streak = 0
            self.branch_loss_streak[branch] += 1
            if self.loss_streak == 2:
                self.apply_morale_delta(-10)
            if self.branch_loss_streak[branch] == 2:
                self.apply_morale_delta(-5)
        else:
            self.draws += 1
            self.win_streak = 0
            self.loss_streak = 0
            self.branch_loss_streak[branch] = 0

    @abstractmethod
    def select_card(self, branch: Branch, **kwargs) -> SportCard | None:
        raise NotImplementedError

    def kartSec(self, branch: Branch, **kwargs) -> SportCard | None:
        return self.select_card(branch, **kwargs)


@dataclass(slots=True)
class UserPlayer(Player):
    def select_card(self, branch: Branch, **kwargs) -> SportCard | None:
        requested_id = kwargs.get("card_id")
        for card in self.available_cards(branch):
            if card.card_id == requested_id:
                return card
        return None


@dataclass(slots=True)
class ComputerPlayer(Player):
    strategy: object | None = None

    def select_card(self, branch: Branch, **kwargs) -> SportCard | None:
        if self.strategy is None:
            return None
        return self.strategy.select_card(self, branch, kwargs.get("game_state"))


Sporcu = SportCard
Futbolcu = Footballer
Basketbolcu = Basketballer
Voleybolcu = Volleyballer
Oyuncu = Player
Kullanici = UserPlayer
Bilgisayar = ComputerPlayer
