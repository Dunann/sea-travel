# Brief for itinerary detail research

You are filling in practical, verified detail for one city of a trip itinerary, for a polished travel website.
Read `C:\Users\pdunc\sea_travel\plan\itinerary-draft.md` (the day-by-day draft with fixed stop ids) and `C:\Users\pdunc\sea_travel\plan\current-plan.md` (traveler's own plan + logistics findings). Existing research for many stops (blurbs, coords, links) is in `C:\Users\pdunc\sea_travel\research\*.json` — reuse it.

Today is 24 Nov 2026. The trip is 29 Dec 2026 – 14 Jan 2027. Use current (2025–2026) sources. Check each stop's opening days/hours **for the exact weekday and date it's scheduled** (incl. public holidays like 1 Jan) and flag conflicts.

## Output
Write ONE JSON file: `C:\Users\pdunc\sea_travel\research\details-<city>.json` (city = kl / bangkok / chiang-mai / siem-reap). Save early and rewrite as you go (after every few stops) so a stall loses nothing. Validate with `python -I -c "import json;json.load(open(r'<path>',encoding='utf-8'))"`.

```json
{
  "city": "...",
  "intro": "3–4 sentences on the city's character and what this leg is about",
  "stay": [{"area": "...", "why": "...", "example_hotels": ["..."]}],          // 2–3 neighbourhoods; for KL include rooftop-pool hotels with a NYE fireworks view
  "arrival": "how to get in from the airport/station: mode, time, cost, tips",
  "getting_around": "transit cards/apps (Grab etc.), costs",
  "weather": "Dec–Jan conditions, sunrise/sunset times",
  "etiquette": "dress codes for temples/mosques, scams to avoid, cash vs card",
  "days": [
    {
      "id": "KL1", "date": "2026-12-29", "title": "...",
      "summary": "2–3 sentences: the shape and mood of the day",
      "notes": ["timing warnings, what to cut first if tired"],
      "stops": [
        {
          "id": "kl-perdana-gardens",               // keep ids from the draft
          "name": "...",
          "time": "08:00–09:30",                    // suggested slot
          "description": "4–6 sentences: what it is, its history/meaning, what you actually see and do",
          "tips": ["2–4 specific, practical tips (best spot, what to skip, entrance to use, photo angle)"],
          "hours": "opening hours on THIS date",
          "cost": "local currency + USD",
          "coords": [lat, lon],                     // precise (entrance), 5 decimals
          "from_previous": "how to get here from the previous stop: mode, minutes, cost",
          "optional": false,
          "image": "images/<file>.jpg",             // see Images
          "image_credit": "author, license, Commons URL",
          "video": {"id": "YouTube video id", "title": "...", "channel": "..."} or null,
          "links": ["1–3 official/useful URLs"],
          "warning": "closure / date conflict / booking needed, else null"
        }
      ]
    }
  ],
  "extras": [ /* same stop shape, for swap-in day trips / extensions listed in the draft for this city;
                 add "what_to_swap": "which day/part it replaces", and for Kanchanaburi and Lopburi
                 a fuller description (traveler asked to know more) */ ],
  "transport_out": "next leg: options with times, carriers, durations, price ranges, which airport/station; flag anything that needs booking now"
}
```

You may fix the draft where it's wrong (closed day, impossible timing, geography) — reorder stops, move one to another day of the SAME city, or mark it optional — and explain each change in that day's `notes` starting with "Changed:". Keep the traveler's planned stops unless they're impossible.

## Images
- First check `C:\Users\pdunc\sea_travel\images\` — many stops already have a photo (named after research ids, e.g. `bkk-royal-barges-museum.jpg`). Reuse by pointing `image` to it.
- Otherwise find one good Wikimedia Commons photo that clearly shows that place and download:
  `curl -sL -A "SEATripPlanner/1.0 (personal trip research)" -o "C:/Users/pdunc/sea_travel/images/<stop-id>.jpg" "https://commons.wikimedia.org/wiki/Special:FilePath/<FileName>?width=1200"`
  Check it's a real JPEG/PNG > 20 KB. Wikimedia rate-limits: wait 3 s between downloads, and on HTTP 429 wait 30 s and retry once. Other agents are downloading at the same time.
- Transit-only stops (arrive, train) can have image null.

## Videos (important — the site embeds them)
For each major stop (aim for at least 1 per day, ideally the 2–3 best stops per day), find a good YouTube video: walking tour, drone footage, or a solid short guide; prefer recent (2023+), high quality, no clickbait. VERIFY every id exists and is embeddable:
  `curl -s -o NUL -w "%{http_code}" "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>&format=json"` → must be 200 (use the JSON body for title/channel).
Never invent an id. If unverified, use null.

## Working files
Use your own subfolder of the scratchpad (named after your city) for scripts — other agents share the scratchpad. Do not commit to git.

## Final reply
Short: what you changed in the draft and why, any booking-now items, any unresolved questions for the traveler. Max ~200 words.
