"""Export every idea rated 6+ as Google Maps-ready lists, one per country.

Outputs:
  docs/exports/<country>.csv   for import into Google My Maps (one file = one map/layer)
  docs/lists.html              phone-friendly page: tap a place, it opens in Google Maps, tap Save

Run from the repo root:  python scripts/export_maps_lists.py
"""
import csv
import html
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "research/geocode-cache.json"
OUT = ROOT / "docs/exports"

# rating id -> (country, [(pin name, search text)]).  The first pin uses the researched
# coordinates; extra pins (where one idea covers several places) are looked up by name.
PLACES = {
    # Malaysia
    "kl-nye-countdown": ("Malaysia", [("KLCC Park (New Year's Eve fireworks)", "KLCC Park, Kuala Lumpur")]),
    "kl-forest-eco-park": ("Malaysia", [("KL Forest Eco Park", "KL Forest Eco Park, Kuala Lumpur")]),
    "kl-brickfields": ("Malaysia", [("Brickfields (Little India)", "Little India Brickfields, Kuala Lumpur")]),
    "kl-trx-city-park": ("Malaysia", [("TRX City Park", "TRX City Park, Kuala Lumpur")]),
    "kl-old-railway-station": ("Malaysia", [("Old Kuala Lumpur Railway Station", "Kuala Lumpur Railway Station, Jalan Sultan Hishamuddin")]),
    "kl-pulau-ketam": ("Malaysia", [("Pulau Ketam", "Pulau Ketam, Selangor")]),
    "kl-puncak-alop": ("Malaysia", [("Puncak Alop", "Puncak Alop, Ampang")]),
    "wc-penang-george-town": ("Malaysia", [("George Town, Penang", "George Town, Penang")]),
    "wc-kuching": ("Malaysia", [("Kuching waterfront", "Kuching Waterfront, Sarawak"), ("Bako National Park", "Bako National Park, Sarawak")]),
    # Thailand
    "bkk-chao-phraya-sky-park": ("Thailand", [("Chao Phraya Sky Park", "Chao Phraya Sky Park, Bangkok")]),
    "bkk-countdown-iconsiam": ("Thailand", [("ICONSIAM (New Year countdown)", "ICONSIAM, Bangkok")]),
    "bkk-phetchaburi": ("Thailand", [("Phra Nakhon Khiri (Khao Wang)", "Phra Nakhon Khiri Historical Park, Phetchaburi"), ("Tham Khao Luang cave", "Tham Khao Luang, Phetchaburi")]),
    "bkk-royal-barges-museum": ("Thailand", [("Royal Barges National Museum", "Royal Barges National Museum, Bangkok")]),
    "bkk-wat-ratchabophit": ("Thailand", [("Wat Ratchabophit", "Wat Ratchabophit, Bangkok")]),
    "bkk-kanchanaburi": ("Thailand", [("Bridge over the River Kwai", "Bridge over the River Kwai, Kanchanaburi"), ("Tham Krasae (Wang Pho Viaduct)", "Tham Krasae station, Kanchanaburi")]),
    "bkk-khlong-saen-saep-boat": ("Thailand", [("Phan Fa Leelard Pier (Saen Saep canal boat)", "Phan Fa Leelard Pier, Bangkok")]),
    "bkk-koh-kret": ("Thailand", [("Ko Kret", "Ko Kret, Nonthaburi")]),
    "bkk-lopburi": ("Thailand", [("Phra Prang Sam Yot (Lopburi monkeys)", "Phra Prang Sam Yot, Lopburi")]),
    "bkk-nakhon-pathom": ("Thailand", [("Phra Pathom Chedi", "Phra Pathom Chedi, Nakhon Pathom"), ("Sanam Chandra Palace", "Sanam Chandra Palace, Nakhon Pathom")]),
    "bkk-talat-noi": ("Thailand", [("Talat Noi & Song Wat Road", "Talat Noi, Bangkok")]),
    "bkk-bang-krachao": ("Thailand", [("Bang Krachao (Sri Nakhon Khuean Khan Park)", "Sri Nakhon Khuean Khan Park, Bang Krachao")]),
    "bkk-bang-pa-in": ("Thailand", [("Bang Pa-In Royal Palace", "Bang Pa-In Royal Palace, Ayutthaya")]),
    "bkk-bangkokian-museum": ("Thailand", [("Bangkokian Museum", "Bangkokian Museum, Bangkok")]),
    "bkk-museum-siam": ("Thailand", [("Museum Siam", "Museum Siam, Bangkok")]),
    "bkk-nang-loeng": ("Thailand", [("Nang Loeng Market", "Nang Loeng Market, Bangkok")]),
    "bkk-phra-sumen-fort": ("Thailand", [("Phra Sumen Fort & Santi Chai Prakan Park", "Phra Sumen Fort, Bangkok")]),
    "bkk-wat-suthat": ("Thailand", [("Wat Suthat & the Giant Swing", "Wat Suthat, Bangkok")]),
    "wc-bangkok-chiang-mai-sleeper": ("Thailand", [("Krung Thep Aphiwat station (sleeper train north)", "Krung Thep Aphiwat Central Terminal, Bangkok")]),
    "cm-wat-chedi-luang-night": ("Thailand", [("Wat Chedi Luang", "Wat Chedi Luang, Chiang Mai"), ("Wat Phan Tao", "Wat Phan Tao, Chiang Mai")]),
    "cm-wat-ban-den": ("Thailand", [("Wat Ban Den", "Wat Ban Den, Mae Taeng")]),
    "cm-mon-cham": ("Thailand", [("Mon Cham", "Mon Cham, Mae Rim")]),
    "cm-queen-sirikit-botanic-garden": ("Thailand", [("Queen Sirikit Botanic Garden", "Queen Sirikit Botanic Garden, Mae Rim")]),
    "cm-wua-lai-walking-street": ("Thailand", [("Wua Lai Saturday Walking Street", "Wua Lai Walking Street, Chiang Mai")]),
    "cm-ban-tawai": ("Thailand", [("Ban Tawai woodcarving village", "Ban Tawai, Hang Dong")]),
    "cm-bo-sang-umbrella-festival": ("Thailand", [("Bo Sang Umbrella Village", "Bo Sang Umbrella Village, San Kamphaeng")]),
    "cm-huai-nam-dang": ("Thailand", [("Huai Nam Dang (Doi Kiew Lom viewpoint)", "Huai Nam Dang National Park")]),
    "cm-huay-tung-tao": ("Thailand", [("Huay Tung Tao Lake", "Huay Tung Tao Lake, Chiang Mai")]),
    "cm-warorot-market": ("Thailand", [("Warorot Market", "Warorot Market, Chiang Mai")]),
    "cm-wat-inthrawat": ("Thailand", [("Wat Inthrawat (Wat Ton Kwen)", "Wat Ton Kwen, Chiang Mai")]),
    "cm-wiang-kum-kam": ("Thailand", [("Wiang Kum Kam", "Wiang Kum Kam, Chiang Mai")]),
    "cm-chiang-rai-temples": ("Thailand", [("White Temple (Wat Rong Khun)", "Wat Rong Khun, Chiang Rai"), ("Blue Temple (Wat Rong Suea Ten)", "Wat Rong Suea Ten, Chiang Rai"), ("Baan Dam Museum (Black House)", "Baan Dam Museum, Chiang Rai")]),
    "cm-doi-mae-salong": ("Thailand", [("Doi Mae Salong", "Doi Mae Salong, Chiang Rai")]),
    "cm-lampang": ("Thailand", [("Wat Phra That Lampang Luang", "Wat Phra That Lampang Luang, Lampang")]),
    "cm-phu-chi-fa": ("Thailand", [("Phu Chi Fa", "Phu Chi Fa, Chiang Rai")]),
    "wc-khao-sok-cheow-lan": ("Thailand", [("Cheow Lan Lake (Khao Sok)", "Cheow Lan Lake, Surat Thani")]),
    "wc-sukhothai-si-satchanalai": ("Thailand", [("Sukhothai Historical Park", "Sukhothai Historical Park"), ("Si Satchanalai Historical Park", "Si Satchanalai Historical Park")]),
    "wc-nan": ("Thailand", [("Wat Phumin, Nan", "Wat Phumin, Nan")]),
    # Cambodia
    "sr-baphuon-palilay": ("Cambodia", [("Baphuon", "Baphuon, Angkor Thom"), ("Preah Palilay", "Preah Palilay, Angkor Thom")]),
    "sr-angkor-balloon": ("Cambodia", [("Angkor Balloon", "Angkor Balloon, Siem Reap")]),
    "sr-angkor-thom-walls": ("Cambodia", [("Angkor Thom South Gate (wall walk)", "South Gate, Angkor Thom")]),
    "sr-east-mebon": ("Cambodia", [("East Mebon", "East Mebon, Angkor")]),
    "sr-leper-king-terrace": ("Cambodia", [("Terrace of the Leper King", "Terrace of the Leper King, Angkor Thom"), ("Terrace of the Elephants", "Terrace of the Elephants, Angkor Thom")]),
    "sr-phnom-krom": ("Cambodia", [("Phnom Krom", "Phnom Krom, Siem Reap")]),
    "sr-phnom-kulen": ("Cambodia", [("Phnom Kulen National Park", "Phnom Kulen National Park")]),
    "sr-quad-bike-countryside": ("Cambodia", [("Quad Adventure Cambodia", "Quad Adventure Cambodia, Siem Reap")]),
    "sr-ta-som": ("Cambodia", [("Ta Som", "Ta Som, Angkor")]),
    "wc-kampot-kep": ("Cambodia", [("Kampot", "Kampot, Cambodia"), ("Kep", "Kep, Cambodia")]),
}
COUNTRIES = ["Malaysia", "Thailand", "Cambodia"]


