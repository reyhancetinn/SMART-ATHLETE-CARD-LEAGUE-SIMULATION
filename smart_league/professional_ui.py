from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .card_art import create_card_back, create_card_pixmap
from .card_widget import CardWidget
from .constants import FEATURE_LABELS, Branch, Difficulty, FeatureMode
from .data_loader import DataValidationError
from .game import GameManager, RoundResolution


MAIN_BG = "#090E1A"
SECTION_BG = "#101726"
CARD_BG = "#151D30"
ACCENT = "#FF3EA5"
ACCENT_SOFT = "#FF79C8"
TEXT_PRIMARY = "#F7F3FF"
TEXT_SECONDARY = "#BFC7D5"
SOFT_BORDER = "rgba(255, 62, 165, 0.35)"


def _apply_shadow(widget: QWidget, color: str, blur: int = 30, alpha: int = 90) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 8)
    glow = QColor(color)
    glow.setAlpha(alpha)
    effect.setColor(glow)
    widget.setGraphicsEffect(effect)


class MetricCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("MetricValue")
        self.meta_label = QLabel("Hazır")
        self.meta_label.setObjectName("MetricMeta")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.meta_label)

    def update_content(self, value: str, meta: str = "") -> None:
        self.value_label.setText(value)
        self.meta_label.setText(meta or " ")


class HeaderBar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        self.title_label = QLabel("Akıllı Sporcu Kart Ligi")
        self.title_label.setObjectName("HeaderTitle")
        self.subtitle_label = QLabel("Akıllı kart seçimi, lig akışı, enerji ve moral yönetimi")
        self.subtitle_label.setObjectName("HeaderSubtitle")
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.subtitle_label)
        layout.addLayout(title_column, 1)

        badge_layout = QGridLayout()
        badge_layout.setHorizontalSpacing(10)
        badge_layout.setVerticalSpacing(10)
        self.badges = {
            "round": self._make_badge("Tur Bekleniyor", True),
            "branch": self._make_badge("Branş Bekleniyor", True),
            "difficulty": self._make_badge("Zorluk: -", False),
            "mode": self._make_badge("Özellik Modu: -", False),
        }
        badge_layout.addWidget(self.badges["round"], 0, 0)
        badge_layout.addWidget(self.badges["branch"], 0, 1)
        badge_layout.addWidget(self.badges["difficulty"], 1, 0)
        badge_layout.addWidget(self.badges["mode"], 1, 1)
        layout.addLayout(badge_layout)

    def _make_badge(self, text: str, highlight: bool) -> QLabel:
        label = QLabel(text)
        label.setObjectName("BadgePrimary" if highlight else "BadgeSecondary")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def update_status(self, round_text: str, branch_text: str, difficulty: str, mode: str) -> None:
        self.badges["round"].setText(round_text)
        self.badges["branch"].setText(branch_text)
        self.badges["difficulty"].setText(f"Zorluk: {difficulty}")
        self.badges["mode"].setText(f"Özellik Modu: {mode}")


