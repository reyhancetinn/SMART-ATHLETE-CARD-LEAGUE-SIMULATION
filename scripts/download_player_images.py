from __future__ import annotations

import json
import sys
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "assets" / "player_images"
USER_AGENT = "Mozilla/5.0 (compatible; CodexPlayerImageDownloader/1.0)"

PLAYER_PAGES = {
    "lionel_messi": "Lionel_Messi",
    "angel_di_maria": "Ángel_Di_María",
    "cristiano_ronaldo": "Cristiano_Ronaldo",
    "bruno_fernandes": "Bruno_Fernandes_(footballer,_born_1994)",
    "kylian_mbappe": "Kylian_Mbappé",
    "antoine_griezmann": "Antoine_Griezmann",
    "erling_haaland": "Erling_Haaland",
    "martin_odegaard": "Martin_Ødegaard",
    "lebron_james": "LeBron_James",
    "stephen_curry": "Stephen_Curry",
    "nikola_jokic": "Nikola_Jokić",
    "bogdan_bogdanovic": "Bogdan_Bogdanović_(basketball)",
    "kevin_durant": "Kevin_Durant",
    "jayson_tatum": "Jayson_Tatum",
    "luka_doncic": "Luka_Dončić",
    "goran_dragic": "Goran_Dragić",
    "melissa_vargas": "Melissa_Vargas",
    "eda_erdem": "Eda_Erdem_Dündar",
    "paola_egonu": "Paola_Egonu",
    "alessia_orro": "Alessia_Orro",
    "tijana_boskovic": "Tijana_Bošković",
    "maja_ognjenovic": "Maja_Ognjenović",
    "gabi_guimaraes": "Gabriela_Guimarães",
    "carol_gattaz": "Caroline_Gattaz",
}


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, context=ssl.create_default_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def download_binary(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, context=ssl.create_default_context()) as response:
        destination.write_bytes(response.read())


def find_image_url(title: str) -> str | None:
    encoded_title = urllib.parse.quote(title, safe="")
    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
    try:
        summary_data = fetch_json(summary_url)
        thumbnail = summary_data.get("thumbnail", {})
        if thumbnail.get("source"):
            return thumbnail["source"]
    except Exception:
        pass

    fallback_url = (
        "https://en.wikipedia.org/w/api.php?"
        f"action=query&prop=pageimages&format=json&pithumbsize=600&titles={encoded_title}"
    )
    try:
        fallback_data = fetch_json(fallback_url)
        pages = fallback_data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumbnail = page.get("thumbnail", {})
            if thumbnail.get("source"):
                return thumbnail["source"]
    except Exception:
        return None
    return None


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    requested = set(sys.argv[1:])
    items = PLAYER_PAGES.items() if not requested else [
        (slug, PLAYER_PAGES[slug]) for slug in PLAYER_PAGES if slug in requested
    ]
    for slug, title in items:
        destination = OUTPUT_DIR / f"{slug}.jpg"
        if destination.exists():
            print(f"SKIP {slug}: already exists")
            continue
        image_url = find_image_url(title)
        if not image_url:
            failed.append(slug)
            print(f"FAIL {slug}: image not found")
            continue
        try:
            download_binary(image_url, destination)
            print(f"OK {slug}: {destination}")
            time.sleep(1.6)
        except Exception as exc:
            failed.append(slug)
            print(f"FAIL {slug}: {exc}")
            time.sleep(2.5)

    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
