from __future__ import annotations

import unittest
from pathlib import Path
import random
from tempfile import NamedTemporaryFile

from smart_league.constants import Branch, Difficulty, FeatureMode
from smart_league.data_loader import DataLoader, DataValidationError
from smart_league.game import GameManager
from smart_league.abilities import AbilityContext, create_ability
from smart_league.models import ComputerPlayer, Footballer
from smart_league.strategies import EasyStrategy, KartSecmeStratejisi, KolayStrateji, MediumStrategy, OrtaStrateji
from smart_league import (
    Basketbolcu,
    Bilgisayar,
    Futbolcu,
    Kullanici,
    MacIstatistik,
    OyunYonetici,
    Oyuncu,
    Sporcu,
    VeriOkuyucu,
    Voleybolcu,
)


ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "sporcular.csv"


class CoreGameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = DataLoader()
        self.cards = self.loader.load_cards(DATA_FILE)

    def test_loader_reads_24_cards(self) -> None:
        self.assertEqual(len(self.cards), 24)
        counts = {branch: 0 for branch in Branch}
        for card in self.cards:
            counts[card.branch] += 1
        self.assertEqual(counts[Branch.FOOTBALL], 8)
        self.assertEqual(counts[Branch.BASKETBALL], 8)
        self.assertEqual(counts[Branch.VOLLEYBALL], 8)
        self.assertTrue(all(card.special_ability_coefficient > 0 for card in self.cards))

    def test_loader_accepts_txt_extension(self) -> None:
        with DATA_FILE.open("r", encoding="utf-8") as source:
            content = source.read()
        with NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        try:
            cards = self.loader.load_cards(temp_path)
            self.assertEqual(len(cards), 24)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_loader_uses_default_ability_coefficient_when_column_missing(self) -> None:
        content = "\n".join(
            [
                "tur,sporcu_adi,takim_adi,brans,ozellik_a,ozellik_b,ozellik_c,dayaniklilik,enerji,ozel_yetenek",
                "futbolcu,Test Oyuncu,Test Takim,Futbol,80,81,82,90,100,Legend",
                "futbolcu,Test Oyuncu 2,Test Takim,Futbol,80,81,82,90,100,Yok",
                "futbolcu,Test Oyuncu 3,Test Takim,Futbol,80,81,82,90,100,Yok",
                "futbolcu,Test Oyuncu 4,Test Takim,Futbol,80,81,82,90,100,Yok",
                "futbolcu,Test Oyuncu 5,Test Takim,Futbol,80,81,82,90,100,Yok",
                "futbolcu,Test Oyuncu 6,Test Takim,Futbol,80,81,82,90,100,Yok",
                "futbolcu,Test Oyuncu 7,Test Takim,Futbol,80,81,82,90,100,Yok",
                "futbolcu,Test Oyuncu 8,Test Takim,Futbol,80,81,82,90,100,Yok",
                "basketbolcu,B1,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B2,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B3,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B4,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B5,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B6,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B7,Takim,Basketbol,80,81,82,90,100,Yok",
                "basketbolcu,B8,Takim,Basketbol,80,81,82,90,100,Yok",
                "voleybolcu,V1,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V2,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V3,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V4,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V5,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V6,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V7,Takim,Voleybol,80,81,82,90,100,Yok",
                "voleybolcu,V8,Takim,Voleybol,80,81,82,90,100,Yok",
            ]
        )
        with NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        try:
            cards = self.loader.load_cards(temp_path)
            self.assertTrue(all(card.special_ability_coefficient == 10 for card in cards))
        finally:
            temp_path.unlink(missing_ok=True)

    def test_loader_raises_error_for_missing_required_column(self) -> None:
        content = "\n".join(
            [
                "tur,sporcu_adi,takim_adi,brans,ozellik_a,ozellik_b,dayaniklilik,enerji,ozel_yetenek",
                "futbolcu,Test,Takim,Futbol,80,81,90,100,Yok",
            ]
        )
        with NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        try:
            with self.assertRaises(DataValidationError):
                self.loader.load_cards(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_distribution_keeps_four_cards_per_branch(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.MEDIUM, FeatureMode.RANDOM)
        for branch in Branch:
            self.assertEqual(len(game.user.available_cards(branch)), 4)
            self.assertEqual(len(game.computer.available_cards(branch)), 4)

    def test_medium_strategy_returns_valid_card(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.MEDIUM, FeatureMode.RANDOM)
        strategy = MediumStrategy()
        card = strategy.select_card(
            game.computer,
            Branch.FOOTBALL,
            {
                "round_number": 1,
                "total_expected_rounds": 12,
                "opponent": game.user,
            },
        )
        self.assertIsNotNone(card)
        self.assertEqual(card.branch, Branch.FOOTBALL)

    def test_strategy_alias_classes_exist(self) -> None:
        self.assertTrue(issubclass(KartSecmeStratejisi, object))
        self.assertTrue(issubclass(KolayStrateji, EasyStrategy))
        self.assertTrue(issubclass(OrtaStrateji, MediumStrategy))

    def test_turkish_class_aliases_exist(self) -> None:
        self.assertIs(Sporcu, Footballer.__mro__[1])
        self.assertIs(Futbolcu, Footballer)
        self.assertIs(Basketbolcu.__name__, "Basketballer")
        self.assertIs(Voleybolcu.__name__, "Volleyballer")
        self.assertIs(Kullanici.__name__, "UserPlayer")
        self.assertIs(Bilgisayar.__name__, "ComputerPlayer")
        self.assertIs(OyunYonetici.__name__, "GameManager")
        self.assertIs(VeriOkuyucu.__name__, "DataLoader")
        self.assertIs(MacIstatistik.__name__, "MatchStatistics")

    def test_easy_strategy_selects_random_valid_branch_card(self) -> None:
        computer = ComputerPlayer(player_id=2, player_name="Bilgisayar")
        first = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        second = self._make_footballer(
            card_id=2,
            penalti=81,
            serbest_vurus=81,
            kaleci_karsi_karsiya=81,
        )
        computer.cards = [first, second]
        chosen_sets = set()
        for seed in range(8):
            strategy = EasyStrategy(random.Random(seed))
            card = strategy.select_card(computer, Branch.FOOTBALL, {})
            self.assertIn(card, [first, second])
            chosen_sets.add(card.card_id)
        self.assertEqual(chosen_sets, {1, 2})

    def test_medium_strategy_selects_highest_average_current_performance(self) -> None:
        computer = ComputerPlayer(player_id=2, player_name="Bilgisayar")
        computer.morale = 60
        user_opponent = GameManager().user
        strong = self._make_footballer(
            card_id=1,
            penalti=92,
            serbest_vurus=91,
            kaleci_karsi_karsiya=90,
            energy=90,
        )
        weak = self._make_footballer(
            card_id=2,
            penalti=70,
            serbest_vurus=71,
            kaleci_karsi_karsiya=72,
            energy=90,
        )
        opponent_card = self._make_footballer(
            card_id=3,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            energy=90,
        )
        computer.cards = [strong, weak]
        user_opponent.cards = [opponent_card]
        strategy = MediumStrategy()
        card = strategy.select_card(
            computer,
            Branch.FOOTBALL,
            {
                "round_number": 1,
                "total_expected_rounds": 12,
                "opponent": user_opponent,
            },
        )
        self.assertEqual(card, strong)

    def test_play_round_updates_history(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        user_card = game.user.available_cards(game.current_branch())[0]
        attribute = game.branch_features(game.current_branch())[0]
        resolution = game.play_round(user_card.card_id, attribute)
        self.assertGreaterEqual(len(game.statistics.round_history), 1)
        self.assertEqual(resolution.branch, Branch.FOOTBALL)
        self.assertIn(
            resolution.outcome_type,
            {"normal", "backup", "special", "durability", "energy", "level", "draw"},
        )

    def test_play_round_keeps_single_active_turn_source_of_truth(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        user_card = game.user.available_cards(game.current_branch())[0]
        attribute = game.branch_features(game.current_branch())[0]

        resolution = game.play_round(user_card.card_id, attribute)

        self.assertIs(game.active_turn_state.resolution, resolution)
        self.assertIs(game.active_turn_state.user_card, resolution.user_card)
        self.assertIs(game.active_turn_state.computer_card, resolution.computer_card)
        self.assertEqual(game.active_turn_state.branch, resolution.branch)
        self.assertEqual(game.active_turn_state.attribute_name, resolution.attribute_name)
        self.assertTrue(resolution.debug_messages)

    def test_play_round_rejects_wrong_branch_user_card(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        wrong_branch_card = game.user.available_cards(Branch.BASKETBALL)[0]

        with self.assertRaises(ValueError):
            game.play_round(wrong_branch_card.card_id, game.branch_features(Branch.FOOTBALL)[0])

    def test_branch_order_is_fixed(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        sequence = []
        for _ in range(6):
            sequence.append(game.current_branch())
            user_card = game.user.available_cards(game.current_branch())[0]
            attribute = game.branch_features(game.current_branch())[0]
            game.play_round(user_card.card_id, attribute)
        self.assertEqual(
            sequence,
            [
                Branch.FOOTBALL,
                Branch.BASKETBALL,
                Branch.VOLLEYBALL,
                Branch.FOOTBALL,
                Branch.BASKETBALL,
                Branch.VOLLEYBALL,
            ],
        )

    def test_forfeit_when_only_one_side_has_current_branch_card(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        football_cards = game.user.available_cards(Branch.FOOTBALL)
        self.assertTrue(football_cards)
        for card in football_cards:
            card.used_in_league = True
        resolution = game.play_round(-1, game.branch_features(Branch.FOOTBALL)[0])
        self.assertEqual(resolution.outcome_type, "forfeit")
        self.assertEqual(resolution.winner, game.computer)
        self.assertEqual(game.statistics.round_history[-1].outcome_type, "forfeit")

    def test_skip_when_both_sides_have_no_current_branch_card(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        for player in (game.user, game.computer):
            for card in player.available_cards(Branch.FOOTBALL):
                card.used_in_league = True
        resolution = game.play_round(-1, game.branch_features(Branch.FOOTBALL)[0])
        self.assertEqual(resolution.outcome_type, "skip")
        self.assertEqual(game.statistics.skipped_rounds, 1)

    def test_user_choice_mode_uses_selected_attribute(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        user_card = game.user.available_cards(Branch.FOOTBALL)[0]
        resolution = game.play_round(user_card.card_id, "serbest_vurus")
        self.assertEqual(resolution.attribute_name, "serbest_vurus")

    def test_random_mode_selects_valid_branch_attribute(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.RANDOM)
        user_card = game.user.available_cards(Branch.FOOTBALL)[0]
        resolution = game.play_round(user_card.card_id)
        self.assertIn(resolution.attribute_name, {"penalti", "serbest_vurus", "kaleci_karsi_karsiya"})

    def test_special_ability_coefficient_affects_performance_bonus(self) -> None:
        low_coeff = Footballer(
            card_id=1,
            player_name="Test One",
            team_name="Team",
            branch=Branch.FOOTBALL,
            durability=80,
            energy=90,
            max_energy=90,
            ability_name="Clutch Player",
            special_ability_coefficient=10,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        high_coeff = Footballer(
            card_id=2,
            player_name="Test Two",
            team_name="Team",
            branch=Branch.FOOTBALL,
            durability=80,
            energy=90,
            max_energy=90,
            ability_name="Clutch Player",
            special_ability_coefficient=12,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        low_breakdown = low_coeff.calculate_performance(
            "penalti", 60, 12, 12, "P1", 1, 0, 70
        )
        high_breakdown = high_coeff.calculate_performance(
            "penalti", 60, 12, 12, "P2", 1, 0, 70
        )
        self.assertGreater(high_breakdown.ability_bonus, low_breakdown.ability_bonus)

    def test_energy_penalty_thresholds_follow_spec(self) -> None:
        card = Footballer(
            card_id=1,
            player_name="Threshold Test",
            team_name="Team",
            branch=Branch.FOOTBALL,
            durability=80,
            energy=71,
            max_energy=100,
            penalti=100,
            serbest_vurus=90,
            kaleci_karsi_karsiya=80,
        )
        self.assertEqual(card.energy_penalty(100), 0)
        card.energy = 70
        self.assertEqual(card.energy_penalty(100), 10)
        card.energy = 40
        self.assertEqual(card.energy_penalty(100), 10)
        card.energy = 39
        self.assertEqual(card.energy_penalty(100), 20)
        card.energy = 0
        self.assertFalse(card.can_play())

    def test_morale_and_level_bonus_follow_spec(self) -> None:
        card = Footballer(
            card_id=1,
            player_name="Bonus Test",
            team_name="Team",
            branch=Branch.FOOTBALL,
            durability=80,
            energy=90,
            max_energy=90,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        self.assertEqual(card.morale_bonus(85), 5)
        self.assertEqual(card.morale_bonus(95), 10)
        self.assertEqual(card.morale_bonus(30), -5)
        self.assertEqual(card.level_bonus(), 0)
        card.level = 2
        self.assertEqual(card.level_bonus(), 5)
        card.level = 3
        self.assertEqual(card.level_bonus(), 10)

    def test_total_performance_formula_matches_spec(self) -> None:
        card = Footballer(
            card_id=1,
            player_name="Formula Test",
            team_name="Team",
            branch=Branch.FOOTBALL,
            durability=80,
            energy=60,
            max_energy=90,
            ability_name="Clutch Player",
            special_ability_coefficient=10,
            level=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        breakdown = card.calculate_performance(
            "penalti",
            85,
            12,
            12,
            "User",
            1,
            0,
            70,
        )
        self.assertEqual(breakdown.base_value, 80)
        self.assertEqual(breakdown.moral_bonus, 5)
        self.assertEqual(breakdown.ability_bonus, 10)
        self.assertEqual(breakdown.energy_penalty, 8)
        self.assertEqual(breakdown.level_bonus, 5)
        self.assertEqual(breakdown.energy_at_calculation, 60)
        self.assertEqual(breakdown.total, 92)

    def test_energy_examples_match_document(self) -> None:
        def build_card(energy: int) -> Footballer:
            return Footballer(
                card_id=1,
                player_name="Example Test",
                team_name="Team",
                branch=Branch.FOOTBALL,
                durability=80,
                energy=energy,
                max_energy=100,
                ability_name="Clutch Player",
                special_ability_coefficient=10,
                level=2,
                penalti=80,
                serbest_vurus=80,
                kaleci_karsi_karsiya=80,
            )

        high_energy = build_card(85).calculate_performance("penalti", 85, 12, 12, "User", 1, 0, 70)
        mid_energy = build_card(60).calculate_performance("penalti", 85, 12, 12, "User", 1, 0, 70)
        low_energy = build_card(30).calculate_performance("penalti", 85, 12, 12, "User", 1, 0, 70)

        self.assertEqual(high_energy.energy_penalty, 0)
        self.assertEqual(high_energy.total, 100)
        self.assertEqual(mid_energy.energy_penalty, 8)
        self.assertEqual(mid_energy.total, 92)
        self.assertEqual(low_energy.energy_penalty, 16)
        self.assertEqual(low_energy.total, 84)

    def _make_footballer(
        self,
        *,
        card_id: int,
        penalti: int,
        serbest_vurus: int,
        kaleci_karsi_karsiya: int,
        durability: int = 80,
        energy: int = 90,
        level: int = 1,
        ability_name: str = "Yok",
    ) -> Footballer:
        return Footballer(
            card_id=card_id,
            player_name=f"Player {card_id}",
            team_name="Team",
            branch=Branch.FOOTBALL,
            durability=durability,
            energy=energy,
            max_energy=energy,
            level=level,
            ability_name=ability_name,
            special_ability_coefficient=10,
            penalti=penalti,
            serbest_vurus=serbest_vurus,
            kaleci_karsi_karsiya=kaleci_karsi_karsiya,
        )

    def _resolve_custom_duel(
        self,
        user_card: Footballer,
        computer_card: Footballer,
        attribute_name: str,
        *,
        round_number: int = 1,
        total_expected_rounds: int = 12,
    ):
        game = GameManager()
        game.round_number = round_number
        game.total_expected_rounds = total_expected_rounds
        game.user.cards = [user_card]
        game.computer.cards = [computer_card]
        return game, game._resolve_duel(Branch.FOOTBALL, attribute_name, user_card, computer_card)

    def test_backup_attribute_comparison_breaks_tie(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=90,
            kaleci_karsi_karsiya=70,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=85,
            kaleci_karsi_karsiya=95,
        )
        _, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        self.assertEqual(resolution.outcome_type, "backup")
        self.assertEqual(resolution.winner.player_name, "Kullanici")

    def test_special_ability_stage_breaks_full_tie(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=70,
            serbest_vurus=70,
            kaleci_karsi_karsiya=70,
            ability_name="Clutch Player",
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        _, resolution = self._resolve_custom_duel(
            user_card,
            computer_card,
            "penalti",
            round_number=12,
            total_expected_rounds=12,
        )
        self.assertEqual(resolution.outcome_type, "special")
        self.assertEqual(resolution.winner.player_name, "Kullanici")

    def test_durability_stage_breaks_tie(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=90,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
        )
        _, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        self.assertEqual(resolution.outcome_type, "durability")
        self.assertEqual(resolution.winner.player_name, "Kullanici")

    def test_energy_stage_breaks_tie(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
            energy=95,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
            energy=85,
        )
        _, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        self.assertEqual(resolution.outcome_type, "energy")
        self.assertEqual(resolution.winner.player_name, "Kullanici")

    def test_level_stage_breaks_tie_after_equal_totals(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=75,
            serbest_vurus=75,
            kaleci_karsi_karsiya=75,
            level=2,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            level=1,
        )
        _, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        self.assertEqual(resolution.outcome_type, "level")
        self.assertEqual(resolution.winner.player_name, "Kullanici")

    def test_draw_keeps_cards_in_hand_and_only_reduces_energy(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
            energy=90,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
            energy=90,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.outcome_type, "draw")
        self.assertEqual(game.user.score, 0)
        self.assertEqual(game.computer.score, 0)
        self.assertFalse(user_card.used_in_league)
        self.assertFalse(computer_card.used_in_league)
        self.assertEqual(user_card.energy, 87)
        self.assertEqual(computer_card.energy, 87)

    def test_normal_win_gives_10_points(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.score_awarded, 10)
        self.assertEqual(resolution.bonus_points, 0)
        self.assertEqual(game.user.score, 10)

    def test_special_ability_win_gives_15_points(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=70,
            serbest_vurus=70,
            kaleci_karsi_karsiya=70,
            ability_name="Clutch Player",
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        game, resolution = self._resolve_custom_duel(
            user_card,
            computer_card,
            "penalti",
            round_number=12,
            total_expected_rounds=12,
        )
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.outcome_type, "special")
        self.assertEqual(resolution.score_awarded, 15)

    def test_forfeit_win_gives_8_points(self) -> None:
        game = GameManager()
        game.start_new_game(str(DATA_FILE), Difficulty.EASY, FeatureMode.USER_CHOICE)
        for card in game.user.available_cards(Branch.FOOTBALL):
            card.used_in_league = True
        resolution = game.play_round(-1, game.branch_features(Branch.FOOTBALL)[0])
        self.assertEqual(resolution.outcome_type, "forfeit")
        self.assertEqual(resolution.score_awarded, 8)
        self.assertEqual(game.computer.score, 8)

    def test_draw_gives_zero_points(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
            energy=90,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=80,
            energy=90,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.outcome_type, "draw")
        self.assertEqual(resolution.score_awarded, 0)
        self.assertEqual(game.user.score, 0)
        self.assertEqual(game.computer.score, 0)

    def test_three_win_streak_adds_10_bonus(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        game.user.win_streak = 2
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.score_awarded, 10)
        self.assertEqual(resolution.bonus_points, 10)
        self.assertEqual(game.user.score, 20)

    def test_five_win_streak_adds_20_bonus(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        game.user.win_streak = 4
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.score_awarded, 10)
        self.assertEqual(resolution.bonus_points, 20)
        self.assertEqual(game.user.score, 30)

    def test_low_energy_win_adds_5_bonus(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            energy=29,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=60,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            energy=90,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.score_awarded, 10)
        self.assertEqual(resolution.bonus_points, 5)

    def test_post_level_up_first_win_adds_5_bonus(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        game, resolution = self._resolve_custom_duel(user_card, computer_card, "penalti")
        user_card.just_leveled_up = True
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.score_awarded, 10)
        self.assertEqual(resolution.bonus_points, 5)
        self.assertFalse(user_card.just_leveled_up)

    def test_clutch_player_win_in_last_three_rounds_adds_5_bonus(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            ability_name="Clutch Player",
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        game, resolution = self._resolve_custom_duel(
            user_card,
            computer_card,
            "penalti",
            round_number=10,
            total_expected_rounds=12,
        )
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.score_awarded, 15)
        self.assertEqual(resolution.bonus_points, 5)

    def test_losing_card_that_used_special_bonus_loses_extra_5_energy(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=90,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            energy=90,
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=70,
            serbest_vurus=70,
            kaleci_karsi_karsiya=70,
            energy=90,
            ability_name="Clutch Player",
        )
        game, resolution = self._resolve_custom_duel(
            user_card,
            computer_card,
            "penalti",
            round_number=12,
            total_expected_rounds=12,
        )
        game._apply_resolution_effects(resolution)
        self.assertEqual(user_card.energy, 85)
        self.assertEqual(computer_card.energy, 75)

    def test_draw_with_special_bonus_applies_extra_5_energy_loss(self) -> None:
        user_card = self._make_footballer(
            card_id=1,
            penalti=70,
            serbest_vurus=70,
            kaleci_karsi_karsiya=70,
            energy=90,
            ability_name="Clutch Player",
        )
        computer_card = self._make_footballer(
            card_id=2,
            penalti=70,
            serbest_vurus=70,
            kaleci_karsi_karsiya=70,
            energy=90,
            ability_name="Clutch Player",
        )
        game, resolution = self._resolve_custom_duel(
            user_card,
            computer_card,
            "penalti",
            round_number=12,
            total_expected_rounds=12,
        )
        game._apply_resolution_effects(resolution)
        self.assertEqual(resolution.outcome_type, "draw")
        self.assertEqual(user_card.energy, 82)
        self.assertEqual(computer_card.energy, 82)

    def test_critical_card_threshold_matches_spec(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            energy=19,
        )
        self.assertTrue(card.is_critical())
        card.energy = 20
        self.assertFalse(card.is_critical())

    def test_morale_streak_updates_follow_spec(self) -> None:
        game = GameManager()
        player = game.user
        self.assertEqual(player.morale, 60)
        player.register_round_result("win", Branch.FOOTBALL)
        self.assertEqual(player.morale, 60)
        player.register_round_result("win", Branch.BASKETBALL)
        self.assertEqual(player.morale, 70)
        player.register_round_result("win", Branch.VOLLEYBALL)
        self.assertEqual(player.morale, 85)
        player.register_round_result("draw", Branch.FOOTBALL)
        self.assertEqual(player.morale, 85)

    def test_same_branch_two_losses_apply_extra_5_once(self) -> None:
        game = GameManager()
        player = game.user
        player.register_round_result("loss", Branch.FOOTBALL)
        self.assertEqual(player.morale, 60)
        player.register_round_result("loss", Branch.FOOTBALL)
        self.assertEqual(player.morale, 45)
        player.register_round_result("loss", Branch.FOOTBALL)
        self.assertEqual(player.morale, 45)

    def test_experience_gain_follows_spec(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        card.register_result("win")
        self.assertEqual(card.experience_points, 2)
        card.register_result("draw")
        self.assertEqual(card.experience_points, 3)
        card.register_result("loss")
        self.assertEqual(card.experience_points, 3)

    def test_level_two_reached_with_two_wins_and_stats_increase(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=81,
            kaleci_karsi_karsiya=82,
            durability=90,
            energy=100,
        )
        card.win_count = 2
        leveled = card.level_up_if_needed()
        self.assertTrue(leveled)
        self.assertEqual(card.level, 2)
        self.assertEqual(card.penalti, 85)
        self.assertEqual(card.serbest_vurus, 86)
        self.assertEqual(card.kaleci_karsi_karsiya, 87)
        self.assertEqual(card.max_energy, 110)
        self.assertEqual(card.durability, 95)

    def test_level_two_reached_with_four_experience(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        card.experience_points = 4
        leveled = card.level_up_if_needed()
        self.assertTrue(leveled)
        self.assertEqual(card.level, 2)

    def test_level_three_reached_with_four_wins(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=90,
            energy=100,
        )
        card.win_count = 4
        leveled = card.level_up_if_needed()
        self.assertTrue(leveled)
        self.assertEqual(card.level, 3)
        self.assertEqual(card.penalti, 90)
        self.assertEqual(card.serbest_vurus, 90)
        self.assertEqual(card.kaleci_karsi_karsiya, 90)
        self.assertEqual(card.max_energy, 120)
        self.assertEqual(card.durability, 100)

    def test_level_three_reached_with_eight_experience(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        card.experience_points = 8
        leveled = card.level_up_if_needed()
        self.assertTrue(leveled)
        self.assertEqual(card.level, 3)

    def test_card_cannot_exceed_level_three(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            durability=90,
            energy=100,
            level=3,
        )
        card.win_count = 10
        card.experience_points = 20
        leveled = card.level_up_if_needed()
        self.assertFalse(leveled)
        self.assertEqual(card.level, 3)
        self.assertEqual(card.penalti, 80)
        self.assertEqual(card.max_energy, 100)

    def test_clutch_player_bonus_in_last_three_rounds(self) -> None:
        ability = create_ability("Clutch Player")
        context = AbilityContext(
            round_number=10,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=1,
            same_team_branch_support=0,
            owner_energy=90,
            opponent_attribute_base=80,
        )
        self.assertEqual(ability.pre_round_bonus(80, context), 10)

    def test_captain_bonus_with_same_team_branch_support(self) -> None:
        ability = create_ability("Captain")
        supported = AbilityContext(
            round_number=1,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=2,
            same_team_branch_support=1,
            owner_energy=90,
            opponent_attribute_base=80,
        )
        unsupported = AbilityContext(
            round_number=1,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=1,
            same_team_branch_support=0,
            owner_energy=90,
            opponent_attribute_base=80,
        )
        self.assertEqual(ability.pre_round_bonus(80, supported), 5)
        self.assertEqual(ability.pre_round_bonus(80, unsupported), 0)

    def test_legend_ability_can_trigger_once_per_match(self) -> None:
        ability = create_ability("Legend")
        context = AbilityContext(
            round_number=1,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=1,
            same_team_branch_support=0,
            owner_energy=90,
            opponent_attribute_base=90,
        )
        first_bonus = ability.pre_round_bonus(80, context)
        ability.mark_used_if_needed(first_bonus)
        second_bonus = ability.pre_round_bonus(80, context)
        self.assertEqual(first_bonus, 80)
        self.assertTrue(ability.used)
        self.assertEqual(second_bonus, 0)

    def test_defender_halves_opponent_special_bonus(self) -> None:
        ability = create_ability("Defender")
        context = AbilityContext(
            round_number=1,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=1,
            same_team_branch_support=0,
            owner_energy=90,
            opponent_attribute_base=80,
        )
        self.assertEqual(ability.modify_opponent_bonus(11, context), 5)

    def test_veteran_reduces_energy_loss_by_half(self) -> None:
        ability = create_ability("Veteran")
        self.assertEqual(ability.adjust_energy_loss(10), 5)
        self.assertEqual(ability.adjust_energy_loss(5), 3)

    def test_finisher_bonus_when_energy_is_low(self) -> None:
        ability = create_ability("Finisher")
        low_energy_context = AbilityContext(
            round_number=1,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=1,
            same_team_branch_support=0,
            owner_energy=35,
            opponent_attribute_base=80,
        )
        high_energy_context = AbilityContext(
            round_number=1,
            total_expected_rounds=12,
            attribute_name="penalti",
            owner_player_name="User",
            owner_branch_card_count=1,
            same_team_branch_support=0,
            owner_energy=50,
            opponent_attribute_base=80,
        )
        self.assertEqual(ability.pre_round_bonus(80, low_energy_context), 8)
        self.assertEqual(ability.pre_round_bonus(80, high_energy_context), 0)

    def test_card_detail_shows_ability_description_and_usage_rule(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
            ability_name="Legend",
        )
        details = "\n".join(card.detail_lines())
        self.assertIn("Yetenek Kullanimi: Bir macta bir kez", details)
        self.assertIn("Yetenek Aciklamasi: Bir mac boyunca bir kez secilen ozelligi iki kat etkiler.", details)

    def test_abstract_design_alias_methods_exist_and_work(self) -> None:
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=81,
            kaleci_karsi_karsiya=82,
            energy=100,
        )
        self.assertEqual(card.sporcuID, 1)
        self.assertEqual(card.sporcuAdi, "Player 1")
        self.assertEqual(card.sporcuTakim, "Team")
        self.assertEqual(card.maxEnerji, 100)
        self.assertEqual(card.deneyimPuani, 0)
        self.assertFalse(card.kartKullanildiMi)
        self.assertEqual(card.ozelYetenek, "Yok")
        self.assertEqual(card.sporcuPuaniGoster()["penalti"], 80)
        self.assertIn("ID: 1", card.kartBilgisiYazdir())
        card.enerjiGuncelle(5)
        self.assertEqual(card.energy, 95)
        card.win_count = 2
        self.assertTrue(card.seviyeAtlaKontrol())
        self.assertEqual(card.level, 2)
        bonus = card.ozelYetenekUygula(
            80,
            AbilityContext(
                round_number=1,
                total_expected_rounds=12,
                attribute_name="penalti",
                owner_player_name="User",
                owner_branch_card_count=1,
                same_team_branch_support=0,
                owner_energy=card.energy,
                opponent_attribute_base=70,
            ),
        )
        self.assertEqual(bonus, 0)

    def test_player_alias_properties_and_kart_sec_work(self) -> None:
        player = Kullanici(player_id=1, player_name="Kullanici")
        card = self._make_footballer(
            card_id=1,
            penalti=80,
            serbest_vurus=80,
            kaleci_karsi_karsiya=80,
        )
        player.cards = [card]
        self.assertEqual(player.oyuncuID, 1)
        self.assertEqual(player.oyuncuAdi, "Kullanici")
        self.assertEqual(player.kartListesi, [card])
        self.assertEqual(player.galibiyetSerisi, 0)
        self.assertEqual(player.kaybetmeSerisi, 0)
        self.assertEqual(player.kartSec(Branch.FOOTBALL, card_id=1), card)

    def test_winner_summary_prefers_total_score_first(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 35
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (puan ustunlugu)")

    def test_winner_summary_uses_round_wins_after_score_tie(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 5
        game.computer.rounds_won = 4
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (tur galibiyeti kriteri)")

    def test_winner_summary_uses_series_count_after_round_wins(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 4
        game.computer.rounds_won = 4
        game.user.series_count = 2
        game.computer.series_count = 1
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (galibiyet serisi sayisi kriteri)")

    def test_winner_summary_uses_remaining_energy_after_series(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 4
        game.computer.rounds_won = 4
        game.user.series_count = 1
        game.computer.series_count = 1
        user_card = self._make_footballer(card_id=1, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=50)
        computer_card = self._make_footballer(card_id=2, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40)
        game.user.cards = [user_card]
        game.computer.cards = [computer_card]
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (kalan toplam enerji kriteri)")

    def test_winner_summary_uses_highest_level_card_count_after_energy(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 4
        game.computer.rounds_won = 4
        game.user.series_count = 1
        game.computer.series_count = 1
        game.user.cards = [
            self._make_footballer(card_id=1, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3),
            self._make_footballer(card_id=2, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3),
        ]
        game.computer.cards = [
            self._make_footballer(card_id=3, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3),
            self._make_footballer(card_id=4, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=2),
        ]
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (en yuksek seviyeli kart sayisi kriteri)")

    def test_winner_summary_uses_special_ability_wins_after_level_count(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 4
        game.computer.rounds_won = 4
        game.user.series_count = 1
        game.computer.series_count = 1
        game.user.cards = [self._make_footballer(card_id=1, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3)]
        game.computer.cards = [self._make_footballer(card_id=2, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3)]
        game.user.special_ability_wins = 2
        game.computer.special_ability_wins = 1
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (ozel yetenekli galibiyet kriteri)")

    def test_winner_summary_prefers_fewer_draws_after_special_ability_wins(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 4
        game.computer.rounds_won = 4
        game.user.series_count = 1
        game.computer.series_count = 1
        game.user.cards = [self._make_footballer(card_id=1, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3)]
        game.computer.cards = [self._make_footballer(card_id=2, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3)]
        game.user.special_ability_wins = 1
        game.computer.special_ability_wins = 1
        game.user.draws = 1
        game.computer.draws = 3
        self.assertEqual(game.winner_summary(), "Kazanan: Kullanici (beraberlik azligi kriteri)")

    def test_winner_summary_declares_draw_if_all_tiebreakers_equal(self) -> None:
        game = GameManager()
        game.finished = True
        game.user.score = 40
        game.computer.score = 40
        game.user.rounds_won = 4
        game.computer.rounds_won = 4
        game.user.series_count = 1
        game.computer.series_count = 1
        game.user.cards = [self._make_footballer(card_id=1, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3)]
        game.computer.cards = [self._make_footballer(card_id=2, penalti=80, serbest_vurus=80, kaleci_karsi_karsiya=80, energy=40, level=3)]
        game.user.special_ability_wins = 1
        game.computer.special_ability_wins = 1
        game.user.draws = 2
        game.computer.draws = 2
        self.assertEqual(game.winner_summary(), "Mac berabere bitti.")


if __name__ == "__main__":
    unittest.main()
