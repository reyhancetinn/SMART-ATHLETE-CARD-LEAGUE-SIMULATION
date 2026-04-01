from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from smart_league.constants import Difficulty, FeatureMode
from smart_league.professional_ui import MainWindow


class MainWindowUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()

    def test_pre_game_state_shows_placeholder_and_disables_play(self) -> None:
        self.assertFalse(self.window.play_button.isEnabled())
        self.assertIn("Oyun baslatildiginda", self.window.detail_box.toPlainText())
        self.assertIsNotNone(self.window.detail_image.pixmap())
        self.assertIn("sporcular.csv", self.window.control_panel.file_status_label.text())
        self.assertNotIn("\\", self.window.control_panel.file_status_label.text())
        self.assertEqual(self.window.control_panel.file_status_label.toolTip(), self.window.default_data_file)

    def test_start_game_selects_first_user_card_and_enables_play(self) -> None:
        self.window.game.start_new_game(
            self.window.default_data_file,
            Difficulty.MEDIUM,
            FeatureMode.RANDOM,
        )
        self.window.game_started = True
        self.window.refresh_all()

        self.assertEqual(self.window.user_table.rowCount(), 12)
        self.assertEqual(len(self.window.user_card_widgets), 12)
        self.assertIsNotNone(self.window.selected_user_card_id())
        self.assertTrue(self.window.play_button.isEnabled())
        self.assertIn("Gorsel: Var", self.window.detail_box.toPlainText())

    def test_computer_cards_render_as_widgets_when_reveal_enabled(self) -> None:
        self.window.game.start_new_game(
            self.window.default_data_file,
            Difficulty.MEDIUM,
            FeatureMode.RANDOM,
        )
        self.window.game_started = True
        self.window.show_computer_checkbox.setChecked(True)
        self.window.refresh_all()

        self.assertEqual(len(self.window.computer_card_widgets), 12)
        self.assertEqual(self.window.computer_table.rowCount(), 12)
        self.assertIsNone(self.window.selected_computer_card_id_value)
        self.assertTrue(all(not widget.interactive for widget in self.window.computer_card_widgets.values()))

    def test_main_and_card_areas_are_scrollable(self) -> None:
        self.assertTrue(self.window.page_scroll.widgetResizable())
        self.assertTrue(self.window.card_area.scroll_area.widgetResizable())

    def test_played_round_uses_same_cards_for_engine_stage_and_log(self) -> None:
        self.window.start_game()
        self.window.show_computer_checkbox.setChecked(False)

        selected_card_id = self.window.selected_user_card_id()
        self.assertIsNotNone(selected_card_id)
        self.window.play_selected_card()

        resolution = self.window.game.active_turn_state.resolution
        self.assertIsNotNone(resolution)
        self.assertEqual(self.window.displayed_user_card_id, resolution.user_card.card_id)
        self.assertEqual(self.window.displayed_computer_card_id, resolution.computer_card.card_id)
        self.assertEqual(resolution.user_card.branch, resolution.branch)
        self.assertEqual(resolution.computer_card.branch, resolution.branch)
        log_text = self.window.log_box.toPlainText()
        self.assertIn(str(resolution.user_card.card_id), log_text)
        self.assertIn(str(resolution.computer_card.card_id), log_text)

    def test_selecting_new_turn_card_clears_previous_turn_snapshot(self) -> None:
        self.window.start_game()
        self.window.play_selected_card()

        self.assertIsNotNone(self.window.game.active_turn_state.resolution)
        next_card = self.window.game.user.available_cards(self.window.game.current_branch())[0]
        self.window._select_user_card(next_card.card_id)

        self.assertIsNone(self.window.game.active_turn_state.resolution)
        self.assertIsNone(self.window.displayed_computer_card_id)
        self.assertIn("tur oynandiginda", self.window.computer_stage_caption.text())

    def test_wrong_branch_selection_shows_warning_without_score_penalty(self) -> None:
        self.window.start_game()
        wrong_branch_card = self.window.game.user.available_cards(self.window.game.current_branch())[0]
        for branch in self.window.game.user.cards:
            if branch.branch != self.window.game.current_branch() and branch.can_play():
                wrong_branch_card = branch
                break
        self.window.game.user.score = 7
        self.window._select_user_card(wrong_branch_card.card_id)

        with patch("smart_league.professional_ui.QMessageBox.warning") as warning_mock:
            self.window.play_selected_card()

        self.assertTrue(warning_mock.called)
        self.assertEqual(self.window.game.user.score, 7)
        self.assertIn("Uyari:", self.window.log_box.toPlainText())

    def test_invalid_selection_applies_minus_five_without_going_below_zero(self) -> None:
        self.window.start_game()
        self.window.game.user.score = 7
        self.window.selected_user_card_id_value = None

        with patch("smart_league.professional_ui.QMessageBox.warning") as warning_mock:
            self.window.play_selected_card()

        self.assertTrue(warning_mock.called)
        self.assertEqual(self.window.game.user.score, 2)
        self.assertIn("Gecersiz kart secimi", self.window.log_box.toPlainText())
        self.assertIn("Gecersiz kart secimi", "\n".join(self.window.game.statistics.event_notes))

    def test_invalid_selection_penalty_does_not_drop_score_below_zero(self) -> None:
        self.window.start_game()
        self.window.game.user.score = 3
        self.window.selected_user_card_id_value = None

        with patch("smart_league.professional_ui.QMessageBox.warning"):
            self.window.play_selected_card()

        self.assertEqual(self.window.game.user.score, 0)

    def test_timeout_auto_selects_card_without_penalty(self) -> None:
        self.window.turn_time_combo.setCurrentIndex(1)
        self.window.start_game()
        expected_card = self.window.game.user.available_cards(self.window.game.current_branch())[0]
        self.window.selected_user_card_id_value = None
        self.window.game.user.score = 7

        with patch.object(self.window, "_play_round_with_auto_computer_response", return_value=None) as play_mock:
            self.window._handle_turn_timeout()

        play_mock.assert_called_once_with(expected_card.card_id)
        self.assertEqual(self.window.selected_user_card_id_value, expected_card.card_id)
        self.assertEqual(self.window.game.user.score, 7)
        self.assertIn("Sure asimi", self.window.log_box.toPlainText())

    def test_timer_resets_on_new_game_round_end_and_game_over(self) -> None:
        self.window.turn_time_combo.setCurrentIndex(1)
        self.window.start_game()
        self.assertTrue(self.window.turn_timer.isActive())

        with patch("smart_league.professional_ui.QMessageBox.information"):
            self.window.play_selected_card()
        self.assertTrue(self.window.turn_timer.isActive())

        self.window.game.finished = True
        self.window._update_turn_timer_for_current_state()
        self.assertFalse(self.window.turn_timer.isActive())

        self.window.start_game()
        self.assertTrue(self.window.turn_timer.isActive())


if __name__ == "__main__":
    unittest.main()
