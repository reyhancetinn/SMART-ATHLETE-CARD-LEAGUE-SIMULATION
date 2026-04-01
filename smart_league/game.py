from __future__ import annotations

import random
from dataclasses import dataclass, field

from .constants import (
    BRANCH_FEATURES,
    BRANCH_SEQUENCE,
    CLUTCH_WIN_BONUS,
    FEATURE_LABELS,
    FIVE_STREAK_BONUS,
    FORFEIT_WIN_POINTS,
    LEVEL_UP_FIRST_WIN_BONUS,
    LOW_ENERGY_BONUS_POINTS,
    NORMAL_WIN_POINTS,
    SPECIAL_ABILITY_WIN_POINTS,
    THREE_STREAK_BONUS,
    Branch,
    Difficulty,
    FeatureMode,
)
from .data_loader import DataLoader
from .models import ComputerPlayer, PerformanceBreakdown, Player, SportCard, UserPlayer
from .strategies import EasyStrategy, MediumStrategy


@dataclass(slots=True)
class RoundRecord:
    round_number: int
    branch: Branch
    attribute_name: str | None
    user_card_name: str | None
    computer_card_name: str | None
    winner_name: str | None
    outcome_type: str
    user_score_after: int
    computer_score_after: int
    explanation: str


@dataclass(slots=True)
class RoundResolution:
    round_number: int
    branch: Branch
    attribute_name: str | None = None
    user_card: SportCard | None = None
    computer_card: SportCard | None = None
    user_breakdown: PerformanceBreakdown | None = None
    computer_breakdown: PerformanceBreakdown | None = None
    winner: Player | None = None
    loser: Player | None = None
    winner_card: SportCard | None = None
    loser_card: SportCard | None = None
    outcome_type: str = "normal"
    explanation: str = ""
    score_awarded: int = 0
    bonus_points: int = 0
    winner_used_special_bonus: bool = False
    user_used_special_bonus: bool = False
    computer_used_special_bonus: bool = False
    debug_messages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ActiveTurnState:
    round_number: int | None = None
    branch: Branch | None = None
    attribute_name: str | None = None
    user_card: SportCard | None = None
    computer_card: SportCard | None = None
    resolution: RoundResolution | None = None

    def clear(self, round_number: int | None = None, branch: Branch | None = None) -> None:
        self.round_number = round_number
        self.branch = branch
        self.attribute_name = None
        self.user_card = None
        self.computer_card = None
        self.resolution = None


@dataclass(slots=True)
class MatchStatistics:
    round_history: list[RoundRecord] = field(default_factory=list)
    skipped_rounds: int = 0
    event_notes: list[str] = field(default_factory=list)

    def add_record(self, record: RoundRecord) -> None:
        self.round_history.append(record)

    def add_note(self, note: str) -> None:
        self.event_notes.append(note)

    def create_report(self, user: Player, computer: Player) -> str:
        lines = [
            "AKILLI SPORCU KART LIGI RAPORU",
            "=" * 38,
            f"Kullanici Skoru: {user.score}",
            f"Bilgisayar Skoru: {computer.score}",
            f"Kullanici Moral: {user.morale}",
            f"Bilgisayar Moral: {computer.morale}",
            f"Kullanici Tur Galibiyeti: {user.rounds_won}",
            f"Bilgisayar Tur Galibiyeti: {computer.rounds_won}",
            f"Beraberlik Sayisi: {user.draws}",
            f"Atlanan Tur Sayisi: {self.skipped_rounds}",
            "",
            "TUR OZETLERI",
        ]
        for record in self.round_history:
            lines.append(
                f"{record.round_number}. tur [{record.branch.value}] -> {record.explanation} "
                f"(Skor {record.user_score_after}:{record.computer_score_after})"
            )
        if self.event_notes:
            lines.extend(["", "EK NOTLAR"])
            lines.extend(self.event_notes[-5:])
        return "\n".join(lines)