class ControlPanel(QFrame):
    def __init__(self, initial_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionCard")
        self._selected_path = initial_path
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        self.title_label = QLabel("Kontrol Merkezi")
        self.title_label.setObjectName("SectionTitle")
        self.subtitle_label = QLabel("Dosya seçimi ve oyun ayarları için kompakt kontrol çekmecesi")
        self.subtitle_label.setObjectName("SectionSubtitle")
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.subtitle_label)

        self.file_status_label = QLabel()
        self.file_status_label.setObjectName("FileStatus")
        self.browse_button = QPushButton("Dosya Seç")
        self.start_button = QPushButton("Yeni Oyun Başlat")
        self.collapse_button = QToolButton()
        self.collapse_button.setText("Gelişmiş Ayarlar")
        self.collapse_button.setCheckable(True)
        self.collapse_button.setChecked(True)
        self.collapse_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._sync_toggle_text(True)

        header_row.addLayout(title_column, 1)
        header_row.addWidget(self.file_status_label, 0)
        header_row.addWidget(self.browse_button, 0)
        header_row.addWidget(self.start_button, 0)
        header_row.addWidget(self.collapse_button, 0)
        layout.addLayout(header_row)

        self.advanced_body = QFrame()
        self.advanced_body.setObjectName("InnerPanel")
        advanced_layout = QGridLayout(self.advanced_body)
        advanced_layout.setContentsMargins(14, 14, 14, 14)
        advanced_layout.setHorizontalSpacing(12)
        advanced_layout.setVerticalSpacing(12)
        self.turn_time_combo = QComboBox()
        self.turn_time_combo.addItem("Kapalı", 0)
        self.turn_time_combo.addItem("10 sn", 10)
        self.turn_time_combo.addItem("15 sn", 15)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems([Difficulty.EASY.value, Difficulty.MEDIUM.value])
        self.feature_mode_combo = QComboBox()
        self.feature_mode_combo.addItems([FeatureMode.RANDOM.value, FeatureMode.USER_CHOICE.value])
        self.feature_select_label = QLabel("Seçilecek Özellik")
        self.feature_select_label.setObjectName("FieldLabel")
        self.feature_select_combo = QComboBox()
        self.show_computer_checkbox = QCheckBox("Bilgisayar kartlarını göster")

        advanced_layout.addWidget(self._field("Zorluk"), 0, 0)
        advanced_layout.addWidget(self.difficulty_combo, 0, 1)
        advanced_layout.addWidget(self._field("Özellik Modu"), 0, 2)
        advanced_layout.addWidget(self.feature_mode_combo, 0, 3)
        advanced_layout.addWidget(self.feature_select_label, 1, 0)
        advanced_layout.addWidget(self.feature_select_combo, 1, 1, 1, 2)
        advanced_layout.addWidget(self.show_computer_checkbox, 1, 3)
        advanced_layout.addWidget(self._field("Tur Süresi"), 2, 0)
        advanced_layout.addWidget(self.turn_time_combo, 2, 1)
        layout.addWidget(self.advanced_body)

        self.set_file_path(initial_path)
        self.collapse_button.toggled.connect(self._toggle_advanced)

    def _field(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _sync_toggle_text(self, expanded: bool) -> None:
        self.collapse_button.setArrowType(
            Qt.ArrowType.UpArrow if expanded else Qt.ArrowType.DownArrow
        )

    def _toggle_advanced(self, expanded: bool) -> None:
        self.advanced_body.setVisible(expanded)
        self._sync_toggle_text(expanded)

    def set_file_path(self, path: str) -> None:
        self._selected_path = path
        filename = Path(path).name if path else "Dosya seçilmedi"
        self.file_status_label.setText(f"Dosya: {filename} yüklendi" if path else "Dosya seçilmedi")
        self.file_status_label.setToolTip(path)

    def file_path(self) -> str:
        return self._selected_path

    def set_feature_mode_manual(self, manual: bool) -> None:
        self.feature_select_label.setVisible(manual)
        self.feature_select_combo.setVisible(manual)
        self.feature_select_combo.setEnabled(manual)


class SummaryPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Maç Durumu")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Skor, moral, enerji ve branş dağılımı tek bakışta izlenir")
        subtitle.setObjectName("SectionSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(12)
        metrics_grid.setVerticalSpacing(12)
        self.tiles = {
            "user_score": MetricCard("Kullanıcı Skoru"),
            "computer_score": MetricCard("Bilgisayar Skoru"),
            "turn": MetricCard("Aktif Tur"),
            "branch": MetricCard("Sıradaki Branş"),
            "user_morale": MetricCard("Kullanıcı Morali"),
            "computer_morale": MetricCard("Bilgisayar Morali"),
            "user_energy": MetricCard("Kullanıcı Enerjisi"),
            "computer_energy": MetricCard("Bilgisayar Enerjisi"),
        }
        positions = [
            ("user_score", 0, 0),
            ("computer_score", 0, 1),
            ("turn", 0, 2),
            ("branch", 0, 3),
            ("user_morale", 1, 0),
            ("computer_morale", 1, 1),
            ("user_energy", 1, 2),
            ("computer_energy", 1, 3),
        ]
        for key, row, col in positions:
            metrics_grid.addWidget(self.tiles[key], row, col)
        layout.addLayout(metrics_grid)

        distribution_frame = QFrame()
        distribution_frame.setObjectName("InnerPanel")
        distribution_layout = QHBoxLayout(distribution_frame)
        distribution_layout.setContentsMargins(14, 12, 14, 12)
        distribution_layout.setSpacing(10)
        self.branch_distribution_labels: dict[Branch, QLabel] = {}
        for branch in Branch:
            label = QLabel()
            label.setObjectName("BranchPill")
            distribution_layout.addWidget(label, 1)
            self.branch_distribution_labels[branch] = label
        layout.addWidget(distribution_frame)

    def update_summary(
        self,
        *,
        round_number: int,
        branch_text: str,
        user_score: int,
        computer_score: int,
        user_morale: int,
        computer_morale: int,
        user_energy_total: int,
        computer_energy_total: int,
        user_branch_counts: dict[Branch, int],
        computer_branch_counts: dict[Branch, int],
    ) -> None:
        self.tiles["user_score"].update_content(str(user_score), "Lig puanı")
        self.tiles["computer_score"].update_content(str(computer_score), "Rakip puanı")
        self.tiles["turn"].update_content(str(round_number), "Sabit tur akışı")
        self.tiles["branch"].update_content(branch_text, "Sıradaki mücadele")
        self.tiles["user_morale"].update_content(str(user_morale), "Takım morali")
        self.tiles["computer_morale"].update_content(str(computer_morale), "Takım morali")
        self.tiles["user_energy"].update_content(str(user_energy_total), "Kalan toplam enerji")
        self.tiles["computer_energy"].update_content(str(computer_energy_total), "Kalan toplam enerji")
        for branch, label in self.branch_distribution_labels.items():
            label.setText(
                f"{branch.value}: Kullanıcı {user_branch_counts[branch]} | Bilgisayar {computer_branch_counts[branch]}"
            )


class StageCardPanel(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StagePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("StagePanelTitle")
        self.image_label = QLabel()
        self.image_label.setObjectName("StageImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(280, 390)
        self.caption_label = QLabel("Kart seçildiğinde burada büyük görünür.")
        self.caption_label.setObjectName("StageCaption")
        self.caption_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.caption_label)

    def show_placeholder(self, message: str) -> None:
        self.image_label.setPixmap(create_card_back(280, 390))
        self.caption_label.setText(message)

    def show_card(self, card, status_text: str) -> None:
        self.image_label.setPixmap(
            create_card_pixmap(
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
                280,
                390,
            )
        )
        self.caption_label.setText(
            f"{card.player_name}\n{card.team_name} | {card.branch.value}\nEnerji {card.energy}/{card.max_energy} | Seviye {card.level}"
        )


class MatchScenePanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.user_panel = StageCardPanel("Kullanıcı Kartı")
        self.computer_panel = StageCardPanel("Bilgisayar Kartı")

        self.center_panel = QFrame()
        self.center_panel.setObjectName("BattlePanel")
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setContentsMargins(18, 18, 18, 18)
        center_layout.setSpacing(10)
        self.title_label = QLabel("Maç Konsolu")
        self.title_label.setObjectName("SectionTitle")
        self.branch_label = QLabel("Sıradaki Branş: -")
        self.branch_label.setObjectName("BattleHeadline")
        self.computer_line = QLabel("Bilgisayar | Skor: 0 | Moral: 60 | Enerji: 0")
        self.computer_line.setObjectName("BattleLineDanger")
        self.user_line = QLabel("Sen | Skor: 0 | Moral: 60 | Enerji: 0")
        self.user_line.setObjectName("BattleLineSuccess")
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("BattleConsole")
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Tur akışı, sonuçlar ve karar mekanizması burada görünür.")
        center_layout.addWidget(self.title_label)
        center_layout.addWidget(self.branch_label)
        center_layout.addWidget(self.computer_line)
        center_layout.addWidget(self.user_line)
        center_layout.addWidget(self.log_box, 1)

        layout.addWidget(self.user_panel, 4)
        layout.addWidget(self.center_panel, 7)
        layout.addWidget(self.computer_panel, 4)

    def update_status(self, branch_text: str, computer_line: str, user_line: str) -> None:
        self.branch_label.setText(branch_text)
        self.computer_line.setText(computer_line)
        self.user_line.setText(user_line)


class CardSectionWidget(QFrame):
    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("SectionSubtitle")
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.subtitle_label)
        self.count_badge = QLabel("0 Kart")
        self.count_badge.setObjectName("BadgeSecondary")
        header_row.addLayout(title_column, 1)
        header_row.addWidget(self.count_badge, 0)

        self.grid_host = QWidget()
        self.grid_host.setObjectName("CardGridHost")
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(18)

        layout.addLayout(header_row)
        layout.addWidget(self.grid_host)

    def populate(
        self,
        *,
        cards: list,
        selected_card_id: int | None,
        current_branch: Branch | None,
        owner_morale: int,
        reveal: bool,
        click_handler,
        interactive: bool,
        empty_text: str,
    ) -> dict[int, CardWidget]:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        widgets: dict[int, CardWidget] = {}
        self.count_badge.setText(f"{len(cards)} Kart")
        if not cards:
            empty_label = QLabel(empty_text)
            empty_label.setObjectName("EmptyLabel")
            empty_label.setWordWrap(True)
            self.grid.addWidget(empty_label, 0, 0)
            return widgets

        for index, card in enumerate(cards):
            widget = CardWidget(compact=True)
            widget.set_interactive(interactive)
            widget.set_data(
                card_id=card.card_id,
                player_name=card.player_name,
                team_name=card.team_name,
                branch=card.branch,
                ability_name=card.ability_name,
                image_path=card.image_path,
                stats={
                    **card.base_attributes(),
                    "dayaniklilik": card.durability,
                    "ozel_yetenek_katsayisi": card.special_ability_coefficient,
                },
                energy=card.energy,
                max_energy=card.max_energy,
                level=card.level,
                durability=card.durability,
                status_text="KULLANILDI" if card.used_in_league else ("KRITIK" if card.is_critical() else "HAZIR"),
                selected=card.card_id == selected_card_id,
                current_branch=current_branch is not None and card.branch == current_branch,
                owner_morale=owner_morale,
                reveal=reveal,
            )
            if interactive and click_handler is not None:
                widget.clicked.connect(click_handler)
            self.grid.addWidget(widget, index // 3, index % 3)
            widgets[card.card_id] = widget
        return widgets


class ScrollableCardArea(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Kart Koleksiyonu")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Tüm kullanıcı kartları branşa göre gruplanır; alanda dikey kaydırma zorunludur.")
        subtitle.setObjectName("SectionSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("CollectionScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumHeight(560)

        self.content = QWidget()
        self.content.setObjectName("ScrollableViewport")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(14)

        self.user_sections = {
            Branch.FOOTBALL: CardSectionWidget("Futbol Kartları", "Sıradaki futbol turları için oynanabilir kartlar"),
            Branch.BASKETBALL: CardSectionWidget("Basketbol Kartları", "Atış ve ikilik/üçlük odaklı kart seçimi"),
            Branch.VOLLEYBALL: CardSectionWidget("Voleybol Kartları", "Servis, blok ve smaç odaklı kart seti"),
        }
        for branch in Branch:
            self.content_layout.addWidget(self.user_sections[branch])

        self.computer_section = CardSectionWidget(
            "Bilgisayar Kartları",
            "Göster seçeneği açıksa bilgisayarın mevcut eli burada görünür.",
        )
        self.content_layout.addWidget(self.computer_section)
        self.content_layout.addStretch(1)
        self.scroll_area.setWidget(self.content)
        layout.addWidget(self.scroll_area)

        self.user_card_widgets: dict[int, CardWidget] = {}
        self.computer_card_widgets: dict[int, CardWidget] = {}

    def populate(
        self,
        *,
        user_cards_by_branch: dict[Branch, list],
        computer_cards: list,
        show_computer: bool,
        current_branch: Branch | None,
        user_morale: int,
        computer_morale: int,
        selected_user_card_id: int | None,
        selected_computer_card_id: int | None,
        user_click_handler,
        computer_click_handler,
    ) -> None:
        self.user_card_widgets = {}
        for branch, section in self.user_sections.items():
            widgets = section.populate(
                cards=user_cards_by_branch[branch],
                selected_card_id=selected_user_card_id,
                current_branch=current_branch,
                owner_morale=user_morale,
                reveal=True,
                click_handler=user_click_handler,
                interactive=True,
                empty_text="Bu branşta kullanılabilir kart kalmadı.",
            )
            self.user_card_widgets.update(widgets)

        self.computer_section.setVisible(show_computer)
        self.computer_section.subtitle_label.setText(
            "Göster seçeneği açıksa bilgisayarın mevcut eli sadece görüntülenir; seçim yapılamaz."
        )
        if show_computer:
            self.computer_card_widgets = self.computer_section.populate(
                cards=computer_cards,
                selected_card_id=selected_computer_card_id,
                current_branch=current_branch,
                owner_morale=computer_morale,
                reveal=True,
                click_handler=None,
                interactive=False,
                empty_text="Bilgisayarın kullanılabilir kartı kalmadı.",
            )
        else:
            self.computer_card_widgets = {}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.game = GameManager()
        self.game_started = False
        self.selected_user_card_id_value: int | None = None
        self.selected_computer_card_id_value: int | None = None
        self.detail_focus_owner = "user"
        self.displayed_user_card_id: int | None = None
        self.displayed_computer_card_id: int | None = None
        self.turn_timer = QTimer(self)
        self.turn_timer.setSingleShot(True)
        self.turn_timer.timeout.connect(self._handle_turn_timeout)
        self.default_data_file = str(Path(__file__).resolve().parent.parent / "data" / "sporcular.csv")

        self.setWindowTitle("Akıllı Sporcu Kart Ligi")
        self.resize(1600, 950)
        self.setMinimumSize(1380, 860)

        self._build_ui()
        self._connect_signals()
        self.control_panel.set_file_path(self.default_data_file)
        self.data_path_input.setText(self.default_data_file)
        self._apply_styles()
        self._apply_effects()
        self._show_empty_detail_state()
        self._update_feature_mode_visibility()
        self._update_interaction_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        self.header_bar = HeaderBar()
        self.control_panel = ControlPanel(self.default_data_file)
        self.control_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.data_path_input = QLineEdit()
        self.data_path_input.hide()
        self.user_table = self._create_hidden_table()
        self.computer_table = self._create_hidden_table()

        self.page_scroll = QScrollArea()
        self.page_scroll.setObjectName("PageScroll")
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        page = QWidget()
        page.setObjectName("ScrollableViewport")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(14)

        self.summary_panel = SummaryPanel()
        self.match_scene = MatchScenePanel()
        self.card_area = ScrollableCardArea()

        self.action_bar = QFrame()
        self.action_bar.setObjectName("SectionCard")
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(18, 14, 18, 14)
        action_layout.setSpacing(12)
        action_title = QLabel("Tur Komutları")
        action_title.setObjectName("SectionTitle")
        action_subtitle = QLabel("Seçili kart yalnızca sıradaki branş için oynatılabilir.")
        action_subtitle.setObjectName("SectionSubtitle")
        action_text = QVBoxLayout()
        action_text.setSpacing(2)
        action_text.addWidget(action_title)
        action_text.addWidget(action_subtitle)
        self.play_button = QPushButton("Seçili Kartı Oyna")
        action_layout.addLayout(action_text, 1)
        action_layout.addWidget(self.play_button, 0)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        detail_panel = QFrame()
        detail_panel.setObjectName("SectionCard")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(12)
        detail_title = QLabel("Kart Detayı")
        detail_title.setObjectName("SectionTitle")
        self.detail_image = QLabel()
        self.detail_image.setObjectName("DetailCardImage")
        self.detail_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_image.setMinimumSize(340, 480)
        self.detail_box = QPlainTextEdit()
        self.detail_box.setObjectName("InfoConsole")
        self.detail_box.setReadOnly(True)
        detail_layout.addWidget(detail_title)
        detail_layout.addWidget(self.detail_image)
        detail_layout.addWidget(self.detail_box)

        performance_panel = QFrame()
        performance_panel.setObjectName("SectionCard")
        performance_layout = QVBoxLayout(performance_panel)
        performance_layout.setContentsMargins(16, 16, 16, 16)
        performance_layout.setSpacing(12)
        performance_title = QLabel("Dinamik Puan Hesaplama")
        performance_title.setObjectName("SectionTitle")
        self.performance_box = QPlainTextEdit()
        self.performance_box.setObjectName("InfoConsole")
        self.performance_box.setReadOnly(True)
        self.performance_box.setPlaceholderText("Tur oynandığında performans formülü burada açılır.")
        performance_layout.addWidget(performance_title)
        performance_layout.addWidget(self.performance_box)

        report_panel = QFrame()
        report_panel.setObjectName("SectionCard")
        report_layout = QVBoxLayout(report_panel)
        report_layout.setContentsMargins(16, 16, 16, 16)
        report_layout.setSpacing(12)
        report_title = QLabel("Lig Sonu Özeti")
        report_title.setObjectName("SectionTitle")
        self.report_box = QPlainTextEdit()
        self.report_box.setObjectName("InfoConsole")
        self.report_box.setReadOnly(True)
        self.report_box.setPlaceholderText("Lig tamamlandığında özet ve kazanan burada görünür.")
        report_layout.addWidget(report_title)
        report_layout.addWidget(self.report_box)

        bottom_row.addWidget(detail_panel, 4)
        bottom_row.addWidget(performance_panel, 4)
        bottom_row.addWidget(report_panel, 4)

        page_layout.addWidget(self.summary_panel)
        page_layout.addWidget(self.match_scene)
        page_layout.addWidget(self.action_bar)
        page_layout.addWidget(self.card_area)
        page_layout.addLayout(bottom_row)
        page_layout.addStretch(1)

        self.page_scroll.setWidget(page)
        outer.addWidget(self.header_bar)
        outer.addWidget(self.control_panel)
        outer.addWidget(self.page_scroll, 1)

        self.browse_button = self.control_panel.browse_button
        self.start_button = self.control_panel.start_button
        self.difficulty_combo = self.control_panel.difficulty_combo
        self.feature_mode_combo = self.control_panel.feature_mode_combo
        self.turn_time_combo = self.control_panel.turn_time_combo
        self.feature_select_combo = self.control_panel.feature_select_combo
        self.show_computer_checkbox = self.control_panel.show_computer_checkbox
        self.log_box = self.match_scene.log_box
        self.user_stage_image = self.match_scene.user_panel.image_label
        self.computer_stage_image = self.match_scene.computer_panel.image_label
        self.user_stage_caption = self.match_scene.user_panel.caption_label
        self.computer_stage_caption = self.match_scene.computer_panel.caption_label
        self.turn_chip = self.header_bar.badges["round"]
        self.branch_chip = self.header_bar.badges["branch"]
        self.difficulty_chip = self.header_bar.badges["difficulty"]
        self.mode_chip = self.header_bar.badges["mode"]
        self.user_card_widgets = {}
        self.computer_card_widgets = {}

    def _connect_signals(self) -> None:
        self.browse_button.clicked.connect(self._browse_file)
        self.start_button.clicked.connect(self.start_game)
        self.play_button.clicked.connect(self.play_selected_card)
        self.show_computer_checkbox.toggled.connect(self.refresh_tables)
        self.feature_mode_combo.currentTextChanged.connect(self._update_feature_mode_visibility)
        self.turn_time_combo.currentIndexChanged.connect(self._update_turn_timer_for_current_state)

    def _create_hidden_table(self) -> QTableWidget:
        table = QTableWidget(0, 9)
        table.setHorizontalHeaderLabels(
            ["Kart", "ID", "Ad", "Takım", "Branş", "Enerji", "Seviye", "Yetenek", "Durum"]
        )
        table.setVisible(False)
        return table

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget#Root {{
                background: {MAIN_BG};
                color: {TEXT_PRIMARY};
                font-family: "Segoe UI";
            }}
            QFrame#HeaderBar, QFrame#SectionCard, QFrame#BattlePanel, QFrame#StagePanel, QFrame#InnerPanel {{
                background: {SECTION_BG};
                border: 1px solid {SOFT_BORDER};
                border-radius: 16px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
            QLabel#HeaderTitle {{
                font-size: 28px;
                font-weight: 800;
            }}
            QLabel#HeaderSubtitle, QLabel#SectionSubtitle, QLabel#MetricMeta, QLabel#StageCaption, QLabel#EmptyLabel {{
                color: {TEXT_SECONDARY};
                font-size: 12px;
            }}
            QLabel#SectionTitle {{
                font-size: 16px;
                font-weight: 800;
                color: {TEXT_PRIMARY};
            }}
            QLabel#BadgePrimary {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_SOFT});
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 13px;
                padding: 10px 16px;
                font-size: 12px;
                font-weight: 800;
                min-width: 150px;
            }}
            QLabel#BadgeSecondary, QLabel#BranchPill, QLabel#FileStatus {{
                background: {CARD_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {SOFT_BORDER};
                border-radius: 13px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#FieldLabel, QLabel#MetricTitle {{
                color: {TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel#MetricValue {{
                color: {TEXT_PRIMARY};
                font-size: 22px;
                font-weight: 800;
            }}
            QFrame#MetricCard {{
                background: {CARD_BG};
                border: 1px solid {SOFT_BORDER};
                border-radius: 14px;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_SOFT});
                color: white;
                border: none;
                border-radius: 14px;
                padding: 12px 18px;
                font-size: 13px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: #ff5eb4;
            }}
            QPushButton:pressed {{
                background: #e23190;
            }}
            QPushButton:disabled {{
                background: #48334a;
                color: #c6adc1;
            }}
            QComboBox, QPlainTextEdit, QLineEdit {{
                background: {CARD_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {SOFT_BORDER};
                border-radius: 12px;
                padding: 10px 12px;
                selection-background-color: {ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QToolButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {SOFT_BORDER};
                border-radius: 12px;
                padding: 10px 12px;
                font-weight: 700;
            }}
            QCheckBox {{
                color: {TEXT_PRIMARY};
                spacing: 8px;
                font-weight: 700;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid {SOFT_BORDER};
                background: {CARD_BG};
            }}
            QCheckBox::indicator:checked {{
                background: {ACCENT};
                border: 1px solid {ACCENT_SOFT};
            }}
            QLabel#BattleHeadline {{
                color: {TEXT_PRIMARY};
                font-size: 20px;
                font-weight: 800;
            }}
            QLabel#BattleLineDanger {{
                color: #ff9da7;
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#BattleLineSuccess {{
                color: #9dffbf;
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#StagePanelTitle {{
                font-size: 15px;
                font-weight: 800;
                color: {TEXT_PRIMARY};
            }}
            QLabel#StageImage, QLabel#DetailCardImage {{
                background: {CARD_BG};
                border: 1px solid rgba(255, 121, 200, 0.55);
                border-radius: 18px;
                padding: 10px;
            }}
            QPlainTextEdit#BattleConsole, QPlainTextEdit#InfoConsole {{
                background: rgba(10, 15, 28, 0.98);
                border: 1px solid {SOFT_BORDER};
                border-radius: 16px;
                padding: 12px;
                font-size: 12px;
            }}
            QScrollArea#PageScroll, QScrollArea#CollectionScroll {{
                background: transparent;
                border: none;
            }}
            QWidget#ScrollableViewport, QWidget#CardGridHost {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: rgba(14, 18, 29, 0.95);
                width: 12px;
                margin: 4px 2px 4px 2px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {ACCENT};
                border-radius: 6px;
                min-height: 26px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

    def _apply_effects(self) -> None:
        _apply_shadow(self.header_bar, ACCENT_SOFT, 40, 80)
        _apply_shadow(self.control_panel, ACCENT, 32, 70)
        _apply_shadow(self.summary_panel, ACCENT_SOFT, 26, 55)
        _apply_shadow(self.match_scene, ACCENT, 32, 60)
        _apply_shadow(self.action_bar, ACCENT_SOFT, 26, 55)
        _apply_shadow(self.card_area, ACCENT, 26, 55)

    def _browse_file(self) -> None:
        base_dir = str(Path(self.data_path_input.text() or self.default_data_file).parent)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Veri Dosyası Seç",
            base_dir,
            "CSV Files (*.csv);;Text Files (*.txt)",
        )
        if path:
            self.data_path_input.setText(path)
            self.control_panel.set_file_path(path)

    def _update_feature_mode_visibility(self) -> None:
        manual = self.feature_mode_combo.currentText() == FeatureMode.USER_CHOICE.value
        self.control_panel.set_feature_mode_manual(manual)

    def start_game(self) -> None:
        self._reset_turn_timer()
        try:
            self.game.start_new_game(
                self.data_path_input.text().strip(),
                Difficulty(self.difficulty_combo.currentText()),
                FeatureMode(self.feature_mode_combo.currentText()),
            )
        except (DataValidationError, ValueError) as exc:
            QMessageBox.critical(self, "Başlatma Hatası", str(exc))
            return

        self.game_started = True
        self.selected_user_card_id_value = None
        self.selected_computer_card_id_value = None
        self.detail_focus_owner = "user"
        self.displayed_user_card_id = None
        self.displayed_computer_card_id = None
        self.log_box.clear()
        self.report_box.clear()
        self.performance_box.clear()
        self._append_log(self._start_flow_text())
        self.refresh_all()
        self._update_turn_timer_for_current_state()

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
        branch_text = self.game.current_branch().value if not self.game.finished else "Lig Tamamlandı"

        self.header_bar.update_status(
            f"Tur {self.game.round_number}",
            branch_text,
            self.difficulty_combo.currentText(),
            self.feature_mode_combo.currentText(),
        )
        self.summary_panel.update_summary(
            round_number=self.game.round_number,
            branch_text=branch_text,
            user_score=self.game.user.score,
            computer_score=self.game.computer.score,
            user_morale=self.game.user.morale,
            computer_morale=self.game.computer.morale,
            user_energy_total=user_energy_total,
            computer_energy_total=computer_energy_total,
            user_branch_counts={branch: len(self.game.user.available_cards(branch)) for branch in Branch},
            computer_branch_counts={branch: len(self.game.computer.available_cards(branch)) for branch in Branch},
        )
        self.match_scene.update_status(
            self._match_scene_branch_text(branch_text),
            f"Bilgisayar | Skor: {self.game.computer.score} | Moral: {self.game.computer.morale} | Enerji: {computer_energy_total}",
            f"Sen | Skor: {self.game.user.score} | Moral: {self.game.user.morale} | Enerji: {user_energy_total}",
        )

    def refresh_feature_combo(self) -> None:
        self.feature_select_combo.clear()
        branch = self.game.current_branch()
        for attribute in self.game.branch_features(branch):
            self.feature_select_combo.addItem(FEATURE_LABELS[attribute], attribute)

    def refresh_tables(self) -> None:
        self.selected_user_card_id_value = self._preferred_user_card_id(self.selected_user_card_id_value)
        self.selected_computer_card_id_value = self._visible_computer_card_id()
        self._populate_hidden_table(self.user_table, self.game.user.available_cards(), reveal=True)
        self._populate_hidden_table(
            self.computer_table,
            self.game.computer.available_cards(),
            reveal=self.show_computer_checkbox.isChecked(),
        )
        current_branch = self.game.current_branch() if self.game_started and not self.game.finished else None
        self.card_area.populate(
            user_cards_by_branch={branch: self.game.user.available_cards(branch) for branch in Branch},
            computer_cards=self.game.computer.available_cards(),
            show_computer=self.show_computer_checkbox.isChecked(),
            current_branch=current_branch,
            user_morale=self.game.user.morale,
            computer_morale=self.game.computer.morale,
            selected_user_card_id=self.selected_user_card_id_value,
            selected_computer_card_id=self.selected_computer_card_id_value,
            user_click_handler=self._select_user_card,
            computer_click_handler=None,
        )
        self.user_card_widgets = self.card_area.user_card_widgets
        self.computer_card_widgets = self.card_area.computer_card_widgets
        if self.detail_focus_owner == "computer" and not self.show_computer_checkbox.isChecked():
            self.detail_focus_owner = "user"
        self._sync_card_widget_states()
        self._update_stage_panels()
        self._update_interaction_state()

    def _populate_hidden_table(self, table: QTableWidget, cards: list, reveal: bool) -> None:
        table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            thumb_item = QTableWidgetItem()
            thumb_item.setIcon(QIcon(self._card_thumbnail(card, reveal)))
            table.setItem(row, 0, thumb_item)
            values = [
                str(card.card_id),
                card.player_name if reveal else "Gizli Kart",
                card.team_name if reveal else "-",
                card.branch.value,
                f"{card.energy}/{card.max_energy}" if reveal else "?",
                str(card.level) if reveal else "?",
                card.ability_name if reveal else "?",
                self._card_status_text(card) if reveal else "Gizli",
            ]
            for column_offset, value in enumerate(values, start=1):
                table.setItem(row, column_offset, QTableWidgetItem(value))

    def _card_thumbnail(self, card, reveal: bool) -> QPixmap:
        if reveal:
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
                self._card_status_text(card),
                110,
                148,
            )
        return create_card_back(110, 148)

    def _preferred_user_card_id(self, preferred_card_id: int | None) -> int | None:
        cards = self.game.user.available_cards()
        if not cards:
            return None
        if self._has_stale_resolved_turn():
            return None
        available_ids = {card.card_id for card in cards}
        if preferred_card_id in available_ids:
            return preferred_card_id
        if self.game_started and not self.game.finished:
            branch_cards = self.game.user.available_cards(self.game.current_branch())
            if branch_cards:
                return branch_cards[0].card_id
        return cards[0].card_id

    def _visible_computer_card_id(self) -> int | None:
        active_computer_card = self._resolved_turn_computer_card()
        if active_computer_card is None:
            return None
        cards = self.game.computer.available_cards()
        available_ids = {card.card_id for card in cards}
        if active_computer_card.card_id in available_ids:
            return active_computer_card.card_id
        return None

    def _active_turn_resolution(self) -> RoundResolution | None:
        return self.game.active_turn_state.resolution

    def _has_stale_resolved_turn(self) -> bool:
        resolution = self._active_turn_resolution()
        return resolution is not None and resolution.round_number != self.game.round_number

    def _match_scene_branch_text(self, current_branch_text: str) -> str:
        resolution = self._active_turn_resolution()
        if resolution is not None:
            return f"Aktif Tur {resolution.round_number}: {resolution.branch.value}"
        if self.game_started and not self.game.finished:
            return f"Sıradaki Branş: {current_branch_text}"
        return "Sıradaki Branş: -"

    def _resolved_turn_user_card(self):
        resolution = self._active_turn_resolution()
        return resolution.user_card if resolution is not None else None

    def _resolved_turn_computer_card(self):
        resolution = self._active_turn_resolution()
        return resolution.computer_card if resolution is not None else None

    def _clear_completed_turn_snapshot(self) -> None:
        if not self._has_stale_resolved_turn():
            return
        self.game.clear_active_turn_state()
        self.selected_computer_card_id_value = None
        self.displayed_user_card_id = None
        self.displayed_computer_card_id = None

    def selected_user_card_id(self) -> int | None:
        selected_card = self._selected_user_card()
        if selected_card is None or selected_card.branch != self.game.current_branch():
            return None
        return selected_card.card_id

    def _selected_user_card(self):
        return self._card_by_id(self.selected_user_card_id_value)

    def _selected_valid_user_card_id(self) -> int | None:
        selected_card = self._selected_user_card()
        if (
            selected_card is not None
            and selected_card.branch == self.game.current_branch()
            and selected_card.can_play()
        ):
            return selected_card.card_id
        return None

    def _turn_duration_seconds(self) -> int:
        return int(self.turn_time_combo.currentData() or 0)

    def _reset_turn_timer(self) -> None:
        self.turn_timer.stop()

    def _update_turn_timer_for_current_state(self) -> None:
        self._reset_turn_timer()
        if not self.game_started or self.game.finished:
            return
        duration_seconds = self._turn_duration_seconds()
        if duration_seconds <= 0:
            return
        self.turn_timer.start(duration_seconds * 1000)

    def _register_ui_note(self, message: str) -> None:
        self.game.statistics.add_note(message)

    def _apply_invalid_selection_penalty(self) -> None:
        self.game.user.score = max(0, self.game.user.score - 5)
        message = "Gecersiz kart secimi: kullanici skorundan 5 puan dusuruldu."
        self._append_log(message)
        self._register_ui_note(message)
        QMessageBox.warning(self, "Geçersiz Seçim", message)
        self.refresh_summary()

    def _handle_wrong_branch_selection(self) -> None:
        message = (
            f"Uyari: Bu tur sadece {self.game.current_branch().value} branşına ait kart seçebilirsin."
        )
        QMessageBox.warning(self, "Yanlış Branş", message)
        self._append_log(message)

    def _finalize_round(self, resolution: RoundResolution) -> None:
        self.refresh_all()
        self._assert_active_turn_sync(resolution)
        self._log_resolution(resolution)
        self._show_performance_breakdown(resolution)

    def _handle_turn_timeout(self) -> None:
        if not self.game_started or self.game.finished:
            self._reset_turn_timer()
            return

        branch_cards = self.game.user.available_cards(self.game.current_branch())
        selected_card = self._selected_user_card()
        selected_card_id = self._selected_valid_user_card_id()

        if selected_card_id is not None:
            self._append_log("Sure asimi: secili kart otomatik oynatildi.")
        elif branch_cards:
            auto_card = branch_cards[0]
            self.selected_user_card_id_value = auto_card.card_id
            self.detail_focus_owner = "user"
            self._sync_card_widget_states()
            self.update_detail_panel()
            self._update_stage_panels()
            selected_card_id = auto_card.card_id
            self._append_log("Sure asimi: kullanici icin otomatik kart secildi.")
        else:
            selected_card_id = -1
            self._append_log(
                "Sure asimi: kullanicinin uygun karti olmadigi icin tur mevcut kuralla devam etti."
            )

        resolution = self._play_round_with_auto_computer_response(selected_card_id)
        if resolution is None:
            self._update_turn_timer_for_current_state()
            return

        self._finalize_round(resolution)

        if self.game.finished or (not self.game.user.available_cards() and not self.game.computer.available_cards()):
            self.game.finished = True
            self._reset_turn_timer()
            winner_text = self.game.winner_summary()
            self.report_box.setPlainText(
                "\n".join(
                    [
                        "Lig sonu raporu gösterildi.",
                        winner_text,
                        "",
                        self.game.match_summary_text(),
                    ]
                )
            )
            self._append_log(
                "\n".join(
                    [
                        "13. Tüm kartlar bittiğinde lig sonu raporu gösterildi.",
                        f"14. {winner_text}",
                    ]
                )
            )
            QMessageBox.information(self, "Oyun Sonu", winner_text)
            return

        self._update_turn_timer_for_current_state()

    def play_selected_card(self) -> None:
        if self.game.finished:
            return

        branch_cards = self.game.user.available_cards(self.game.current_branch())
        selected_card = self._selected_user_card()
        selected_card_id = self._selected_valid_user_card_id()
        if selected_card is not None and selected_card.branch != self.game.current_branch() and branch_cards:
            self._handle_wrong_branch_selection()
            return

        if selected_card_id is None and branch_cards:
            self._apply_invalid_selection_penalty()
            return

        if selected_card_id is None:
            selected_card_id = -1

        self._reset_turn_timer()
        resolution = self._play_round_with_auto_computer_response(selected_card_id)
        if resolution is None:
            self._update_turn_timer_for_current_state()
            return

        self._finalize_round(resolution)

        if self.game.finished or (not self.game.user.available_cards() and not self.game.computer.available_cards()):
            self.game.finished = True
            self._reset_turn_timer()
            winner_text = self.game.winner_summary()
            self.report_box.setPlainText(
                "\n".join(
                    [
                        "Lig sonu raporu gösterildi.",
                        winner_text,
                        "",
                        self.game.match_summary_text(),
                    ]
                )
            )
            self._append_log(
                "\n".join(
                    [
                        "13. Tüm kartlar bittiğinde lig sonu raporu gösterildi.",
                        f"14. {winner_text}",
                    ]
                )
            )
            QMessageBox.information(self, "Oyun Sonu", winner_text)
            return

        self._update_turn_timer_for_current_state()

    def _resolve_human_turn_card_id(self) -> int | None:
        return self.selected_user_card_id()

    def _play_round_with_auto_computer_response(
        self,
        selected_card_id: int,
    ) -> RoundResolution | None:
        attribute = None
        if self.feature_mode_combo.currentText() == FeatureMode.USER_CHOICE.value:
            attribute = self.feature_select_combo.currentData()
        try:
            return self.game.play_round(selected_card_id, attribute)
        except ValueError as exc:
            QMessageBox.warning(self, "Tur Hatası", str(exc))
            return None

    def _start_flow_text(self) -> str:
        return "\n".join(
            [
                "OYUN AKIŞI",
                "1. Sporcu verileri dosyadan okundu.",
                "2. Kart destesi oluşturuldu.",
                "3. Kartlar dağıtıldı.",
                f"4. Kullanıcı zorluk seçti: {self.difficulty_combo.currentText()}",
                "5. Tur sırası belirlendi: Futbol -> Basketbol -> Voleybol",
            ]
        )

    def _show_performance_breakdown(self, resolution: RoundResolution) -> None:
        if not resolution.user_breakdown or not resolution.computer_breakdown:
            self.performance_box.setPlainText("Bu tur için performans hesabı yok.")
            return
        selected_feature = FEATURE_LABELS.get(
            resolution.attribute_name or resolution.user_breakdown.attribute_name,
            resolution.attribute_name or "-",
        )
        lines = [
            f"DİNAMİK PUAN HESAPLAMA - {selected_feature}",
            "",
            f"Kullanıcı: {resolution.user_card.label() if resolution.user_card else '-'}",
            f"Temel Özellik: +{resolution.user_breakdown.base_value}",
            f"Moral Bonusu: {resolution.user_breakdown.moral_bonus:+}",
            f"Özel Yetenek Bonusu: {resolution.user_breakdown.ability_bonus:+}",
            f"Enerji Kaybı Cezası: -{resolution.user_breakdown.energy_penalty}",
            f"Seviye Bonusu: {resolution.user_breakdown.level_bonus:+}",
            f"Toplam Puan: {resolution.user_breakdown.total}",
            f"Enerji Açıklaması: {self._energy_explanation(resolution.user_breakdown.base_value, resolution.user_breakdown.energy_at_calculation)}",
            "",
            f"Bilgisayar: {resolution.computer_card.label() if resolution.computer_card else '-'}",
            f"Temel Özellik: +{resolution.computer_breakdown.base_value}",
            f"Moral Bonusu: {resolution.computer_breakdown.moral_bonus:+}",
            f"Özel Yetenek Bonusu: {resolution.computer_breakdown.ability_bonus:+}",
            f"Enerji Kaybı Cezası: -{resolution.computer_breakdown.energy_penalty}",
            f"Seviye Bonusu: {resolution.computer_breakdown.level_bonus:+}",
            f"Toplam Puan: {resolution.computer_breakdown.total}",
            f"Enerji Açıklaması: {self._energy_explanation(resolution.computer_breakdown.base_value, resolution.computer_breakdown.energy_at_calculation)}",
            "",
            "Formül:",
            "Güncel Özellik = Temel Özellik + Moral Bonusu + Özel Yetenek Bonusu - Enerji Kaybı Cezası + Seviye Bonusu",
            "",
            "Enerji Aralıkları:",
            "Enerji > 70 -> Ceza uygulanmaz",
            "40 <= Enerji <= 70 -> İlgili özellik puanından %10 düşülür",
            "0 < Enerji < 40 -> İlgili özellik puanından %20 düşülür",
            "Enerji = 0 -> Kart oynatılamaz",
        ]
        self.performance_box.setPlainText("\n".join(lines))

    def _energy_explanation(self, base_value: int, energy: int) -> str:
        if energy > 70:
            return f"Enerji {energy}. 70'ten büyük olduğu için ceza yok; temel özellikten düşüş yapılmadı."
        if 40 <= energy <= 70:
            penalty = round(base_value * 0.10)
            return f"Enerji {energy}. %10 ceza uygulandı; {base_value} temel özellikten {penalty} puan düşürüldü."
        if 0 < energy < 40:
            penalty = round(base_value * 0.20)
            return f"Enerji {energy}. %20 ceza uygulandı; {base_value} temel özellikten {penalty} puan düşürüldü."
        return "Enerji 0. Kart oynatılamaz."

    def _log_resolution(self, resolution: RoundResolution) -> None:
        self._assert_active_turn_sync(resolution)
        selected_feature = FEATURE_LABELS[resolution.attribute_name] if resolution.attribute_name else "-"
        lines = [
            f"{resolution.round_number}. tur - {resolution.branch.value}",
            f"5. Tur sırası: {resolution.branch.value}",
        ]
        if resolution.user_card and resolution.computer_card:
            lines.append(
                "6. Kullanıcı ve bilgisayar kartlarını seçti: "
                f"Kullanıcı={resolution.user_card.label()} | Bilgisayar={resolution.computer_card.label()}"
            )
        elif resolution.winner or resolution.outcome_type in {"skip", "forfeit"}:
            lines.append("6. Kart seçim kontrolü yapıldı: uygun branş kartlarına göre tur sonucu belirlendi.")
        lines.extend(resolution.debug_messages)
        lines.append(f"7. Özellik belirlendi: {selected_feature}")
        if resolution.user_breakdown and resolution.computer_breakdown:
            lines.append(
                "8. Performans hesaplandı: "
                f"Kullanıcı={resolution.user_breakdown.total}, Bilgisayar={resolution.computer_breakdown.total}"
            )
            lines.append(f"9. Karşılaştırma yapıldı: {resolution.explanation}")
        else:
            lines.append("8. Performans hesaplanmadı; tur otomatik durum kuralına göre sonuçlandı.")
            lines.append(f"9. Karşılaştırma sonucu: {resolution.explanation}")
        lines.append("10. Puan, enerji, moral ve deneyim güncellendi.")
        lines.append("11. Seviye kontrolü yapıldı.")
        lines.append("12. İstatistikler kaydedildi.")
        lines.append("-" * 52)
        self._append_log("\n".join(lines))

    def _append_log(self, text: str) -> None:
        current = self.log_box.toPlainText().strip()
        self.log_box.setPlainText(text if not current else f"{current}\n{text}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _select_user_card(self, card_id: int) -> None:
        self._clear_completed_turn_snapshot()
        self.selected_user_card_id_value = card_id
        self.detail_focus_owner = "user"
        self._sync_card_widget_states()
        self.update_detail_panel()
        self._update_stage_panels()
        self._update_interaction_state()

    def _select_computer_card(self, card_id: int) -> None:
        resolution = self._active_turn_resolution()
        if resolution is None or resolution.computer_card is None:
            return
        self.selected_computer_card_id_value = resolution.computer_card.card_id
        self.detail_focus_owner = "computer"
        self._sync_card_widget_states()
        self.update_detail_panel()
        self._update_stage_panels()

    def _sync_card_widget_states(self) -> None:
        current_branch = self.game.current_branch() if self.game_started and not self.game.finished else None
        for card_id, widget in self.user_card_widgets.items():
            card = self._card_by_id(card_id)
            if card is not None:
                widget.set_current_branch(current_branch is not None and card.branch == current_branch)
                widget.set_selected(card_id == self.selected_user_card_id_value)
        for card_id, widget in self.computer_card_widgets.items():
            card = self._card_by_id(card_id)
            if card is not None:
                widget.set_current_branch(current_branch is not None and card.branch == current_branch)
                widget.set_selected(card_id == self.selected_computer_card_id_value)

    def _card_by_id(self, card_id: int | None):
        if card_id is None:
            return None
        all_cards = self.game.user.cards + self.game.computer.cards
        return next((card for card in all_cards if card.card_id == card_id), None)

    def _card_status_text(self, card) -> str:
        resolution = self._active_turn_resolution()
        if resolution is not None and (
            resolution.user_card is card or resolution.computer_card is card
        ):
            return "Aktif Tur"
        if card.used_in_league:
            return "Kullanıldı"
        if card.is_critical():
            return "Kritik"
        return "Hazır"

    def _assert_active_turn_sync(self, resolution: RoundResolution) -> None:
        active_state = self.game.active_turn_state
        if active_state.resolution is not resolution:
            raise RuntimeError("UI ve engine farklı RoundResolution nesneleri kullanıyor.")
        if active_state.user_card is not resolution.user_card:
            raise RuntimeError("UI ve engine kullanıcı kartı için farklı referans kullanıyor.")
        if active_state.computer_card is not resolution.computer_card:
            raise RuntimeError("UI ve engine bilgisayar kartı için farklı referans kullanıyor.")
        if resolution.user_card is not None and resolution.user_card.branch != resolution.branch:
            raise RuntimeError("Aktif kullanıcı kartı mevcut branş ile uyuşmuyor.")
        if resolution.computer_card is not None and resolution.computer_card.branch != resolution.branch:
            raise RuntimeError("Aktif bilgisayar kartı mevcut branş ile uyuşmuyor.")

    def _render_detail_card(self, card) -> None:
        self.detail_image.setPixmap(
            create_card_pixmap(
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
                self._card_status_text(card),
                340,
                480,
            )
        )
        self.detail_box.setPlainText("\n".join(card.detail_lines()))

    def _show_empty_detail_state(self) -> None:
        self.detail_image.setPixmap(create_card_back(340, 480))
        self.match_scene.user_panel.show_placeholder("Oynanabilir bir kart secildiginde burada buyuk gorunur.")
        self.match_scene.computer_panel.show_placeholder("Bilgisayarin aktif karti tur oynandiginda burada gorunur.")
        if self.game_started:
            self.detail_box.setPlainText("Bir kart secerek detaylarini gorebilirsiniz.")
        else:
            self.detail_box.setPlainText("Oyun baslatildiginda kart detaylari burada gorunecek.")

    def _update_interaction_state(self) -> None:
        can_play = self.game_started and not self.game.finished
        self.play_button.setEnabled(can_play)

    def _update_stage_panels(self) -> None:
        resolution = self._active_turn_resolution()
        user_card = self._resolved_turn_user_card()
        computer_card = self._resolved_turn_computer_card()

        if user_card is None:
            selected_card = self._selected_user_card()
            if selected_card is not None and selected_card.branch == self.game.current_branch():
                user_card = selected_card

        if user_card is None:
            self.match_scene.user_panel.show_placeholder("Oynanabilir bir kart secildiginde burada buyuk gorunur.")
            self.displayed_user_card_id = None
        else:
            self.match_scene.user_panel.show_card(user_card, self._card_status_text(user_card))
            self.displayed_user_card_id = user_card.card_id

        if computer_card is None:
            self.match_scene.computer_panel.show_placeholder("Bilgisayarin aktif karti tur oynandiginda burada gorunur.")
            self.displayed_computer_card_id = None
        else:
            self.match_scene.computer_panel.show_card(computer_card, self._card_status_text(computer_card))
            self.displayed_computer_card_id = computer_card.card_id

        if resolution is not None:
            self._assert_active_turn_sync(resolution)
            if resolution.user_card is not None and self.displayed_user_card_id != resolution.user_card.card_id:
                raise RuntimeError("UI'da gösterilen kullanıcı kartı ile engine kartı farklı.")
            if resolution.computer_card is not None and self.displayed_computer_card_id != resolution.computer_card.card_id:
                raise RuntimeError("UI'da gösterilen bilgisayar kartı ile engine kartı farklı.")

    def update_detail_panel(self) -> None:
        if self.detail_focus_owner == "computer":
            computer_card = self._resolved_turn_computer_card()
            if computer_card is not None:
                self._render_detail_card(computer_card)
                return

        resolution = self._active_turn_resolution()
        if resolution is not None and resolution.user_card is not None:
            self._assert_active_turn_sync(resolution)
            self._render_detail_card(resolution.user_card)
            return

        user_card = self._selected_user_card()
        if user_card is not None:
            self._render_detail_card(user_card)
            return

        self._show_empty_detail_state()

