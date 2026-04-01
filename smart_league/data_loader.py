from __future__ import annotations

import csv
from pathlib import Path

from .constants import Branch
from .models import Basketballer, Footballer, SportCard, Volleyballer


class DataValidationError(Exception):
    """Veri dosyasi hatalarini temsil eder."""


class DataLoader:
    REQUIRED_FIELDS = {
        "tur",
        "sporcu_adi",
        "takim_adi",
        "brans",
        "ozellik_a",
        "ozellik_b",
        "ozellik_c",
        "dayaniklilik",
        "enerji",
        "ozel_yetenek",
    }

    def load_cards(self, file_path: str | Path) -> list[SportCard]:
        path = Path(file_path)
        if not path.exists():
            raise DataValidationError(f"Veri dosyasi bulunamadi: {path}")
        if path.suffix.lower() not in {".csv", ".txt"}:
            raise DataValidationError("Veri dosyasi .csv veya .txt olmalidir.")

        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise DataValidationError("Veri dosyasi baslik satiri icermiyor.")
            missing = self.REQUIRED_FIELDS - set(reader.fieldnames)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise DataValidationError(f"Eksik sutunlar: {missing_text}")

            cards: list[SportCard] = []
            for row_index, row in enumerate(reader, start=2):
                cards.append(self._parse_row(row, row_index))

        self._validate_distribution(cards)
        return cards

    def _parse_row(self, row: dict[str, str], row_index: int) -> SportCard:
        try:
            card_type = row["tur"].strip().lower()
            branch = Branch(row["brans"].strip())
            name = row["sporcu_adi"].strip()
            team = row["takim_adi"].strip()
            attr_a = int(row["ozellik_a"])
            attr_b = int(row["ozellik_b"])
            attr_c = int(row["ozellik_c"])
            durability = int(row["dayaniklilik"])
            energy = int(row["enerji"])
            ability_name = row["ozel_yetenek"].strip() or "Yok"
            raw_coefficient = row.get("ozel_yetenek_katsayisi", "").strip()
            ability_coefficient = int(raw_coefficient) if raw_coefficient else 10
            image_path = row.get("gorsel", "").strip()
        except Exception as exc:
            raise DataValidationError(f"{row_index}. satir okunamadi: {exc}") from exc

        numeric_values = [attr_a, attr_b, attr_c, durability, energy, ability_coefficient]
        if any(value < 0 for value in numeric_values):
            raise DataValidationError(f"{row_index}. satirda negatif deger var.")
        if energy == 0:
            raise DataValidationError(f"{row_index}. satirda baslangic enerjisi 0 olamaz.")
        if ability_coefficient == 0:
            raise DataValidationError(f"{row_index}. satirda ozel yetenek katsayisi 0 olamaz.")

        card_id = row_index - 1
        common_kwargs = dict(
            card_id=card_id,
            player_name=name,
            team_name=team,
            branch=branch,
            durability=durability,
            energy=energy,
            max_energy=energy,
            ability_name=ability_name,
            special_ability_coefficient=ability_coefficient,
            image_path=image_path,
        )

        if card_type == "futbolcu":
            return Footballer(
                **common_kwargs,
                penalti=attr_a,
                serbest_vurus=attr_b,
                kaleci_karsi_karsiya=attr_c,
            )
        if card_type == "basketbolcu":
            return Basketballer(
                **common_kwargs,
                ucluk=attr_a,
                ikilik=attr_b,
                serbest_atis=attr_c,
            )
        if card_type == "voleybolcu":
            return Volleyballer(
                **common_kwargs,
                servis=attr_a,
                blok=attr_b,
                smac=attr_c,
            )

        raise DataValidationError(f"{row_index}. satirda gecersiz sporcu tipi: {row['tur']}")

    def _validate_distribution(self, cards: list[SportCard]) -> None:
        if len(cards) != 24:
            raise DataValidationError("Toplam kart sayisi tam olarak 24 olmalidir.")

        counts = {branch: 0 for branch in Branch}
        for card in cards:
            counts[card.branch] += 1

        for branch, count in counts.items():
            if count != 8:
                raise DataValidationError(f"{branch.value} kart sayisi 8 olmalidir, bulunan: {count}")


VeriOkuyucu = DataLoader
