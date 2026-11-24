"""Build docs/data/trip.json (the itinerary website's data) and docs/images.

Inputs:
  plan/site-config.json        hand-written: trip title, city meta, legs, checklist, practical, questions
  plan/itinerary-draft.md      which stops came from the traveler's own plan ("(planned")
  research/details-<city>.json detailed days and stops from the research agents
  research/ratings.json        the traveler's 1–10 scores
  ratings-page/items.json      researched ideas (for backup ideas list)

Run from the repo root:  python scripts/build_site.py
"""
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT_IMG = DOCS / "images"
MAX_WIDTH = 1100

# itinerary stop id -> ratings id, where they differ
SCORE_ALIASES = {
    "kl-nye": "kl-nye-countdown",
    "bkk-sky-park": "bkk-chao-phraya-sky-park",
    "bkk-phra-sumen": "bkk-phra-sumen-fort",
    "bkk-royal-barges": "bkk-royal-barges-museum",
    "bkk-saen-saep": "bkk-khlong-saen-saep-boat",
    "bkk-x-phetchaburi": "bkk-phetchaburi",
    "bkk-x-kanchanaburi": "bkk-kanchanaburi",
    "bkk-x-koh-kret": "bkk-koh-kret",
    "bkk-x-nakhon-pathom": "bkk-nakhon-pathom",
    "bkk-x-lopburi": "bkk-lopburi",
    "cm-wat-chedi-luang": "cm-wat-chedi-luang-night",
    "cm-botanic-garden": "cm-queen-sirikit-botanic-garden",
    "cm-wua-lai": "cm-wua-lai-walking-street",
    "cm-x-chiang-rai": "cm-chiang-rai-temples",
    "cm-x-sukhothai": "wc-sukhothai-si-satchanalai",
    "cm-x-lampang": "cm-lampang",
    "cm-x-doi-mae-salong": "cm-doi-mae-salong",
    "cm-x-phu-chi-fa": "cm-phu-chi-fa",
    "sr-balloon": "sr-angkor-balloon",
    "sr-quad": "sr-quad-bike-countryside",
    "sr-baphuon": "sr-baphuon-palilay",
    "sr-terraces": "sr-leper-king-terrace",
    "sr-thom-walls": "sr-angkor-thom-walls",
}


def load(path, default=None):
    p = ROOT / path
    if not p.exists():
        if default is not None:
            return default
        raise SystemExit(f"missing {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def planned_ids():
    text = (ROOT / "plan/itinerary-draft.md").read_text(encoding="utf-8")
    ids = set()
    for line in text.splitlines():
        m = re.search(r"\b((?:kl|bkk|cm|sr)-[a-z0-9-]+)\b", line)
        if m and "(planned" in line:
            ids.add(m.group(1))
    return ids


def copy_image(rel):
    """Compress images/<x> into docs/images/<x>.jpg; return the site path or None."""
    if not rel:
        return None
    src = ROOT / rel
    if not src.exists() or src.stat().st_size < 15_000:
        print(f"  ! missing image {rel}")
        return None
    dest = OUT_IMG / (src.stem + ".jpg")
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        try:
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.width > MAX_WIDTH:
                    im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
                im.save(dest, "JPEG", quality=80, optimize=True, progressive=True)
        except Exception as e:
            print(f"  ! bad image {rel}: {e}")
            return None
    return "images/" + dest.name


def enrich(stop, ratings, planned, used):
    rid = SCORE_ALIASES.get(stop["id"], stop["id"])
    r = ratings.get(rid)
    if r and r.get("score"):
        stop["score"] = r["score"]
        if r.get("note"):
            stop["rating_note"] = r["note"]
        used.add(rid)
    stop["planned"] = stop["id"] in planned
    stop["image"] = copy_image(stop.get("image"))
    v = stop.get("video")
    if v and not (isinstance(v, dict) and v.get("id")):
        stop["video"] = None
    return stop


def main():
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    (DOCS / "data").mkdir(exist_ok=True)
    cfg = load("plan/site-config.json")
    ratings = load("research/ratings.json")
    planned = planned_ids()
    used = set()

    cities = []
    for meta in cfg["cities"]:
        if not (ROOT / f"research/details-{meta['key']}.json").exists():
            print(f"skipping {meta['key']}: no details yet")
            continue
        try:
            det = load(f"research/details-{meta['key']}.json")
        except json.JSONDecodeError as e:
            print(f"skipping {meta['key']}: details file mid-write ({e})")
            continue
        city = dict(meta)
        for k in ("intro", "stay", "arrival", "getting_around", "weather", "etiquette", "transport_out"):
            city.setdefault(k, det.get(k))
        city["days"] = det["days"]
        for d in city["days"]:
            d["stops"] = [enrich(s, ratings, planned, used) for s in d.get("stops", [])]
        city["extras"] = [enrich(s, ratings, planned, used) for s in det.get("extras", [])]
        city["hero"] = copy_image(meta.get("hero"))
        n = sum(len(d["stops"]) for d in city["days"])
        print(f"{meta['key']}: {len(city['days'])} days, {n} stops, {len(city['extras'])} extras")
        cities.append(city)

    # backup ideas: scored 6+ and not scheduled anywhere
    items = {i["id"]: i for i in load("ratings-page/items.json")}
    backup = []
    for rid, r in ratings.items():
        if (r.get("score") or 0) >= 6 and rid not in used and rid in items:
            it = items[rid]
            backup.append({"name": it["name"], "region": it["region"], "score": r["score"], "note": r.get("note", ""), "blurb": it.get("blurb", "")})
    backup.sort(key=lambda b: -b["score"])

    trip = {k: v for k, v in cfg.items() if k != "cities"}
    for k in ("hero", "extras_hero", "practical_hero"):
        if trip.get(k):
            trip[k] = copy_image(trip[k])
    trip["cities"] = cities
    trip["backup_ideas"] = backup
    (DOCS / "data/trip.json").write_text(json.dumps(trip, ensure_ascii=False, indent=1), encoding="utf-8")

    videos = sum(1 for c in cities for d in c["days"] for s in d["stops"] if s.get("video"))
    imgs = sum(1 for c in cities for d in c["days"] for s in d["stops"] if s.get("image"))
    size = sum(f.stat().st_size for f in OUT_IMG.glob("*.jpg")) / 1e6
    print(f"backup ideas: {len(backup)} | stops with photo: {imgs} | videos: {videos} | images {size:.1f} MB")


if __name__ == "__main__":
    main()
