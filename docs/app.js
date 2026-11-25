/* Renders the itinerary from data/trip.json.
   Views (by URL hash): #overview, #<city key>, #extras, #practical. #day-<ID> opens that day's city and scrolls to it. */
(function () {
  "use strict";
  let trip = null;
  const app = document.getElementById("app");
  const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
  const DAY_COLORS = ["#c7700f", "#1f6f6a", "#7b4bb3", "#c23b5a", "#2a7fb8", "#5f7d1a", "#8a5a2b"];

  // ---------- helpers ----------
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const url = u => (typeof u === "string" && /^https?:\/\//.test(u)) ? esc(u) : null;
  const fmtDate = iso => { const d = new Date(iso + "T12:00:00"); return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" }); };
  const hostOf = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return "link"; } };
  const cityByKey = k => trip.cities.find(c => c.key === k);
  const cityOfDay = id => trip.cities.find(c => c.days.some(d => d.id === id));
  const hasCoords = s => Array.isArray(s.coords) && s.coords.length === 2 && isFinite(s.coords[0]) && isFinite(s.coords[1]);

  // ---------- maps (lazy) ----------
  const pendingMaps = [];
  const io = "IntersectionObserver" in window ? new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); const job = pendingMaps.find(j => j.el === e.target); if (job) job.init(); } });
  }, { rootMargin: "300px" }) : null;
  function lazyMap(el, init) { const job = { el, init: () => { if (!job.done) { job.done = true; init(); } } }; pendingMaps.push(job); if (io) io.observe(el); else job.init(); }

  function baseMap(el, opts) {
    const m = L.map(el, Object.assign({ scrollWheelZoom: false, zoomControl: true }, opts || {}));
    L.tileLayer(TILE_URL, { attribution: TILE_ATTR, maxZoom: 19 }).addTo(m);
    return m;
  }
  function numIcon(n, color, optional) {
    return L.divIcon({ className: "", html: `<div class="marker${optional ? " opt" : ""}" style="background:${color}">${esc(n)}</div>`, iconSize: [26, 26], iconAnchor: [13, 13], popupAnchor: [0, -12] });
  }
  function popup(s, label) { return `<b>${esc(label ? label + " · " : "")}${esc(s.name)}</b>${s.time ? `<br>${esc(s.time)}` : ""}`; }

  // ---------- nav ----------
  function renderNav(active) {
    const items = [["overview", "Overview", null]].concat(trip.cities.map(c => [c.key, c.short || c.name, c.color]), [["extras", "Extras & swaps", null], ["practical", "Bookings & practical", null]]);
    document.getElementById("navlinks").innerHTML = items.map(([k, label, color]) =>
      `<a href="#${k}" ${k === active ? 'aria-current="page"' : ""}>${color ? `<span class="dot" style="background:${color}"></span>` : ""}${esc(label)}</a>`).join("");
  }

  // ---------- shared pieces ----------
  function hero(img, credit, eyebrow, title, text) {
    return `<header class="hero">${img ? `<img class="bg" src="${esc(img)}" alt="">` : ""}
      <div class="wrap"><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(title)}</h1>${text ? `<p>${esc(text)}</p>` : ""}</div>
      ${credit ? `<span class="credit">Photo: ${esc(credit)}</span>` : ""}</header>`;
  }

  function video(v) {
    if (!v || !v.id || !/^[\w-]{6,20}$/.test(v.id)) return "";
    return `<button class="yt" type="button" data-yt="${esc(v.id)}" aria-label="Play video: ${esc(v.title || "")}">
      <img src="https://i.ytimg.com/vi/${esc(v.id)}/hqdefault.jpg" alt="" loading="lazy">
      <span class="play"><span></span></span>
      <span class="vt">${esc(v.title || "Video")}${v.channel ? " · " + esc(v.channel) : ""}</span></button>`;
  }

  function stopCard(s, n, color) {
    const badges = [];
    if (s.score) badges.push(`<span class="badge score" title="Your rating">You: ${esc(s.score)}/10</span>`);
    if (s.planned) badges.push(`<span class="badge planned">From your plan</span>`);
    if (s.optional) badges.push(`<span class="badge opt">Optional</span>`);
    const facts = [["Hours", s.hours], ["Cost", s.cost], ["Getting here", s.from_previous], ["Time", s.duration]].filter(f => f[1]);
    const links = (s.links || []).map(url).filter(Boolean).map(u => `<a href="${u}" target="_blank" rel="noopener">${esc(hostOf(u))} ↗</a>`);
    if (hasCoords(s)) links.unshift(`<a href="https://www.google.com/maps/search/?api=1&query=${s.coords[0]},${s.coords[1]}" target="_blank" rel="noopener">Google Maps ↗</a>`);
    const media = (s.image || (s.video && s.video.id)) ? `<div class="media">
        ${s.image ? `<figure><img src="${esc(s.image)}" alt="${esc(s.name)}" loading="lazy">${s.image_credit ? `<figcaption>${esc(s.image_credit)}</figcaption>` : ""}</figure>` : ""}
        ${video(s.video)}</div>` : "";
    return `<li class="stop${s.optional ? " optional" : ""}" id="stop-${esc(s.id)}" style="--c:${color}">
      <div class="rail"><span class="num">${esc(n)}</span></div>
      <article class="card${media ? " withimg" : ""}">
        <div class="body">
          <div class="stoptop">${s.time ? `<span class="time">${esc(s.time)}</span>` : ""}${badges.join("")}</div>
          <h3>${esc(s.name)}</h3>
          ${s.description ? `<p>${esc(s.description)}</p>` : ""}
          ${s.rating_note ? `<p class="lede"><i>Your note: “${esc(s.rating_note)}”</i></p>` : ""}
          ${s.warning ? `<div class="warn">⚠ ${esc(s.warning)}</div>` : ""}
          ${(s.tips || []).length ? `<ul class="tips">${s.tips.map(t => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
          ${facts.length ? `<dl class="facts">${facts.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>` : ""}
          ${s.what_to_swap ? `<div class="warn" style="background:var(--surface-2);color:var(--ink)">Swap: ${esc(s.what_to_swap)}</div>` : ""}
          ${links.length ? `<div class="links">${links.join("")}</div>` : ""}
        </div>${media}
      </article></li>`;
  }

  // ---------- overview ----------
  function renderOverview() {
    const allDays = trip.cities.flatMap(c => c.days.map(d => ({ d, c })));
    const strip = allDays.map(({ d, c }) => `<a href="#day-${esc(d.id)}" style="--c:${c.color}" title="${esc(d.title)}">
      <span class="d">${esc(fmtDate(d.date).split(" ").slice(0, 2).join(" "))}</span><span class="n">${esc(d.id.replace(/^[A-Z]+/, ""))}</span><span class="c">${esc(c.code)}</span></a>`).join("");
    const cards = trip.cities.map(c => `<a class="citycard" href="#${c.key}" style="--c:${c.color}">
      ${c.hero ? `<img src="${esc(c.hero)}" alt="" loading="lazy">` : ""}
      <div class="t"><span class="eyebrow">${esc(c.dates)} · ${esc(c.nights)} nights</span><h3>${esc(c.name)}</h3><span>${esc(c.tagline || "")}</span></div></a>`).join("");
    const legs = (trip.legs || []).map(l => `<tr><td><b>${esc(l.date)}</b></td><td>${esc(l.from)} → ${esc(l.to)}</td><td>${esc(l.how)}</td><td>${esc(l.status || "")}</td></tr>`).join("");
    app.innerHTML = hero(trip.hero, trip.hero_credit, trip.dates, trip.title, trip.summary) + `
      <div class="wrap">
        <section class="section"><h2>The route</h2>
          <div class="strip" style="--n:${allDays.length}">${strip}</div>
          <div class="bigmap" id="map-overview" role="img" aria-label="Map of the whole route"></div>
          <div class="maplegend">${trip.cities.map(c => `<span><i style="background:${c.color}"></i> ${esc(c.name)}</span>`).join("")}<span>Dashed line = flight</span></div>
        </section>
        <section class="section"><h2>Four stops</h2><div class="cities">${cards}</div></section>
        ${legs ? `<section class="section"><h2>Getting between cities</h2><div class="tablewrap"><table class="legs"><thead><tr><th>Date</th><th>Leg</th><th>How</th><th>Status</th></tr></thead><tbody>${legs}</tbody></table></div></section>` : ""}
        ${(trip.principles || []).length ? `<section class="section"><h2>How this plan was built</h2><div class="panel prose"><ul>${trip.principles.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div></section>` : ""}
      </div>`;
    lazyMap(document.getElementById("map-overview"), () => {
      const m = baseMap("map-overview");
      const pts = [];
      trip.cities.forEach(c => {
        const stops = c.days.flatMap(d => d.stops).filter(hasCoords);
        stops.forEach(s => L.circleMarker(s.coords, { radius: 3, color: c.color, weight: 1, fillOpacity: .7 }).addTo(m));
        if (c.center) {
          pts.push(c.center);
          L.marker(c.center, { icon: numIcon(c.code, c.color) }).addTo(m).bindPopup(`<b>${esc(c.name)}</b><br>${esc(c.dates)}`);
        }
      });
      if (pts.length > 1) L.polyline(pts, { color: "#c7700f", weight: 2.5, dashArray: "6 6" }).addTo(m);
      if (pts.length) m.fitBounds(L.latLngBounds(pts).pad(0.12));
    });
  }

  // ---------- city ----------
  function renderCity(c) {
    const daynav = c.days.map(d => `<a href="#day-${esc(d.id)}">${esc(d.id)} · ${esc(fmtDate(d.date))}</a>`).join("");
    const stay = (c.stay || []).map(s => `<div class="panel"><h3>${esc(s.area)}</h3><p>${esc(s.why)}</p>${(s.example_hotels || []).length ? `<p class="lede" style="font-size:14px">e.g. ${esc(s.example_hotels.join(" · "))}</p>` : ""}</div>`).join("");
    const kv = [["Arriving", c.arrival], ["Getting around", c.getting_around], ["Weather", c.weather], ["Etiquette", c.etiquette]].filter(x => x[1]);
    const days = c.days.map((d, di) => {
      const color = DAY_COLORS[di % DAY_COLORS.length];
      const stops = d.stops.map((s, i) => stopCard(s, i + 1, c.color)).join("");
      const notes = (d.notes || []).map(n => `<li class="${/^Changed:/i.test(n) ? "changed" : ""}">${esc(n)}</li>`).join("");
      return `<section class="day" id="day-${esc(d.id)}" style="--c:${c.color}">
        <div class="dayhead"><span class="tag"><b>${esc(d.id)}</b>${esc(fmtDate(d.date))}</span><h2>${esc(d.title)}</h2>${d.summary ? `<p>${esc(d.summary)}</p>` : ""}</div>
        ${notes ? `<ul class="notes">${notes}</ul>` : ""}
        ${d.stops.some(hasCoords) ? `<div class="daymap" id="map-${esc(d.id)}" data-day="${esc(d.id)}" role="img" aria-label="Map of ${esc(d.id)}"></div>` : ""}
        <ol class="stops">${stops}</ol></section>`;
    }).join("");
    const extras = (c.extras || []).length ? `<section class="day" id="extras-${esc(c.key)}" style="--c:${c.color}">
        <div class="dayhead"><span class="tag"><b>Extras</b>swap-ins & extensions</span><h2>If you have a spare day in ${esc(c.short || c.name)}</h2></div>
        <ol class="stops">${c.extras.map((s, i) => stopCard(Object.assign({ optional: true }, s), "+", c.color)).join("")}</ol></section>` : "";
    const legend = c.days.map((d, i) => `<button type="button" data-filter="${esc(d.id)}" aria-pressed="true"><i style="background:${DAY_COLORS[i % DAY_COLORS.length]}"></i>${esc(d.id)}</button>`).join("");

    app.innerHTML = hero(c.hero, c.hero_credit, `${c.dates} · ${c.nights} nights`, c.name, c.intro) + `
      <div class="wrap" style="--c:${c.color}">
        <section class="cityhead">
          <div class="daynav">${daynav}${extras ? `<a href="#extras-${esc(c.key)}">Extras</a>` : ""}</div>
          <div class="citymap" id="map-city" role="img" aria-label="Map of all stops in ${esc(c.name)}"></div>
          <div class="maplegend" id="citylegend">${legend}</div>
          ${stay ? `<h2 style="font-size:1.4rem">Where to stay</h2><div class="stay" style="--c:${c.color}">${stay}</div>` : ""}
          ${kv.length ? `<div class="panel"><dl class="kv">${kv.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl></div>` : ""}
        </section>
        ${days}${extras}
        ${c.transport_out ? `<section class="day"><div class="dayhead"><span class="tag" style="color:var(--muted)"><b style="background:var(--muted)">Next</b>leaving ${esc(c.short || c.name)}</span></div><div class="panel"><p>${esc(c.transport_out)}</p></div></section>` : ""}
      </div>`;

    // city overview map with day filter
    lazyMap(document.getElementById("map-city"), () => {
      const m = baseMap("map-city");
      const layers = {}; const all = [];
      c.days.forEach((d, i) => {
        const color = DAY_COLORS[i % DAY_COLORS.length];
        const g = L.layerGroup().addTo(m); layers[d.id] = g;
        const pts = [];
        d.stops.forEach((s, j) => { if (!hasCoords(s)) return; pts.push(s.coords); all.push(s.coords);
          L.marker(s.coords, { icon: numIcon(j + 1, color, s.optional) }).addTo(g).bindPopup(popup(s, d.id)); });
        if (pts.length > 1) L.polyline(pts, { color, weight: 2, opacity: .6 }).addTo(g);
      });
      if (all.length) m.fitBounds(L.latLngBounds(all).pad(0.08));
      document.getElementById("citylegend").onclick = e => {
        const b = e.target.closest("button"); if (!b) return;
        const on = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", String(on));
        const g = layers[b.dataset.filter]; if (on) g.addTo(m); else m.removeLayer(g);
      };
    });
    // per-day maps
    c.days.forEach(d => {
      const el = document.getElementById("map-" + d.id); if (!el) return;
      lazyMap(el, () => {
        const m = baseMap(el);
        const pts = d.stops.map((s, i) => ({ s, i })).filter(x => hasCoords(x.s));
        pts.forEach(({ s, i }) => L.marker(s.coords, { icon: numIcon(i + 1, c.color, s.optional) }).addTo(m).bindPopup(popup(s))
          .on("click", () => { const card = document.getElementById("stop-" + s.id); if (card) card.scrollIntoView({ behavior: "smooth", block: "center" }); }));
        const line = pts.filter(x => !x.s.optional).map(x => x.s.coords);
        if (line.length > 1) L.polyline(line, { color: c.color, weight: 3, opacity: .7 }).addTo(m);
        if (pts.length === 1) m.setView(pts[0].s.coords, 14); else m.fitBounds(L.latLngBounds(pts.map(x => x.s.coords)).pad(0.15));
      });
    });
  }

  // ---------- extras ----------
  function renderExtras() {
    const sections = trip.cities.filter(c => (c.extras || []).length).map(c => `<section class="day" style="--c:${c.color}">
      <div class="dayhead"><span class="tag"><b>${esc(c.code)}</b>${esc(c.name)}</span><h2>Swap-ins & extensions</h2></div>
      <ol class="stops">${c.extras.map(s => stopCard(Object.assign({ optional: true }, s), "+", c.color)).join("")}</ol></section>`).join("");
    const backup = (trip.backup_ideas || []).map(b => `<tr><td><b>${esc(b.score)}</b></td><td><b>${esc(b.name)}</b><br><span class="lede" style="font-size:13px">${esc(b.blurb || "")}</span></td><td>${esc(b.region)}</td><td>${esc(b.note || "")}</td></tr>`).join("");
    app.innerHTML = hero(trip.extras_hero, trip.extras_hero_credit, "If plans change", "Extras & swaps", "Day trips you can swap in, extensions if the trip grows to 17 nights, and every idea you scored 6 or higher that didn't make the main plan.") + `
      <div class="wrap">${(trip.route_options || []).length ? `<section class="section"><h2>Route variations</h2><div class="grid2">${trip.route_options.map(o => `<div class="panel"><span class="eyebrow">${esc(o.tag || "")}</span><h3>${esc(o.title)}</h3><p>${esc(o.body)}</p>${o.cost ? `<p class="lede" style="font-size:14px">Costs: ${esc(o.cost)}</p>` : ""}</div>`).join("")}</div></section>` : ""}
      ${sections}
      ${backup ? `<section class="section"><h2>Backup ideas you liked (6+)</h2><p class="lede">Not scheduled, but good to have in your pocket if a day opens up.</p><div class="tablewrap"><table class="legs"><thead><tr><th>You</th><th>Idea</th><th>Where</th><th>Your note</th></tr></thead><tbody>${backup}</tbody></table></div></section>` : ""}
      </div>`;
  }

  // ---------- practical ----------
  const CHECK_KEY = "sea-trip-checklist-v1";
  function loadChecks() { try { return JSON.parse(localStorage.getItem(CHECK_KEY) || "{}"); } catch (e) { return {}; } }
  function renderPractical() {
    const checks = loadChecks();
    const list = (trip.checklist || []).map((t, i) => `<li><label><input type="checkbox" id="chk-${i}" data-k="${esc(t.id || i)}" ${checks[t.id || i] ? "checked" : ""}><span><b>${esc(t.when || "")}</b> ${esc(t.text)}</span></label></li>`).join("");
    const panels = (trip.practical || []).map(p => `<div class="panel prose"><h3>${esc(p.title)}</h3>${(p.items || []).length ? `<ul>${p.items.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p>${esc(p.body || "")}</p>`}</div>`).join("");
    const qs = (trip.open_questions || []).map(q => `<li>${esc(q)}</li>`).join("");
    app.innerHTML = hero(trip.practical_hero, trip.practical_hero_credit, "Before you go", "Bookings & practical", "What to book and when, money, visas, and the questions still open.") + `
      <div class="wrap">
        <section class="section"><div class="panel"><h3>Google Maps lists</h3><p>Every place you rated 6 or higher, split by country, ready to save to Google Maps lists or import into My Maps. <a href="lists.html">Open the lists →</a></p></div></section>
        ${list ? `<section class="section"><h2>Booking checklist</h2><p class="lede">Ticks are saved in this browser.</p><div class="panel"><ul class="checklist">${list}</ul></div></section>` : ""}
        ${panels ? `<section class="section"><h2>Good to know</h2><div class="grid2">${panels}</div></section>` : ""}
        ${qs ? `<section class="section"><h2>Open questions for you</h2><div class="panel prose"><ul>${qs}</ul></div></section>` : ""}
      </div>`;
    app.querySelectorAll(".checklist input").forEach(inp => inp.onchange = () => {
      const c = loadChecks(); c[inp.dataset.k] = inp.checked; try { localStorage.setItem(CHECK_KEY, JSON.stringify(c)); } catch (e) {}
    });
  }

  // ---------- router ----------
  function route() {
    pendingMaps.length = 0;
    let h = decodeURIComponent(location.hash.replace(/^#/, "")) || "overview";
    let scrollTo = null;
    if (h.startsWith("day-")) { const c = cityOfDay(h.slice(4)); if (c) { scrollTo = h; h = c.key; } }
    if (h.startsWith("extras-")) { scrollTo = h; h = h.slice(7); }
    const c = cityByKey(h);
    if (c) renderCity(c); else if (h === "extras") renderExtras(); else if (h === "practical") renderPractical(); else { h = "overview"; renderOverview(); }
    renderNav(h);
    if (scrollTo) { const el = document.getElementById(scrollTo); if (el) requestAnimationFrame(() => el.scrollIntoView()); }
    else window.scrollTo(0, 0);
  }

  // video click-to-play
  app.addEventListener("click", e => {
    const b = e.target.closest(".yt"); if (!b || b.querySelector("iframe")) return;
    const f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(b.dataset.yt) + "?autoplay=1&rel=0";
    f.allow = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen";
    f.allowFullscreen = true; f.title = "YouTube video";
    b.appendChild(f);
  });

  let lastView = null;
  window.addEventListener("hashchange", () => {
    // same-city day links: just scroll, don't re-render
    const h = location.hash.replace(/^#/, "");
    if (h.startsWith("day-") || h.startsWith("extras-")) {
      const el = document.getElementById(h);
      const c = h.startsWith("day-") ? cityOfDay(h.slice(4)) : cityByKey(h.slice(7));
      if (el && c && lastView === c.key) { el.scrollIntoView({ behavior: "smooth" }); return; }
    }
    route(); lastView = currentView();
  });
  function currentView() { const a = document.querySelector('.navlinks a[aria-current="page"]'); return a ? a.getAttribute("href").slice(1) : null; }

  fetch("data/trip.json").then(r => r.json()).then(d => { trip = d; route(); lastView = currentView(); })
    .catch(() => { app.innerHTML = '<div class="wrap loading">Could not load the itinerary data. Reload to try again.</div>'; });
})();
