/* FireOps Cloud - single page app (no build step). */
"use strict";

const S = {
  token: localGet("fireops_token"), me: null, view: "command", ws: null, wsRetry: 0,
  robots: [], incidents: [], world: { fires: [] }, sites: [], feed: [], charts: {}, timers: [],
  selectedRobot: null, liveSeries: [],
};
const SEV_COLOR = { low: "#3fb950", medium: "#d29922", high: "#f0883e", critical: "#f85149" };
const STATUS_COLOR = { online: "#3fb950", engaged: "#ff6b35", low_battery: "#d29922", offline: "#5b6878" };

// ------------------------------------------------------------------ utils
function localGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function localSet(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} }
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
function esc(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function fmt(n, d = 1) { return n == null || Number.isNaN(n) ? "—" : Number(n).toFixed(d); }
function ago(ts) {
  if (!ts) return "never";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return `${Math.floor(s)}s ago`; if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`; return `${Math.floor(s / 86400)}d ago`;
}
function dur(sec) { if (sec == null) return "—"; if (sec < 60) return `${Math.round(sec)}s`; if (sec < 3600) return `${(sec / 60).toFixed(1)}m`; return `${(sec / 3600).toFixed(1)}h`; }
function time(ts) { return new Date(ts * 1000).toLocaleTimeString(); }
function dateTime(ts) { return new Date(ts * 1000).toLocaleString(); }
const sevBadge = s => `<span class="badge sev-${esc(s)}">${esc(s)}</span>`;
const stBadge = s => `<span class="badge st-${esc(s)}">${esc(String(s).replace("_", " "))}</span>`;
function bar(v, color) { const p = Math.max(0, Math.min(100, v ?? 0)); const c = color || (p < 20 ? "#f85149" : p < 40 ? "#d29922" : "#3fb950"); return `<div class="bar" title="${fmt(v, 0)}%"><i style="width:${p}%;background:${c}"></i></div>`; }
const can = role => ({ viewer: 0, operator: 1, admin: 2 })[S.me?.user.role] >= ({ viewer: 0, operator: 1, admin: 2 })[role];

function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`; el.innerHTML = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

async function api(path, opts = {}) {
  const headers = { ...(opts.body ? { "Content-Type": "application/json" } : {}), ...(S.token ? { Authorization: `Bearer ${S.token}` } : {}) };
  const res = await fetch(path, { ...opts, headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (res.status === 401 && S.token) { logout(); throw new Error("Session expired"); }
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const d = data?.detail; const msg = Array.isArray(d) ? d.map(e => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join("; ") : d || res.statusText;
    throw new Error(msg);
  }
  return data;
}
async function act(fn, okMsg) {
  try { const r = await fn(); if (okMsg) toast(okMsg, "ok"); return r; }
  catch (e) { toast(esc(e.message), "err"); throw e; }
}

// ------------------------------------------------------------------ auth
function showAuth(mode = "login") {
  $("#app").classList.add("hidden"); $("#auth").classList.remove("hidden");
  $("#auth").className = `auth ${mode}`;
  $$("#auth-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.mode === mode));
  $("#auth-submit").textContent = mode === "login" ? "Sign in" : "Create organization";
  $$(".signup-only input").forEach(i => (i.required = mode === "signup"));
  $("#auth-form").dataset.mode = mode;
}
$$("#auth-tabs .tab").forEach(t => t.addEventListener("click", () => showAuth(t.dataset.mode)));
$("#auth-form").addEventListener("submit", async e => {
  e.preventDefault();
  const f = Object.fromEntries(new FormData(e.target)); const mode = e.target.dataset.mode;
  $("#auth-error").textContent = "";
  try {
    const r = await api(`/api/auth/${mode}`, { method: "POST", body: mode === "login" ? { email: f.email, password: f.password } : f });
    S.token = r.access_token; localSet("fireops_token", S.token); await boot();
  } catch (err) { $("#auth-error").textContent = err.message; }
});
function logout() {
  S.token = null; localSet("fireops_token", null); S.ws?.close(); S.ws = null; showAuth("login");
}
$("#logout").addEventListener("click", logout);

// ------------------------------------------------------------------ realtime
function connectWS() {
  if (!S.token) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(S.token)}`);
  S.ws = ws;
  ws.onopen = () => { S.wsRetry = 0; setLive(true); };
  ws.onclose = () => { setLive(false); if (S.token && S.ws === ws) setTimeout(connectWS, Math.min(15000, 1000 * 2 ** S.wsRetry++)); };
  ws.onmessage = m => { const { event, data } = JSON.parse(m.data); onEvent(event, data); };
  clearInterval(S.pingTimer); S.pingTimer = setInterval(() => ws.readyState === 1 && ws.send("ping"), 20000);
}
function setLive(on) { const l = $("#live"); l.className = `live ${on ? "on" : "off"}`; l.textContent = on ? "live" : "offline"; }

function pushFeed(kind, html) {
  S.feed.unshift({ ts: Date.now() / 1000, kind, html }); S.feed.length = Math.min(S.feed.length, 60);
  const el = $("#feed"); if (el) el.innerHTML = renderFeed();
}
const renderFeed = () => S.feed.length ? S.feed.map(f => `<div class="feed-item ${f.kind}"><div class="t">${time(f.ts)}</div>${f.html}</div>`).join("") : `<div class="muted small">Waiting for events…</div>`;

let refreshPending = false;
function scheduleRefresh() { if (refreshPending) return; refreshPending = true; setTimeout(() => { refreshPending = false; refreshIncidents(); }, 800); }

function onEvent(event, d) {
  if (event === "telemetry") {
    const r = S.robots.find(r => r.id === d.robot_id);
    if (r) { r.last_telemetry = d; r.risk_score = d.risk_score; r.status = d.status; r.last_seen = d.ts; }
    else refreshRobots();
    S.liveSeries.push({ ts: d.ts, robot: d.robot_name, risk: d.risk_score, temp: d.temperature });
    if (S.liveSeries.length > 2000) S.liveSeries.splice(0, 500);
  } else if (event === "incident.opened") {
    const crit = d.severity === "critical" || d.severity === "high";
    toast(`<b>${esc(d.title)}</b><div class="small muted">${esc(d.severity)} · incident #${d.id}</div>`, crit ? "crit" : "");
    pushFeed(crit ? "crit" : "high", `${sevBadge(d.severity)} <a onclick="openIncident(${d.id})">#${d.id}</a> ${esc(d.title)}`);
    scheduleRefresh();
  } else if (event === "incident.escalated") {
    pushFeed("crit", `Incident <a onclick="openIncident(${d.id})">#${d.id}</a> escalated to ${sevBadge(d.severity)}`);
    scheduleRefresh();
  } else if (event === "incident.updated") {
    scheduleRefresh();
  } else if (event === "anomaly") {
    pushFeed("high", `Anomaly on <b>${esc(d.robot_name)}</b>: ${d.anomalies.map(a => `${esc(a.metric)} ${fmt(a.value)} (baseline ${fmt(a.baseline)})`).join(", ")}`);
  } else if (event === "command") {
    const name = S.robots.find(r => r.id === d.robot_id)?.name || `robot ${d.robot_id}`;
    pushFeed(d.status === "failed" ? "crit" : d.status === "completed" ? "ok" : "info", `<b>${esc(d.kind)}</b> → ${esc(name)} ${stBadge(d.status)}`);
    if (S.view === "commands") renderView();
  }
}

// ------------------------------------------------------------------ data
async function refreshRobots() { S.robots = await api("/api/robots"); }
async function refreshIncidents() {
  S.incidents = await api("/api/incidents?status=active");
  const n = S.incidents.length; $("#nav-incidents").textContent = n || "";
  if (S.view === "incidents") renderView();
  if (S.view === "command") updateCommandKpis();
}
async function refreshWorld() { try { S.world = await api("/api/demo/world"); } catch { S.world = { fires: [] }; } }

// ------------------------------------------------------------------ boot & nav
async function boot() {
  if (!S.token) return showAuth("login");
  try { S.me = await api("/api/auth/me"); } catch { return showAuth("login"); }
  $("#auth").classList.add("hidden"); $("#app").classList.remove("hidden");
  $("#org-name").textContent = S.me.org.name; $("#user-name").textContent = `${S.me.user.name} · ${S.me.user.role}`;
  $("#plan-badge").textContent = S.me.plan.name;
  await Promise.all([refreshRobots(), refreshIncidents(), api("/api/sites").then(s => (S.sites = s))]);
  connectWS();
  navigate(location.hash.slice(1) || "command");
}
$$("#nav a").forEach(a => a.addEventListener("click", () => navigate(a.dataset.view)));
window.addEventListener("hashchange", () => { const v = location.hash.slice(1); if (v && v !== S.view) navigate(v); });

function navigate(view) {
  if (!VIEWS[view]) view = "command";
  S.view = view; if (location.hash.slice(1) !== view) location.hash = view;
  $$("#nav a").forEach(a => a.classList.toggle("active", a.dataset.view === view));
  renderView();
}
function clearView() {
  S.timers.forEach(clearInterval); S.timers = [];
  Object.values(S.charts).forEach(c => c.destroy()); S.charts = {};
}
async function renderView() {
  clearView();
  try { await VIEWS[S.view]($("#view")); } catch (e) { $("#view").innerHTML = `<div class="card error">${esc(e.message)}</div>`; }
}
function every(ms, fn) { S.timers.push(setInterval(fn, ms)); }

// ------------------------------------------------------------------ charts
Chart.defaults.color = "#8b98a9"; Chart.defaults.borderColor = "#243042"; Chart.defaults.font.family = "Inter, system-ui, sans-serif";
function lineChart(canvas, datasets, opts = {}) {
  return new Chart(canvas, {
    type: "line", data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false, parsing: false, normalized: true,
      interaction: { mode: "nearest", intersect: false },
      scales: {
        x: { type: "linear", ticks: { callback: v => new Date(v * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), maxTicksLimit: 6 } },
        y: { beginAtZero: true, ...(opts.y || {}) }, ...(opts.scales || {}),
      },
      plugins: { legend: { display: datasets.length > 1, labels: { boxWidth: 10 } }, tooltip: { callbacks: { title: i => i[0] && dateTime(i[0].parsed.x) } } },
      elements: { point: { radius: opts.points ? 2 : 0 }, line: { borderWidth: 2, tension: .25 } },
    },
  });
}
const PALETTE = ["#ff6b35", "#58a6ff", "#3fb950", "#d2a8ff", "#ffb547", "#f778ba", "#79c0ff", "#56d364"];

// ------------------------------------------------------------------ site map
function drawMap(canvas, { heat = null, onClick = null } = {}) {
  const site = S.sites[0] || { width: 100, height: 60 };
  const dpr = window.devicePixelRatio || 1; const W = canvas.clientWidth, H = canvas.clientHeight;
  if (canvas.width !== W * dpr) { canvas.width = W * dpr; canvas.height = H * dpr; }
  const g = canvas.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
  const sx = W / site.width, sy = H / site.height; const P = (x, y) => [x * sx, y * sy];
  g.strokeStyle = "#1a2431"; g.lineWidth = 1;
  for (let x = 0; x <= site.width; x += 10) { g.beginPath(); g.moveTo(x * sx, 0); g.lineTo(x * sx, H); g.stroke(); }
  for (let y = 0; y <= site.height; y += 10) { g.beginPath(); g.moveTo(0, y * sy); g.lineTo(W, y * sy); g.stroke(); }
  if (heat) {
    for (const c of heat.cells) {
      const a = Math.min(.85, c.risk * .9); g.fillStyle = `rgba(255,${Math.round(180 - 150 * c.risk)},53,${a})`;
      g.fillRect(c.cx * heat.cell * sx, c.cy * heat.cell * sy, heat.cell * sx + .5, heat.cell * sy + .5);
    }
  }
  g.fillStyle = "#58a6ff22"; g.strokeStyle = "#58a6ff88"; g.fillRect(...P(1, 1), 8 * sx, 52 * sy); g.strokeRect(...P(1, 1), 8 * sx, 52 * sy);
  g.fillStyle = "#58a6ffaa"; g.font = "11px Inter, sans-serif"; g.fillText("BASE", ...P(2, 58));
  const t = Date.now() / 300;
  for (const f of S.world.fires || []) {
    const [x, y] = P(f.x, f.y); const r = (6 + 18 * f.intensity) * (1 + .08 * Math.sin(t)) * Math.min(sx, sy) / 2;
    const grad = g.createRadialGradient(x, y, 0, x, y, r * 2.2);
    grad.addColorStop(0, "rgba(255,200,80,.95)"); grad.addColorStop(.4, "rgba(255,90,40,.6)"); grad.addColorStop(1, "rgba(255,60,30,0)");
    g.fillStyle = grad; g.beginPath(); g.arc(x, y, r * 2.2, 0, Math.PI * 2); g.fill();
  }
  for (const i of S.incidents) {
    if (i.x == null) continue; const [x, y] = P(i.x, i.y);
    g.strokeStyle = SEV_COLOR[i.severity]; g.lineWidth = 2; g.setLineDash([4, 3]);
    g.beginPath(); g.arc(x, y, 14, 0, Math.PI * 2); g.stroke(); g.setLineDash([]);
  }
  for (const r of S.robots) {
    const tl = r.last_telemetry; if (!tl || tl.x == null) continue;
    const [x, y] = P(tl.x, tl.y); const c = r.status === "offline" ? STATUS_COLOR.offline : SEV_COLOR[sevOf(r.risk_score)];
    if (S.selectedRobot === r.id) { g.strokeStyle = "#fff"; g.lineWidth = 2; g.beginPath(); g.arc(x, y, 10, 0, Math.PI * 2); g.stroke(); }
    g.fillStyle = c; g.beginPath(); g.arc(x, y, 6, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#e6edf3"; g.font = "11px Inter, sans-serif"; g.fillText(r.name, x + 9, y - 7);
  }
  if (onClick && !canvas._bound) {
    canvas._bound = true;
    canvas.addEventListener("click", e => {
      const b = canvas.getBoundingClientRect(); const s = S.sites[0] || { width: 100, height: 60 };
      onClick(((e.clientX - b.left) / b.width) * s.width, ((e.clientY - b.top) / b.height) * s.height, e);
    });
  }
}
const sevOf = s => (s >= .85 ? "critical" : s >= .6 ? "high" : s >= .3 ? "medium" : "low");

// ------------------------------------------------------------------ views
const VIEWS = {};

VIEWS.command = async root => {
  await Promise.all([refreshRobots(), refreshWorld()]);
  if (!S.robots.length) {
    root.innerHTML = `<div class="card hero"><div class="logo" style="width:48px;height:48px;margin:0 auto"></div>
      <h1 style="margin-top:16px">Welcome to FireOps Cloud</h1>
      <p class="muted">Connect your fire-fighting robots to stream telemetry, score fire risk in real time, open incidents automatically and dispatch robots from one screen.</p>
      <div class="row" style="justify-content:center;max-width:460px;margin:auto">
        ${can("admin") ? `<button class="btn primary" id="seed">Launch simulated demo fleet</button><button class="btn" onclick="navigate('fleet')">Register a real robot</button>` : `<span class="muted">Ask an admin to register robots.</span>`}
      </div></div>`;
    $("#seed")?.addEventListener("click", async () => { await act(() => api("/api/demo/seed", { method: "POST" }), "Demo fleet launched — telemetry starts in a few seconds"); S.me = await api("/api/auth/me"); setTimeout(renderView, 2500); });
    return;
  }
  root.innerHTML = `
    <div class="head"><div><h1>Command center</h1><div class="muted small">${esc(S.sites[0]?.name || "")} · click a robot to select it${can("operator") ? ", then click the map to send it there" : ""}</div></div>
      <div class="actions">${can("operator") && S.me.org.simulator_enabled ? `<button class="btn" id="ignite">🔥 Start drill fire</button>` : ""}<button class="btn" onclick="navigate('incidents')">Incidents</button></div></div>
    <div class="grid kpis" id="kpis"></div>
    <div class="grid cols-2" style="margin-top:16px">
      <div class="card"><h3>Live site map</h3><div class="mapwrap"><canvas id="map"></canvas></div>
        <div class="legend"><span><i style="background:${SEV_COLOR.low}"></i>Low risk</span><span><i style="background:${SEV_COLOR.medium}"></i>Medium</span><span><i style="background:${SEV_COLOR.high}"></i>High</span><span><i style="background:${SEV_COLOR.critical}"></i>Critical</span><span><i style="background:transparent;border:2px dashed ${SEV_COLOR.high}"></i>Active incident</span><span id="sel-robot"></span></div></div>
      <div class="card"><h3>Live event feed</h3><div class="feed" id="feed">${renderFeed()}</div></div>
    </div>
    <div class="grid cols-2" style="margin-top:16px">
      <div class="card"><h3>Fire risk by robot (live)</h3><div class="chartbox"><canvas id="risk-chart"></canvas></div></div>
      <div class="card"><h3>Fleet</h3><div class="tablewrap" id="mini-fleet"></div></div>
    </div>`;
  const map = $("#map");
  const onMapClick = async (x, y) => {
    const hit = S.robots.find(r => r.last_telemetry && Math.hypot(r.last_telemetry.x - x, r.last_telemetry.y - y) < 3);
    if (hit) { S.selectedRobot = S.selectedRobot === hit.id ? null : hit.id; updateSel(); return; }
    if (!can("operator")) return;
    if (S.selectedRobot) {
      await act(() => api(`/api/robots/${S.selectedRobot}/commands`, { method: "POST", body: { kind: "move_to", params: { x: +x.toFixed(1), y: +y.toFixed(1) } } }), "Move command queued");
    } else if (S.me.org.simulator_enabled) {
      await act(() => api("/api/demo/ignite", { method: "POST", body: { x, y, intensity: .45 } }), "Drill fire started");
    } else toast("Select a robot on the map first, then click where to send it.");
  };
  const updateSel = () => { const r = S.robots.find(r => r.id === S.selectedRobot); $("#sel-robot").innerHTML = r ? `Selected: <b>${esc(r.name)}</b> — click the map to send it there` : ""; };
  $("#ignite")?.addEventListener("click", () => act(() => api("/api/demo/ignite", { method: "POST", body: {} }), "Drill fire started at a random location"));
  const riskChart = S.charts.risk = lineChart($("#risk-chart"), [], { y: { max: 1 } });
  const tick = () => {
    drawMap(map, { onClick: onMapClick });
    const now = Date.now() / 1000; const names = [...new Set(S.robots.map(r => r.name))];
    riskChart.data.datasets = names.map((n, i) => ({ label: n, borderColor: PALETTE[i % PALETTE.length], data: S.liveSeries.filter(p => p.robot === n && p.ts > now - 300).map(p => ({ x: p.ts, y: p.risk })) }));
    riskChart.update("none");
  };
  const slow = () => { updateCommandKpis(); renderMiniFleet(); };
  // Seed the risk chart with the last 5 minutes so it is not empty on load.
  if (!S.liveSeries.length) {
    const hist = await Promise.all(S.robots.map(r => api(`/api/robots/${r.id}/telemetry?minutes=5&limit=200`).then(rows => rows.map(t => ({ ts: t.ts, robot: r.name, risk: t.risk_score, temp: t.temperature })))));
    S.liveSeries = hist.flat().sort((a, b) => a.ts - b.ts);
  }
  tick(); slow(); updateSel();
  every(500, () => { if (!$("#map")) return; tick(); });
  every(2000, slow);
  every(2000, refreshWorld);
};

function updateCommandKpis() {
  const el = $("#kpis"); if (!el) return;
  const online = S.robots.filter(r => r.status !== "offline");
  const bat = online.map(r => r.last_telemetry?.battery).filter(v => v != null);
  const maxRisk = Math.max(0, ...online.map(r => r.risk_score || 0));
  const crit = S.incidents.filter(i => i.severity === "critical").length;
  el.innerHTML = [
    ["Robots online", `${online.length}<span class="muted" style="font-size:16px"> / ${S.robots.length}</span>`, `${S.robots.filter(r => r.status === "engaged").length} engaged`],
    ["Active incidents", `<span style="color:${S.incidents.length ? "var(--crit)" : "var(--ok)"}">${S.incidents.length}</span>`, `${crit} critical`],
    ["Peak fire risk", `<span style="color:${SEV_COLOR[sevOf(maxRisk)]}">${(maxRisk * 100).toFixed(0)}%</span>`, sevOf(maxRisk)],
    ["Avg battery", bat.length ? `${fmt(bat.reduce((a, b) => a + b, 0) / bat.length, 0)}%` : "—", `${online.filter(r => (r.last_telemetry?.battery ?? 100) < 20).length} below 20%`],
    ["Active fires (sim)", `${(S.world.fires || []).length}`, "demo mode"],
  ].map(([l, v, s]) => `<div class="card kpi"><div class="label">${l}</div><div class="value">${v}</div><div class="sub">${esc(s)}</div></div>`).join("");
}
function renderMiniFleet() {
  const el = $("#mini-fleet"); if (!el) return;
  el.innerHTML = `<table><tr><th>Robot</th><th>Status</th><th>Risk</th><th>Battery</th><th>Water</th></tr>${S.robots.map(r => {
    const t = r.last_telemetry || {};
    return `<tr class="click" onclick="openRobot(${r.id})"><td>${esc(r.name)}</td><td>${stBadge(r.status)}</td><td>${sevBadge(sevOf(r.risk_score))}</td><td>${bar(t.battery)}</td><td>${bar(t.water_level, "#58a6ff")}</td></tr>`;
  }).join("")}</table>`;
}

VIEWS.fleet = async root => {
  await refreshRobots();
  const draw = () => {
    root.innerHTML = `<div class="head"><h1>Fleet</h1><div class="actions">
      <a class="btn" href="/api/telemetry/export.csv?minutes=1440" id="export">Export 24h CSV</a>
      ${can("admin") ? `<button class="btn primary" id="add-robot">Register robot</button>` : ""}</div></div>
      <div class="card tablewrap">${S.robots.length ? `<table><tr><th>Name</th><th>Model</th><th>Status</th><th>Risk</th><th>Temp</th><th>Smoke</th><th>Battery</th><th>Water</th><th>Motor</th><th>Key</th><th>Last seen</th></tr>
      ${S.robots.map(r => { const t = r.last_telemetry || {}; return `<tr class="click" onclick="openRobot(${r.id})">
        <td><b>${esc(r.name)}</b></td><td class="muted">${esc(r.model)}</td><td>${stBadge(r.status)}</td><td>${sevBadge(sevOf(r.risk_score))} <span class="muted small">${fmt(r.risk_score * 100, 0)}%</span></td>
        <td>${fmt(t.temperature)}°C</td><td>${fmt(t.smoke, 0)}</td><td>${bar(t.battery)}</td><td>${bar(t.water_level, "#58a6ff")}</td><td>${fmt(t.motor_temp)}°C</td>
        <td><code>${esc(r.api_key_prefix)}…</code></td><td class="muted">${ago(r.last_seen)}</td></tr>`; }).join("")}</table>` : `<div class="empty">No robots yet.</div>`}</div>
      <div class="card" style="margin-top:16px"><h3>Connect a robot</h3><p class="muted">Robots authenticate with their device key and push telemetry over HTTPS, then poll for commands. See <code>robot_client.py</code> for a ready-made client.</p>
<pre>curl -X POST ${esc(location.origin)}/api/device/telemetry \\
  -H "X-Device-Key: fod_…" -H "Content-Type: application/json" \\
  -d '{"temperature":27.5,"smoke":40,"gas":90,"humidity":45,"flame":false,"battery":88,"water_level":95,"motor_temp":44,"x":20,"y":12}'</pre></div>`;
    $("#export").addEventListener("click", e => { e.preventDefault(); downloadCsv(); });
    $("#add-robot")?.addEventListener("click", addRobotModal);
  };
  draw();
  every(3000, async () => { await refreshRobots(); if (!$("#drawer").classList.contains("hidden")) return; draw(); });
};

async function downloadCsv() {
  const res = await fetch("/api/telemetry/export.csv?minutes=1440", { headers: { Authorization: `Bearer ${S.token}` } });
  const url = URL.createObjectURL(await res.blob()); const a = document.createElement("a");
  a.href = url; a.download = "fireops-telemetry.csv"; a.click(); URL.revokeObjectURL(url);
}

function modal(html) { $("#modal-card").innerHTML = html; $("#modal").classList.remove("hidden"); }
function closeModal() { $("#modal").classList.add("hidden"); }
$("#modal").addEventListener("click", e => { if (e.target.id === "modal") closeModal(); });
function drawer(html) { $("#drawer-panel").innerHTML = html; $("#drawer").classList.remove("hidden"); }
function closeDrawer() { $("#drawer").classList.add("hidden"); Object.keys(S.charts).filter(k => k.startsWith("d_")).forEach(k => { S.charts[k].destroy(); delete S.charts[k]; }); }
$("#drawer").addEventListener("click", e => { if (e.target.id === "drawer") closeDrawer(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") { closeModal(); closeDrawer(); } });

function addRobotModal() {
  modal(`<button class="btn ghost small close" onclick="closeModal()">✕</button><h2>Register robot</h2>
    <form class="form" id="robot-form"><label>Name<input name="name" required maxlength="100" placeholder="Unit 7"></label>
    <label>Model<input name="model" value="FFHR-1"></label>
    <label>Site<select name="site_id">${S.sites.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join("")}</select></label>
    <button class="btn primary">Create &amp; generate device key</button></form>`);
  $("#robot-form").addEventListener("submit", async e => {
    e.preventDefault(); const f = Object.fromEntries(new FormData(e.target));
    const r = await act(() => api("/api/robots", { method: "POST", body: { ...f, site_id: +f.site_id } }));
    showKey(r.name, r.api_key); refreshRobots().then(() => S.view === "fleet" && renderView());
  });
}
function showKey(name, key) {
  modal(`<h2>Device key for ${esc(name)}</h2><p class="muted">Copy it now — it is stored hashed and will not be shown again.</p>
    <pre id="key">${esc(key)}</pre><div class="row"><button class="btn" onclick="navigator.clipboard.writeText(document.getElementById('key').textContent).then(()=>toast('Copied','ok'))">Copy</button><button class="btn primary" onclick="closeModal()">Done</button></div>`);
}

window.openRobot = async id => {
  const r = await api(`/api/robots/${id}`); const t = r.last_telemetry || {}; const m = r.maintenance;
  drawer(`<button class="btn ghost small close" onclick="closeDrawer()">✕</button>
    <h2>${esc(r.name)} ${stBadge(r.status)}</h2><div class="muted small">${esc(r.model)} · key ${esc(r.api_key_prefix)}… · last seen ${ago(r.last_seen)}</div>
    <div class="grid kpis" style="margin-top:16px">
      <div class="card kpi"><div class="label">Fire risk</div><div class="value" style="color:${SEV_COLOR[sevOf(r.risk_score)]}">${fmt(r.risk_score * 100, 0)}%</div></div>
      <div class="card kpi"><div class="label">Health score</div><div class="value">${m.health_score}</div></div>
    </div>
    ${can("operator") ? `<h3 style="margin-top:18px">Commands</h3><div class="row">${["scan", "suppress", "patrol", "return_to_base", "halt"].map(k => `<button class="btn small" onclick="sendCmd(${id},'${k}')">${k.replace(/_/g, " ")}</button>`).join("")}</div>` : ""}
    <h3 style="margin-top:18px">Predictive maintenance</h3>
    <dl class="kv"><dt>Battery</dt><dd>${fmt(t.battery)}% · drain ${fmt(m.battery_drain_per_hour)}%/h · reserve in ${m.battery_eta_minutes == null ? "—" : fmt(m.battery_eta_minutes, 0) + " min"}</dd>
      <dt>Motor</dt><dd>${fmt(t.motor_temp)}°C · trend ${fmt(m.motor_temp_trend_per_hour)}°C/h${m.motor_overheat_eta_minutes != null ? ` · overheat in ${fmt(m.motor_overheat_eta_minutes, 0)} min` : ""}</dd>
      <dt>Water tank</dt><dd>${fmt(m.water_level, 0)}%</dd>
      <dt>Advice</dt><dd>${m.recommendations.length ? m.recommendations.map(esc).join("<br>") : '<span class="muted">No action needed</span>'}</dd></dl>
    ${r.risk_explanation ? `<h3 style="margin-top:18px">Why this risk score</h3><dl class="kv">${r.risk_explanation.map(e => `<dt>${esc(e.feature)}</dt><dd><span style="color:${e.contribution > 0 ? "var(--high)" : "var(--ok)"}">${e.contribution > 0 ? "+" : ""}${e.contribution}</span></dd>`).join("")}</dl>` : ""}
    <h3 style="margin-top:18px">Last hour</h3><div class="chartbox"><canvas id="d-env"></canvas></div>
    <div class="chartbox" style="margin-top:12px"><canvas id="d-sys"></canvas></div>
    ${can("admin") ? `<h3 style="margin-top:18px">Admin</h3><div class="row"><button class="btn small" onclick="rotateKey(${id})">Rotate device key</button><button class="btn small danger" onclick="deleteRobot(${id})">Delete robot</button></div>` : ""}`);
  const rows = await api(`/api/robots/${id}/telemetry?minutes=60&limit=1500`);
  const ser = k => rows.filter(x => x[k] != null).map(x => ({ x: x.ts, y: x[k] }));
  S.charts.d_env = lineChart($("#d-env"), [
    { label: "Temp °C", data: ser("temperature"), borderColor: "#ff6b35" },
    { label: "Smoke ppm", data: ser("smoke"), borderColor: "#8b98a9", yAxisID: "y2" },
  ], { scales: { y2: { position: "right", beginAtZero: true, grid: { display: false } } } });
  S.charts.d_sys = lineChart($("#d-sys"), [
    { label: "Battery %", data: ser("battery"), borderColor: "#3fb950" },
    { label: "Water %", data: ser("water_level"), borderColor: "#58a6ff" },
    { label: "Motor °C", data: ser("motor_temp"), borderColor: "#d2a8ff" },
  ]);
};
window.sendCmd = (id, kind) => act(() => api(`/api/robots/${id}/commands`, { method: "POST", body: { kind, params: {} } }), `${kind.replace(/_/g, " ")} queued`);
window.rotateKey = async id => { if (!confirm("Rotate key? The robot must be updated with the new key.")) return; const r = await act(() => api(`/api/robots/${id}/rotate-key`, { method: "POST" })); closeDrawer(); showKey("robot", r.api_key); };
window.deleteRobot = async id => { if (!confirm("Delete this robot and all its telemetry?")) return; await act(() => api(`/api/robots/${id}`, { method: "DELETE" }), "Robot deleted"); closeDrawer(); await refreshRobots(); renderView(); };

VIEWS.incidents = async root => {
  const filter = S.incFilter || "active";
  const list = await api(`/api/incidents?status=${filter}&limit=300`);
  root.innerHTML = `<div class="head"><h1>Incidents</h1><div class="actions">${can("operator") ? `<button class="btn primary" id="new-inc">Report incident</button>` : ""}</div></div>
    <div class="tabs" style="max-width:520px;margin:0 0 16px">${["active", "open", "acknowledged", "resolved"].map(f => `<button class="tab ${f === filter ? "active" : ""}" data-f="${f}">${f}</button>`).join("")}</div>
    <div class="card tablewrap">${list.length ? `<table><tr><th>#</th><th>Severity</th><th>Title</th><th>Status</th><th>Robot</th><th>Source</th><th>Peak risk</th><th>Assignee</th><th>Opened</th></tr>
    ${list.map(i => `<tr class="click" onclick="openIncident(${i.id})"><td class="muted">${i.id}</td><td>${sevBadge(i.severity)}</td><td>${esc(i.title)}</td><td>${stBadge(i.status)}</td>
      <td>${esc(i.robot_name || "—")}</td><td class="muted">${esc(i.source.replace("_", " "))}</td><td>${fmt(i.peak_risk * 100, 0)}%</td><td>${esc(i.assignee_name || "—")}</td><td class="muted">${ago(i.created_at)}</td></tr>`).join("")}</table>`
    : `<div class="empty">No ${filter} incidents. ${filter === "active" ? "All clear 🧯" : ""}</div>`}</div>`;
  $$(".tabs .tab", root).forEach(t => t.addEventListener("click", () => { S.incFilter = t.dataset.f; renderView(); }));
  $("#new-inc")?.addEventListener("click", () => {
    modal(`<button class="btn ghost small close" onclick="closeModal()">✕</button><h2>Report incident</h2><form class="form" id="inc-form">
      <label>Title<input name="title" required minlength="3" placeholder="Smoke reported in warehouse B"></label>
      <label>Severity<select name="severity"><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label>
      <label>Robot (optional)<select name="robot_id"><option value="">—</option>${S.robots.map(r => `<option value="${r.id}">${esc(r.name)}</option>`).join("")}</select></label>
      <div class="row"><label>X<input name="x" type="number" step="any"></label><label>Y<input name="y" type="number" step="any"></label></div>
      <button class="btn primary">Create</button></form>`);
    $("#inc-form").addEventListener("submit", async e => {
      e.preventDefault(); const f = Object.fromEntries(new FormData(e.target));
      const body = { title: f.title, severity: f.severity, robot_id: f.robot_id ? +f.robot_id : null, x: f.x === "" ? null : +f.x, y: f.y === "" ? null : +f.y };
      await act(() => api("/api/incidents", { method: "POST", body }), "Incident created"); closeModal(); renderView();
    });
  });
  every(5000, () => { if ($("#drawer").classList.contains("hidden") && $("#modal").classList.contains("hidden")) VIEWS.incidents(root); });
};

window.openIncident = async id => {
  const [i, team] = await Promise.all([api(`/api/incidents/${id}`), api("/api/team")]);
  drawer(`<button class="btn ghost small close" onclick="closeDrawer()">✕</button>
    <div class="muted small">Incident #${i.id} · ${esc(i.source.replace("_", " "))}</div><h2 style="margin-top:4px">${esc(i.title)}</h2>
    <div style="display:flex;gap:6px">${sevBadge(i.severity)} ${stBadge(i.status)}</div>
    <dl class="kv" style="margin-top:14px"><dt>Robot</dt><dd>${esc(i.robot_name || "—")}</dd><dt>Location</dt><dd>${i.x != null ? `${fmt(i.x)}, ${fmt(i.y)}` : "—"}</dd>
      <dt>Peak risk</dt><dd>${fmt(i.peak_risk * 100, 0)}%</dd><dt>Opened</dt><dd>${dateTime(i.created_at)}</dd>
      <dt>Time to ack</dt><dd>${i.acknowledged_at ? dur(i.acknowledged_at - i.created_at) : "—"}</dd><dt>Time to resolve</dt><dd>${i.resolved_at ? dur(i.resolved_at - i.created_at) : "—"}</dd></dl>
    ${can("operator") ? `<h3 style="margin-top:18px">Response</h3><div class="row">
      ${i.status !== "resolved" && i.x != null ? `<button class="btn primary small" onclick="dispatchInc(${id})">Dispatch nearest robots</button>` : ""}
      ${i.status === "open" ? `<button class="btn small" onclick="patchInc(${id},{status:'acknowledged'})">Acknowledge</button>` : ""}
      ${i.status !== "resolved" ? `<button class="btn small" onclick="patchInc(${id},{status:'resolved'})">Resolve</button>` : `<button class="btn small" onclick="patchInc(${id},{status:'open'})">Reopen</button>`}</div>
      <div class="row" style="margin-top:10px"><label>Assignee<select id="assignee"><option value="">—</option>${team.map(u => `<option value="${u.id}" ${u.id === i.assignee_id ? "selected" : ""}>${esc(u.name)}</option>`).join("")}</select></label>
      <label>Severity<select id="sev">${["low", "medium", "high", "critical"].map(s => `<option ${s === i.severity ? "selected" : ""}>${s}</option>`).join("")}</select></label></div>
      <form id="note-form" class="row" style="margin-top:10px"><input name="note" placeholder="Add a note to the timeline" maxlength="2000"><button class="btn small" style="flex:0">Add</button></form>` : ""}
    <h3 style="margin-top:18px">Timeline</h3><div class="timeline">${i.timeline.map(e => `<div class="ev"><div class="t">${time(e.ts)}</div><div><b>${esc(e.kind)}</b> ${esc(e.message)}${e.user_name ? ` <span class="muted small">— ${esc(e.user_name)}</span>` : ""}</div></div>`).join("")}</div>`);
  $("#assignee")?.addEventListener("change", e => e.target.value && patchInc(id, { assignee_id: +e.target.value }));
  $("#sev")?.addEventListener("change", e => patchInc(id, { severity: e.target.value }));
  $("#note-form")?.addEventListener("submit", e => { e.preventDefault(); const n = e.target.note.value.trim(); if (n) patchInc(id, { note: n }); });
};
window.patchInc = async (id, body) => { await act(() => api(`/api/incidents/${id}`, { method: "PATCH", body }), "Incident updated"); openIncident(id); refreshIncidents(); };
window.dispatchInc = async id => { const r = await act(() => api(`/api/incidents/${id}/dispatch`, { method: "POST", body: { count: 2 } })); toast(`Dispatched ${r.dispatched.length} robot(s)`, "ok"); openIncident(id); refreshIncidents(); };

VIEWS.commands = async root => {
  const list = await api("/api/commands?limit=200");
  root.innerHTML = `<div class="head"><h1>Commands</h1></div><div class="card tablewrap">${list.length ? `<table><tr><th>#</th><th>Robot</th><th>Command</th><th>Params</th><th>Status</th><th>Result</th><th>Issued</th></tr>
    ${list.map(c => `<tr><td class="muted">${c.id}</td><td>${esc(c.robot_name)}</td><td><b>${esc(c.kind)}</b></td><td><code>${esc(JSON.stringify(c.params))}</code></td><td>${stBadge(c.status)}</td><td><code>${esc(c.result ? JSON.stringify(c.result) : "")}</code></td><td class="muted">${ago(c.created_at)}</td></tr>`).join("")}</table>`
    : `<div class="empty">No commands yet. Send one from a robot's panel or dispatch robots to an incident.</div>`}</div>`;
  every(4000, () => S.view === "commands" && VIEWS.commands(root));
};

VIEWS.rules = async root => {
  const rules = await api("/api/rules");
  const metrics = ["temperature", "smoke", "gas", "humidity", "flame", "battery", "water_level", "motor_temp", "risk_score"];
  root.innerHTML = `<div class="head"><div><h1>Alert rules</h1><div class="muted small">Evaluated on every telemetry sample, alongside the ML risk model and anomaly detector.</div></div></div>
    <div class="card tablewrap">${rules.length ? `<table><tr><th>Name</th><th>Condition</th><th>Severity</th><th>Enabled</th><th></th></tr>
    ${rules.map(r => `<tr><td>${esc(r.name)}</td><td><code>${esc(r.metric)} ${esc(r.op)} ${r.threshold}</code></td><td>${sevBadge(r.severity)}</td>
      <td>${can("admin") ? `<input type="checkbox" style="width:auto" ${r.enabled ? "checked" : ""} onchange='toggleRule(${JSON.stringify(r).replace(/'/g, "&#39;")}, this.checked)'>` : r.enabled ? "yes" : "no"}</td>
      <td>${can("admin") ? `<button class="btn small danger" onclick="deleteRule(${r.id})">Delete</button>` : ""}</td></tr>`).join("")}</table>` : `<div class="empty">No rules.</div>`}</div>
    ${can("admin") ? `<div class="card" style="margin-top:16px"><h3>New rule</h3><form class="row" id="rule-form">
      <label>Name<input name="name" required placeholder="Battery critical"></label>
      <label>Metric<select name="metric">${metrics.map(m => `<option>${m}</option>`).join("")}</select></label>
      <label>Operator<select name="op">${[">", ">=", "<", "<=", "=="].map(o => `<option>${esc(o)}</option>`).join("")}</select></label>
      <label>Threshold<input name="threshold" type="number" step="any" required></label>
      <label>Severity<select name="severity"><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label>
      <button class="btn primary" style="flex:0">Add rule</button></form></div>` : ""}`;
  $("#rule-form")?.addEventListener("submit", async e => {
    e.preventDefault(); const f = Object.fromEntries(new FormData(e.target));
    await act(() => api("/api/rules", { method: "POST", body: { ...f, threshold: +f.threshold } }), "Rule created"); renderView();
  });
};
window.toggleRule = (r, enabled) => act(() => api(`/api/rules/${r.id}`, { method: "PUT", body: { name: r.name, metric: r.metric, op: r.op, threshold: r.threshold, severity: r.severity, enabled } }), enabled ? "Rule enabled" : "Rule disabled");
window.deleteRule = async id => { if (!confirm("Delete rule?")) return; await act(() => api(`/api/rules/${id}`, { method: "DELETE" }), "Rule deleted"); renderView(); };

VIEWS.analytics = async root => {
  const hours = S.anHours || 24;
  const [o, heat] = await Promise.all([api(`/api/analytics/overview?hours=${hours}`), api(`/api/analytics/heatmap?hours=${hours}&cell=5`)]);
  const inc = o.incidents; const pct = o.usage.quota ? (o.usage.period_count / o.usage.quota) * 100 : 0;
  root.innerHTML = `<div class="head"><h1>Analytics</h1><div class="tabs" style="margin:0">${[1, 24, 168, 720].map(h => `<button class="tab ${h === hours ? "active" : ""}" data-h="${h}">${h < 24 ? h + "h" : h / 24 + "d"}</button>`).join("")}</div></div>
    <div class="grid kpis">
      <div class="card kpi"><div class="label">Incidents</div><div class="value">${inc.created}</div><div class="sub">${Object.entries(inc.by_source).map(([k, v]) => `${k.replace("_", " ")}: ${v}`).join(" · ") || "none"}</div></div>
      <div class="card kpi"><div class="label">Mean time to acknowledge</div><div class="value">${dur(inc.mtta_seconds)}</div></div>
      <div class="card kpi"><div class="label">Mean time to resolve</div><div class="value">${dur(inc.mttr_seconds)}</div><div class="sub">p90 ${dur(inc.p90_mttr_seconds)}</div></div>
      <div class="card kpi"><div class="label">Telemetry samples</div><div class="value">${o.telemetry.samples.toLocaleString()}</div></div>
      <div class="card kpi"><div class="label">Monthly quota used</div><div class="value">${fmt(pct, 1)}%</div><div class="sub">${o.usage.period_count.toLocaleString()} / ${o.usage.quota.toLocaleString()}</div></div>
    </div>
    <div class="grid cols-2" style="margin-top:16px">
      <div class="card"><h3>Fleet fire risk over time</h3><div class="chartbox"><canvas id="a-risk"></canvas></div></div>
      <div class="card"><h3>Risk hotspot map</h3><div class="mapwrap"><canvas id="a-heat"></canvas></div><div class="muted small" style="margin-top:8px">Peak risk recorded per 5 m cell</div></div>
    </div>
    <div class="grid cols-even" style="margin-top:16px">
      <div class="card"><h3>What-if risk predictor</h3><form class="form" id="predict">
        <div class="row"><label>Temperature °C<input name="temperature" type="number" step="any" value="45"></label><label>Smoke ppm<input name="smoke" type="number" step="any" value="120"></label></div>
        <div class="row"><label>Gas ppm<input name="gas" type="number" step="any" value="150"></label><label>Humidity %<input name="humidity" type="number" step="any" value="35"></label></div>
        <label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="flame" style="width:auto"> Flame detected</label></form>
        <div id="predict-out" style="margin-top:12px"></div></div>
      <div class="card"><h3>Active incidents by severity</h3><div class="chartbox"><canvas id="a-sev"></canvas></div></div>
    </div>`;
  $$(".tabs .tab", root).forEach(t => t.addEventListener("click", () => { S.anHours = +t.dataset.h; renderView(); }));
  const s = o.telemetry.series;
  S.charts.risk = lineChart($("#a-risk"), [
    { label: "Max risk", data: s.map(p => ({ x: p.bucket, y: p.max_risk })), borderColor: "#f85149" },
    { label: "Avg risk", data: s.map(p => ({ x: p.bucket, y: p.avg_risk })), borderColor: "#ffb547" },
  ], { y: { max: 1 }, points: true });
  const sevs = ["low", "medium", "high", "critical"];
  S.charts.sev = new Chart($("#a-sev"), { type: "bar", data: { labels: sevs, datasets: [{ data: sevs.map(k => inc.active_by_severity[k] || 0), backgroundColor: sevs.map(k => SEV_COLOR[k]), borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } });
  drawMap($("#a-heat"), { heat });
  const predict = async () => {
    const f = new FormData($("#predict")); const body = {}; for (const k of ["temperature", "smoke", "gas", "humidity"]) body[k] = +f.get(k); body.flame = f.get("flame") ? 1 : 0;
    const r = await api("/api/analytics/predict", { method: "POST", body });
    $("#predict-out").innerHTML = `<div style="font-size:26px;font-weight:700;color:${SEV_COLOR[r.severity]}">${fmt(r.risk_score * 100, 1)}% ${sevBadge(r.severity)}</div>
      <div class="muted small" style="margin-top:6px">Top drivers: ${r.explanation.slice(0, 3).map(e => `${esc(e.feature)} (${e.contribution > 0 ? "+" : ""}${e.contribution})`).join(", ")}</div>`;
  };
  $("#predict").addEventListener("input", predict); predict();
};

VIEWS.settings = async root => {
  const isAdmin = can("admin");
  const [team, plans, me] = await Promise.all([api("/api/team"), api("/api/billing/plans"), api("/api/auth/me")]);
  S.me = me;
  const [hooks, auditRows] = isAdmin ? await Promise.all([api("/api/webhooks"), api("/api/audit?limit=100")]) : [[], []];
  root.innerHTML = `<div class="head"><h1>Settings</h1></div>
    <div class="card"><h3>Plan &amp; billing</h3><div class="plans">${plans.map(p => `<div class="plan ${p.id === me.plan.id ? "current" : ""}">
      <b>${esc(p.name)}</b><div class="price">$${p.price}<span class="muted small">/mo</span></div>
      <div class="muted small">${p.max_robots >= 10000 ? "Unlimited" : p.max_robots} robots · ${p.max_users >= 10000 ? "unlimited" : p.max_users} users<br>${(p.telemetry_per_month / 1e6).toLocaleString()}M samples/month<br>${p.webhooks ? "Webhooks included" : "No webhooks"}</div>
      ${p.id === me.plan.id ? `<span class="badge">Current plan</span>` : isAdmin ? `<button class="btn small" onclick="changePlan('${p.id}')">Switch to ${esc(p.name)}</button>` : ""}</div>`).join("")}</div></div>

    <div class="card" style="margin-top:16px"><h3>Team</h3><div class="tablewrap"><table><tr><th>Name</th><th>Email</th><th>Role</th><th></th></tr>
      ${team.map(u => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${isAdmin && u.id !== me.user.id ? `<select onchange="setRole(${u.id}, this.value)" style="width:auto">${["viewer", "operator", "admin"].map(r => `<option ${r === u.role ? "selected" : ""}>${r}</option>`).join("")}</select>` : esc(u.role)}</td>
      <td>${isAdmin && u.id !== me.user.id ? `<button class="btn small danger" onclick="removeUser(${u.id})">Remove</button>` : ""}</td></tr>`).join("")}</table></div>
      ${isAdmin ? `<form class="row" id="invite" style="margin-top:12px"><label>Name<input name="name" required></label><label>Email<input name="email" type="email" required></label>
        <label>Temporary password<input name="password" type="password" minlength="8" required></label><label>Role<select name="role"><option>viewer</option><option selected>operator</option><option>admin</option></select></label>
        <button class="btn primary" style="flex:0">Add member</button></form>` : ""}</div>

    ${isAdmin ? `<div class="card" style="margin-top:16px"><h3>Demo mode</h3><p class="muted">The built-in simulator drives your robots through patrols, battery drain and random fires, using the same pipeline as real hardware.</p>
      <div class="row"><button class="btn" onclick="toggleSim(${!me.org.simulator_enabled})">${me.org.simulator_enabled ? "Stop simulator" : "Start simulator"}</button><button class="btn" onclick="seedDemo()">Add demo robots</button></div></div>

    <div class="card" style="margin-top:16px"><h3>Webhooks</h3><p class="muted">Signed with HMAC-SHA256 in <code>X-FireOps-Signature</code>. Events: incident.opened, incident.escalated, incident.updated, billing.plan_changed.</p>
      ${hooks.length ? `<div class="tablewrap"><table><tr><th>URL</th><th>Events</th><th>Secret</th><th>Last delivery</th><th></th></tr>${hooks.map(h => `<tr><td>${esc(h.url)}</td><td>${esc(h.events)}</td><td><code>${esc(h.secret)}</code></td><td class="muted">${esc(h.last_status || "—")}</td>
        <td><div class="row"><button class="btn small" onclick="testHook(${h.id})">Test</button><button class="btn small danger" onclick="deleteHook(${h.id})">Delete</button></div></td></tr>`).join("")}</table></div>` : ""}
      ${me.plan.webhooks ? `<form class="row" id="hook" style="margin-top:12px"><label>Endpoint URL<input name="url" type="url" required placeholder="https://example.com/fireops"></label><label>Events<input name="events" value="*"></label><button class="btn primary" style="flex:0">Add webhook</button></form>` : `<div class="muted">Upgrade to Pro to enable webhooks.</div>`}</div>

    <div class="card" style="margin-top:16px"><h3>Audit log</h3><div class="tablewrap" style="max-height:360px;overflow-y:auto"><table><tr><th>When</th><th>User</th><th>Action</th><th>Detail</th></tr>
      ${auditRows.map(a => `<tr><td class="muted">${dateTime(a.ts)}</td><td>${esc(a.user_name || "system")}</td><td><code>${esc(a.action)}</code></td><td class="muted small"><code>${esc(a.detail)}</code></td></tr>`).join("")}</table></div></div>` : ""}`;
  $("#invite")?.addEventListener("submit", async e => { e.preventDefault(); await act(() => api("/api/team", { method: "POST", body: Object.fromEntries(new FormData(e.target)) }), "Member added"); renderView(); });
  $("#hook")?.addEventListener("submit", async e => { e.preventDefault(); await act(() => api("/api/webhooks", { method: "POST", body: Object.fromEntries(new FormData(e.target)) }), "Webhook added"); renderView(); });
};
window.changePlan = async plan => { await act(() => api("/api/billing/plan", { method: "POST", body: { plan } }), "Plan updated"); S.me = await api("/api/auth/me"); $("#plan-badge").textContent = S.me.plan.name; renderView(); };
window.setRole = (id, role) => act(() => api(`/api/team/${id}`, { method: "PATCH", body: { role } }), "Role updated");
window.removeUser = async id => { if (!confirm("Remove this member?")) return; await act(() => api(`/api/team/${id}`, { method: "DELETE" }), "Member removed"); renderView(); };
window.toggleSim = async enabled => { await act(() => api("/api/org/simulator", { method: "POST", body: { enabled } }), enabled ? "Simulator started" : "Simulator stopped"); S.me = await api("/api/auth/me"); renderView(); };
window.seedDemo = async () => { const r = await act(() => api("/api/demo/seed", { method: "POST" })); toast(`Added ${r.created_robot_ids.length} demo robot(s)`, "ok"); await refreshRobots(); renderView(); };
window.testHook = async id => { const r = await act(() => api(`/api/webhooks/${id}/test`, { method: "POST" })); toast(`Delivery result: ${esc(r.status)}`); renderView(); };
window.deleteHook = async id => { await act(() => api(`/api/webhooks/${id}`, { method: "DELETE" }), "Webhook deleted"); renderView(); };
Object.assign(window, { navigate, closeModal, closeDrawer, toast });

boot();
