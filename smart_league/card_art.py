from __future__ import annotations

import hashlib
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QBrush,
)

from .constants import FEATURE_LABELS, Branch


def _seed_values(key: str) -> list[int]:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return list(digest)


def _branch_palette(branch: Branch) -> tuple[QColor, QColor, QColor]:
    if branch == Branch.FOOTBALL:
        return QColor("#76ff3b"), QColor("#132a1d"), QColor("#0e1511")
    if branch == Branch.BASKETBALL:
        return QColor("#ff9d2e"), QColor("#2a1f12"), QColor("#15110c")
    return QColor("#27d4ff"), QColor("#0f1d2b"), QColor("#0c1118")


def create_card_pixmap(
    player_name: str,
    branch: Branch,
    team_name: str,
    ability_name: str,
    image_path: str = "",
    stats: dict[str, int] | None = None,
    energy: int | None = None,
    max_energy: int | None = None,
    level: int | None = None,
    durability: int | None = None,
    status_text: str = "Hazir",
    width: int = 240,
    height: int = 320,
) -> QPixmap:
    base_width = 240
    base_height = 400
    target_width = max(1, width)
    target_height = max(1, height)
    pixmap = QPixmap(target_width, target_height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    scale = min(target_width / base_width, target_height / base_height)
    offset_x = (target_width - (base_width * scale)) / 2
    offset_y = (target_height - (base_height * scale)) / 2
    painter.translate(offset_x, offset_y)
    painter.scale(scale, scale)

    values = _seed_values(f"{player_name}|{team_name}|{branch.value}|{ability_name}")
    initials = "".join(part[0] for part in player_name.split()[:2]).upper()
    accent_color, top_color, panel_color = _branch_palette(branch)
    skin = [
        QColor("#f7d7c4"),
        QColor("#edc0a7"),
        QColor("#c98f72"),
        QColor("#8f5f47"),
    ][values[0] % 4]
    hair = [
        QColor("#4a2c2a"),
        QColor("#20140f"),
        QColor("#7a4d33"),
        QColor("#8d6e63"),
        QColor("#5f3562"),
    ][values[1] % 5]
    jersey = QColor.fromHsv((values[2] * 3) % 360, 120 + values[3] % 80, 220)

    outer_rect = QRectF(6, 6, base_width - 12, base_height - 12)
    background = QLinearGradient(0, 0, base_width, base_height)
    background.setColorAt(0.0, QColor("#23262b"))
    background.setColorAt(0.65, panel_color)
    background.setColorAt(1.0, QColor("#111318"))
    painter.setBrush(background)
    painter.setPen(QPen(QColor("#3b4350"), 2))
    painter.drawRoundedRect(outer_rect, 22, 22)
    painter.setPen(QPen(QColor(255, 255, 255, 36), 1))
    painter.drawRoundedRect(QRectF(14, 14, base_width - 28, base_height - 28), 18, 18)

    accent = QLinearGradient(0, 0, base_width, 0)
    accent.setColorAt(0.0, accent_color)
    accent.setColorAt(1.0, accent_color.lighter(115))
    painter.setBrush(accent)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(18, 18, base_width - 36, 6), 3, 3)

    painter.setPen(QColor("#f7f8fb"))
    title_font = QFont("Segoe UI", 9)
    title_font.setBold(True)
    title_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 120)
    painter.setFont(title_font)
    painter.drawText(QRectF(28, 28, base_width - 56, 22), Qt.AlignmentFlag.AlignCenter, branch.value.upper())
    painter.setBrush(QColor("#20252c"))
    painter.setPen(QPen(QColor("#495362"), 1))
    painter.drawEllipse(QRectF(base_width - 58, 22, 28, 28))
    badge_font = QFont("Segoe UI", 8)
    badge_font.setBold(True)
    painter.setFont(badge_font)
    painter.setPen(QColor("#dbe7f8"))
    painter.drawText(QRectF(base_width - 58, 22, 28, 28), Qt.AlignmentFlag.AlignCenter, initials)

    portrait_rect = QRectF(16, 54, base_width - 32, 160)
    painter.setBrush(QColor("#161C28"))
    painter.setPen(QPen(QColor("#4E5B71"), 1))
    painter.drawRoundedRect(portrait_rect, 22, 22)

    photo_loaded = _draw_player_photo(painter, image_path, portrait_rect)
    if not photo_loaded:
        _draw_stylized_portrait(painter, base_width, skin, hair, jersey)

    if ability_name and ability_name != "Yok":
        painter.setBrush(accent_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(22, 60, 84, 20), 10, 10)
        chip_font = QFont("Segoe UI", 6)
        chip_font.setBold(True)
        painter.setFont(chip_font)
        painter.setPen(QColor("#09121e"))
        painter.drawText(QRectF(22, 60, 84, 20), Qt.AlignmentFlag.AlignCenter, "YETENEK")

    name_font = QFont("Segoe UI", 12)
    name_font.setBold(True)
    painter.setFont(name_font)
    painter.setPen(QColor("#f4f6fb"))
    painter.drawText(QRectF(20, 220, base_width - 40, 34), Qt.TextFlag.TextWordWrap, player_name.upper())

    body_font = QFont("Segoe UI", 8)
    body_font.setBold(True)
    painter.setFont(body_font)
    painter.setPen(QColor("#D6DEEA"))
    painter.drawText(QRectF(20, 258, base_width - 40, 16), Qt.AlignmentFlag.AlignLeft, team_name.upper())

    energy_ratio = 0.0 if not max_energy else max(0.0, min(1.0, (energy or 0) / max_energy))
    painter.setPen(QColor("#C9D2E0"))
    painter.setFont(QFont("Segoe UI", 7, 700))
    painter.drawText(QRectF(20, 282, 112, 16), Qt.AlignmentFlag.AlignLeft, "ENERJI")
    painter.setPen(accent_color)
    painter.setFont(QFont("Segoe UI", 10, 800))
    painter.drawText(QRectF(base_width - 74, 280, 54, 18), Qt.AlignmentFlag.AlignRight, f"%{int(energy_ratio * 100)}")
    painter.setBrush(QColor("#232A3A"))
    painter.setPen(QPen(QColor("#41506A"), 1))
    painter.drawRoundedRect(QRectF(20, 300, base_width - 40, 10), 5, 5)
    painter.setBrush(accent_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(21, 301, (base_width - 42) * energy_ratio, 8), 4, 4)

    if status_text:
        painter.setPen(accent_color)
        painter.setFont(QFont("Segoe UI", 8, 700))
        painter.drawText(QRectF(20, 314, 120, 14), Qt.AlignmentFlag.AlignLeft, status_text.upper())
    painter.setPen(QColor("#7f8ea7"))
    painter.drawText(
        QRectF(base_width - 95, 314, 75, 14),
        Qt.AlignmentFlag.AlignRight,
        f"Seviye {level or 1}",
    )

    stat_items = _visible_stat_items(stats)
    _draw_stat_grid(painter, stat_items, accent_color)

    painter.end()
    return pixmap