def km(a, b):
    r = math.radians
    dlat, dlon = r(b[0] - a[0]), r(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(r(a[0])) * math.cos(r(b[0])) * math.sin(dlon / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def geocode(query, country, cache):
    """Look up coordinates with OpenStreetMap Nominatim (cached; 1 request per second)."""
    key = f"{query}|{country}"
    if key in cache:
        return cache[key]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": f"{query}, {country}", "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "trip-list-export/1.0"})
    time.sleep(1.1)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.load(r)
        cache[key] = [round(float(res[0]["lat"]), 5), round(float(res[0]["lon"]), 5)] if res else None
    except Exception as e:
        print(f"  ! geocode failed for {query}: {e}")
        return None
    return cache[key]


def maps_link(search, country):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{search}, {country}")


def main():
    ratings = json.loads((ROOT / "research/ratings.json").read_text(encoding="utf-8"))
    items = {i["id"]: i for i in json.loads((ROOT / "ratings-page/items.json").read_text(encoding="utf-8"))}
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    wanted = [rid for rid, r in ratings.items() if (r.get("score") or 0) >= 6 and rid in items]
    missing = [rid for rid in wanted if rid not in PLACES]
    if missing:
        raise SystemExit(f"no pin names for: {missing}")

    rows = {c: [] for c in COUNTRIES}
    for rid in wanted:
        country, pins = PLACES[rid]
        it, r = items[rid], ratings[rid]
        for n, (name, search) in enumerate(pins):
            coords = it["coords"] if n == 0 else geocode(search, country, cache)
            if n > 0 and coords and km(coords, it["coords"]) > 80:
                print(f"  ! {name}: lookup is {km(coords, it['coords']):.0f} km from the idea's pin; not trusting it")
                coords = None
            if n > 0 and not coords:
                coords = it["coords"]
                print(f"  ~ {name}: using the idea's coordinates")
            rows[country].append({
                "name": name, "score": r["score"], "lat": coords[0], "lon": coords[1],
                "idea": it["name"], "area": it.get("area", ""), "blurb": it.get("blurb", ""),
                "note": r.get("note", ""), "link": maps_link(search, country),
            })
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    OUT.mkdir(parents=True, exist_ok=True)
    for c in COUNTRIES:
        rows[c].sort(key=lambda x: (-x["score"], x["name"]))
        with open(OUT / f"{c.lower()}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Name", "Latitude", "Longitude", "Rating", "Description", "Google Maps"])
            for x in rows[c]:
                desc = x["blurb"] + (f" Your note: {x['note']}" if x["note"] else "")
                w.writerow([x["name"], x["lat"], x["lon"], f"{x['score']}/10", desc, x["link"]])
        print(f"{c}: {len(rows[c])} pins")

    write_page(rows)


