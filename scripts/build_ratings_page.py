"""Merge research/*.json into ratings-page/items.json and copy compressed images.

Run from the repo root:  python scripts/build_ratings_page.py
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
PAGE = ROOT / "ratings-page"
OUT_IMAGES = PAGE / "images"

# Region order on the page
FILES = ["kl.json", "bangkok.json", "chiang-mai.json", "siem-reap.json", "wildcards.json"]
MAX_WIDTH = 900


def compress(src: Path, dest: Path) -> bool:
    try:
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > MAX_WIDTH:
                im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
            im.save(dest, "JPEG", quality=78, optimize=True, progressive=True)
        return True
    except Exception as e:  # broken download, HTML error page, etc.
        print(f"  ! bad image {src.name}: {e}")
        return False


def main():
    OUT_IMAGES.mkdir(parents=True, exist_ok=True)
    items, seen = [], set()
    for name in FILES:
        path = RESEARCH / name
        if not path.exists():
            print(f"missing {name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"{name}: {len(data)} items")
        for item in data:
            if item["id"] in seen:
                print(f"  ! duplicate id {item['id']}")
                continue
            seen.add(item["id"])
            img = item.get("image")
            if img:
                src = ROOT / img
                dest = OUT_IMAGES / (item["id"] + ".jpg")
                if src.exists() and src.stat().st_size > 15_000 and compress(src, dest):
                    item["image"] = "images/" + dest.name
                else:
                    print(f"  ! no usable image for {item['id']}")
                    item["image"] = None
            items.append(item)
    (PAGE / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT_IMAGES.glob("*.jpg"))
    print(f"\n{len(items)} items, {sum(1 for i in items if i.get('image'))} with images, images total {total/1e6:.1f} MB")


if __name__ == "__main__":
    main()