def create_card_back(width: int = 240, height: int = 320) -> QPixmap:
    base_width = 240
    base_height = 400
    target_width = max(1, width)
    target_height = max(1, height)
    pixmap = QPixmap(target_width, target_height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    scale = min(target_width / base_width, target_height / base_height)
    offset_x = (target_width - (base_width * scale)) / 2
    offset_y = (target_height - (base_height * scale)) / 2
    painter.translate(offset_x, offset_y)
    painter.scale(scale, scale)
    gradient = QLinearGradient(0, 0, base_width, base_height)
    gradient.setColorAt(0.0, QColor("#161c28"))
    gradient.setColorAt(0.5, QColor("#0e1320"))
    gradient.setColorAt(1.0, QColor("#0b1018"))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor("#2f4c7b"), 2))
    painter.drawRoundedRect(QRectF(6, 6, base_width - 12, base_height - 12), 22, 22)
    painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
    painter.drawRoundedRect(QRectF(14, 14, base_width - 28, base_height - 28), 18, 18)
    shine = QLinearGradient(0, 0, base_width, base_height / 2)
    shine.setColorAt(0.0, QColor(255, 255, 255, 55))
    shine.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(shine)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(20, 20, base_width - 40, 90), 18, 18)
    painter.setPen(QPen(QColor("#5ea0ff"), 3))
    painter.drawEllipse(QRectF(base_width / 2 - 46, 110, 92, 92))
    painter.drawRoundedRect(QRectF(base_width / 2 - 70, 236, 140, 40), 14, 14)
    font = QFont("Segoe UI", 12)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#e4eeff"))
    painter.drawText(QRectF(30, 300, base_width - 60, 32), Qt.AlignmentFlag.AlignCenter, "Gizli Kart")
    painter.end()
    return pixmap


def _draw_branch_accent(painter: QPainter, branch: Branch, width: int, values: list[int]) -> None:
    center_x = width // 2
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#ffffff"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if branch == Branch.FOOTBALL:
        painter.drawEllipse(QRectF(center_x - 22, 206, 44, 44))
        painter.drawLine(center_x - 22, 228, center_x + 22, 228)
        painter.drawLine(center_x, 206, center_x, 250)
    elif branch == Branch.BASKETBALL:
        painter.drawEllipse(QRectF(center_x - 22, 206, 44, 44))
        painter.drawLine(center_x - 22, 228, center_x + 22, 228)
        painter.drawArc(QRectF(center_x - 28, 206, 56, 44), 90 * 16, 180 * 16)
        painter.drawArc(QRectF(center_x - 28, 206, 56, 44), -90 * 16, 180 * 16)
    else:
        painter.drawEllipse(QRectF(center_x - 21, 208, 42, 42))
        painter.setPen(QPen(QColor("#ffffff"), 3))
        for offset in (-10, -3, 4, 11):
            painter.drawLine(center_x - 18, 228 + offset, center_x + 18, 214 + offset)