def write_page(rows):
    e = html.escape
    sections = []
    for c in COUNTRIES:
        lis = "".join(
            f'<li><a class="place" href="{e(x["link"])}" target="_blank" rel="noopener">'
            f'<span class="sc s{x["score"]}">{x["score"]}</span>'
            f'<span class="nm"><b>{e(x["name"])}</b><small>{e(x["area"])}</small></span>'
            f'<span class="go">Open ↗</span></a></li>' for x in rows[c])
        sections.append(f'''<section class="section" id="{c.lower()}">
  <div class="cty"><h2>{c}</h2><span class="eyebrow">{len(rows[c])} places</span>
  <a class="dl" href="exports/{c.lower()}.csv" download>Download {c.lower()}.csv</a></div>
  <ol class="plist">{lis}</ol></section>''')
    total = sum(len(v) for v in rows.values())
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Places I Rated 6+</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;600&family=IBM+Plex+Mono:wght@500&display=swap">
<link rel="stylesheet" href="style.css">
<style>
.cty {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; }}
.dl {{ margin-left: auto; font-size: 14px; }}
.plist {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }}
.place {{ display: grid; grid-template-columns: 34px 1fr auto; gap: 12px; align-items: center; text-decoration: none; color: var(--ink);
  background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }}
.place:hover {{ border-color: var(--accent); }}
.nm {{ display: grid; min-width: 0; }} .nm small {{ color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }}
.sc {{ width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; color: #fff; font: 800 14px var(--font-display); background: #8a8f3c; }}
.sc.s9, .sc.s10 {{ background: #2f7d4f; }} .sc.s8 {{ background: #3f8f5a; }} .sc.s7 {{ background: #6c8f3a; }}
.go {{ font-size: 13px; color: var(--river); white-space: nowrap; }}
.how {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); }}
.how ol {{ margin: 0; padding-left: 20px; display: grid; gap: 4px; }}
</style></head><body>
<nav class="topnav"><div class="wrap navrow"><a class="brand" href="./">KL → Angkor</a>
<div class="navlinks"><a href="./">Itinerary</a><a href="#malaysia">Malaysia</a><a href="#thailand">Thailand</a><a href="#cambodia">Cambodia</a></div></div></nav>
<main class="wrap">
<section class="section"><span class="eyebrow">For Google Maps</span><h1 style="font-size:clamp(2rem,5vw,3rem)">Places I rated 6+</h1>
<p class="lede">{total} pins from the ideas you scored 6 or higher, split by country. Ideas that covered several places (for example the three Chiang Rai temples) are split into separate pins.</p>
<div class="how">
 <div class="panel prose"><h3>Option A: saved lists, on your phone</h3><ol>
  <li>In Google Maps, create three lists: Malaysia, Thailand, Cambodia (You → Saved → New list).</li>
  <li>Open this page on your phone and tap a place. It opens in Google Maps.</li>
  <li>Tap Save and pick the country's list. Use back to return here.</li></ol></div>
 <div class="panel prose"><h3>Option B: one import per country (fastest)</h3><ol>
  <li>On a computer, download the country's CSV file below.</li>
  <li>Go to mymaps.google.com → Create a new map → name it (e.g. "Thailand") → Import → choose the file.</li>
  <li>When asked, pick Latitude and Longitude for the pin position, then Name for the title.</li>
  <li>The map appears in the Google Maps app under You → Maps, with your rating and description on each pin.</li></ol></div>
</div></section>
{"".join(sections)}
</main>
<footer class="wrap site-foot"><span>Map links search Google Maps by place name; if a search lands on the wrong place, search the name yourself.</span></footer>
</body></html>
'''
    (ROOT / "docs/lists.html").write_text(page, encoding="utf-8")
    print("wrote docs/lists.html")


if __name__ == "__main__":
    main()
