from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QGraphicsDropShadowEffect,
)

from .card_widget import CardWidget
from .constants import FEATURE_LABELS, Branch, Difficulty, FeatureMode
from .card_art import create_card_back, create_card_pixmap
from .data_loader import DataValidationError
from .game import GameManager, RoundResolution


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.game = GameManager()
        self.game_started = False
        self.last_user_card_id: int | None = None
        self.last_computer_card_id: int | None = None
        self.selected_user_card_id_value: int | None = None
        self.selected_computer_card_id_value: int | None = None
        self.detail_focus_owner = "user"
        self._syncing_selection = False
        self.default_data_file = str(Path(__file__).resolve().parent.parent / "data" / "sporcular.csv")
        self.setWindowTitle("Akilli Sporcu Kart Ligi")
        self.resize(1560, 1020)
        self._build_ui()
        self._connect_signals()
        self.data_path_input.setText(self.default_data_file)
        self._apply_styles()
        self._apply_neon_effects()
        self._show_empty_detail_state()
        self._update_interaction_state()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        hero = QGroupBox("Mac Ustu Panel")
        hero_layout = QGridLayout(hero)
        self.hero_title = QLabel("Akilli Sporcu Kart Ligi")
        self.hero_title.setObjectName("HeroTitle")
        self.hero_subtitle = QLabel(
            "Futbol, basketbol ve voleybol kartlariyla cok turlu premium lig deneyimi"
        )
        self.hero_subtitle.setObjectName("HeroSubtitle")
        self.turn_chip = QLabel("Tur Bekleniyor")
        self.turn_chip.setObjectName("InfoChip")
        self.branch_chip = QLabel("Brans Bekleniyor")
        self.branch_chip.setObjectName("InfoChip")
        self.difficulty_chip = QLabel("Zorluk: -")
        self.difficulty_chip.setObjectName("InfoChipSoft")
        self.mode_chip = QLabel("Ozellik Modu: -")
        self.mode_chip.setObjectName("InfoChipSoft")
        hero_layout.addWidget(self.hero_title, 0, 0, 1, 3)
        hero_layout.addWidget(self.hero_subtitle, 1, 0, 1, 3)
        hero_layout.addWidget(self.turn_chip, 0, 3)
        hero_layout.addWidget(self.branch_chip, 0, 4)
        hero_layout.addWidget(self.difficulty_chip, 1, 3)
        hero_layout.addWidget(self.mode_chip, 1, 4)
        layout.addWidget(hero)

        controls = QGroupBox("Oyun Ayarlari")
        controls_layout = QGridLayout(controls)
        self.data_path_input = QLineEdit()
        self.browse_button = QPushButton("Dosya Sec")
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems([Difficulty.EASY.value, Difficulty.MEDIUM.value])
        self.feature_mode_combo = QComboBox()
        self.feature_mode_combo.addItems([FeatureMode.RANDOM.value, FeatureMode.USER_CHOICE.value])
        self.start_button = QPushButton("Yeni Oyun Baslat")
        self.show_computer_checkbox = QCheckBox("Bilgisayar Kartlarini Goster")
        self.feature_select_combo = QComboBox()
        controls_layout.addWidget(QLabel("Veri Dosyasi"), 0, 0)
        controls_layout.addWidget(self.data_path_input, 0, 1, 1, 3)
        controls_layout.addWidget(self.browse_button, 0, 4)
        controls_layout.addWidget(QLabel("Zorluk"), 1, 0)
        controls_layout.addWidget(self.difficulty_combo, 1, 1)
        controls_layout.addWidget(QLabel("Ozellik Modu"), 1, 2)
        controls_layout.addWidget(self.feature_mode_combo, 1, 3)
        controls_layout.addWidget(self.start_button, 1, 4)
        controls_layout.addWidget(QLabel("Secilecek Ozellik"), 2, 0)
        controls_layout.addWidget(self.feature_select_combo, 2, 1, 1, 2)
        controls_layout.addWidget(self.show_computer_checkbox, 2, 3, 1, 2)
        layout.addWidget(controls)

        summary = QGroupBox("Mac Durumu")
        summary_layout = QGridLayout(summary)
        self.round_label = QLabel("Tur: -")
        self.branch_label = QLabel("Brans: -")
        self.user_score_label = QLabel("Kullanici Skor: 0")
        self.computer_score_label = QLabel("Bilgisayar Skor: 0")
        self.user_morale_label = QLabel("Kullanici Moral: 60")
        self.computer_morale_label = QLabel("Bilgisayar Moral: 60")
        self.user_deck_label = QLabel("Kullanici toplam enerji: 0")
        self.computer_deck_label = QLabel("Bilgisayar toplam enerji: 0")
        summary_layout.addWidget(self.round_label, 0, 0)
        summary_layout.addWidget(self.branch_label, 0, 1)
        summary_layout.addWidget(self.user_score_label, 0, 2)
        summary_layout.addWidget(self.computer_score_label, 0, 3)
        summary_layout.addWidget(self.user_morale_label, 1, 0)
        summary_layout.addWidget(self.computer_morale_label, 1, 1)
        summary_layout.addWidget(self.user_deck_label, 1, 2)
        summary_layout.addWidget(self.computer_deck_label, 1, 3)
        layout.addWidget(summary)

        distribution = QGroupBox("Brans Dagilimi")
        distribution_layout = QHBoxLayout(distribution)
        self.branch_distribution_labels = {}
        for branch in Branch:
            label = QLabel(f"{branch.value}: Kullanici 0 | Bilgisayar 0")
            label.setObjectName("InfoChipSoft")
            distribution_layout.addWidget(label)
            self.branch_distribution_labels[branch] = label
        layout.addWidget(distribution)

        self.user_table = self._create_table()
        self.computer_table = self._create_table()
        battle_group = QGroupBox("Karsilasma Sahnesi")
        battle_layout = QHBoxLayout(battle_group)
        battle_layout.setSpacing(14)
        user_focus_group = QGroupBox("Senin Kartin")
        user_focus_layout = QVBoxLayout(user_focus_group)
        self.user_stage_image = QLabel()
        self.user_stage_image.setObjectName("StageCardImage")
        self.user_stage_image.setMinimumSize(240, 330)
        self.user_stage_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_stage_caption = QLabel("Kart secildiginde burada buyuk gorunur.")
        self.user_stage_caption.setObjectName("StageCaption")
        user_focus_layout.addWidget(self.user_stage_image)
        user_focus_layout.addWidget(self.user_stage_caption)

        center_focus_group = QGroupBox("Mac Ekrani")
        center_focus_layout = QVBoxLayout(center_focus_group)
        self.center_stage_title = QLabel("Siradaki Brans: -")
        self.center_stage_title.setObjectName("StageTitle")
        self.center_stage_score = QLabel("Bilgisayar | Skor: 0 | Moral: 60 | Enerji: 0")
        self.center_stage_score.setObjectName("StageScore")
        self.center_stage_user = QLabel("Sen | Skor: 0 | Moral: 60 | Enerji: 0")
        self.center_stage_user.setObjectName("StageScoreUser")
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("BattleConsole")
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Tur aciklamalari burada gorunecek.")
        center_focus_layout.addWidget(self.center_stage_title)
        center_focus_layout.addWidget(self.center_stage_score)
        center_focus_layout.addWidget(self.center_stage_user)
        center_focus_layout.addWidget(self.log_box)

        computer_focus_group = QGroupBox("Bilgisayar Karti")
        computer_focus_layout = QVBoxLayout(computer_focus_group)
        self.computer_stage_image = QLabel()
        self.computer_stage_image.setObjectName("StageCardImage")
        self.computer_stage_image.setMinimumSize(240, 330)
        self.computer_stage_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.computer_stage_caption = QLabel("Bilgisayar karti burada gorunur.")
        self.computer_stage_caption.setObjectName("StageCaption")
        computer_focus_layout.addWidget(self.computer_stage_image)
        computer_focus_layout.addWidget(self.computer_stage_caption)

        battle_layout.addWidget(user_focus_group, 2)
        battle_layout.addWidget(center_focus_group, 5)
        battle_layout.addWidget(computer_focus_group, 2)
        layout.addWidget(battle_group)

        deck_group = QGroupBox("Kart Secim Sahasi")
        deck_layout = QHBoxLayout(deck_group)
        deck_layout.setSpacing(12)
        self.user_branch_grids: dict[Branch, QGridLayout] = {}
        self.user_card_widgets: dict[int, CardWidget] = {}
        for branch in Branch:
            branch_group = QGroupBox(branch.value)
            branch_layout = QVBoxLayout(branch_group)
            section_label = QLabel(f"{branch.value} Kartlari")
            section_label.setObjectName("SectionLabel")
            branch_layout.addWidget(section_label)
            branch_scroll = QScrollArea()
            branch_scroll.setWidgetResizable(True)
            branch_scroll.setFrameShape(QFrame.Shape.NoFrame)
            branch_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            branch_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            branch_scroll.setObjectName("CardScroll")
            branch_container = QWidget()
            branch_container.setObjectName("CardViewport")
            branch_grid = QGridLayout(branch_container)
            branch_grid.setContentsMargins(4, 4, 4, 4)
            branch_grid.setHorizontalSpacing(10)
            branch_grid.setVerticalSpacing(10)
            branch_scroll.setWidget(branch_container)
            branch_layout.addWidget(branch_scroll)
            self.user_branch_grids[branch] = branch_grid
            deck_layout.addWidget(branch_group)
        layout.addWidget(deck_group)

        action_group = QGroupBox("Tur Komutlari")
        action_layout = QHBoxLayout(action_group)
        self.play_button = QPushButton("Secili Karti Oyna")
        action_layout.addWidget(self.play_button)
        layout.addWidget(action_group)

        self.computer_group = QGroupBox("Bilgisayar Kartlari")
        computer_layout = QVBoxLayout(self.computer_group)
        self.computer_hint_label = QLabel("Goster secenegi acildiginda bilgisayarin kartlari burada neon kart kutulari ile listelenir.")
        self.computer_hint_label.setObjectName("SectionLabel")
        computer_layout.addWidget(self.computer_hint_label)
        self.computer_scroll = QScrollArea()
        self.computer_scroll.setWidgetResizable(True)
        self.computer_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.computer_scroll.setObjectName("CardScroll")
        self.computer_scroll.setMinimumHeight(360)
        computer_container = QWidget()
        computer_container.setObjectName("CardViewport")
        self.computer_card_grid = QGridLayout(computer_container)
        self.computer_card_grid.setContentsMargins(4, 4, 4, 4)
        self.computer_card_grid.setHorizontalSpacing(12)
        self.computer_card_grid.setVerticalSpacing(12)
        self.computer_scroll.setWidget(computer_container)
        computer_layout.addWidget(self.computer_scroll)
        self.computer_card_widgets: dict[int, CardWidget] = {}
        layout.addWidget(self.computer_group)

        bottom_layout = QHBoxLayout()
        self.detail_image = QLabel()
        self.detail_image.setObjectName("DetailCardImage")
        self.detail_image.setMinimumSize(280, 360)
        self.detail_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_box = QPlainTextEdit()
        self.detail_box.setObjectName("GlassPanel")
        self.detail_box.setReadOnly(True)
        self.detail_box.setPlaceholderText("Kart detaylari burada gorunecek.")
        self.report_box = QPlainTextEdit()
        self.report_box.setObjectName("GlassPanel")
        self.report_box.setReadOnly(True)
        self.report_box.setPlaceholderText("Mac bittiginde genel ozet burada gorunecek.")
        detail_group = QGroupBox("Kart Detayi")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(self.detail_image)
        detail_layout.addWidget(self.detail_box)
        right_panel = QVBoxLayout()
        performance_group = QGroupBox("Dinamik Puan Hesaplama")
        performance_layout = QVBoxLayout(performance_group)
        self.performance_box = QPlainTextEdit()
        self.performance_box.setObjectName("GlassPanel")
        self.performance_box.setReadOnly(True)
        self.performance_box.setPlaceholderText("Tur oynandiginda formuldaki butun kalemler burada gorunecek.")
        performance_layout.addWidget(self.performance_box)
        report_group = QGroupBox("Mac Ozeti")
        report_layout = QVBoxLayout(report_group)
        report_layout.addWidget(self.report_box)
        right_panel.addWidget(performance_group)
        right_panel.addWidget(report_group)
        bottom_layout.addWidget(detail_group)
        bottom_layout.addLayout(right_panel)
        layout.addLayout(bottom_layout)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #070914, stop:0.45 #0b0f1a, stop:1 #151022);
            }
            QGroupBox {
                border: 1px solid #3b284a;
                border-radius: 22px;
                margin-top: 12px;
                font-weight: 700;
                background: rgba(11, 15, 26, 0.97);
                padding-top: 6px;
                color: #ffe6f5;
                font-family: "Segoe UI";
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #f2f6ff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff2e97, stop:1 #ff6ec7);
                color: white;
                border-radius: 16px;
                padding: 12px 16px;
                font-weight: 700;
                border: 1px solid #ff9cda;
            }
            QPushButton:hover {
                background: #ff5bb4;
            }
            QPushButton:pressed {
                background: #d6247d;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget {
                background: rgba(17, 24, 39, 0.98);
                color: #fdf1f8;
                border: 1px solid #5a2d57;
                border-radius: 16px;
                padding: 6px;
                selection-background-color: #6d1e57;
                selection-color: #ffffff;
            }
            QTableWidget {
                alternate-background-color: rgba(24, 19, 38, 0.95);
                gridline-color: #41294d;
            }
            QLabel {
                color: #f2f6ff;
                font-weight: 600;
                font-family: "Segoe UI";
            }
            QLabel#HeroTitle {
                font-size: 28px;
                font-weight: 800;
                color: #f2f6ff;
            }
            QLabel#HeroSubtitle {
                font-size: 13px;
                color: #e3abc9;
                font-weight: 500;
            }
            QLabel#InfoChip {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff2e97, stop:1 #ff6ec7);
                color: white;
                border-radius: 18px;
                padding: 10px 14px;
                font-weight: 800;
                border: 1px solid #ff9cda;
            }
            QLabel#InfoChipSoft {
                background: rgba(39, 22, 52, 0.95);
                color: #ffdff0;
                border-radius: 18px;
                padding: 10px 14px;
                border: 1px solid #834a84;
                font-weight: 700;
            }
            QLabel#StageTitle {
                font-size: 24px;
                font-weight: 800;
                color: #ff8fd0;
            }
            QLabel#StageScore {
                font-size: 15px;
                font-weight: 800;
                color: #ff9d9d;
            }
            QLabel#StageScoreUser {
                font-size: 15px;
                font-weight: 800;
                color: #8fffb4;
            }
            QLabel#StageCaption {
                font-size: 12px;
                color: #f3bfd9;
                padding: 4px 8px;
            }
            QLabel#SectionLabel {
                color: #ffc9e8;
                font-size: 12px;
                font-weight: 700;
                padding: 0 6px 4px 6px;
            }
            QLabel#StageCardImage, QLabel#DetailCardImage {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(27, 19, 41, 0.96), stop:1 rgba(17, 24, 39, 0.98));
                border: 2px solid #ff6ec7;
                border-radius: 24px;
                padding: 10px;
            }
            QPlainTextEdit#BattleConsole {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(18, 25, 42, 0.98), stop:1 rgba(12, 16, 29, 0.98));
                border: 1px solid #ff5cb9;
                border-radius: 20px;
                padding: 14px;
                font-size: 13px;
                selection-background-color: #ff2e97;
            }
            QPlainTextEdit#GlassPanel {
                background: rgba(16, 22, 35, 0.97);
                border: 1px solid #6a2f68;
                border-radius: 20px;
                padding: 12px;
            }
            QScrollArea#CardScroll {
                background: transparent;
                border: none;
            }
            QWidget#CardViewport {
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(14, 18, 29, 0.9);
                width: 12px;
                margin: 4px 2px 4px 2px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #ff4dad;
                border-radius: 6px;
                min-height: 28px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QHeaderView::section {
                background: #3a2248;
                color: #ffeaf4;
                border: none;
                border-bottom: 1px solid #643660;
                padding: 8px;
                font-weight: 700;
            }
            QCheckBox {
                color: #dceaff;
                font-weight: 600;
            }
            """
        )

    def _apply_neon_effects(self) -> None:
        for widget, color, blur in (
            (self.start_button, QColor("#FF2E97"), 28),
            (self.play_button, QColor("#FF2E97"), 30),
            (self.browse_button, QColor("#FF6EC7"), 22),
            (self.user_stage_image, QColor("#FF2E97"), 34),
            (self.computer_stage_image, QColor("#FF6EC7"), 34),
        ):
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(blur)
            effect.setOffset(0, 0)
            effect.setColor(color)
            widget.setGraphicsEffect(effect)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget(0, 9)
        table.setHorizontalHeaderLabels(
            ["Kart", "ID", "Ad", "Takim", "Brans", "Enerji", "Seviye", "Yetenek", "Durum"]
        )
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setIconSize(QSize(86, 116))
        table.verticalHeader().setDefaultSectionSize(124)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _connect_signals(self) -> None:
        self.browse_button.clicked.connect(self._browse_file)
        self.start_button.clicked.connect(self.start_game)
        self.play_button.clicked.connect(self.play_selected_card)
        self.show_computer_checkbox.toggled.connect(self.refresh_tables)
        self.feature_mode_combo.currentTextChanged.connect(self._update_feature_mode_visibility)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Veri Dosyasi Sec",
            str(Path(self.data_path_input.text()).parent),
            "CSV Files (*.csv);;Text Files (*.txt)",
        )
        if path:
            self.data_path_input.setText(path)

    def _update_feature_mode_visibility(self) -> None:
        manual = self.feature_mode_combo.currentText() == FeatureMode.USER_CHOICE.value
        self.feature_select_combo.setEnabled(manual)

    def start_game(self) -> None:
        try:
            self.game.start_new_game(
                self.data_path_input.text().strip(),
                Difficulty(self.difficulty_combo.currentText()),
                FeatureMode(self.feature_mode_combo.currentText()),
            )
        except (DataValidationError, ValueError) as exc:
            QMessageBox.critical(self, "Baslatma Hatasi", str(exc))
            return

        self.game_started = True
        self.last_user_card_id = None
        self.last_computer_card_id = None
        self.selected_user_card_id_value = None
        self.selected_computer_card_id_value = None
        self.detail_focus_owner = "user"
        self.log_box.clear()
        self.report_box.clear()
        self.performance_box.clear()
        self._append_log(self._start_flow_text())
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_summary()
        self.refresh_feature_combo()
        self.refresh_tables()
        self.update_detail_panel()
        self._update_feature_mode_visibility()
        self._update_interaction_state()

    def refresh_summary(self) -> None:
        user_energy_total = sum(card.energy for card in self.game.user.available_cards())
        computer_energy_total = sum(card.energy for card in self.game.computer.available_cards())
        self.round_label.setText(f"Tur: {self.game.round_number}")
        self.branch_label.setText(f"Brans: {self.game.current_branch().value if not self.game.finished else 'Bitti'}")
        self.user_score_label.setText(f"Kullanici Skor: {self.game.user.score}")
        self.computer_score_label.setText(f"Bilgisayar Skor: {self.game.computer.score}")
        self.user_morale_label.setText(f"Kullanici Moral: {self.game.user.morale}")
        self.computer_morale_label.setText(f"Bilgisayar Moral: {self.game.computer.morale}")
        self.user_deck_label.setText(f"Kullanici toplam enerji: {user_energy_total}")
        self.computer_deck_label.setText(f"Bilgisayar toplam enerji: {computer_energy_total}")
        self.turn_chip.setText(f"Tur {self.game.round_number}")
        self.branch_chip.setText(
            self.game.current_branch().value if not self.game.finished else "Lig Tamamlandi"
        )
        self.difficulty_chip.setText(f"Zorluk: {self.difficulty_combo.currentText()}")
        self.mode_chip.setText(f"Ozellik Modu: {self.feature_mode_combo.currentText()}")
        self.center_stage_title.setText(
            f"Siradaki Brans: {self.game.current_branch().value if not self.game.finished else 'Lig Tamamlandi'}"
        )
        self.center_stage_score.setText(
            f"Bilgisayar | Skor: {self.game.computer.score} | Moral: {self.game.computer.morale} | Enerji: {computer_energy_total}"
        )
        self.center_stage_user.setText(
            f"Sen | Skor: {self.game.user.score} | Moral: {self.game.user.morale} | Enerji: {user_energy_total}"
        )
        for branch, label in self.branch_distribution_labels.items():
            label.setText(
                f"{branch.value}: Kullanici {len(self.game.user.available_cards(branch))} | "
                f"Bilgisayar {len(self.game.computer.available_cards(branch))}"
            )
        self._update_interaction_state()

    def refresh_feature_combo(self) -> None:
        self.feature_select_combo.clear()
        branch = self.game.current_branch()
        for attribute in self.game.branch_features(branch):
            self.feature_select_combo.addItem(FEATURE_LABELS[attribute], attribute)

    def refresh_tables(self) -> None:
        self.selected_user_card_id_value = self._preferred_user_card_id(self.selected_user_card_id_value)
        self.selected_computer_card_id_value = self._preferred_computer_card_id(
            self.selected_computer_card_id_value
        )
        self._populate_table(self.user_table, self.game.user.available_cards(), reveal=True)
        self._populate_table(
            self.computer_table,
            self.game.computer.available_cards(),
            reveal=self.show_computer_checkbox.isChecked(),
        )
        self._populate_user_card_sections()
        self._populate_computer_card_grid()
        if self.detail_focus_owner == "computer" and not self.show_computer_checkbox.isChecked():
            self.detail_focus_owner = "user"
        self.computer_group.setVisible(self.show_computer_checkbox.isChecked())
        self.update_detail_panel()
        self._update_stage_panels()
        self._update_interaction_state()

    def _populate_table(self, table: QTableWidget, cards: list, reveal: bool) -> None:
        table.setRowCount(len(cards))
        current_branch = self.game.current_branch() if self.game_started and not self.game.finished else None
        for row, card in enumerate(cards):
            thumb_item = QTableWidgetItem()
            thumb_item.setIcon(QIcon(self._card_thumbnail(card, reveal)))
            thumb_item.setData(Qt.ItemDataRole.UserRole, card.card_id)
            if current_branch is not None and card.branch != current_branch:
                thumb_item.setBackground(QColor("#172743"))
            table.setItem(row, 0, thumb_item)
            values = [
                str(card.card_id),
                card.player_name if reveal else "Gizli Kart",
                card.team_name if reveal else "-",
                card.branch.value,
                f"{card.energy}/{card.max_energy}" if reveal else "?",
                str(card.level) if reveal else "?",
                card.ability_name if reveal else "?",
                "Kritik" if card.is_critical() and reveal else ("Hazir" if reveal else "Gizli"),
            ]
            for column_offset, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, card.card_id)
                if current_branch is not None and card.branch != current_branch:
                    item.setBackground(QColor("#172743"))
                    item.setForeground(QColor("#8397b8"))
                elif reveal and card.is_critical():
                    item.setBackground(QColor("#ffd9d9"))
                elif reveal and card.energy <= 40:
                    item.setBackground(QColor("#ffe7f1"))
                table.setItem(row, column_offset, item)
        table.resizeColumnsToContents()

    def _preferred_user_card_id(self, preferred_card_id: int | None) -> int | None:
        cards = self.game.user.available_cards()
        if not cards:
            return None
        available_ids = {card.card_id for card in cards}
        if preferred_card_id in available_ids:
            return preferred_card_id
        if self.game_started and not self.game.finished:
            branch_cards = self.game.user.available_cards(self.game.current_branch())
            if branch_cards:
                return branch_cards[0].card_id
        return cards[0].card_id

    def _preferred_computer_card_id(self, preferred_card_id: int | None) -> int | None:
        cards = self.game.computer.available_cards()
        if not cards:
            return None
        available_ids = {card.card_id for card in cards}
        if preferred_card_id in available_ids:
            return preferred_card_id
        if self.last_computer_card_id in available_ids:
            return self.last_computer_card_id
        return cards[0].card_id

    def _clear_layout(self, layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _card_status_text(self, card) -> str:
        if card.used_in_league:
            return "KULLANILDI"
        if card.is_critical():
            return "KRITIK"
        return "HAZIR"

    def _card_stats(self, card) -> dict[str, int]:
        return {
            **card.base_attributes(),
            "dayaniklilik": card.durability,
            "ozel_yetenek_katsayisi": card.special_ability_coefficient,
        }

    def _populate_user_card_sections(self) -> None:
        current_branch = self.game.current_branch() if self.game_started and not self.game.finished else None
        self.user_card_widgets = {}
        for branch, grid in self.user_branch_grids.items():
            self._clear_layout(grid)
            cards = self.game.user.available_cards(branch)
            if not cards:
                empty_label = QLabel("Bu bransta kullanilabilir kart kalmadi.")
                empty_label.setObjectName("SectionLabel")
                grid.addWidget(empty_label, 0, 0)
                continue
            for index, card in enumerate(cards):
                widget = CardWidget(compact=True)
                widget.set_data(
                    card_id=card.card_id,
                    player_name=card.player_name,
                    team_name=card.team_name,
                    branch=card.branch,
                    ability_name=card.ability_name,
                    image_path=card.image_path,
                    stats=self._card_stats(card),
                    energy=card.energy,
                    max_energy=card.max_energy,
                    level=card.level,
                    durability=card.durability,
                    status_text=self._card_status_text(card),
                    selected=card.card_id == self.selected_user_card_id_value,
                    current_branch=current_branch is not None and card.branch == current_branch,
                    owner_morale=self.game.user.morale,
                    reveal=True,
                )
                widget.clicked.connect(self._select_user_card)
                grid.addWidget(widget, index // 2, index % 2)
                self.user_card_widgets[card.card_id] = widget

    def _populate_computer_card_grid(self) -> None:
        current_branch = self.game.current_branch() if self.game_started and not self.game.finished else None
        self._clear_layout(self.computer_card_grid)
        self.computer_card_widgets = {}
        if not self.show_computer_checkbox.isChecked():
            hidden_label = QLabel("Bilgisayar kartlari gizli. Gostermek icin ustteki secenegi ac.")
            hidden_label.setObjectName("SectionLabel")
            self.computer_card_grid.addWidget(hidden_label, 0, 0)
            return
        cards = self.game.computer.available_cards()
        if not cards:
            empty_label = QLabel("Bilgisayarin kullanilabilir karti kalmadi.")
            empty_label.setObjectName("SectionLabel")
            self.computer_card_grid.addWidget(empty_label, 0, 0)
            return
        for index, card in enumerate(cards):
            widget = CardWidget(compact=True)
            widget.set_data(
                card_id=card.card_id,
                player_name=card.player_name,
                team_name=card.team_name,
                branch=card.branch,
                ability_name=card.ability_name,
                image_path=card.image_path,
                stats=self._card_stats(card),
                energy=card.energy,
                max_energy=card.max_energy,
                level=card.level,
                durability=card.durability,
                status_text=self._card_status_text(card),
                selected=card.card_id == self.selected_computer_card_id_value,
                current_branch=current_branch is not None and card.branch == current_branch,
                owner_morale=self.game.computer.morale,
                reveal=True,
            )
            widget.clicked.connect(self._select_computer_card)
            self.computer_card_grid.addWidget(widget, index // 4, index % 4)
            self.computer_card_widgets[card.card_id] = widget

    def _card_thumbnail(self, card, reveal: bool) -> QPixmap:
        if reveal:
            status_text = "Kullanildi" if card.used_in_league else ("Kritik" if card.is_critical() else "Hazir")
            return create_card_pixmap(
                card.player_name,
                card.branch,
                card.team_name,
                card.ability_name,
                card.image_path,
                {
                    **card.base_attributes(),
                    "dayaniklilik": card.durability,
                    "ozel_yetenek_katsayisi": card.special_ability_coefficient,
                },
                card.energy,
                card.max_energy,
                card.level,
                card.durability,
                status_text,
                108,
                144,
            )
        return create_card_back(108, 144)

    def selected_user_card_id(self) -> int | None:
        selected_card = self._selected_user_card()
        if selected_card is None or selected_card.branch != self.game.current_branch():
            return None
        return selected_card.card_id

    def _selected_user_card(self):
        return self._card_by_id(self.selected_user_card_id_value)

    def play_selected_card(self) -> None:
        if self.game.finished:
            return

        selected_card_id = self.selected_user_card_id()
        if selected_card_id is None:
            QMessageBox.warning(
                self,
                "Kart Sec",
                f"Bu tur sadece {self.game.current_branch().value} bransina ait kart oynayabilirsin.",
            )
            self._append_log(
                f"Uyari: Bu tur sadece {self.game.current_branch().value} bransina ait kart secilebilir."
            )
            return

        attribute = None
        if self.feature_mode_combo.currentText() == FeatureMode.USER_CHOICE.value:
            attribute = self.feature_select_combo.currentData()

        try:
            resolution = self.game.play_round(selected_card_id, attribute)
        except ValueError as exc:
            QMessageBox.warning(self, "Tur Hatasi", str(exc))
            return

        self.last_user_card_id = resolution.user_card.card_id if resolution.user_card else None
        self.last_computer_card_id = resolution.computer_card.card_id if resolution.computer_card else None

        self._log_resolution(resolution)
        self._show_performance_breakdown(resolution)
        self.refresh_all()

        if self.game.finished or (not self.game.user.available_cards() and not self.game.computer.available_cards()):
            self.game.finished = True
            winner_text = self.game.winner_summary()
            self.report_box.setPlainText(
                "\n".join(
                    [
                        "13. Tum kartlar bittiginde lig sonu raporu gosterildi.",
                        f"14. {winner_text}",
                        "",
                        self.game.match_summary_text(),
                    ]
                )
            )
            self._append_log(
                "\n".join(
                    [
                        "13. Tum kartlar bittiginde lig sonu raporu gosterildi.",
                        f"14. {winner_text}",
                    ]
                )
            )
            QMessageBox.information(self, "Oyun Sonu", winner_text)

    def _start_flow_text(self) -> str:
        return "\n".join(
            [
                "OYUN AKISI",
                "1. Sporcu verileri dosyadan okundu.",
                "2. Kart destesi olusturuldu.",
                "3. Kartlar dagitildi.",
                f"4. Kullanici zorluk secti: {self.difficulty_combo.currentText()}",
                "5. Tur sirasi belirlendi: Futbol -> Basketbol -> Voleybol",
            ]
        )

    def _show_performance_breakdown(self, resolution: RoundResolution) -> None:
        if not resolution.user_breakdown or not resolution.computer_breakdown:
            self.performance_box.setPlainText("Bu tur icin performans hesabi yok.")
            return
        selected_feature = FEATURE_LABELS.get(
            resolution.attribute_name or resolution.user_breakdown.attribute_name,
            resolution.attribute_name or "-",
        )
        lines = [
            f"DINAMIK PUAN HESAPLAMA - {selected_feature}",
            "",
            f"Kullanici: {resolution.user_card.label() if resolution.user_card else '-'}",
            f"Temel Ozellik: +{resolution.user_breakdown.base_value}",
            f"Moral Bonusu: {resolution.user_breakdown.moral_bonus:+}",
            f"Ozel Yetenek Bonusu: {resolution.user_breakdown.ability_bonus:+}",
            f"Enerji Kaybi Cezasi: -{resolution.user_breakdown.energy_penalty}",
            f"Seviye Bonusu: {resolution.user_breakdown.level_bonus:+}",
            f"Toplam Puan: {resolution.user_breakdown.total}",
            f"Enerji Aciklamasi: {self._energy_explanation(resolution.user_breakdown.base_value, resolution.user_breakdown.energy_at_calculation)}",
            "",
            f"Bilgisayar: {resolution.computer_card.label() if resolution.computer_card else '-'}",
            f"Temel Ozellik: +{resolution.computer_breakdown.base_value}",
            f"Moral Bonusu: {resolution.computer_breakdown.moral_bonus:+}",
            f"Ozel Yetenek Bonusu: {resolution.computer_breakdown.ability_bonus:+}",
            f"Enerji Kaybi Cezasi: -{resolution.computer_breakdown.energy_penalty}",
            f"Seviye Bonusu: {resolution.computer_breakdown.level_bonus:+}",
            f"Toplam Puan: {resolution.computer_breakdown.total}",
            f"Enerji Aciklamasi: {self._energy_explanation(resolution.computer_breakdown.base_value, resolution.computer_breakdown.energy_at_calculation)}",
            "",
            "Formul:",
            "Guncel Ozellik = Temel Ozellik + Moral Bonusu + Ozel Yetenek Bonusu - Enerji Kaybi Cezasi + Seviye Bonusu",
            "",
            "Enerji Araliklari:",
            "Enerji > 70 -> Ceza uygulanmaz",
            "40 <= Enerji <= 70 -> Ilgili ozellik puanindan %10 dusulur",
            "0 < Enerji < 40 -> Ilgili ozellik puanindan %20 dusulur",
            "Enerji = 0 -> Kart oynatilamaz",
        ]
        self.performance_box.setPlainText("\n".join(lines))

    def _energy_explanation(self, base_value: int, energy: int) -> str:
        if energy > 70:
            return (
                f"Enerji {energy}. 70'ten buyuk oldugu icin ceza yok; "
                f"temel ozellikten dusus yapilmadi."
            )
        if 40 <= energy <= 70:
            penalty = round(base_value * 0.10)
            return (
                f"Enerji {energy}. 40 ile 70 arasinda oldugu icin %10 ceza uygulandi; "
                f"{base_value} temel ozellikten {penalty} puan dusuldu."
            )
        if 0 < energy < 40:
            penalty = round(base_value * 0.20)
            return (
                f"Enerji {energy}. 40'in altinda oldugu icin %20 ceza uygulandi; "
                f"{base_value} temel ozellikten {penalty} puan dusuldu."
            )
        return "Enerji 0. Kart oynatilamaz."

    def _log_resolution(self, resolution: RoundResolution) -> None:
        selected_feature = FEATURE_LABELS[resolution.attribute_name] if resolution.attribute_name else "-"
        lines = [
            f"{max(1, self.game.round_number - 1)}. tur - {resolution.branch.value}",
            f"5. Tur sirasi: {resolution.branch.value}",
        ]
        if resolution.user_card and resolution.computer_card:
            lines.append(
                "6. Kullanici ve bilgisayar kartlarini secti: "
                f"Kullanici={resolution.user_card.label()} | Bilgisayar={resolution.computer_card.label()}"
            )
        elif resolution.winner or resolution.outcome_type in {"skip", "forfeit"}:
            lines.append(
                "6. Kart secim kontrolu yapildi: uygun brans kartlarina gore tur sonucu belirlendi."
            )
        lines.append(f"7. Ozellik belirlendi: {selected_feature}")
        if resolution.user_breakdown and resolution.computer_breakdown:
            lines.append(
                "8. Performans hesaplandi: "
                f"Kullanici={resolution.user_breakdown.total}, Bilgisayar={resolution.computer_breakdown.total}"
            )
            lines.append(
                "9. Karsilastirma yapildi: "
                f"{resolution.explanation}"
            )
            lines.append(
                "10. Puan, enerji, moral ve deneyim guncellendi."
            )
            lines.append("11. Seviye kontrolu yapildi.")
            lines.append("12. Istatistikler kaydedildi.")
        else:
            lines.append("8. Performans hesaplanmadi; tur otomatik durum kuralina gore sonuclandi.")
            lines.append(f"9. Karsilastirma sonucu: {resolution.explanation}")
            lines.append("10. Puan, enerji, moral ve deneyim uygun kurala gore guncellendi.")
            lines.append("11. Seviye kontrolu yapildi.")
            lines.append("12. Istatistikler kaydedildi.")
        lines.append("-" * 48)
        self._append_log("\n".join(lines))

    def _append_log(self, text: str) -> None:
        current = self.log_box.toPlainText().strip()
        self.log_box.setPlainText(text if not current else f"{current}\n{text}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _select_user_card(self, card_id: int) -> None:
        if self.selected_user_card_id_value == card_id and self.detail_focus_owner == "user":
            return
        self.selected_user_card_id_value = card_id
        self.detail_focus_owner = "user"
        self._sync_card_widget_states()
        self.update_detail_panel()
        self._update_stage_panels()
        self._update_interaction_state()

    def _select_computer_card(self, card_id: int) -> None:
        if self.selected_computer_card_id_value == card_id and self.detail_focus_owner == "computer":
            return
        self.selected_computer_card_id_value = card_id
        self.detail_focus_owner = "computer"
        self._sync_card_widget_states()
        self.update_detail_panel()
        self._update_stage_panels()

    def _sync_card_widget_states(self) -> None:
        current_branch = self.game.current_branch() if self.game_started and not self.game.finished else None
        for card_id, widget in self.user_card_widgets.items():
            card = self._card_by_id(card_id)
            if card is None:
                continue
            widget.set_current_branch(current_branch is not None and card.branch == current_branch)
            widget.set_selected(card_id == self.selected_user_card_id_value)
        for card_id, widget in self.computer_card_widgets.items():
            card = self._card_by_id(card_id)
            if card is None:
                continue
            widget.set_current_branch(current_branch is not None and card.branch == current_branch)
            widget.set_selected(card_id == self.selected_computer_card_id_value)

    def _card_by_id(self, card_id: int | None):
        if card_id is None:
            return None
        all_cards = self.game.user.cards + self.game.computer.cards
        return next((card for card in all_cards if card.card_id == card_id), None)

    def _show_empty_detail_state(self) -> None:
        self.detail_image.setPixmap(create_card_back(240, 320))
        self.user_stage_image.setPixmap(create_card_back(240, 320))
        self.computer_stage_image.setPixmap(create_card_back(240, 320))
        self.user_stage_caption.setText("Kart secildiginde burada buyuk gorunur.")
        self.computer_stage_caption.setText("Bilgisayar karti burada gorunur.")
        if self.game_started:
            self.detail_box.setPlainText("Bir kart secerek detaylarini gorebilirsiniz.")
        else:
            self.detail_box.setPlainText("Oyun baslatildiginda kart detaylari burada gorunecek.")

    def _update_interaction_state(self) -> None:
        selected_card = self._selected_user_card()
        can_play = (
            self.game_started
            and not self.game.finished
            and selected_card is not None
            and selected_card.branch == self.game.current_branch()
        )
        self.play_button.setEnabled(can_play)

    def _update_stage_panels(self) -> None:
        user_card = self._selected_user_card() or self._card_by_id(self.last_user_card_id)
        computer_card = self._card_by_id(self.selected_computer_card_id_value) or self._card_by_id(
            self.last_computer_card_id
        )

        if user_card is None:
            self.user_stage_image.setPixmap(create_card_back(240, 320))
            self.user_stage_caption.setText("Kart secildiginde burada buyuk gorunur.")
        else:
            self.user_stage_image.setPixmap(
                create_card_pixmap(
                    user_card.player_name,
                    user_card.branch,
                    user_card.team_name,
                    user_card.ability_name,
                    user_card.image_path,
                    {
                        **user_card.base_attributes(),
                        "dayaniklilik": user_card.durability,
                        "ozel_yetenek_katsayisi": user_card.special_ability_coefficient,
                    },
                    user_card.energy,
                    user_card.max_energy,
                    user_card.level,
                    user_card.durability,
                    "Kullanildi" if user_card.used_in_league else ("Kritik" if user_card.is_critical() else "Hazir"),
                    220,
                    300,
                )
            )
            self.user_stage_caption.setText(
                f"{user_card.player_name} | {user_card.team_name} | {user_card.branch.value}"
            )

        if computer_card is None or not self.show_computer_checkbox.isChecked():
            self.computer_stage_image.setPixmap(create_card_back(240, 320))
            self.computer_stage_caption.setText("Bilgisayar karti gizli veya henuz secilmedi.")
        else:
            self.computer_stage_image.setPixmap(
                create_card_pixmap(
                    computer_card.player_name,
                    computer_card.branch,
                    computer_card.team_name,
                    computer_card.ability_name,
                    computer_card.image_path,
                    {
                        **computer_card.base_attributes(),
                        "dayaniklilik": computer_card.durability,
                        "ozel_yetenek_katsayisi": computer_card.special_ability_coefficient,
                    },
                    computer_card.energy,
                    computer_card.max_energy,
                    computer_card.level,
                    computer_card.durability,
                    "Kullanildi" if computer_card.used_in_league else ("Kritik" if computer_card.is_critical() else "Hazir"),
                    220,
                    300,
                )
            )
            self.computer_stage_caption.setText(
                f"{computer_card.player_name} | {computer_card.team_name} | {computer_card.branch.value}"
            )

    def update_detail_panel(self) -> None:
        if self.detail_focus_owner == "computer" and self.selected_computer_card_id_value is not None:
            if not self.show_computer_checkbox.isChecked():
                self.detail_image.setPixmap(create_card_back(240, 320))
                self.detail_box.setPlainText("Bilgisayar karti su anda gizli.")
                return
            computer_card = self._card_by_id(self.selected_computer_card_id_value)
            if computer_card is not None:
                self.detail_image.setPixmap(
                    create_card_pixmap(
                        computer_card.player_name,
                        computer_card.branch,
                        computer_card.team_name,
                        computer_card.ability_name,
                        computer_card.image_path,
                        self._card_stats(computer_card),
                        computer_card.energy,
                        computer_card.max_energy,
                        computer_card.level,
                        computer_card.durability,
                        self._card_status_text(computer_card).title(),
                        240,
                        320,
                    )
                )
                self.detail_box.setPlainText("\n".join(computer_card.detail_lines()))
                return
        user_card = self._selected_user_card()
        if user_card is not None:
            self.detail_image.setPixmap(
                create_card_pixmap(
                    user_card.player_name,
                    user_card.branch,
                    user_card.team_name,
                    user_card.ability_name,
                    user_card.image_path,
                    self._card_stats(user_card),
                    user_card.energy,
                    user_card.max_energy,
                    user_card.level,
                    user_card.durability,
                    self._card_status_text(user_card).title(),
                    240,
                    320,
                )
            )
            self.detail_box.setPlainText("\n".join(user_card.detail_lines()))
            return
        self._show_empty_detail_state()


from .professional_ui import MainWindow as MainWindow