class GameManager:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.data_loader = DataLoader()
        self.user = UserPlayer(player_id=1, player_name="Kullanici")
        self.computer = ComputerPlayer(player_id=2, player_name="Bilgisayar")
        self.feature_mode = FeatureMode.RANDOM
        self.round_number = 1
        self.branch_index = 0
        self.total_expected_rounds = 12
        self.statistics = MatchStatistics()
        self.loaded_cards: list[SportCard] = []
        self.finished = False
        self.active_turn_state = ActiveTurnState()

    def load_cards(self, file_path: str) -> list[SportCard]:
        self.loaded_cards = self.data_loader.load_cards(file_path)
        return self.loaded_cards

    def start_new_game(
        self,
        file_path: str,
        difficulty: Difficulty = Difficulty.MEDIUM,
        feature_mode: FeatureMode = FeatureMode.RANDOM,
    ) -> None:
        cards = self.load_cards(file_path)
        self.user = UserPlayer(player_id=1, player_name="Kullanici")
        self.computer = ComputerPlayer(player_id=2, player_name="Bilgisayar")
        self.feature_mode = feature_mode
        self.round_number = 1
        self.branch_index = 0
        self.total_expected_rounds = 12
        self.statistics = MatchStatistics()
        self.finished = False
        self.clear_active_turn_state()
        self._configure_strategy(difficulty)
        self._distribute_cards(cards)
        self._advance_until_playable_branch()

    def _configure_strategy(self, difficulty: Difficulty) -> None:
        self.computer.strategy = EasyStrategy(self.rng) if difficulty == Difficulty.EASY else MediumStrategy()

    def _distribute_cards(self, cards: list[SportCard]) -> None:
        grouped = {branch: [] for branch in Branch}
        for card in cards:
            card.used_in_league = False
            card.usage_count = 0
            card.win_count = 0
            card.loss_count = 0
            card.draw_count = 0
            card.level = 1
            card.experience_points = 0
            card.just_leveled_up = False
            card.energy = card.max_energy
            card.special_ability.reset()
            grouped[card.branch].append(card)

        self.user.cards.clear()
        self.computer.cards.clear()
        for branch in Branch:
            branch_cards = grouped[branch]
            self.rng.shuffle(branch_cards)
            self.user.cards.extend(branch_cards[:4])
            self.computer.cards.extend(branch_cards[4:])

    def current_branch(self) -> Branch:
        return BRANCH_SEQUENCE[self.branch_index % len(BRANCH_SEQUENCE)]

    def branch_features(self, branch: Branch | None = None) -> list[str]:
        return BRANCH_FEATURES[branch or self.current_branch()]

    def create_game_state(self) -> dict[str, object]:
        return {
            "round_number": self.round_number,
            "total_expected_rounds": self.total_expected_rounds,
            "opponent": self.user,
            "current_branch": self.current_branch(),
        }

    def clear_active_turn_state(self) -> None:
        branch = None
        if not self.finished:
            branch = self.current_branch()
        self.active_turn_state.clear(self.round_number, branch)

    def play_round(self, user_card_id: int, selected_attribute: str | None = None) -> RoundResolution:
        if self.finished:
            raise ValueError("Oyun zaten bitti.")

        branch = self.current_branch()
        self._begin_turn_state(branch)
        user_branch_cards = self.user.available_cards(branch)
        computer_branch_cards = self.computer.available_cards(branch)

        if not user_branch_cards and not computer_branch_cards:
            self.statistics.skipped_rounds += 1
            resolution = RoundResolution(
                round_number=self.round_number,
                branch=branch,
                explanation=f"{branch.value} turu otomatik atlandi; iki tarafta da oynanabilir kart yok.",
                outcome_type="skip",
            )
            self._finalize_active_turn_state(resolution)
            self._record_resolution(resolution)
            self._move_next_round()
            self._advance_until_playable_branch()
            return resolution

        if not user_branch_cards or not computer_branch_cards:
            winner = self.computer if not user_branch_cards else self.user
            loser = self.user if winner is self.computer else self.computer
            winner.register_round_result("win", branch)
            loser.register_round_result("loss", branch)
            winner.score += FORFEIT_WIN_POINTS
            resolution = RoundResolution(
                round_number=self.round_number,
                branch=branch,
                winner=winner,
                loser=loser,
                outcome_type="forfeit",
                score_awarded=FORFEIT_WIN_POINTS,
                explanation=f"{loser.player_name} tarafinda {branch.value} karti kalmadigi icin "
                f"{winner.player_name} hukmen kazandi.",
            )
            self._finalize_active_turn_state(resolution)
            self._record_resolution(resolution)
            self._move_next_round()
            self._advance_until_playable_branch()
            return resolution

        user_card = self.user.select_card(branch, card_id=user_card_id)
        self._validate_selected_card(user_card, branch, "Kullanici")

        computer_card = self.computer.select_card(branch, game_state=self.create_game_state())
        self._validate_selected_card(computer_card, branch, "Bilgisayar")
        self._bind_active_turn_cards(branch, user_card, computer_card)

        attribute_name = self._determine_attribute(branch, selected_attribute)
        self.active_turn_state.attribute_name = attribute_name
        resolution = self._resolve_duel(branch, attribute_name, user_card, computer_card)
        self._finalize_active_turn_state(resolution)
        self._apply_resolution_effects(resolution)
        self._record_resolution(resolution)
        self._move_next_round()
        self._advance_until_playable_branch()
        return resolution

    def _begin_turn_state(self, branch: Branch) -> None:
        self.active_turn_state.clear(self.round_number, branch)

    def _validate_selected_card(
        self,
        card: SportCard | None,
        branch: Branch,
        owner_label: str,
    ) -> SportCard:
        if card is None:
            raise ValueError(f"{owner_label} bu tur icin uygun kart secemedi.")
        if card.branch != branch:
            raise ValueError(
                f"{owner_label} icin secilen kartin bransi uyusmuyor: "
                f"{card.card_id} - {card.player_name} ({card.branch.value})"
            )
        if not card.can_play():
            raise ValueError(
                f"{owner_label} icin secilen kart oynanamaz durumda: "
                f"{card.card_id} - {card.player_name}"
            )
        return card

    def _bind_active_turn_cards(
        self,
        branch: Branch,
        user_card: SportCard,
        computer_card: SportCard,
    ) -> None:
        self.active_turn_state.branch = branch
        self.active_turn_state.user_card = self._validate_selected_card(user_card, branch, "Kullanici")
        self.active_turn_state.computer_card = self._validate_selected_card(computer_card, branch, "Bilgisayar")

    def _turn_debug_messages(
        self,
        branch: Branch,
        user_card: SportCard | None,
        computer_card: SportCard | None,
    ) -> list[str]:
        messages = [f"DEBUG [{self.round_number}. tur] brans={branch.value}"]
        messages.append(
            "DEBUG kullanici karti="
            + (
                f"id={user_card.card_id}, ad={user_card.player_name}, brans={user_card.branch.value}"
                if user_card is not None
                else "yok"
            )
        )
        messages.append(
            "DEBUG bilgisayar karti="
            + (
                f"id={computer_card.card_id}, ad={computer_card.player_name}, brans={computer_card.branch.value}"
                if computer_card is not None
                else "yok"
            )
        )
        return messages

    def _finalize_active_turn_state(self, resolution: RoundResolution) -> None:
        self.active_turn_state.round_number = resolution.round_number
        self.active_turn_state.branch = resolution.branch
        self.active_turn_state.attribute_name = resolution.attribute_name
        self.active_turn_state.user_card = resolution.user_card
        self.active_turn_state.computer_card = resolution.computer_card
        self.active_turn_state.resolution = resolution
        self._validate_active_turn_state()
        resolution.debug_messages = self._turn_debug_messages(
            resolution.branch,
            resolution.user_card,
            resolution.computer_card,
        ) + resolution.debug_messages

    def _validate_active_turn_state(self) -> None:
        branch = self.active_turn_state.branch
        if branch is None:
            return
        user_card = self.active_turn_state.user_card
        computer_card = self.active_turn_state.computer_card
        if user_card is not None and user_card.branch != branch:
            raise ValueError(
                f"active_user_card.branch == current_branch kuralı ihlal edildi: "
                f"{user_card.card_id} -> {user_card.branch.value}, beklenen {branch.value}"
            )
        if computer_card is not None and computer_card.branch != branch:
            raise ValueError(
                f"active_computer_card.branch == current_branch kuralı ihlal edildi: "
                f"{computer_card.card_id} -> {computer_card.branch.value}, beklenen {branch.value}"
            )
        resolution = self.active_turn_state.resolution
        if resolution is None:
            return
        if resolution.branch != branch:
            raise ValueError("Aktif tur state ile resolution branch bilgisi uyusmuyor.")
        if user_card is not None and resolution.user_card is not user_card:
            raise ValueError("UI/engine senkronizasyonu bozuk: kullanici kart referansi degisti.")
        if computer_card is not None and resolution.computer_card is not computer_card:
            raise ValueError("UI/engine senkronizasyonu bozuk: bilgisayar kart referansi degisti.")

    def _determine_attribute(self, branch: Branch, selected_attribute: str | None) -> str:
        attributes = BRANCH_FEATURES[branch]
        if self.feature_mode == FeatureMode.USER_CHOICE:
            if selected_attribute not in attributes:
                raise ValueError("Bu tur icin gecersiz ozellik secildi.")
            return selected_attribute
        return self.rng.choice(attributes)

    def _backup_attribute_order(self, branch: Branch, primary_attribute: str) -> list[str]:
        return [attribute for attribute in BRANCH_FEATURES[branch] if attribute != primary_attribute]

    def _breakdown_for(
        self,
        player: Player,
        opponent: Player,
        card: SportCard,
        opponent_card: SportCard,
        attribute_name: str,
    ) -> PerformanceBreakdown:
        return card.calculate_performance(
            attribute_name=attribute_name,
            player_morale=player.morale,
            round_number=self.round_number,
            total_expected_rounds=self.total_expected_rounds,
            owner_player_name=player.player_name,
            owner_branch_card_count=player.branch_card_count(card.branch),
            same_team_branch_support=player.same_team_branch_support(card),
            opponent_attribute_base=opponent_card.base_attributes()[attribute_name],
        )

    def _resolve_duel(
        self,
        branch: Branch,
        attribute_name: str,
        user_card: SportCard,
        computer_card: SportCard,
    ) -> RoundResolution:
        user_breakdown = self._breakdown_for(self.user, self.computer, user_card, computer_card, attribute_name)
        computer_breakdown = self._breakdown_for(
            self.computer, self.user, computer_card, user_card, attribute_name
        )

        user_context = user_card.build_ability_context(
            attribute_name=attribute_name,
            round_number=self.round_number,
            total_expected_rounds=self.total_expected_rounds,
            owner_player_name=self.user.player_name,
            owner_branch_card_count=self.user.branch_card_count(branch),
            same_team_branch_support=self.user.same_team_branch_support(user_card),
            opponent_attribute_base=computer_card.base_attributes()[attribute_name],
        )
        computer_context = computer_card.build_ability_context(
            attribute_name=attribute_name,
            round_number=self.round_number,
            total_expected_rounds=self.total_expected_rounds,
            owner_player_name=self.computer.player_name,
            owner_branch_card_count=self.computer.branch_card_count(branch),
            same_team_branch_support=self.computer.same_team_branch_support(computer_card),
            opponent_attribute_base=user_card.base_attributes()[attribute_name],
        )

        adjusted_user_ability = computer_card.special_ability.modify_opponent_bonus(
            user_breakdown.ability_bonus, computer_context
        )
        adjusted_computer_ability = user_card.special_ability.modify_opponent_bonus(
            computer_breakdown.ability_bonus, user_context
        )
        user_breakdown.total += adjusted_user_ability - user_breakdown.ability_bonus
        computer_breakdown.total += adjusted_computer_ability - computer_breakdown.ability_bonus
        user_breakdown.ability_bonus = adjusted_user_ability
        computer_breakdown.ability_bonus = adjusted_computer_ability

        resolution = RoundResolution(
            round_number=self.round_number,
            branch=branch,
            attribute_name=attribute_name,
            user_card=user_card,
            computer_card=computer_card,
            user_breakdown=user_breakdown,
            computer_breakdown=computer_breakdown,
            user_used_special_bonus=user_breakdown.ability_bonus > 0,
            computer_used_special_bonus=computer_breakdown.ability_bonus > 0,
        )

        if user_breakdown.total != computer_breakdown.total:
            if user_breakdown.total > computer_breakdown.total:
                self._fill_resolution_win(
                    resolution, self.user, self.computer, user_card, computer_card, user_breakdown, computer_breakdown, "normal"
                )
            else:
                self._fill_resolution_win(
                    resolution, self.computer, self.user, computer_card, user_card, computer_breakdown, user_breakdown, "normal"
                )
            return resolution

        for backup_attribute in self._backup_attribute_order(branch, attribute_name):
            backup_user = self._breakdown_for(
                self.user, self.computer, user_card, computer_card, backup_attribute
            )
            backup_computer = self._breakdown_for(
                self.computer, self.user, computer_card, user_card, backup_attribute
            )
            if backup_user.total != backup_computer.total:
                if backup_user.total > backup_computer.total:
                    self._fill_resolution_win(
                        resolution, self.user, self.computer, user_card, computer_card, backup_user, backup_computer, "backup"
                    )
                else:
                    self._fill_resolution_win(
                        resolution, self.computer, self.user, computer_card, user_card, backup_computer, backup_user, "backup"
                    )
                resolution.explanation = (
                    f"Ana ozellik esitti, {FEATURE_LABELS[backup_attribute]} yedek karsilastirmasi sonucu "
                    f"{resolution.winner.player_name} kazandi."
                )
                return resolution

        if user_breakdown.ability_bonus != computer_breakdown.ability_bonus:
            if user_breakdown.ability_bonus > computer_breakdown.ability_bonus:
                self._fill_resolution_win(
                    resolution, self.user, self.computer, user_card, computer_card, user_breakdown, computer_breakdown, "special"
                )
            else:
                self._fill_resolution_win(
                    resolution, self.computer, self.user, computer_card, user_card, computer_breakdown, user_breakdown, "special"
                )
            resolution.explanation = (
                f"Tum ozellikler esit kaldigi icin ozel yetenek etkisi belirleyici oldu ve "
                f"{resolution.winner.player_name} kazandi."
            )
            return resolution

        if user_card.durability != computer_card.durability:
            if user_card.durability > computer_card.durability:
                self._fill_resolution_win(
                    resolution, self.user, self.computer, user_card, computer_card, user_breakdown, computer_breakdown, "durability"
                )
            else:
                self._fill_resolution_win(
                    resolution, self.computer, self.user, computer_card, user_card, computer_breakdown, user_breakdown, "durability"
                )
            resolution.explanation = "Esitlik dayaniklilik ile bozuldu."
            return resolution

        if user_card.energy != computer_card.energy:
            if user_card.energy > computer_card.energy:
                self._fill_resolution_win(
                    resolution, self.user, self.computer, user_card, computer_card, user_breakdown, computer_breakdown, "energy"
                )
            else:
                self._fill_resolution_win(
                    resolution, self.computer, self.user, computer_card, user_card, computer_breakdown, user_breakdown, "energy"
                )
            resolution.explanation = "Esitlik enerji degeri ile bozuldu."
            return resolution

        if user_card.level != computer_card.level:
            if user_card.level > computer_card.level:
                self._fill_resolution_win(
                    resolution, self.user, self.computer, user_card, computer_card, user_breakdown, computer_breakdown, "level"
                )
            else:
                self._fill_resolution_win(
                    resolution, self.computer, self.user, computer_card, user_card, computer_breakdown, user_breakdown, "level"
                )
            resolution.explanation = "Esitlik seviye ile bozuldu."
            return resolution

        resolution.outcome_type = "draw"
        resolution.explanation = (
            f"{FEATURE_LABELS[attribute_name]} turu tamamen esit bitti. Kartlar elde kaldi ve sadece dusuk enerji kaybi uygulandi."
        )
        return resolution

    def _fill_resolution_win(
        self,
        resolution: RoundResolution,
        winner: Player,
        loser: Player,
        winner_card: SportCard,
        loser_card: SportCard,
        winner_breakdown: PerformanceBreakdown,
        loser_breakdown: PerformanceBreakdown,
        outcome_type: str,
    ) -> None:
        resolution.winner = winner
        resolution.loser = loser
        resolution.winner_card = winner_card
        resolution.loser_card = loser_card
        if winner is self.user:
            resolution.user_breakdown = winner_breakdown
            resolution.computer_breakdown = loser_breakdown
        else:
            resolution.user_breakdown = loser_breakdown
            resolution.computer_breakdown = winner_breakdown
        resolution.outcome_type = outcome_type

    def _apply_resolution_effects(self, resolution: RoundResolution) -> None:
        if resolution.outcome_type == "draw":
            assert resolution.user_card is not None
            assert resolution.computer_card is not None
            resolution.user_card.register_usage(decisive=False)
            resolution.computer_card.register_usage(decisive=False)
            resolution.user_card.register_result("draw")
            resolution.computer_card.register_result("draw")
            resolution.user_card.apply_energy_change(3)
            resolution.computer_card.apply_energy_change(3)
            if resolution.user_used_special_bonus:
                resolution.user_card.apply_energy_change(5)
            if resolution.computer_used_special_bonus:
                resolution.computer_card.apply_energy_change(5)
            self.user.register_round_result("draw", resolution.branch)
            self.computer.register_round_result("draw", resolution.branch)
            return

        assert resolution.winner is not None
        assert resolution.loser is not None
        assert resolution.winner_card is not None
        assert resolution.loser_card is not None

        resolution.winner.register_round_result("win", resolution.branch)
        resolution.loser.register_round_result("loss", resolution.branch)
        resolution.winner_card.register_usage(decisive=True)
        resolution.loser_card.register_usage(decisive=True)
        resolution.winner_card.register_result("win")
        resolution.loser_card.register_result("loss")

        winner_ability_bonus = (
            resolution.user_breakdown.ability_bonus
            if resolution.winner is self.user
            else resolution.computer_breakdown.ability_bonus
        )
        resolution.winner_used_special_bonus = winner_ability_bonus > 0

        base_points = (
            FORFEIT_WIN_POINTS
            if resolution.outcome_type == "forfeit"
            else SPECIAL_ABILITY_WIN_POINTS
            if resolution.winner_used_special_bonus
            else NORMAL_WIN_POINTS
        )
        bonus_points = 0
        if resolution.winner.win_streak == 3:
            bonus_points += THREE_STREAK_BONUS
        if resolution.winner.win_streak == 5:
            bonus_points += FIVE_STREAK_BONUS
        if resolution.winner_card.energy < 30:
            bonus_points += LOW_ENERGY_BONUS_POINTS
        if resolution.winner_card.consume_level_up_bonus():
            bonus_points += LEVEL_UP_FIRST_WIN_BONUS
        if resolution.winner_card.ability_name == "Clutch Player" and self.round_number >= 10:
            bonus_points += CLUTCH_WIN_BONUS

        resolution.score_awarded = base_points
        resolution.bonus_points = bonus_points
        resolution.winner.score += base_points + bonus_points
        if resolution.winner_used_special_bonus:
            resolution.winner.special_ability_wins += 1

        resolution.winner_card.apply_energy_change(5)
        if resolution.user_used_special_bonus:
            resolution.user_card.apply_energy_change(5)
        if resolution.computer_used_special_bonus:
            resolution.computer_card.apply_energy_change(5)
        resolution.loser_card.apply_energy_change(10)

        resolution.winner_card.level_up_if_needed()
        resolution.loser_card.level_up_if_needed()

        if not resolution.explanation:
            resolution.explanation = (
                f"{resolution.winner.player_name}, {FEATURE_LABELS[resolution.attribute_name]} "
                f"degerinde ustun gelerek turu kazandi."
            )

    def _record_resolution(self, resolution: RoundResolution) -> None:
        winner_name = resolution.winner.player_name if resolution.winner else None
        self.statistics.add_record(
            RoundRecord(
                round_number=resolution.round_number,
                branch=resolution.branch,
                attribute_name=resolution.attribute_name,
                user_card_name=resolution.user_card.label() if resolution.user_card else None,
                computer_card_name=resolution.computer_card.label() if resolution.computer_card else None,
                winner_name=winner_name,
                outcome_type=resolution.outcome_type,
                user_score_after=self.user.score,
                computer_score_after=self.computer.score,
                explanation=resolution.explanation,
            )
        )

    def _move_next_round(self) -> None:
        self.round_number += 1
        self.branch_index = (self.branch_index + 1) % len(BRANCH_SEQUENCE)

    def _advance_until_playable_branch(self) -> None:
        for _ in range(len(BRANCH_SEQUENCE)):
            branch = self.current_branch()
            if self.user.available_cards(branch) or self.computer.available_cards(branch):
                return
            self.statistics.skipped_rounds += 1
            self.statistics.add_record(
                RoundRecord(
                    round_number=self.round_number,
                    branch=branch,
                    attribute_name=None,
                    user_card_name=None,
                    computer_card_name=None,
                    winner_name=None,
                    outcome_type="skip",
                    user_score_after=self.user.score,
                    computer_score_after=self.computer.score,
                    explanation=f"{branch.value} turu otomatik gecildi.",
                )
            )
            self._move_next_round()
        if not self.user.available_cards() and not self.computer.available_cards():
            self.finished = True

    def winner_summary(self) -> str:
        if not self.finished and (self.user.available_cards() or self.computer.available_cards()):
            return "Oyun devam ediyor."

        self.finished = True
        if self.user.score != self.computer.score:
            winner = self.user if self.user.score > self.computer.score else self.computer
            return f"Kazanan: {winner.player_name} (puan ustunlugu)"

        tie_checks = [
            ("tur galibiyeti", self.user.rounds_won, self.computer.rounds_won),
            ("galibiyet serisi sayisi", self.user.series_count, self.computer.series_count),
            (
                "kalan toplam enerji",
                sum(card.energy for card in self.user.available_cards()),
                sum(card.energy for card in self.computer.available_cards()),
            ),
            (
                "en yuksek seviyeli kart sayisi",
                sum(1 for card in self.user.cards if card.level == 3),
                sum(1 for card in self.computer.cards if card.level == 3),
            ),
            (
                "ozel yetenekli galibiyet",
                self.user.special_ability_wins,
                self.computer.special_ability_wins,
            ),
            ("beraberlik azligi", -self.user.draws, -self.computer.draws),
        ]

        for label, user_value, computer_value in tie_checks:
            if user_value != computer_value:
                winner = self.user if user_value > computer_value else self.computer
                return f"Kazanan: {winner.player_name} ({label} kriteri)"

        return "Mac berabere bitti."

    def report_text(self) -> str:
        return self.statistics.create_report(self.user, self.computer)

    def match_summary_text(self) -> str:
        lines = [
            self.winner_summary(),
            "",
            f"Kullanici skor: {self.user.score}",
            f"Bilgisayar skor: {self.computer.score}",
            f"Kullanici moral: {self.user.morale}",
            f"Bilgisayar moral: {self.computer.morale}",
            f"Kullanici tur galibiyeti: {self.user.rounds_won}",
            f"Bilgisayar tur galibiyeti: {self.computer.rounds_won}",
            f"Beraberlik: {self.user.draws}",
            f"Atlanan tur: {self.statistics.skipped_rounds}",
            "",
            "Son turlar:",
        ]
        for record in self.statistics.round_history[-5:]:
            lines.append(
                f"{record.round_number}. tur {record.branch.value}: {record.explanation}"
            )
        if self.statistics.event_notes:
            lines.extend(["", "Ek notlar:"])
            lines.extend(self.statistics.event_notes[-3:])
        return "\n".join(lines)


MacIstatistik = MatchStatistics
OyunYonetici = GameManager