def _visible_stat_items(stats: dict[str, int] | None) -> list[tuple[str, int]]:
    items = list((stats or {}).items())
    preferred_order = [
        "penalti",
        "serbest_vurus",
        "kaleci_karsi_karsiya",
        "ucluk",
        "ikilik",
        "serbest_atis",
        "servis",
        "blok",
        "smac",
        "dayaniklilik",
    ]
    ordered: list[tuple[str, int]] = []
    for name in preferred_order:
        for item in items:
            if item[0] == name and item not in ordered:
                ordered.append(item)
    for item in items:
        if item not in ordered and item[0] != "ozel_yetenek_katsayisi":
            ordered.append(item)
    visible = ordered[:4]
    while len(visible) < 4:
        visible.append((f"stat_{len(visible)}", 0))
    return visible


def _draw_player_photo(painter: QPainter, image_path: str, rect: QRectF) -> bool:
    if not image_path:
        return False
    path = Path(image_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    if not path.exists():
        return False
    photo = QPixmap(str(path))
    if photo.isNull():
        return False

    scaled = photo.scaled(
        int(rect.width()),
        int(rect.height()),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    clip = QPainterPath()
    clip.addRoundedRect(rect, 22, 22)
    painter.save()
    painter.setClipPath(clip)
    x = rect.x() + (rect.width() - scaled.width()) / 2
    y = rect.y()
    painter.drawPixmap(int(x), int(y), scaled)
    overlay = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    overlay.setColorAt(0.0, QColor(255, 255, 255, 12))
    overlay.setColorAt(1.0, QColor(0, 0, 0, 18))
    painter.fillRect(rect, QBrush(overlay))
    painter.restore()
    return True


def _draw_stylized_portrait(
    painter: QPainter,
    width: int,
    skin: QColor,
    hair: QColor,
    jersey: QColor,
) -> None:
    circle_center = QPointF(width / 2, 126)
    painter.setBrush(QColor("#fff6fb"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(circle_center, 70, 70)

    head_rect = QRectF(width / 2 - 26, 72, 52, 56)
    painter.setBrush(skin)
    painter.drawEllipse(head_rect)

    hair_path = QPainterPath()
    hair_path.addEllipse(QRectF(width / 2 - 29, 67, 58, 40))
    painter.setBrush(hair)
    painter.drawPath(hair_path)
    painter.drawRect(QRectF(width / 2 - 28, 88, 56, 12))

    painter.setBrush(skin.darker(105))
    painter.drawRoundedRect(QRectF(width / 2 - 10, 120, 20, 18), 6, 6)

    painter.setBrush(jersey)
    torso_path = QPainterPath()
    torso_path.moveTo(width / 2 - 48, 190)
    torso_path.quadTo(width / 2, 142, width / 2 + 48, 190)
    torso_path.lineTo(width / 2 + 34, 252)
    torso_path.lineTo(width / 2 - 34, 252)
    torso_path.closeSubpath()
    painter.drawPath(torso_path)

    painter.setBrush(QColor("#fff8fb"))
    painter.drawRect(QRectF(width / 2 - 4, 163, 8, 52))
    painter.drawEllipse(QRectF(width / 2 - 20, 150, 40, 30))
    painter.setBrush(QColor(255, 255, 255, 90))
    painter.drawEllipse(QRectF(width / 2 - 42, 86, 24, 24))


def _draw_stat_grid(
    painter: QPainter,
    stat_items: list[tuple[str, int]],
    accent_color: QColor,
) -> None:
    start_x = 20
    start_y = 332
    gap = 10
    box_width = (240 - 40 - gap) / 2
    box_height = 30
    for index, (name, value) in enumerate(stat_items[:4]):
        x = start_x + (index % 2) * (box_width + gap)
        y = start_y + (index // 2) * (box_height + 8)
        rect = QRectF(x, y, box_width, box_height)
        painter.setBrush(QColor("#1B2434"))
        painter.setPen(QPen(QColor(accent_color), 1))
        painter.drawRoundedRect(rect, 10, 10)
        label = FEATURE_LABELS.get(name, name.replace("_", " ").title()).upper()
        painter.setPen(QColor("#D9E2F1"))
        label_font = QFont("Segoe UI", 7)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.drawText(QRectF(x + 8, y + 4, box_width - 16, 10), Qt.AlignmentFlag.AlignLeft, label[:16])
        painter.setPen(QColor("#F7F9FD"))
        value_font = QFont("Segoe UI", 12)
        value_font.setBold(True)
        painter.setFont(value_font)
        painter.drawText(
            QRectF(x + 6, y + 11, box_width - 12, 15),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            str(value),
        )
