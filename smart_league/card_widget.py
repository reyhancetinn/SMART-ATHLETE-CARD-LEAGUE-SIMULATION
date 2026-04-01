from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from .card_art import create_card_back, create_card_pixmap
from .constants import Branch, FEATURE_LABELS


ACCENT_PINK = QColor("#FF3EA5")
ACCENT_SOFT = QColor("#FF79C8")
ACCENT_GREEN = QColor("#64FFB4")
ACCENT_RED = QColor("#FF5C75")


class CardWidget(QWidget):
    clicked = pyqtSignal(int)

    def __init__(self, *, compact: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.compact = compact
        self.interactive = True
        self.card_id: int | None = None
        self.energy = 100
        self.max_energy = 100
        self.branch: Branch | None = None
        self.owner_morale = 60
        self.selected = False
        self.current_branch = False
        self.reveal = True
        self.status_text = "HAZIR"
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(292, 468 if compact else 560)

        self.panel = QFrame(self)
        self.panel.setObjectName("CardPanel")
        self.panel.setGeometry(self._target_rect())

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(ACCENT_SOFT)
        self.panel.setGraphicsEffect(self.shadow)

        self.animation = QPropertyAnimation(self.panel, b"geometry", self)
        self.animation.setDuration(140)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedHeight(360 if compact else 430)

        self.caption_label = QLabel("Kart secildiginde bilgiler gorunecek.")
        self.caption_label.setWordWrap(True)
        self.caption_label.setObjectName("CaptionLabel")

        layout.addWidget(self.preview_label)
        layout.addWidget(self.caption_label)

        self._refresh_style()
        self.set_placeholder()

    def _target_rect(self) -> QRect:
        inactive = 10 if self.compact else 14
        active = 3 if self.compact else 6
        inset = active if self.selected or self.current_branch else inactive
        return QRect(inset, inset, self.width() - inset * 2, self.height() - inset * 2)

    def resizeEvent(self, event) -> None:
        self.panel.setGeometry(self._target_rect())
        super().resizeEvent(event)

    def enterEvent(self, event) -> None:
        if self.interactive:
            self._animate(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self.interactive:
            self._animate(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.interactive and self.card_id is not None:
            self.clicked.emit(self.card_id)
        super().mousePressEvent(event)

    def _animate(self, hovered: bool) -> None:
        self.animation.stop()
        current = self.panel.geometry()
        if hovered:
            end_rect = QRect(2, 2, self.width() - 4, self.height() - 4)
        else:
            end_rect = self._target_rect()
        self.animation.setStartValue(current)
        self.animation.setEndValue(end_rect)
        self.animation.start()

    def set_placeholder(self) -> None:
        self.card_id = None
        self.preview_label.setPixmap(create_card_back(self.preview_label.width(), self.preview_label.height()))
        self.caption_label.setText("Kart bekleniyor")
        self._refresh_style()

    def set_data(
        self,
        *,
        card_id: int,
        player_name: str,
        team_name: str,
        branch: Branch,
        ability_name: str,
        image_path: str,
        stats: dict[str, int],
        energy: int,
        max_energy: int,
        level: int,
        durability: int,
        status_text: str,
        selected: bool,
        current_branch: bool,
        owner_morale: int,
        reveal: bool,
    ) -> None:
        self.card_id = card_id
        self.energy = energy
        self.max_energy = max_energy
        self.branch = branch
        self.owner_morale = owner_morale
        self.selected = selected
        self.current_branch = current_branch
        self.reveal = reveal
        self.status_text = status_text

        if reveal:
            pixmap = create_card_pixmap(
                player_name,
                branch,
                team_name,
                ability_name,
                image_path,
                stats,
                energy,
                max_energy,
                level,
                durability,
                status_text,
                self.preview_label.width(),
                self.preview_label.height(),
            )
            caption = (
                f"{player_name}\n"
                f"{team_name} | {branch.value}\n"
                f"{self._stat_summary(stats)}\n"
                f"Enerji {energy}/{max_energy} | Lv {level} | {ability_name}"
            )
        else:
            pixmap = create_card_back(self.preview_label.width(), self.preview_label.height())
            caption = "Gizli Kart\nBilgisayar Eli"

        self.preview_label.setPixmap(pixmap)
        self.caption_label.setText(caption)
        self._refresh_style()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.panel.setGeometry(self._target_rect())
        self._refresh_style()

    def set_current_branch(self, current_branch: bool) -> None:
        self.current_branch = current_branch
        self.panel.setGeometry(self._target_rect())
        self._refresh_style()

    def set_interactive(self, interactive: bool) -> None:
        self.interactive = interactive
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if interactive else Qt.CursorShape.ArrowCursor
        )
        self._refresh_style()

    def _refresh_style(self) -> None:
        border_color = ACCENT_SOFT
        glow_color = ACCENT_SOFT
        background = "#151D30"
        if self.energy < 20 and self.card_id is not None:
            border_color = ACCENT_RED
            glow_color = ACCENT_RED
        elif self.owner_morale >= 80:
            glow_color = ACCENT_GREEN
        if self.current_branch:
            border_color = ACCENT_PINK
        if self.selected:
            border_color = ACCENT_PINK
            glow_color = ACCENT_PINK
            background = "#1F1731"

        if not self.interactive:
            glow_color = QColor("#273042")
        self.shadow.setColor(glow_color)
        self.shadow.setBlurRadius(28 if self.selected else 18 if self.current_branch else 12)
        self.panel.setStyleSheet(
            f"""
            QFrame#CardPanel {{
                background: {background};
                border: {3 if self.selected else 2}px solid {border_color.name()};
                border-radius: 20px;
            }}
            QLabel {{
                color: #FFF7FB;
                font-weight: 700;
            }}
            QLabel#CaptionLabel {{
                color: #F4EAF1;
                font-size: 13px;
                font-weight: 600;
                line-height: 1.4;
            }}
            """
        )

    def _stat_summary(self, stats: dict[str, int]) -> str:
        visible = []
        for name, value in stats.items():
            if name in {"dayaniklilik", "ozel_yetenek_katsayisi"}:
                continue
            label = FEATURE_LABELS.get(name, name.replace("_", " ").title())
            visible.append(f"{label}: {value}")
            if len(visible) == 2:
                break
        return " | ".join(visible)
