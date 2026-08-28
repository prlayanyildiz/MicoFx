"use strict";

/* ------------------------------------------------------------------ utils */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function helpTitle(k, ns) {
  const h = typeof FIELD_HELP === "undefined" ? {} : FIELD_HELP;
  if (ns && h[`${ns}.${k}`]) return h[`${ns}.${k}`];
  return h[k] || "";
}

function titled(node, k, ns) {
  const tip = helpTitle(k, ns);
  if (tip) node.title = tip;
  return node;
}

function applyStaticHelp() {
  $$("[data-help]").forEach((node) => {
    const tip = helpTitle(node.dataset.help);
    if (tip) node.title = tip;
  });
}

const GROUP_LABEL = { forex: "Forex", index: "Endeks", commodity: "Emtia",
                      crypto: "Kripto", stock: "Hisse" };
// Every <select> of groups is built from this, so a group added to the book
// cannot go missing from the panel that has to offer it.
function fillGroupSelects() {
  document.querySelectorAll("select[data-groups]").forEach((sel) => {
    const keep = sel.dataset.groups === "filter";
    const cur = sel.value;
    sel.innerHTML = (keep ? `<option value="">Tum gruplar</option>` : "")
      + Object.entries(GROUP_LABEL)
          .map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
    if (cur) sel.value = cur;
  });
}
const DAY_LABEL = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"];
const LOG_LEVELS = ["TRADE", "SIGNAL", "OPT", "AI", "CFG", "INFO", "WARN", "ERROR", "DEBUG"];
const AI_STATE = {
  ok: ["on", "Saglikli"], watch: ["warn", "Izlemede"],
  quarantine: ["bad", "Karantina"], idle: ["off", "Veri yok"],
};

let STATE = {};
let SYMBOLS = [];
let OPT_PARAMS = null;
let activeTab = "panel";
let optSelection = new Set();
let optTfSelection = new Set();
const OPT_TF_OPTIONS = ["M5", "M15", "M30"];
let logAfter = 0;
let logEpoch = 0;
let logFilter = new Set(LOG_LEVELS);
let logSymbolFilter = new Set(); // empty = all symbols
let logSeenSymbols = new Set();
let logSearch = "";
let logSearchTimer = null;
let logPaused = false;
let logPending = [];
let logUnseen = 0;
let logCompact = false;
let cardsBuilt = false;
let pollTimer = null;
let optPickerSig = "";
let portfolioSig = "";
let aiTableSig = "";
let refreshBusy = false;
let refreshQueued = false;
let lastViewPulse = "";
let lastViewTab = "";

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const res = await fetch(path, {
    ...options,
    headers,
    credentials: "same-origin",
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
  return data;
}

// Symbol names (broker_symbol is user/API-settable), broker/account strings
// and log/error text land in innerHTML only after esc(). Session is an
// HttpOnly cookie, not a meta token; still escape, because a future sink
// would run in the same origin as every mutation.
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

// Position side / signal direction land straight in a CSS class attribute
// in several tables (`class="pill ${v}"`) with no allowlist - esc() alone
// still leaves them free to break out of the attribute (an unescaped quote
// inside the escaped text is still just text, but esc() doesn't stop a
// value from containing one either way). Only "buy"/"sell" are ever real
// values here; anything else - a bug upstream, a corrupted payload - is
// dropped to a neutral class instead of trusted into the markup.
const sideClass = (v) => (v === "buy" || v === "sell" ? v : "dim");

function toast(message, kind = "") {
  const box = document.createElement("div");
  box.className = kind;
  box.textContent = message;
  $("#toast").appendChild(box);
  setTimeout(() => box.remove(), 4200);
}

// /api/symbols-bulk only reports "changed" in its happy path - a per-symbol
// guard (open position blocking a strategy/TF/magic/exit-field change) skips
// that symbol silently unless the caller also surfaces res.rejected. Shared
// so every bulk action reports the same way instead of a success-only toast
// hiding a partial failure.
function toastBulkResult(res, verb) {
  const rejected = res.rejected || [];
  if (!rejected.length) {
    toast(`${res.changed} sembol ${verb}`, "ok");
    return;
  }
  toast(`${res.changed} sembol ${verb}, ${rejected.length} sembol atlandi `
      + `(acik pozisyon var): ${rejected.join(", ")}`, "err");
}

function num(value, digits = 2) {
  const v = Number(value);
  if (!isFinite(v)) return "-";
  return v.toLocaleString("tr-TR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function signed(value, digits = 2) {
  const v = Number(value) || 0;
  return (v > 0 ? "+" : "") + num(v, digits);
}

function cls(value) {
  const v = Number(value) || 0;
  return v > 0 ? "pos" : v < 0 ? "neg" : "dim";
}

function price(value, digits = 5) {
  const v = Number(value);
  if (!isFinite(v) || v === 0) return "-";
  return v.toFixed(digits);
}

function duration(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  if (s < 60) return `${s}sn`;
  if (s < 3600) return `${Math.floor(s / 60)}dk`;
  const h = Math.floor(s / 3600);
  return `${h}s ${Math.floor((s % 3600) / 60)}dk`;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (child) node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function rowsInto(table, rows, emptyText, colspan) {
  const body = $("tbody", table);
  body.innerHTML = "";
  if (!rows.length) {
    body.appendChild(el("tr", {}, el("td", { class: "empty", colspan })));
    $("td", body).textContent = emptyText;
    return;
  }
  rows.forEach((r) => body.appendChild(r));
}

/* ------------------------------------------------------------------ tabs */

function selectTab(name) {
  activeTab = name;
  lastViewPulse = "";
  lastViewTab = "";
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`));
  if (name === "opt") {
    renderOptJob();
    if (!OPT_PARAMS) loadOptParams().then(loadOptHistory);
    else syncOptPicker();
  }
  if (name === "tani") {
    loadGates(); loadBlocks(); loadSpreadRatio(); loadAutopsies();
    renderExecution(); renderLive();
  }
  if (name === "panel" && STATE && STATE.bot) {
    renderTop(); renderCapacity(); renderPositions(); renderHarvest(); renderDayTable();
    renderExecution(); renderLive();
  }
  // These three used to render only on the next poll, so switching to them
  // showed an empty panel for up to one interval - 3s focused, 6s when the
  // window is in the background, which is exactly when an operator tabs back
  // to it. panel/tani/opt already painted on the switch; this makes the rest
  // behave the same instead of three tabs being slower for no stated reason.
  if (name === "sistem" && STATE && STATE.system) renderSystem();
  if (name === "semboller") {
    if (!cardsBuilt && SYMBOLS.length) buildSymbolCards();
    updateSymbolCards();
  }
  if (name === "ai" && STATE && STATE.ai) renderAI();
  if (name === "log") pollLogs();
}

/* ------------------------------------------------------- pruning gates */

// Four separate gates rather than one verdict, because two symbols were cut
// this session on the wrong number - one for low productivity that was really
// a spread ceiling set under its own normal spread, three on a month of data
// gathered under a session regime fixed twenty minutes earlier. Seeing WHICH
// gate a symbol fails is the whole point; a single score would hide it again.
// Review layers, as classification only - nothing here switches a symbol off.
// The split that matters is a weak edge measured on a THICK sample (US30,
// 1.80 sigma over 407 trades: small edge, precisely known) against one on a
// thin sample (CHFJPY, 0.28 over 39: cannot tell yet). Treating those the same
// is how half a book gets cut in one evening.
const LAYER_LABEL = {
  normal: ["normal", "on"],
  izle_zayif: ["izle - kalin ama zayif", "off"],
  izle_ince_sigma: ["izle - sigma ince ornekten", "off"],
  soft_aday: ["gozden gecir - ince + olculemez", "off"],
};

const GATE_LABEL = {
  olculebilir: "olculemez",
  maliyet: "maliyet",
  tavan: "tavan",
  siklik: "siklik",
};

function gateCell(value, limit, bad, digits = 3) {
  if (value == null) return '<span class="dim">-</span>';
  const shown = limit != null
    ? `${num(value, digits)} <span class="dim">/ ${num(limit, digits)}</span>`
    : num(value, digits);
  return `<span class="${bad ? "neg" : "dim"}">${shown}</span>`;
}

async function loadGates() {
  const note = $("#gates-note");
  let data;
  try {
    data = await api("/api/analysis/portfolio-gates");
  } catch (err) {
    if (note) note.textContent = `Kapilar okunamadi: ${err.message || err}`;
    return;
  }
  const rows = (data.rows || []).map((r) => {
    const f = r.fails || [];
    const has = (g) => f.includes(g);
    const tr = el("tr");
    // A thin sample is not a failure, but the measurability flag must not be
    // read alone under one - n=30 at 0.5R clears 2 SE while saying little.
    const sigma = r.sigma == null
      ? '<span class="dim">-</span>'
      : `<span class="${has("olculebilir") ? "neg" : "pos"}">${num(r.sigma, 2)}</span>`
        + (r.thin_sample ? ' <span class="warn-text" title="Orneklem ince - bu bayrak tek basina okunmamali">ince</span>' : "");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td class="dim">${esc(r.strategy || "-")}</td>
      <td class="dim">${esc(r.timeframe || "-")}</td>
      <td class="num ${r.thin_sample ? "warn-text" : "dim"}">${r.trades ?? 0}</td>
      <td class="num">${gateCell(r.expectancy_r, r.needs_r, has("olculebilir"))}</td>
      <td class="num">${sigma}</td>
      <td class="num">${gateCell(r.cost_per_trade_r, r.cost_ceiling_r, has("maliyet"))}</td>
      <td class="num">${gateCell(r.spread_atr_now, r.max_spread_atr, has("tavan"), 4)}</td>
      <td class="num">${gateCell(r.fill_rate, null, has("siklik"), 2)}</td>
      <td>${f.length
        ? f.map((g) => `<span class="pill off">${esc(GATE_LABEL[g] || g)}</span>`).join(" ")
        : '<span class="pill on">temiz</span>'}</td>
      <td><span class="pill ${(LAYER_LABEL[r.layer] || ["", "off"])[1]}">${
        esc((LAYER_LABEL[r.layer] || [r.layer || "-"])[0])}</span></td>`;
    return tr;
  });
  rowsInto($("#gates-table"), rows, "Aktif sembol yok", 11);
  if (note) {
    note.textContent = `${data.note || ""} Siklik penceresi ${data.window_days} gun.`;
  }
}

// Counted only where a signal actually reached the entry stage, which is what
// makes the number decisive: attempts near the holdout's implied count with
// few opens means a gate is eating them and the blocks column names it, while
// attempts that are themselves short clears the gates and points upstream at
// signal generation.
// The search charges the bar's spread; the live gate enforces the tick's. This
// is the measured distance between them, per symbol, and nothing acts on it
// until the sample count clears the threshold - a spot reading here is what
// misled the first attempt at this number.
async function loadSpreadRatio() {
  const note = $("#ratio-note");
  let data;
  try {
    data = await api("/api/analysis/spread-ratio");
  } catch (err) {
    if (note) note.textContent = `Olcum okunamadi: ${err.message || err}`;
    return;
  }
  const rows = (data.rows || []).map((r) => {
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td class="num ${r.enough ? "dim" : "warn-text"}">${r.samples}</td>
      <td class="num ${r.median >= 1.5 ? "neg" : "dim"}"><b>${num(r.median, 2)}x</b></td>
      <td class="num dim">${num(r.p90, 2)}x</td>
      <td>${r.enough
        ? '<span class="pill on">aramaya uygulaniyor</span>'
        : `<span class="pill off">ornek yetersiz (${data.min_samples})</span>`}</td>`;
    return tr;
  });
  rowsInto($("#ratio-table"), rows, "Henuz olcum yok", 5);
  if (note) note.textContent = data.note || "";
}

let symbolsSig = "";

async function loadSymbols() {
  try {
    const res = await api("/api/symbols");
    if (res && res.symbols) {
      SYMBOLS = res.symbols;
    }
  } catch (_) { /* transient; next poll retries */ }
}

async function loadAutopsies() {
  // The endpoint has existed since the autopsies did; nothing rendered it, so
  // every question about an exit meant reading sqlite by hand. Rows only - the
  // aggregate cells live in the note, because a cell under 30 samples is a
  // count and putting it in a grid invites reading it as a finding.
  const note = $("#autopsy-note");
  let data;
  try {
    data = await api("/api/analysis/trade-autopsies");
  } catch (err) {
    if (note) note.textContent = `Otopsi okunamadi: ${err.message || err}`;
    return;
  }
  const rows = (data.rows || []).slice().reverse().map((r) => {
    const after = Number(r.after_1h_bars) > 0;
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol || "")}</td>
      <td class="num dim mono">${r.ticket != null ? esc(String(r.ticket)) : "-"}</td>
      <td><span class="pill ${r.exit_reason === "trail" ? "on" : "off"}">${esc(r.exit_reason || "-")}</span></td>
      <td class="num dim">${r.held_min != null ? num(r.held_min, 1) : "-"}</td>
      <td class="num ${cls(r.r_realised)}">${r.r_realised != null ? signed(r.r_realised, 3) : "-"}</td>
      <td class="num dim">${r.mfe_r != null ? num(r.mfe_r, 3) : "-"}</td>
      <td class="num ${Number(r.r_realised) > 0 && Number(r.left_on_table_r) >= 1 ? "neg" : "dim"}">${
        Number(r.r_realised) > 0 && r.left_on_table_r != null ? num(r.left_on_table_r, 3) : "-"}</td>
      <td class="dim">${after
        ? `${r.after_1h_through_entry ? '<span class="pill off">girise dondu</span>' : ""}`
          + `${r.after_1h_extra_r != null ? ` devam ${num(r.after_1h_extra_r, 2)}R` : ""}`
          + `${r.after_1h_recovery_r != null ? ` toparlanma ${num(r.after_1h_recovery_r, 2)}R` : ""}`
        : '<span class="dim">-</span>'}</td>`;
    return tr;
  });
  rowsInto($("#autopsy-table"), rows, "Henuz kapanis otopsisi yok", 8);
  if (note) {
    const n = Number(data.after_1h_n || 0);
    note.innerHTML = esc(data.note || "")
      + (n
        ? ` | 1 saat olcumu ${n}: girise donen ${data.after_1h_through_entry}`
          + `, >=0.5R devam ${data.after_1h_extra_ge_0_5r}`
          + `, >=0.5R toparlanma ${data.after_1h_recovery_ge_0_5r}`
        : ' | <span class="dim">1 saat olcumu henuz yok (kapanistan 1 saat sonra dolar)</span>')
      + (Number(data.n || 0) < 30 ? ' | <b>n&lt;30: sayi, hukum degil</b>' : "");
  }
}

async function loadBlocks() {
  const note = $("#blocks-note");
  let data;
  try {
    data = await api("/api/analysis/entry-blocks");
  } catch (err) {
    if (note) note.textContent = `Sayaclar okunamadi: ${err.message || err}`;
    return;
  }
  const rows = (data.rows || []).map((r) => {
    const blocks = Object.entries(r.blocks || {});
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)} <span class="dim">${esc(r.leg || "")}</span></td>
      <td class="num">${r.signals}</td>
      <td class="num ${r.opened ? "pos" : "dim"}">${r.opened}</td>
      <td class="num ${r.fill_rate != null && r.fill_rate < 0.25 ? "neg" : "dim"}">${
        r.fill_rate != null ? num(r.fill_rate, 2) : "-"}</td>
      <td>${blocks.length
        ? blocks.map(([k, v]) => {
            const poll = (r.retries || {})[k];
            const tip = poll != null
              ? `${esc(k)}: ${v} sinyal, ${poll} poll`
              : esc(k);
            return `<span class="pill off" title="${tip}">${esc(k)} ${v}</span>`;
          }).join(" ")
        : '<span class="dim">-</span>'}</td>`;
    return tr;
  });
  rowsInto($("#blocks-table"), rows, "Henuz giris denemesi yok", 5);
  if (note) note.textContent = data.note || "";
}

/* ----------------------------------------------------------- panel: cards */

function renderTop() {
  const acc = STATE.account || {};
  const bot = STATE.bot || {};
  const mt5 = STATE.mt5 || {};
  const day = STATE.day || {};
  const cap = overlayCapacityFromPositions(STATE.capacity || {});

  const ai = STATE.ai || {};

  // Operator 26.08: the four gauges moved up here too, so the strip below is
  // gone entirely and the whole account picture is on one row, on every tab.
  // A chip may now carry a progress bar; that is the only thing the cards did
  // that a chip could not.
  const marginPct = cap.margin_usage_pct || 0;
  const marginMax = cap.max_margin_usage_pct || 100;
  const marginRatio = Math.min(100, (marginPct / Math.max(1, marginMax)) * 100);

  const unbounded = cap.open_risk_unbounded === true;

  const paper = Number(cap.projected_monthly ?? 0);
  // 0 is a defined JSON number, so ?? does not fall through. A search-frozen
  // blob with costed=0 and paper=0 is what overlayMonthlyProjection fills;
  // a missing costed slice that left costed at 0 used to keep the chip blank
  // while paper was hundreds.
  const costed = Number(cap.projected_costed_monthly) || paper;
  const projPct = (Number(cap.projected_costed_monthly) ? cap.projected_costed_monthly_pct
                   : null) ?? cap.projected_monthly_pct;
  const projDaily = (Number(cap.projected_costed_monthly) ? cap.projected_costed_daily
                     : null) ?? cap.projected_daily;
  const projDenom = Math.max(Math.abs(paper), Math.abs(costed), 1e-9);
  const projGap = Math.abs(paper - costed) / projDenom;

  // Operator 26.08: ordered by how often it is looked at, not by where the
  // number happens to live. State (is it even running) -> today (the figure
  // checked most) -> the gauges that decide the next entry -> account totals
  // -> the projection, which is the slowest-moving thing on the bar.
  const clockStale = mt5.clock_stale === true || Object.values(STATE.states || {}).some(
    (st) => String((st && st.note) || "").includes("broker saati bayat"));
  const botText = clockStale ? "SAAT BAYAT"
    : (bot.running ? "CALISIYOR" : (bot.watching ? "IZLIYOR" : "DURDU"));
  const items = [
    { lbl: "Bot", val: botText, cls: clockStale ? "neg" : (bot.running ? "pos" : (bot.watching ? "muted" : "dim")) },
    { lbl: "MT5", val: mt5.connected ? "BAGLI" : "KOPUK", cls: mt5.connected ? "pos" : "neg" },
    { lbl: "Saat", val: clockStale ? "BAYAT" : (mt5.server_time || "").slice(11, 16),
      cls: clockStale ? "neg" : "",
      sub: clockStale ? (mt5.server_time || "").slice(11, 16) : "",
      tip: clockStale
        ? `broker saati donmus (${mt5.server_time || "-"}) - yeni giris yok`
        : (mt5.server_time || "") },
    { lbl: "Gun", val: signed(day.realised), cls: cls(day.realised),
      sub: `${signed(day.pnl_pct, 2)}%`,
      tip: `${day.closed_trades || 0} islem %${num(day.win_rate, 0)} basari`
        + ` | lot x${num(ai.risk_scale ?? 1, 2)}`
        + (ai.risk_scale_enforced === false ? " (carpan uygulanmiyor)" : "") },
    { lbl: "Acik K/Z", val: signed(acc.profit),
      cls: unbounded ? "neg" : cls(acc.profit),
      sub: unbounded ? "STOPSUZ" : "",
      tip: unbounded ? "ciplak pozisyon - SL yok, yeni giris yok" : "" },
    { lbl: "Marj Kullanimi", val: `%${num(marginPct, 1)}`,
      tip: `tavan %${num(marginMax, 0)}`,
      bar: marginRatio, barClass: marginRatio > 85 ? "bad" : marginRatio > 60 ? "warn" : "" },
    { lbl: "Varlik", val: num(acc.equity) },
    // Currency and leverage ride in the label, not a second line: the top bar
    // has spare width and no spare height, and these two never change while
    // the account is up - they are context for the number, not a reading.
    // A value is never ellipsised - truncating "-256,23 (-9,75%)" to
    // "-256,23 (-9..." hides the number the chip exists for. Anything that
    // does not fit becomes a short sub plus a hover title instead.
    { lbl: "Bakiye", val: num(acc.balance), sub: acc.currency || "",
      tip: `${acc.currency || ""} | kaldirac 1:${acc.leverage || "-"}` },
    { lbl: "Serbest Marj", val: num(acc.margin_free),
      tip: `kullanilan ${num(acc.margin)}` },
    { lbl: "Beklenen Aylik",
      val: signed(costed),
      cls: cap.projected_costed_negative ? "neg"
        : costed >= 0 ? "pos" : "neg",
      sub: "kagit",
      tip: `holdout kagidi, canli sonuc degil | %${num(projPct, 2)} | gunluk ${signed(projDaily)}`
        + ` | maliyet odenmeden ${signed(paper)}`
        + (projGap > 0.25 ? ` | kagit/maliyetli fark %${num(projGap * 100, 0)}` : "") },
  ];
  if (acc.netting) {
    items.push({ lbl: "Hesap modu", val: "NETTING - ISLEM DURDU", cls: "neg" });
  }
  if (Number(acc.trade_mode) === 2) {
    items.push({ lbl: "Hesap", val: "GERCEK PARA", cls: "neg" });
  }

  $("#topstats").innerHTML = items.map((it) =>
    `<div class="tstat"`
    + ` title="${esc([helpTitle("top." + it.lbl), it.tip].filter(Boolean).join(" — "))}">`
    + `<div class="lbl">${esc(it.lbl)}${
      it.sub ? ` <span class="dim">${esc(it.sub)}</span>` : ""}</div>`
    + `<div class="val ${it.cls || ""}">${esc(it.val)}</div>`
    + (it.bar !== undefined
      ? `<div class="bar"><i class="${it.barClass || ""}" style="width:${it.bar}%"></i></div>` : "")
    + `</div>`
  ).join("");

  $("#btn-start").disabled = !!bot.running;
  $("#btn-stop").disabled = !bot.running;

  const clockWarn = (mt5.session_clock_warning || "").trim();
  const banner = $("#clock-warn");
  if (banner) {
    banner.hidden = !clockWarn;
    banner.textContent = clockWarn;
  }
  const lock = STATE.account_lock || {};
  const lockBanner = $("#lock-warn");
  if (lockBanner) {
    const lockText = (lock.reason || "").trim();
    lockBanner.hidden = !lockText;
    lockBanner.textContent = lockText;
  }
}

// The cost column used to print one number: the share of R that spread and
// commission take *at this instant*. That is a single live tick, and a tick
// taken during the broker rollover reads 10-19x the long-run figure on FX -
// wide enough to make a healthy symbol look permanently unprofitable. Reading
// it without that context led to four symbols being switched off on evidence
// that evaporated an hour later, so the column now carries the walk-forward's
// own long-run cost next to it and says when the live one is inflated.
function costCell(r) {
  if (!r.risk_per_trade) return "-";
  const ceiling = Number((STATE.system || {}).max_cost_pct_of_risk
    || (STATE.capacity || {}).max_cost_pct_of_risk || 0);
  const live = Number(r.cost_pct_of_risk || 0);
  const over = ceiling > 0 && live > ceiling;
  const mark = over
    ? ` <span class="pill off" title="Canli maliyet kapisi bu sembolu engeller">esik %${num(ceiling, 0)}</span>`
    : "";
  const now = `${num(r.cost_per_trade)} (%${num(r.cost_pct_of_risk, 0)})${mark}`;
  if (!r.cost_pct_typical) return now;
  const inflated = r.cost_inflation >= 1.8;
  return inflated
    ? `${now} <span class="dim">/ normal %${num(r.cost_pct_typical, 0)} · ${num(r.cost_inflation, 1)}x</span>`
    : `${now} <span class="dim">/ normal %${num(r.cost_pct_typical, 0)}</span>`;
}

function costCls(r) {
  const ceiling = Number((STATE.system || {}).max_cost_pct_of_risk
    || (STATE.capacity || {}).max_cost_pct_of_risk || 0);
  const typical = Number(r.cost_pct_typical || 0);
  const live = Number(r.cost_pct_of_risk || 0);
  const blocked = ceiling > 0 && (typical > ceiling || live > ceiling);
  if (blocked) return "neg";
  if (r.cost_pct_typical && r.cost_inflation >= 1.8) return "warn-text";
  return live > 15 ? "neg" : "dim";
}

function costTitle(r) {
  const lines = [`Su anki tick: maliyet riskin %${num(r.cost_pct_of_risk, 1)}'i`];
  if (r.cost_pct_typical) {
    lines.push(`Yuruyen-ileri uzun vade: %${num(r.cost_pct_typical, 1)}`);
    if (r.cost_inflation >= 1.8) {
      lines.push(`Su an normalin ${num(r.cost_inflation, 1)} katinda - spread gecici olarak sismis `
               + `(broker rollover / ince seans). Sembolun kalici ozelligi degil.`);
      lines.push(`Bu haldeyken maliyet kapisi girisleri engeller; spread normale `
               + `donunce kendiliginden acilir.`);
    }
  } else {
    lines.push("Uzun vade maliyet yok - bu sembol icin henuz optimizasyon ozeti kaydedilmemis.");
  }
  return lines.join("\n");
}

function overlayCapacityFromPositions(cap) {
  // This PID's engine still returns the 10:03 copy while a search holds
  // the MT5 lock. Open count and floating P/L are already on STATE.positions.
  const busy = !!(STATE.opt && (STATE.opt.busy || STATE.opt.state === "running"));
  if (!busy && !cap.search_frozen) {
    if (!(Number(cap.projected_monthly) || Number(cap.projected_costed_monthly))) {
      return Object.assign({}, cap, overlayMonthlyProjection(cap));
    }
    return cap;
  }
  const by = {};
  for (const p of (STATE.positions || [])) {
    const s = p.symbol;
    if (!by[s]) by[s] = { n: 0, pnl: 0 };
    by[s].n += 1;
    by[s].pnl += Number(p.profit || 0) + Number(p.swap || 0);
  }
  const rows = (cap.rows || []).map((r) => {
    const hit = by[r.symbol] || by[r.broker_symbol] || { n: 0, pnl: 0 };
    const oldN = r.open_positions || 0;
    const oldFree = r.free_slots || 0;
    const n = hit.n;
    return Object.assign({}, r, {
      open_positions: n,
      open_profit: hit.pnl,
      free_slots: r.enabled ? Math.max(0, oldFree - (n - oldN)) : 0,
    });
  });
  const nAll = (STATE.positions || []).length;
  const oldTotal = cap.open_total || 0;
  const oldGlobal = cap.global_free_slots || 0;
  const out = Object.assign({}, cap, {
    rows,
    search_frozen: true,
    open_total: nAll,
    global_free_slots: Math.max(0, oldGlobal - (nAll - oldTotal)),
  });
  if (!(Number(out.projected_monthly) || Number(out.projected_costed_monthly))) {
    Object.assign(out, overlayMonthlyProjection(out));
  }
  return out;
}

function overlayMonthlyProjection(cap) {
  // Search-frozen capacity often ships risk_per_trade=0, which zeroes the
  // chip. Recompute from the holdout stamp at configured risk % — paper,
  // not live P/L, which is what the card always was.
  const acc = STATE.account || {};
  const equity = Number(acc.equity || acc.balance || 0);
  const bal = Number(acc.balance || equity || 0);
  const byRow = {};
  for (const r of (cap.rows || [])) byRow[r.symbol] = r;
  let paper = 0;
  let costed = 0;
  for (const s of (typeof SYMBOLS !== "undefined" ? SYMBOLS : [])) {
    if (!s.enabled) continue;
    const osu = s.opt_summary || {};
    const hold = osu.holdout || {};
    const days = Number(osu.holdout_days || 0);
    const net = Number(hold.net_r || 0);
    if (!(days > 0) || !net) continue;
    const row = byRow[s.symbol] || {};
    let risk = Number(row.risk_per_trade || 0);
    if (!(risk > 0) && bal > 0) {
      risk = bal * Number(s.risk_percent || 0) / 100;
      const es = Number(row.edge_scale);
      if (es > 0) risk *= es;
    }
    if (!(risk > 0)) continue;
    paper += net * risk / days;
    const cnet = Number((osu.holdout_costed || {}).net_r || 0);
    costed += (cnet || net) * risk / days;
  }
  const monthly = paper * 21;
  const costedM = costed * 21;
  return {
    projected_daily: paper,
    projected_monthly: monthly,
    projected_monthly_pct: bal > 0 ? monthly / bal * 100 : 0,
    projected_costed_daily: costed,
    projected_costed_monthly: costedM,
    projected_costed_monthly_pct: bal > 0 ? costedM / bal * 100 : 0,
  };
}

function renderCapacity() {
  const cap = overlayCapacityFromPositions(STATE.capacity || {});
  const rows = (cap.rows || []).map((r) => {
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td><span class="pill ${esc(r.group)}">${esc(GROUP_LABEL[r.group] || r.group)}</span></td>
      <td><span class="pill ${r.enabled ? "on" : "off"}">${r.enabled ? "aktif" : "kapali"}</span></td>
      <td class="num">${num(r.lot, 2)}</td>
      <td class="num ${r.edge_scale > 1 ? "pos" : (r.edge_scale < 1 ? "neg" : "dim")}" title="holdout net R / maxDD, karekok medyan, 0.6-2.2">${r.edge_scale != null ? "x" + num(r.edge_scale, 2) : "-"}</td>
      <td class="num dim">${esc(r.lot_note || "risk %")}</td>
      <td class="num ${r.open_positions ? "pos" : "dim"}">${r.open_positions}</td>
      <td class="num ${r.free_slots > 0 ? "pos" : "neg"}"><b>${r.free_slots}</b></td>
      <td class="num">${num(r.margin_per_trade)}</td>
      <td class="num">${r.risk_per_trade ? `${num(r.risk_per_trade)} <span class="dim">${esc(r.risk_sizing || "risk %")}</span>` : "-"}</td>
      <td class="num ${costCls(r)}" title="${costTitle(r)}">${costCell(r)}</td>
      <td class="num ${cls(r.expected_per_trade)}">${r.expectancy_r ? signed(r.expected_per_trade, 3) : '<span class="dim">-</span>'}</td>
      <td class="num ${cls(r.open_profit)}">${r.open_positions ? signed(r.open_profit) : "-"}</td>`;
    return tr;
  });
  rowsInto($("#capacity-table"), rows, "Sembol yok", 13);

  // Deliberately does NOT repeat the cards above it. Open/total positions, free
  // slots and the monthly projection all have their own card; saying them twice
  // made the longest line on the page out of numbers the operator had already
  // read. What stays is what no card carries: the portfolio-wide risk if every
  // slot filled, and the assumption the projection was measured under.
  const costedNote = cap.projected_costed_negative
    ? ` <span class="pill bad" title="En az bir sembolun maliyetli holdout dilimi negatif - toplam artida olsa bile">bazi semboller maliyetli dilimde negatif</span>`
    : "";
  // Operator 26.08: the line wrapped to three right-aligned rows and pushed
  // the table down. Two numbers stay on screen - the risk if every slot fills,
  // and the regime the projection was measured under. The rest is not deleted:
  // sizing multipliers and the margin budget have no card and no column, so
  // they move into the hover title. Out of the way, still one gesture away.
  $("#capacity-summary").title =
    `lot carpani x${num(cap.lot_multiplier, 2)}`
    + `${cap.size_by_edge ? " + avantaj (holdout R/maxDD)" : ""}`
    + ` | guvenli ust sinir x${num(cap.safe_multiplier, 2)}`
    + ` | marj butcesi ${num(cap.margin_budget)}`
    + ` | slot limitinde marj ${num(cap.concurrent_margin)}`
    + ` | hepsi acilirsa toplam risk ${num(cap.total_risk_per_trade)}`
    + ` (%${num(cap.total_risk_pct, 2)})`
    + (cap.projected_costed_monthly
      ? ` | maliyetli dilim ${signed(cap.projected_costed_monthly)}` : "");
  $("#capacity-summary").innerHTML =
    `projeksiyon ${cap.projected_charge_costs ? "maliyetli" : "maliyetsiz"} OPT'ten` +
    costedNote +
    (cap.search_frozen
      ? ` <span class="pill dim" title="Marj ve lot arama kilidinde donuk; acik sayi ve K/Z pozisyon listesinden taze">arama: marj/lot donuk</span>`
      : "");
}

function renderExecution() {
  // Requested-vs-filled quality. The walk-forward cannot model slippage, so
  // this is the only place a silent execution leak becomes visible.
  const ex = STATE.execution || {};
  const per = ex.per_symbol || {};
  const flagged = new Set(ex.flagged || (ex.total || {}).flagged || []);
  const rows = Object.keys(per).sort().map((sym) => {
    const s = per[sym];
    const bad = flagged.has(sym);
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(sym)}</td>
      <td class="num">${s.samples}</td>
      <td class="num">${s.adverse}</td>
      <td class="num">${s.favourable}</td>
      <td class="num ${s.adverse_ratio > 3 ? "neg" : "dim"}">${num(s.adverse_ratio, 2)}x</td>
      <td class="num ${s.mean_points > 0 ? "neg" : "pos"}">${signed(s.mean_points, 2)}</td>
      <td class="num dim">${num(s.worst_points, 2)}</td>
      <td class="num ${s.mean_r > 0.05 ? "neg" : "dim"}">${signed(s.mean_r * 100, 2)}%</td>
      <td class="num ${cls(s.money)}">${signed(s.money)}</td>
      <td><span class="pill ${bad ? "bad" : "on"}">${bad ? "incele" : "normal"}</span></td>`;
    return tr;
  });
  rowsInto($("#exec-table"), rows, "Henuz olculmus emir yok", 10);

  const t = ex.total || {};
  const note = $("#exec-note");
  if (!note) return;
  if (!t.samples) {
    note.textContent = "Emir gerceklestikce istenen ve gerceklesen fiyat karsilastirilir.";
    return;
  }
  note.innerHTML =
    `${t.samples} emir olculdu | aleyhte ${t.adverse} / lehte ${t.favourable} ` +
    `(<b>${num(t.adverse_ratio, 2)}x</b>) | ortalama kayma <b>${signed(t.mean_points, 2)}</b> puan ` +
    `= riskin <b>${signed(t.mean_r * 100, 2)}%</b>'i | toplam etki ${signed(t.money)}` +
    ((t.flagged || []).length ? ` | <span class="pill bad">incele: ${t.flagged.map(esc).join(", ")}</span>` : "");
}

function renderPositions() {
  const now = Date.now() / 1000;
  const rows = (STATE.positions || []).map((p) => {
    const digits = (SYMBOLS.find((s) => s.resolved_symbol === p.symbol) || {}).digits ?? 5;
    // A live position with no stop is the one row that must not read as a
    // quiet blank. The log has said STOPSUZ since this morning; the table
    // showed the same state as a dimmed zero (review 24.08 15:12).
    const naked = !(Number(p.sl) > 0) && Number(p.volume) > 0;
    const cfg = SYMBOLS.find((s) => s.symbol === p.config_symbol
      || s.resolved_symbol === p.symbol) || {};
    const harvestAt = Number(cfg.harvest_at_r || 0);
    const status = [
      p.partial_done ? '<span class="pill on">1/3</span>' : "",
      p.be_locked ? '<span class="pill on">BE</span>' : "",
      p.trail_moved && !p.be_locked ? '<span class="pill on">trail</span>' : "",
      harvestAt > 0 && Number(p.r_open) >= harvestAt
        ? '<span class="pill on">hasat</span>' : "",
    ].filter(Boolean).join(" ") || '<span class="dim">ham</span>';
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(p.symbol)}${p.managed ? "" : ' <span class="pill off">harici</span>'}</td>
      <td><span class="pill ${sideClass(p.side)}">${p.side === "buy" ? "AL" : "SAT"}</span></td>
      <td class="num">${num(p.volume, 2)}</td>
      <td class="num">${price(p.price_open, digits)}</td>
      <td class="num">${price(p.price_current, digits)}</td>
      <td class="num ${naked ? "neg" : (p.sl ? "" : "dim")}">${
        naked ? '<b>STOPSUZ</b>' : price(p.sl, digits)}</td>
      <td class="num ${cls(p.profit + p.swap)}">${signed(p.profit + p.swap)}</td>
      <td>${status}</td>
      <td class="dim mono">${duration(now - p.time)}</td>
      <td class="dim mono">${esc(String(p.ticket))}</td>
      <td class="dim mono">${p.magic ? esc(String(p.magic)) : "-"}</td>`;
    tr.appendChild(el("td", {}, el("button", {
      class: "btn btn-sm btn-danger",
      text: "Kapat",
      onclick: async (e) => {
        e.target.disabled = true;
        try {
          const res = await api(`/api/positions/${p.ticket}/close`, { method: "POST" });
          if (res && res.ok === false) {
            toast(res.partial
              ? `Kısmi kapanış: kalan ${res.remaining_volume} lot, tekrar deneyin`
              : "Pozisyon kapatılamadı", "err");
          }
          refresh();
        } catch (err) { toast(err.message, "err"); e.target.disabled = false; }
      },
    })));
    return tr;
  });
  rowsInto($("#positions-table"), rows, "Acik pozisyon yok", 12);
}

function renderHarvest() {
  const node = $("#harvest-note");
  if (!node) return;
  const h = STATE.harvest || {};
  const n = Number(h.n || 0);
  if (!n) { node.textContent = ""; return; }
  const left = h.left_on_table_r;
  const on = (h.partial_on || []).filter(Boolean);
  const harvest = (h.harvest_on || []).filter(Boolean);
  const by = h.by_symbol || {};
  const worst = Object.entries(by).sort((a, b) => Number(b[1]) - Number(a[1]))[0];
  let text = `${n} kapanis; kazananlarda masada ${left != null ? num(left, 1) : "-"} R`;
  if (worst) text += ` | en cok ${String(worst[0])} ${num(worst[1], 1)}R`;
  text += ` | parca acik: ${on.length ? on.map((s) => String(s)).join(", ") : "yok"}`;
  text += ` | hasat trail: ${harvest.length ? harvest.map((s) => String(s)).join(", ") : "yok"}`;
  // Operator 26.08: this note used to wrap to two lines above the button and
  // cost the open book that height on every screen. One line beside the
  // button now; the full sentence is on hover.
  node.textContent = text;
  node.title = text;
}

function renderDayTable() {
  const rows = ((STATE.day || {}).per_symbol || []).map((r) => {
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td class="num">${r.trades}</td>
      <td class="num pos">${r.wins}</td>
      <td class="num neg">${r.losses}</td>
      <td class="num ${cls(r.profit)}">${signed(r.profit)}</td>`;
    return tr;
  });
  rowsInto($("#day-table"), rows, "Bugun kapanan islem yok", 5);
}

function renderLive() {
  const states = STATE.states || {};
  const rows = SYMBOLS.map((cfg) => {
    const st = states[cfg.symbol] || {};
    const sess = st.session || {};
    let sessionCell = '<span class="pill off">-</span>';
    if (sess.open) {
      const left = sess.minutes_to_close;
      sessionCell = `<span class="pill on">acik</span> <span class="dim mono">${left != null ? left + "dk" : ""}</span>`;
    } else if (sess.minutes_to_open != null) {
      sessionCell = `<span class="pill off">kapali</span> <span class="dim mono">${Math.floor(sess.minutes_to_open / 60)}s${sess.minutes_to_open % 60}dk</span>`;
    }
    // The spread ceiling is a RATIO against ATR, so the same setting is a
    // different price on every timeframe and in every volatility regime. US30
    // moved M30 -> M5 on 24.08: ATR halved, the cap went 2.21 -> 1.51 points
    // and 43 of 44 signals were refused on spread the next morning, with the
    // ratio column beside this one reading a perfectly ordinary "1.4x".
    // Showing the cap in the symbol's own price units is what makes that
    // visible before a day of blocked entries does (measured 25.08 09:06).
    const cap = (cfg.max_spread_atr > 0 && st.atr > 0) ? cfg.max_spread_atr * st.atr : null;
    const digits = cfg.digits ?? 5;
    const headroom = (cap && st.spread_atr > 0 && cfg.max_spread_atr > 0)
      ? st.spread_atr / cfg.max_spread_atr : null;
    const capCell = cap == null ? '<span class="dim">-</span>'
      : `${cap.toFixed(digits)}${headroom ? ` <span class="dim">${num(headroom, 2)}x</span>` : ""}`;
    const capCls = headroom == null ? "dim" : (headroom > 1 ? "neg" : (headroom > 0.8 ? "warn" : "dim"));
    const capTitle = cap == null
      ? "max_spread_atr kapali ya da ATR okunmadi"
      : `Su anki makas tavani = max_spread_atr ${cfg.max_spread_atr} x ATR ${st.atr}`
        + (headroom ? ` | canli makas tavanin ${num(headroom, 2)} kati` : "");
    const sig = st.signal ? `<span class="pill ${sideClass(st.signal)}">${st.signal === "buy" ? "AL" : "SAT"}</span>` : '<span class="dim">-</span>';
    const htf = !cfg.htf_factor ? '<span class="dim">kapali</span>'
      : st.htf > 0 ? '<span class="pos">yukari</span>'
      : st.htf < 0 ? '<span class="neg">asagi</span>' : '<span class="dim">-</span>';
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(cfg.symbol)}</td>
      <td class="dim" title="${esc(STRATEGY_LABEL[cfg.strategy] || cfg.strategy)}">${esc(cfg.strategy)}</td>
      <td class="dim">${esc(cfg.timeframe)}</td>
      <td>${sessionCell}</td>
      <!-- null = this family does not compute a T3 level (flip families), or
           t3 carries a -1/+1 direction rather than a level. The old ternary
           sent both to "asagi", so a strategy with no T3 at all read as one
           whose trend had turned down - beside a BUY signal. -->
      <td class="${st.t3_rising == null ? "" : (st.t3_rising ? "pos" : "neg")}">${(!st.bars_ready || st.t3_rising == null) ? '<span class="dim">-</span>' : (st.t3_rising ? "yukari" : "asagi")}</td>
      <td>${htf}</td>
      <td class="num">${st.k != null ? num(st.k, 1) : "-"}</td>
      <td class="num">${st.d != null ? num(st.d, 1) : "-"}</td>
      <!-- null adx would coerce to 0 in the >= below and read as "meets the
           minimum"; an unmeasured reading meets nothing. -->
      <td class="num ${st.adx != null && st.adx >= (cfg.adx_min || 0) ? "" : "dim"}">${st.adx != null ? num(st.adx, 0) : "-"}</td>
      <td class="num dim">${st.atr ? st.atr.toFixed(cfg.digits ?? 5) : "-"}</td>
      <td class="num ${st.spread_atr > cfg.max_spread_atr ? "neg" : "dim"}">${st.spread_atr ? num(st.spread_atr, 2) + "x" : "-"}</td>
      <td class="num ${capCls}" title="${esc(capTitle)}">${capCell}</td>
      <td>${cfg.enabled ? sig : '<span class="pill off">kapali</span>'}</td>
      <td class="dim">${esc(st.note || "")}</td>`;
    return tr;
  });
  rowsInto($("#live-table"), rows, "Sembol yok", 14);
}

/* --------------------------------------------------------- symbols: spec */

const STRATEGY_LABEL = {
  mtf_pullback: "Ust TF Trend Geri Cekilmesi",
  burst: "Momentum Patlamasi Devami",
  dual_t3: "Ikili T3 + ATR (sade cekirdek)",
  t3_flip: "Tek Tillson T3 Yon Donusu (tek cizgi)",
  // The flip families were missing here entirely, so live symbols showed
  // a raw key instead of a name. Must stay in step with models.STRATEGIES;
  // the card header and live-table title read this map.
  stoch_flip: "Stochastic Yon Donusu",
  parabolic_flip: "Parabolic SAR Yon Donusu",
  aroon_flip: "Aroon Yon Donusu",
  ichimoku: "Ichimoku TK + bulut (gecikmeli, ileri bakissiz)",
};

// Card body is session hours only. Stored risk_percent still sizes
// lots; the header live line prints it. Search writes exits.

function buildSessionEditor(cfg) {
  const wrap = el("div", { class: "sessions" });

  const redraw = () => {
    wrap.innerHTML = "";
    (cfg.sessions || []).forEach((win, index) => {
      const start = el("input", { type: "time", value: win.start });
      const end = el("input", { type: "time", value: win.end });
      const commit = () => {
        const next = (cfg.sessions || []).slice();
        next[index] = { start: start.value || "00:00", end: end.value || "23:59" };
        cfg.sessions = next;
        saveSymbol(cfg.symbol, { sessions: next }, start);
      };
      start.addEventListener("change", commit);
      end.addEventListener("change", commit);
      wrap.appendChild(el("div", { class: "session-row" }, [
        start, el("span", { class: "arrow", text: "-" }), end,
        el("button", {
          class: "btn btn-sm btn-ghost", text: "sil",
          onclick: () => {
            cfg.sessions = (cfg.sessions || []).filter((_, i) => i !== index);
            saveSymbol(cfg.symbol, { sessions: cfg.sessions });
            redraw();
          },
        }),
      ]));
    });
    wrap.appendChild(el("button", {
      class: "btn btn-sm", text: "+ Saat araligi ekle",
      onclick: () => {
        cfg.sessions = (cfg.sessions || []).concat([{ start: "09:00", end: "18:00" }]);
        saveSymbol(cfg.symbol, { sessions: cfg.sessions });
        redraw();
      },
    }));
  };
  redraw();
  return wrap;
}

function buildDayPicker(cfg) {
  const wrap = el("div", { class: "days" });
  DAY_LABEL.forEach((label, i) => {
    const day = i + 1;
    const chip = el("div", {
      class: "day-chip" + ((cfg.trade_days || []).includes(day) ? " sel" : ""),
      text: label,
      onclick: () => {
        const set = new Set(cfg.trade_days || []);
        set.has(day) ? set.delete(day) : set.add(day);
        cfg.trade_days = Array.from(set).sort((a, b) => a - b);
        chip.classList.toggle("sel");
        saveSymbol(cfg.symbol, { trade_days: cfg.trade_days });
      },
    });
    wrap.appendChild(chip);
  });
  return wrap;
}

const POSITION_SECTION = {
  title: "Pozisyon Boyutu",
  fields: [
    { k: "max_lot", t: "num", label: "Maks lot (0=kapali)", step: 0.01, min: 0, max: 100 },
    { k: "max_margin_pct", t: "num", label: "Sembol marji % (0=kapali)", step: 0.1, min: 0, max: 100 },
  ],
};

function buildField(cfg, spec) {
  const input = el("input", {
    type: "number",
    step: spec.t === "int" ? 1 : (spec.step ?? 0.01),
    min: spec.min,
    max: spec.max,
  });
  input.dataset.key = spec.k;
  input.value = cfg[spec.k];
  input.addEventListener("change", () => {
    const raw = input.value;
    const value = spec.t === "int" ? parseInt(raw, 10) : parseFloat(raw);
    if (!isFinite(value)) { input.value = cfg[spec.k]; return; }
    saveSymbol(cfg.symbol, { [spec.k]: value }, input);
  });
  return titled(el("div", { class: "field" }, [el("label", { text: spec.label }), input]), spec.k);
}

function buildSymbolCard(cfg) {
  const card = el("div", { class: "scard", "data-symbol": cfg.symbol });

  const toggle = el("input", { type: "checkbox" });
  toggle.checked = !!cfg.enabled;
  toggle.addEventListener("click", (e) => e.stopPropagation());
  toggle.addEventListener("change", () => saveSymbol(cfg.symbol, { enabled: toggle.checked }));

  const head = el("div", { class: "scard-head" }, [
    el("span", { class: "caret", text: "\u25B6" }),
    el("label", { class: "switch", onclick: (e) => e.stopPropagation() }, [toggle, el("span")]),
    el("div", { class: "scard-title" }, [
      el("div", {}, [
        el("div", { class: "name", text: cfg.symbol }),
        el("div", { class: "desc", text: cfg.description || "" }),
      ]),
      el("span", { class: `pill ${cfg.group}`, text: GROUP_LABEL[cfg.group] || cfg.group }),
    ]),
    el("div", { class: "scard-live" }),
  ]);
  head.addEventListener("click", () => card.classList.toggle("open"));
  card.appendChild(head);

  const body = el("div", { class: "scard-body" });

  body.appendChild(el("div", { class: "subgrid" }, [
    el("div", { class: "title", text: POSITION_SECTION.title }),
    el("div", { class: "form-grid" }, POSITION_SECTION.fields.map((f) => buildField(cfg, f))),
  ]));

  const useSessions = el("input", { type: "checkbox" });
  useSessions.checked = !!cfg.use_sessions;
  useSessions.dataset.key = "use_sessions";
  useSessions.addEventListener("change", () => saveSymbol(cfg.symbol, { use_sessions: useSessions.checked }));

  const flat = el("input", { type: "number", step: 1, min: 0, max: 240 });
  flat.dataset.key = "flat_before_close_min";
  flat.value = cfg.flat_before_close_min;
  flat.addEventListener("change", () => saveSymbol(cfg.symbol, { flat_before_close_min: parseInt(flat.value, 10) || 0 }, flat));

  body.appendChild(el("div", { class: "subgrid" }, [
    el("div", { class: "title", text: "Islem Saatleri (bilgisayarin yerel saati)" }),
    el("div", { class: "form-grid" }, [
      titled(el("div", { class: "field" }, [
        el("label", { text: "Saat filtresi" }),
        el("label", { class: "chk" }, [useSessions, el("span", { text: "Sadece belirtilen saatlerde islem ac" })]),
      ]), "use_sessions"),
      el("div", { class: "field" }, [el("label", { text: "Araliklar" }), buildSessionEditor(cfg)]),
      el("div", { class: "field" }, [el("label", { text: "Gunler" }), buildDayPicker(cfg)]),
      titled(el("div", { class: "field" }, [el("label", { text: "Kapanistan X dk once kapat" }), flat]),
        "flat_before_close_min"),
    ]),
  ]));

  body.appendChild(el("div", { class: "btn-row" }, [
    el("button", {
      class: "btn btn-sm btn-go", text: "Bu Sembolu Optimize Et",
      onclick: () => runOptimizer([cfg.symbol]),
    }),
    el("button", {
      class: "btn btn-sm", text: "Pozisyonlari Kapat",
      onclick: async () => {
        try {
          const r = await api(`/api/symbols/${cfg.symbol}/close`, { method: "POST" });
          const msg = r.remaining < 0
            ? `${cfg.symbol}: MT5 baglantisi dogrulanamadi, durum bilinmiyor`
            : r.remaining
              ? `${cfg.symbol}: ${r.closed} kapatildi, ${r.remaining} HALA ACIK`
              : `${cfg.symbol}: ${r.closed} pozisyon kapatildi`;
          toast(msg, r.remaining ? "err" : "ok");
          refresh();
        } catch (e) { toast(e.message, "err"); }
      },
    }),
  ]));

  card.appendChild(body);
  return card;
}

function buildSymbolCards() {
  const list = $("#symbol-list");
  list.innerHTML = "";
  SYMBOLS.forEach((cfg) => list.appendChild(buildSymbolCard(cfg)));
  cardsBuilt = true;
  applySymbolFilter();
}

function updateSymbolCards() {
  const states = STATE.states || {};
  SYMBOLS.forEach((cfg) => {
    const card = $(`.scard[data-symbol="${cfg.symbol}"]`);
    if (!card) return;
    card.classList.toggle("off", !cfg.enabled);

    // Refresh inputs the user is not currently editing, so optimizer results show up live.
    $$("input, select", card).forEach((input) => {
      const key = input.dataset.key;
      if (!key || input === document.activeElement || !(key in cfg)) return;
      if (input.type === "checkbox") input.checked = !!cfg[key];
      else if (String(input.value) !== String(cfg[key])) input.value = cfg[key];
    });
    const st = states[cfg.symbol] || {};
    const sess = st.session || {};
    const optAge = cfg.opt_updated_at
      ? new Date(cfg.opt_updated_at * 1000).toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" })
      : "-";
    const sig = st.signal
      ? `<span class="pill ${sideClass(st.signal)}">${st.signal === "buy" ? "AL" : "SAT"}</span>`
      : "";
    $(".scard-live", card).innerHTML = `
      <span><b>strateji</b> ${esc(STRATEGY_LABEL[cfg.strategy] || cfg.strategy)} <span class="dim">${esc(cfg.timeframe)}</span></span>
      <span><b>seans</b> ${sess.open ? '<span class="pos">acik</span>' : '<span class="dim">kapali</span>'} ${esc(cfg.session_text)}</span>
      <span><b>lot</b> ${num(cfg.risk_percent, 2)}% bakiye</span>
      <span><b>T3</b> ${(!st.bars_ready || st.t3_rising == null) ? "-" : (st.t3_rising ? '<span class="pos">yukari</span>' : '<span class="neg">asagi</span>')}</span>
      <span><b>K/D</b> ${st.k != null ? num(st.k, 0) + "/" + num(st.d, 0) : "-"}</span>
      <span><b>opt</b> <span class="opt-badge ${cfg.opt_score > 0 ? "pos" : "dim"}">${num(cfg.opt_score, 1)}</span> <span class="dim">${optAge}</span> ${
        cfg.validated === true ? '<span class="pill on">dogrulandi</span>'
          : cfg.validated === false ? '<span class="pill bad">dogrulanmadi</span>'
            : '<span class="dim" title="henuz yazilmadi">-</span>'
      }</span>
      ${sig}
      <span class="dim">${esc(st.note || "")}</span>`;
  });
}

function applySymbolFilter() {
  const text = $("#symbol-filter").value.trim().toUpperCase();
  const group = $("#group-filter").value;
  $$(".scard").forEach((card) => {
    const symbol = card.dataset.symbol;
    const cfg = SYMBOLS.find((s) => s.symbol === symbol) || {};
    const okText = !text || symbol.toUpperCase().includes(text);
    const okGroup = !group || cfg.group === group;
    card.style.display = okText && okGroup ? "" : "none";
  });
}

const saveTimers = {};
function saveSymbol(symbol, patch, flashNode) {
  const key = symbol + Object.keys(patch).join(",");
  clearTimeout(saveTimers[key]);
  saveTimers[key] = setTimeout(async () => {
    try {
      const res = await api(`/api/symbols/${symbol}`, { method: "POST", body: patch });
      const index = SYMBOLS.findIndex((s) => s.symbol === symbol);
      if (index >= 0) SYMBOLS[index] = { ...SYMBOLS[index], ...res.config };
      if (flashNode) {
        flashNode.classList.add("saved-flash");
        setTimeout(() => flashNode.classList.remove("saved-flash"), 900);
      }
    } catch (e) {
      toast(`${symbol}: ${e.message}`, "err");
    }
  }, 350);
}

/* ------------------------------------------------------------- optimizer */

// "How thorough/fast is the search" - the dials actually discussed and tuned
// this far (opt speed vs. depth). Statistical-gate internals left the panel
// 27.08; they stay in opt_params.
const OPT_SETTING_FIELDS = [
  { k: "lookback_days", label: "Gecmis penceresi (gun)", step: 10, min: 20 },
  { k: "refine_rounds", label: "Yerel iyilestirme turu", step: 1, min: 0, max: 5 },
  { k: "max_combos", label: "Maks kombinasyon", step: 100, min: 20 },
];

async function loadOptParams() {
  const res = await api("/api/opt/params");
  OPT_PARAMS = res.params;
  renderOptForm();
  renderOptPicker();
  renderOptTfPicker();
}

function renderOptForm() {
  $("#opt-settings").innerHTML = "";
  OPT_SETTING_FIELDS.forEach((f) => {
    let input;
    if (f.kind === "enum") {
      input = el("select", {});
      (f.options || []).forEach(([value, label]) => {
        const opt = el("option", { value, text: label });
        if (String(OPT_PARAMS[f.k] || "score") === value) opt.selected = true;
        input.appendChild(opt);
      });
      input.dataset.optKind = "enum";
    } else {
      input = el("input", { type: "number", step: f.step, min: f.min, max: f.max });
      input.value = OPT_PARAMS[f.k];
    }
    input.dataset.optKey = f.k;
    $("#opt-settings").appendChild(titled(
      el("div", { class: "field" }, [el("label", { text: f.label }), input]), f.k));
  });
}

function renderOptPicker() {
  const box = $("#opt-picker");
  if (!box) return;
  // Drop names that have left the book. The selection is a Set that outlives
  // the symbol list, so a pick made before the book was cut kept being sent
  // afterwards - the backend filtered every one of them out and answered
  // "Sembol secilmedi" about a request that named several. Nothing was lit on
  // screen either, because the "Tumu" chip only lights when the set is empty.
  // Pruning here means it empties instead, which IS "Tumu" and runs the book.
  const live = new Set(SYMBOLS.map((s) => s.symbol));
  optSelection.forEach((s) => { if (!live.has(s)) optSelection.delete(s); });
  box.innerHTML = "";
  const all = el("div", {
    class: "chip" + (optSelection.size === 0 ? " sel" : ""), text: "Tumu",
    onclick: () => { optSelection.clear(); renderOptPicker(); },
  });
  box.appendChild(all);
  SYMBOLS.forEach((cfg) => {
    box.appendChild(el("div", {
      class: "chip" + (optSelection.has(cfg.symbol) ? " sel" : ""), text: cfg.symbol,
      onclick: () => {
        optSelection.has(cfg.symbol) ? optSelection.delete(cfg.symbol) : optSelection.add(cfg.symbol);
        renderOptPicker();
      },
    }));
  });
  optPickerSig = SYMBOLS.map((s) => s.symbol).join("|");
}

function renderOptTfPicker() {
  const box = $("#opt-tf-picker");
  if (!box) return;
  box.innerHTML = "";
  box.appendChild(el("div", {
    class: "chip" + (optTfSelection.size === 0 ? " sel" : ""), text: "Tumu",
    onclick: () => { optTfSelection.clear(); renderOptTfPicker(); },
  }));
  OPT_TF_OPTIONS.forEach((tf) => {
    box.appendChild(el("div", {
      class: "chip" + (optTfSelection.has(tf) ? " sel" : ""), text: tf,
      onclick: () => {
        optTfSelection.has(tf) ? optTfSelection.delete(tf) : optTfSelection.add(tf);
        renderOptTfPicker();
      },
    }));
  });
}

function syncOptPicker() {
  const sig = SYMBOLS.map((s) => s.symbol).join("|");
  if (sig !== optPickerSig || !$("#opt-picker")?.childElementCount) renderOptPicker();
}

async function saveOptParams() {
  const body = {};
  const skipped = [];
  // A blank/non-numeric field must NOT be sent at all - parseFloat("") is
  // NaN, and JSON.stringify(NaN) silently serialises to null, which the
  // server stored verbatim over a previously-valid default and crashed the
  // optimizer's background thread (int(None)) on the next run.
  $$("[data-opt-key]").forEach((i) => {
    if (i.dataset.optKind === "enum") {
      if (i.value) body[i.dataset.optKey] = i.value;
      else skipped.push(i.dataset.optKey);
      return;
    }
    const value = parseFloat(i.value);
    if (isFinite(value)) body[i.dataset.optKey] = value;
    else skipped.push(i.dataset.optKey);
  });
  // Grid left the panel 27.08. An empty {} here would overwrite the live
  // search axes. Only send a grid when the form still has those inputs.
  const grid = {};
  $$("[data-grid-key]").forEach((i) => {
    const values = i.value.split(",").map((x) => parseFloat(x.trim())).filter((x) => isFinite(x));
    if (values.length) grid[i.dataset.gridKey] = values;
  });
  if (Object.keys(grid).length) body.grid = grid;
  try {
    const res = await api("/api/opt/params", { method: "POST", body });
    OPT_PARAMS = res.params;
    renderOptForm();
    toast(skipped.length
      ? `Kaydedildi (gecersiz alanlar atlandi: ${skipped.join(", ")})`
      : "Optimizasyon ayarlari kaydedildi", skipped.length ? "err" : "ok");
  } catch (e) { toast(e.message, "err"); }
}

async function runOptimizer(symbols) {
  const tfs = Array.from(optTfSelection);
  try {
    await api("/api/opt/run", {
      method: "POST",
      body: {
        symbols: symbols && symbols.length ? symbols : null,
        apply_best: $("#opt-apply").checked,
        timeframes: tfs.length ? tfs : null,
      },
    });
    toast(`Optimizasyon basladi (${symbols && symbols.length ? symbols.join(", ") : "tum semboller"}`
      + `${tfs.length ? ", TF: " + tfs.join(", ") : ""})`, "ok");
    selectTab("opt");
    refresh();
  } catch (e) { toast(e.message, "err"); }
}

function renderOptJob() {
  const job = STATE.opt || {};
  const total = job.total || 0;
  const done = job.done || 0;
  const comboPct = job.combo_total ? (job.combo_done / job.combo_total) : 0;
  const pct = total ? Math.min(100, ((done + comboPct) / total) * 100) : 0;
  $("#opt-progress").style.width = `${job.state === "running" ? pct : (job.state === "done" ? 100 : 0)}%`;

  const label = { idle: "Bekliyor", running: "Calisiyor", done: "Tamamlandi", cancelled: "Iptal edildi" }[job.state] || job.state;
  let text = `${label}`;
  if (job.state === "running") {
    text += ` | ${done}/${total} sembol | ${job.current || ""}`;
    if (job.combo_total) text += ` | kombinasyon ${job.combo_done}/${job.combo_total}`;
    // This is the highest in-sample (selection-window) score seen across every
    // sweep tried so far, not a validated result - most of the search space
    // never clears validation/holdout, so it is routinely far above anything
    // that ends up in the results table. Labelled as such so it doesn't read
    // as "there's a great result and it's missing".
    if (job.best_score != null) text += ` | en iyi ham skor (dogrulanmamis) ${num(job.best_score, 2)}`;
  } else if (job.finished_at) {
    text += ` | ${new Date(job.finished_at * 1000).toLocaleTimeString("tr-TR")}`;
  }
  if (job.error) text += ` | ${job.error}`;
  $("#opt-status").textContent = text;
  const running = job.state === "running" || !!job.busy;
  $("#btn-opt-run").disabled = running;
  $("#btn-opt-cancel").disabled = !running;

  // Best score first; failed symbols sink to the bottom.
  const results = (job.results || []).slice().sort((a, b) => {
    const sa = a.ok && a.best ? a.best.score : -Infinity;
    const sb = b.ok && b.best ? b.best.score : -Infinity;
    return sb - sa;
  });

  const rows = results.map((r) => {
    const tr = el("tr");
    if (!r.ok || !r.best) {
      tr.innerHTML = `<td class="sym">${esc(r.symbol)}</td><td colspan="15" class="neg">${esc(r.keep_reason || r.error || "sonuc yok")}</td>`;
      return tr;
    }
    const h = r.best.holdout;
    const v = r.best.validation || {};
    const s = r.best.selection;
    // A rejected candidate's numbers are a *backtest* result, not the symbol's
    // live setup. Say so on the row, otherwise a red -14R next to a symbol reads
    // as if the running configuration is bleeding money.
    const inc = r.incumbent;
    const kept = !r.applied && inc && inc.net_r != null;
    const closedCand = !!r.closed_candidate;
    const incText = closedCand
      ? `Kapali sembol icin aday bulundu. Canli ayar yazilmadi; acma karari operatorde. `
        + `Soldaki rakamlar adayin backtest sonucudur.`
      : kept
      ? `Uygulanmadi${r.keep_reason ? ": " + esc(r.keep_reason) : ""}. Canli ayar degismedi `
        + `(${esc(inc.strategy || "-")}/${esc(inc.timeframe || "-")}, test ${signed(inc.net_r, 1)}R`
        + `${inc.profit_factor != null ? ", PF " + num(inc.profit_factor, 2) : ""}). `
        + `Soldaki rakamlar reddedilen adayin backtest sonucudur, hesap bakiyesi degil.`
      : esc(r.keep_reason || "");
    // Retention gate itself was removed on request (per-symbol judgment
    // instead of one uniform bar) - shown here so that judgment has a number
    // to work from instead of having to infer overfitting risk from PF alone.
    const ret = r.holdout_retention;
    const retCls = ret == null ? "" : ret < 0.25 ? "neg" : ret < 0.5 ? "" : "pos";
    const retTitle = ret == null ? ""
      : "Test beklentisi, secim/dogrulamanin zayifinin " + num(ret * 100, 0)
        + "%'ini koruyor" + (ret < 0.25 ? " - dusuk, asiri uyum isareti olabilir" : "");
    const status = r.applied ? '<span class="pill on">uygulandi</span>'
      : closedCand ? `<span class="pill warn" title="${incText}">kapali sembol icin aday bulundu</span>`
      : kept ? `<span class="pill warn" title="${incText}">mevcut ayar korundu</span>`
      : r.validated ? `<span class="pill warn" title="${incText}">dogrulandi, uygulanmadi</span>`
      : `<span class="pill bad" title="${incText}">dogrulanmadi</span>`;
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td class="dim">${esc(r.strategy || "-")}</td>
      <td class="dim">${esc(r.timeframe)}</td>
      <td class="num ${r.best.score > 0 ? "pos" : "neg"}"><b>${num(r.best.score, 2)}</b></td>
      <td class="num dim">${num(r.best.positive_ratio * 100, 0)}%</td>
      <td class="num">${s.trades}</td>
      <td class="num ${s.profit_factor >= 1.2 ? "pos" : ""}">${num(s.profit_factor, 2)}</td>
      <td class="num dim">${v.profit_factor != null ? num(v.profit_factor, 2) : "-"}</td>
      <td class="num dim">${v.net_r != null ? signed(v.net_r, 1) + "R" : "-"}</td>
      <td class="num">${h.trades}</td>
      <td class="num ${h.profit_factor >= 1.1 ? "pos" : "neg"}">${num(h.profit_factor, 2)}</td>
      <td class="num ${cls(h.net_r)}" title="${h.capture != null
        ? esc("Hasat (net R / MFE toplami) " + num(h.capture * 100, 0) + "% — skor girdisi degil")
        : ""}"><b>${signed(h.net_r, 1)}R</b>${
          h.capture != null ? ` <span class="dim">${num(h.capture * 100, 0)}%</span>` : ""}</td>
      <td class="num ${retCls}" title="${retTitle}">${ret != null ? num(ret * 100, 0) + "%" : "-"}</td>
      <td>${status}</td>
      <td class="dim mono" style="white-space:normal;max-width:380px">${
        incText ? `<div class="small warn-text">${incText}</div>` : ""
      }${Object.entries(r.best.params).map(([k, v]) => `${esc(k)}=${esc(v)}`).join("  ")}</td>`;
    tr.appendChild(el("td", {}, r.applied ? el("span", { class: "dim", text: "-" })
      : el("button", {
        class: "btn btn-sm", text: "Uygula",
        onclick: async (e) => {
          if (!r.validated && !confirm(
            `${r.symbol}: bu parametreler dokunulmamis test segmentinde kar etmedi ` +
            `(PF ${num(h.profit_factor, 2)}, ${signed(h.net_r, 1)}R). Yine de uygulansin mi?`)) return;
          e.target.disabled = true;
          try {
            const res = await api("/api/opt/apply", {
              method: "POST",
              body: { symbol: r.symbol, params: r.best.params, score: r.best.score,
                      timeframe: r.timeframe, strategy: r.strategy },
            });
            // An apply that bypassed the walk-forward still succeeds, so a
            // plain green toast read exactly like a validated one. Surface
            // what the API reports instead of assuming every 200 is routine.
            if (res && res.warning) toast(`${r.symbol}: ${res.warning}`, "warn");
            else toast(`${r.symbol} parametreleri uygulandi (${r.strategy} ${r.timeframe})`, "ok");
            refresh();
          } catch (err) { toast(err.message, "err"); e.target.disabled = false; }
        },
      })));
    return tr;
  });
  rowsInto($("#opt-results"), rows, "Henuz sonuc yok", 15);
}

async function loadOptHistory() {
  try {
    const res = await api("/api/opt/history?limit=80");
    const mode = $("#opt-history-sort").value;
    const history = res.history.slice().sort((a, b) => mode === "score"
      ? (b.score || 0) - (a.score || 0)
      : (b.created_at || 0) - (a.created_at || 0));

    const rows = history.map((h) => {
      const hold = h.holdout || {};
      const val = h.validation || {};
      const tr = el("tr");
      tr.innerHTML = `
        <td class="dim mono">${new Date(h.created_at * 1000).toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</td>
        <td class="sym">${esc(h.symbol)}</td>
        <td class="dim">${esc(h.strategy || "-")}</td>
        <td class="dim">${esc(h.timeframe || "-")}</td>
        <td class="num ${h.score > 0 ? "pos" : "neg"}">${num(h.score, 2)}</td>
        <td class="num dim">${val.net_r != null ? signed(val.net_r, 1) + "R" : "-"}</td>
        <td class="num">${hold.trades ?? "-"}</td>
        <td class="num ${hold.profit_factor >= 1.1 ? "pos" : ""}">${hold.profit_factor != null ? num(hold.profit_factor, 2) : "-"}</td>
        <td class="num ${cls(hold.net_r)}">${hold.net_r != null ? signed(hold.net_r, 1) + "R" : "-"}</td>
        <td class="num ${h.holdout_retention == null ? "" : h.holdout_retention < 0.25 ? "neg" : h.holdout_retention < 0.5 ? "" : "pos"}">${
          h.holdout_retention != null ? num(h.holdout_retention * 100, 0) + "%" : "-"}</td>
        <td title="${esc(h.applied ? "" : (h.keep_reason || ""))}">${h.applied
          ? '<span class="pill on">evet</span>'
          : h.validated ? '<span class="pill warn">dogrulandi</span>'
          : '<span class="pill off">hayir</span>'}${
          h.applied || !h.keep_reason ? ""
            : `<div class="small warn-text">${esc(h.keep_reason)}</div>`}</td>`;
      // A refused sweep leaves no strategy and no params, and /api/opt/apply
      // answers those with a 400. Offering the button anyway turns a run that
      // found nothing into an error the operator has to interpret.
      if (!h.strategy || !h.params || !Object.keys(h.params).length) {
        tr.appendChild(el("td", { class: "small" }, "-"));
        return tr;
      }
      tr.appendChild(el("td", {}, el("button", {
        class: "btn btn-sm", text: "Uygula",
        onclick: async (e) => {
          e.target.disabled = true;
          try {
            const res = await api("/api/opt/apply",
                                  { method: "POST", body: { symbol: h.symbol, run_id: h.id } });
            // Same reasoning as the results table above - this is the path a
            // force override actually comes in on.
            if (res && res.warning) toast(`${h.symbol}: ${res.warning}`, "warn");
            else toast(`${h.symbol} parametreleri uygulandi`, "ok");
            loadOptHistory(); refresh();
          } catch (err) { toast(err.message, "err"); e.target.disabled = false; }
        },
      })));
      return tr;
    });
    rowsInto($("#opt-history"), rows, "Kayit yok", 11);
  } catch (e) { toast(e.message, "err"); }
}

/* -------------------------------------------------------------- ai tab */

// Supervisor knobs still live on Store / POST /api/ai/settings. The panel
// only offers Aktif; this list is the FIELD_HELP catalog, not a form.
const AI_SETTING_FIELDS = [
  { k: "review_interval_sec", label: "Degerlendirme araligi (sn)", t: "int", min: 30, max: 3600 },
  { k: "lookback_days", label: "Gecmis penceresi (gun)", t: "int", min: 1, max: 90 },
  { k: "min_trades", label: "Karar icin min islem", t: "int", min: 3, max: 100 },
  { k: "quarantine_losses", label: "Karantina: ust uste zarar", t: "int", min: 2, max: 20 },
  { k: "quarantine_pf", label: "Karantina PF esigi", t: "num", step: 0.05, min: 0.1, max: 1.5 },
  { k: "watch_pf", label: "Izleme PF esigi", t: "num", step: 0.05, min: 0.5, max: 2 },
  { k: "quarantine_hours", label: "Karantina suresi (saat)", t: "int", min: 1, max: 168 },
  { k: "watch_risk_scale", label: "Izlemede lot carpani", t: "num", step: 0.05, min: 0.1, max: 1 },
  { k: "bad_hour_min_trades", label: "Kotu saat: min islem", t: "int", min: 3, max: 50 },
  { k: "bad_hour_pf", label: "Kotu saat PF esigi", t: "num", step: 0.05, min: 0.1, max: 1.5 },
  { k: "dd_soft_pct", label: "Lot kismaya baslama (%)", t: "num", step: 0.25, min: 0.25, max: 20 },
  { k: "dd_hard_pct", label: "Lot tabanina inme (%)", t: "num", step: 0.25, min: 0.5, max: 30 },
  { k: "risk_scale_floor", label: "Min lot carpani", t: "num", step: 0.05, min: 0.1, max: 1 },
  { k: "reopt_min_age_hours", label: "Yeniden OPT icin min yas (saat)", t: "int", min: 1, max: 720 },
  { k: "prefer_strong_on_dd", label: "Gunluk kayipta guclu sembole oncelik", t: "bool" },
  { k: "hard_block_only_quarantine", label: "Sert ret yalniz karantina (watch/saat lot kisar)", t: "bool" },
  { k: "edge_decay_min_trades", label: "Kenar dususu: min toplam islem", t: "int", min: 20, max: 200 },
  { k: "edge_decay_min_half", label: "Kenar dususu: her yari min islem", t: "int", min: 10, max: 100 },
];

function renderAI() {
  const ai = STATE.ai || {};
  const counts = ai.counts || {};
  const settings = ai.settings || {};

  $("#ai-enabled").checked = !!ai.enabled;

  const cards = [
    { lbl: "Saglikli", val: counts.ok ?? 0, accent: "green" },
    { lbl: "Izlemede", val: counts.watch ?? 0, accent: "amber" },
    { lbl: "Karantinada", val: counts.quarantine ?? 0, accent: "red" },
    { lbl: "Veri Bekleyen", val: counts.idle ?? 0, accent: "blue" },
    {
      lbl: "Son Degerlendirme",
      val: ai.last_review ? new Date(ai.last_review * 1000).toLocaleTimeString("tr-TR") : "-",
      foot: `her ${settings.review_interval_sec ?? "-"} sn`,
    },
  ];
  $("#ai-cards").innerHTML = cards.map((c) => `
    <div class="card ${c.accent ? "accent-" + c.accent : ""}">
      <div class="lbl">${c.lbl}</div><div class="val">${c.val}</div>
      <div class="foot">${c.foot || ""}</div>
    </div>`).join("");

  // The hours column used to print blocked_hours next to a count taken from
  // hour_risk_scales - two different mechanisms rendered as one phrase - and
  // it did so whether or not the AI layer was switched on. Both are consulted
  // in the gate only AFTER the `enabled` check, so with AI off they are inert,
  // yet a row still read "10:00 (1 saat kisitli)" as though that symbol were
  // being held out of the market.
  const hhmm = (h) => String(h).padStart(2, "0") + ":00";

  function aiHoursCell(r) {
    const hard = (r.blocked_hours || []).map(hhmm);
    const soft = Object.keys(r.hour_risk_scales || {}).map(Number).filter((h) => !(r.blocked_hours || []).includes(h));
    if (!hard.length && !soft.length) return "-";
    const parts = [];
    if (hard.length) parts.push(hard.join(" ") + " kapali");
    if (soft.length) parts.push(soft.map(hhmm).join(" ") + " kucultulmus");
    const text = parts.join(", ");
    // Say plainly when none of it is in force, instead of looking identical.
    return r.hours_enforced === false
      ? `<span class="dim">${text} (AI kapali - uygulanmiyor)</span>`
      : text;
  }

  function aiHoursTitle(r) {
    const soft = Object.entries(r.hour_risk_scales || {})
      .map(([h, s]) => hhmm(h) + " x" + num(s, 2)).join(", ");
    const lines = [];
    lines.push((r.blocked_hours || []).length
      ? "Kapali saatler: " + (r.blocked_hours || []).map(hhmm).join(", ")
      : "Kapali saat yok");
    lines.push(soft ? "Lot carpani: " + soft : "Yumusak kisitlama yok");
    // The question this column kept raising: there is no countdown because
    // there is no timer. These are time-of-day rules re-derived from the
    // recent deal window on every review.
    lines.push("Bunlar gunun saati kurallari, sureli kisitlama degil - geri sayim yoktur. "
             + "Her degerlendirmede son islemlerden yeniden hesaplanir ve o saatin "
             + "islemleri artik zarar ettirmiyorsa kendiliginden kalkar.");
    if (r.hours_enforced === false) lines.push("Denetleyici kapali: su an hicbiri uygulanmiyor.");
    return lines.join("\n");
  }

  // "Serbest birak" clears the stored verdict, not the evidence behind it.
  // review() re-derives quarantine and blocked hours from the same trailing
  // deal window, so a symbol that still meets the criteria is re-flagged on
  // the next pass - with a fresh quarantine clock. Pressing a release button
  // and watching the symbol come straight back, with nothing explaining why,
  // is what makes it look broken. Say what will happen before it happens.
  function aiReleaseWarning(r, s) {
    const back = [];
    const minTrades = Number(s.min_trades);
    const qPf = Number(s.quarantine_pf);
    const qLoss = Number(s.quarantine_losses);
    if (r.consecutive_losses >= qLoss) {
      back.push(`ust uste ${r.consecutive_losses} zarar (esik ${qLoss})`);
    }
    if (r.trades >= minTrades && r.profit_factor < qPf) {
      back.push(`${r.trades} islem, PF ${num(r.profit_factor, 2)} < ${num(qPf, 2)}`);
    }
    if ((r.blocked_hours || []).length) {
      back.push(`kapali saatler son ${s.lookback_days} gunun islemlerinden yeniden hesaplanir`);
    }
    let msg = `${r.symbol} icin AI kararlari silinecek.`;
    if (back.length) {
      msg += `\n\nDIKKAT: kanit hala gecerli, bir sonraki degerlendirmede geri gelecek:\n`
           + back.map((b) => "  - " + b).join("\n")
           + `\n\nKalici cozum: sembolu yeniden optimize edin, ya da AI ayarlarindan esikleri degistirin.`;
    }
    return msg + "\n\nDevam edilsin mi?";
  }

  const notes = (ai.notes || []).join(" | ");
  $("#ai-note").textContent = ai.enabled
    ? (notes || "Tum semboller normal calisiyor.")
    : "Denetleyici kapali - kararlar uygulanmiyor.";

  const aiRows = ai.symbols || [];
  // hours_enforced is part of the signature: toggling the AI switch changes
  // what the hours column says without changing any of the numbers, and the
  // table would otherwise keep showing the stale wording.
  const nextAiSig = aiRows.map((r) =>
    [r.symbol, r.state, r.trades, r.net, r.profit_factor, r.priority, r.effective_scale,
      r.consecutive_losses, r.quarantine_left_min, r.hours_enforced,
      r.gate_allowed, r.gate_reason || "",
      (r.blocked_hours || []).join(","),
      Object.keys(r.hour_risk_scales || {}).join(",")].join("|")).join(";");
  if (nextAiSig !== aiTableSig) {
    aiTableSig = nextAiSig;
    const rows = aiRows.map((r) => {
      const [pill, label] = AI_STATE[r.state] || ["off", r.state];
      const tr = el("tr");
      tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}${r.enabled ? "" : ' <span class="pill off">kapali</span>'}</td>
      <td><span class="pill ${pill}">${esc(label)}</span>${r.quarantine_left_min ? ` <span class="dim mono">${r.quarantine_left_min}dk</span>` : ""}${r.gate_allowed === false && r.state !== "quarantine" ? ` <span class="pill bad" title="${esc(r.gate_reason || "")}">giris kapali</span>` : ""}</td>
      <td class="dim">${esc(r.reason || "")}</td>
      <td class="num">${r.trades}</td>
      <td class="num">${r.trades ? num(r.wins / r.trades * 100, 0) + "%" : "-"}</td>
      <td class="num ${r.profit_factor >= 1 ? "pos" : "neg"}">${r.trades ? num(r.profit_factor, 2) : "-"}</td>
      <td class="num ${cls(r.net)}">${r.trades ? signed(r.net) : "-"}</td>
      <td class="num dim">${r.expected_r ? signed(r.expected_r, 3) + "R" : "-"}</td>
      <td class="num ${r.edge_health >= 1 ? "pos" : (r.edge_health > 0 && r.edge_health < 0.7 ? "neg" : "dim")}">${r.edge_health ? num(r.edge_health * 100, 0) + "%" : "-"}</td>
      <td class="num dim">${r.priority != null ? num(r.priority, 2) : "-"}</td>
      <td class="num ${r.consecutive_losses >= 3 ? "neg" : "dim"}">${r.consecutive_losses}</td>
      <td class="num ${r.effective_scale < 1 ? "neg" : ""}">${num(r.effective_scale, 2)}</td>
      <td class="dim mono" title="${aiHoursTitle(r)}">${aiHoursCell(r)}</td>`;
      tr.appendChild(el("td", {}, r.state === "quarantine" || r.blocked_hours.length
        ? el("button", {
          class: "btn btn-sm btn-ghost", text: "Serbest birak",
          onclick: async () => {
            if (!confirm(aiReleaseWarning(r, ai.settings || {}))) return;
            try {
              await api(`/api/ai/clear?symbol=${encodeURIComponent(r.symbol)}`, { method: "POST" });
              toast(`${r.symbol} kararlari sifirlandi`, "ok");
              refresh();
            } catch (e) { toast(e.message, "err"); }
          },
        })
        : el("span", { class: "dim", text: "-" })));
      return tr;
    });
    rowsInto($("#ai-table"), rows, "Sembol yok", 14);
  }
}

async function saveAI(patch, flashNode) {
  try {
    await api("/api/ai/settings", { method: "POST", body: patch });
    if (flashNode) {
      flashNode.classList.add("saved-flash");
      setTimeout(() => flashNode.classList.remove("saved-flash"), 900);
    }
  } catch (e) { toast(e.message, "err"); }
}

/* ---------------------------------------------------------------- system */

const SYS_FIELDS = [
  { k: "max_margin_usage_pct", label: "Marj kullanimi % (0=kapali)", t: "num", step: 1, min: 0, max: 100 },
  { k: "max_positions", label: "Sembol basi pozisyon", t: "int", min: 1, max: 20 },
  { k: "max_lot", label: "Kitap lot tavani (0=kapali)", t: "num", step: 0.01, min: 0, max: 100 },
];

// Plumbing and settled valves left the panel 27.08. Values stay on
// SystemConfig; search and _try_entry still read them.
const SYS_FIELDS_ADVANCED = [];

// Broker path lives on the connection card, not in Sistem Ayarlari -
// Pepperstone/NCM swap is a reconnect, not a risk dial.
const MT5_PATH_FIELDS = [
  { k: "mt5_terminal_path", label: "MT5 terminal yolu", t: "text", wide: true },
  { k: "autostart_mt5", label: "MT5 otomatik baslat / baglan", t: "bool" },
];

const BACKUP_FIELDS = [
  { k: "backup_dir", label: "Yedek konumu", t: "text", wide: true },
  { k: "backup_dir_secondary", label: "Ikinci yedek konumu", t: "text", wide: true },
  { k: "backup_keep", label: "Tutulacak yedek sayisi", t: "int", min: 1, max: 30 },
];

function buildSysField(f) {
  let input;
  if (f.t === "bool") {
    input = el("input", { type: "checkbox" });
    input.addEventListener("change", () => {
      saveSystem({ [f.k]: input.checked }, input);
    });
  } else if (f.t === "text") {
    input = el("input", { type: "text", spellcheck: "false" });
    input.addEventListener("change", async () => {
      await saveSystem({ [f.k]: input.value.trim() }, input);
    });
  } else if (f.t === "select") {
    input = el("select", {}, f.opts.map(([v, l]) => el("option", { value: v, text: l })));
    input.addEventListener("change", () => {
      const value = parseInt(input.value, 10);
      if (!isFinite(value)) return;
      saveSystem({ [f.k]: value }, input);
    });
  } else {
    input = el("input", { type: "number", step: f.t === "int" ? 1 : (f.step ?? 1), min: f.min, max: f.max });
    input.addEventListener("change", () => {
      const value = f.t === "int" ? parseInt(input.value, 10) : parseFloat(input.value);
      if (!isFinite(value)) return;
      saveSystem({ [f.k]: value }, input);
    });
  }
  input.dataset.sysKey = f.k;
  const field = el("div", { class: "field" }, [
    el("label", { text: f.label }),
    f.t === "bool" ? el("label", { class: "chk" }, [input, el("span", { text: "Aktif" })]) : input,
  ]);
  if (f.wide) field.classList.add("field-wide");
  return titled(field, f.k);
}

function renderSystem() {
  const sys = STATE.system || {};
  const box = $("#sys-settings");

  if (!box.dataset.built) {
    box.innerHTML = "";
    SYS_FIELDS.forEach((f) => box.appendChild(buildSysField(f)));
    box.dataset.built = "1";
  }
  const pathBox = $("#sys-mt5-path");
  if (pathBox && !pathBox.dataset.built) {
    MT5_PATH_FIELDS.forEach((f) => pathBox.appendChild(buildSysField(f)));
    pathBox.dataset.built = "1";
  }
  const bak = $("#sys-backup");
  if (bak && !bak.dataset.built) {
    BACKUP_FIELDS.forEach((f) => bak.appendChild(buildSysField(f)));
    bak.dataset.built = "1";
  }

  $$("[data-sys-key]").forEach((input) => {
    const key = input.dataset.sysKey;
    if (input === document.activeElement || !(key in sys)) return;
    if (input.type === "checkbox") input.checked = !!sys[key];
    else if (String(input.value) !== String(sys[key])) input.value = sys[key];
  });

  const mt5 = STATE.mt5 || {};
  const acc = STATE.account || {};
  const bot = STATE.bot || {};
  // "Durum: Bagli" repeated the MT5 chip in the top bar, which is on screen on
  // every tab; a green pill and a word saying the same thing cost a row. The
  // row earns its place only when it carries something the chip cannot - the
  // broker's reason for the disconnect. Same for the lock: it is printed
  // verbatim under this table and, when it matches the account above, says the
  // account number a third time.
  const account = `${acc.login || "-"} @ ${acc.server || "-"}`;
  // Not `lock` - that name is taken further down by STATE.account_lock.
  const lockedAccount = sys.account_lock_login
    ? `${sys.account_lock_login} @ ${sys.account_lock_server || "-"}`
    : "";
  const rows = [
    ...(mt5.connected ? [] : [["Durum", `Kopuk - ${mt5.error || ""}`]]),
    ["Broker", mt5.company || "-"],
    ["Hesap", account],
    ["Hesap turu", Number(acc.trade_mode) === 2 ? "GERCEK PARA" : (acc.trade_mode == null || acc.trade_mode === "" ? "-" : "demo/contest")],
    ["Kilit", (!lockedAccount
      ? "(bos - demo otomatik, gercek para operator onayi)"
      : (lockedAccount === account ? "hesapla ayni" : lockedAccount))],
    ["Isim", acc.name || "-"],
    ["AutoTrading", mt5.trade_allowed ? "Acik" : "KAPALI"],
    ["Terminal build", mt5.build || "-"],
    ["Terminal saati", mt5.server_time || "-"],
    ["Bagli terminal", mt5.path || "-", true],
  ];
  $("#sys-mt5").innerHTML = rows.map(([k, v, wide]) =>
    `<div${wide ? ' class="kv-wide"' : ""}><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join("");

  $("#sys-bot-note").textContent =
    (bot.running ? "Islem aciyor" : bot.watching ? "Sadece izliyor - islem acmiyor" : "Motor durdu") +
    ` | dongu ${bot.cycle || 0} | son tur ${num(bot.last_cycle_ms, 0)} ms | ` +
    `${bot.last_cycle_at ? new Date(bot.last_cycle_at * 1000).toLocaleTimeString("tr-TR") : "-"}` +
    (bot.last_error ? ` | HATA: ${bot.last_error}` : "");

  const lock = STATE.account_lock || {};
  const lockNote = $("#sys-lock-note");
  if (lockNote) {
    if (lock.reason) {
      lockNote.innerHTML = `<span class="pill bad">KILIT</span> ${esc(lock.reason)}`;
    } else if (sys.account_lock_login) {
      // The Kilit row above already carries this. Repeating the account
      // number verbatim under a table that just said "hesapla ayni" is the
      // third printing of one number; say it only when it disagrees, which
      // is the case actually worth noticing.
      lockNote.textContent = lockedAccount === account
        ? "" : `Kilitli hesap: ${lockedAccount}`;
    } else {
      lockNote.textContent = "Hesap kilidi bos - demo ilk baglanista yazilir; gercek para operator onayi ister.";
    }
  }

  const day = STATE.day || {};
  // The daily-loss % dial left the panel; leftover stored halt still
  // needs a way out. A quiet day does not reprint "limit normal".
  $("#sys-day-note").innerHTML = day.halted
    ? `<span class="pill bad">DURDURULDU</span> ${esc(day.halt_reason)} - devam etmek icin Gunu Devam Ettir`
    : "";
  $("#sys-resume-day").classList.toggle("btn-danger", !!day.halted);
  $("#sys-resume-day").classList.toggle("btn-ghost", !day.halted);

  renderPortfolio();
}

function portfolioSignature() {
  return SYMBOLS.map((s) =>
    [s.symbol, s.group, s.enabled ? 1 : 0, s.broker_symbol || "", s.resolved_symbol || "", s.available ? 1 : 0]
      .join("|")).join(";");
}

function renderPortfolio() {
  const body = $("#portfolio-table tbody");
  if (!body) return;
  const active = document.activeElement;
  const editing = active && body.contains(active);
  if (editing) return;

  const sig = portfolioSignature();
  if (sig === portfolioSig && body.childElementCount) return;
  portfolioSig = sig;

  body.innerHTML = "";
  if (!SYMBOLS.length) {
    body.innerHTML = `<tr><td colspan="7" class="dim">Portfoy bos - asagidan urun ekleyin.</td></tr>`;
    return;
  }

  SYMBOLS.forEach((cfg) => {
    const ok = !!cfg.available;
    const status = ok
      ? `<span class="pill on">bulundu</span>`
      : `<span class="pill bad">bulunamadi</span>`;

    const enable = el("input", { type: "checkbox" });
    enable.checked = !!cfg.enabled;
    enable.addEventListener("change", async () => {
      try {
        await api(`/api/symbols/${encodeURIComponent(cfg.symbol)}`, {
          method: "POST", body: { enabled: enable.checked },
        });
        cardsBuilt = false;
        toast(`${cfg.symbol} ${enable.checked ? "acildi" : "kapatildi"}`, "ok");
        refresh();
      } catch (e) { toast(e.message, "err"); enable.checked = !enable.checked; }
    });

    const broker = el("input", {
      type: "text", spellcheck: "false", value: cfg.broker_symbol || "",
      placeholder: cfg.symbol,
    });
    broker.dataset.pfBroker = cfg.symbol;
    broker.addEventListener("change", async () => {
      try {
        await api(`/api/symbols/${encodeURIComponent(cfg.symbol)}`, {
          method: "POST", body: { broker_symbol: broker.value.trim() },
        });
        broker.classList.add("saved-flash");
        setTimeout(() => broker.classList.remove("saved-flash"), 900);
        refresh();
      } catch (e) { toast(e.message, "err"); }
    });

    const remove = el("button", {
      class: "btn btn-sm btn-danger", text: "Sil",
      onclick: async () => {
        if (!confirm(`${cfg.symbol} portfoyden silinsin mi?`)) return;
        try {
          const res = await api(`/api/symbols/${encodeURIComponent(cfg.symbol)}`, { method: "DELETE" });
          SYMBOLS = res.symbols || [];
          if (res.system) STATE.system = res.system;
          cardsBuilt = false;
          toast(`${cfg.symbol} silindi`, "ok");
          refresh();
        } catch (e) { toast(e.message, "err"); }
      },
    });

    const tr = el("tr");
    tr.innerHTML = `<td class="sym">${esc(cfg.symbol)}</td>
      <td><span class="pill ${esc(cfg.group)}">${esc(GROUP_LABEL[cfg.group] || cfg.group)}</span></td>
      <td></td>
      <td></td>
      <td class="mono ${ok ? "" : "dim"}">${esc(cfg.resolved_symbol || "-")}</td>
      <td>${status}</td><td></td>`;
    tr.children[2].appendChild(enable);
    tr.children[3].appendChild(broker);
    tr.children[6].appendChild(remove);
    body.appendChild(tr);
  });
}

function guessGroup(name) {
  const n = String(name || "").toUpperCase();
  if (/BTC|ETH|XRP|LTC|SOL|ADA|DOGE|CRYPTO/.test(n)) return "crypto";
  if (/XAU|XAG|BRENT|WTI|OIL|SILVER|GOLD|NATGAS|GAS/.test(n)) return "commodity";
  if (/GER|FRA|UK100|NAS|US30|US500|SPX|DAX|CAC|NDX|DJ|HK50|HSTECH|JPN|AUS200|NIKKEI/.test(n)) return "index";
  // Equity CFDs at this broker carry a market suffix: AAPL.US, SMSN.KR.
  if (/^[A-Z]{1,6}\.(US|KR|CN|DE|UK|JP|HK)(-|$)/.test(n)) return "stock";
  return "forex";
}

async function addPortfolioSymbol(symbol, brokerSymbol = "", group = "") {
  const name = String(symbol || "").trim();
  if (!name) { toast("Sembol adi yazin", "err"); return; }
  const g = group || ($("#portfolio-group") && $("#portfolio-group").value) || guessGroup(name);
  const openInput = $("#portfolio-openhour");
  const closeInput = $("#portfolio-closehour");
  const openHour = openInput && openInput.value ? openInput.value : "";
  const closeHour = closeInput && closeInput.value ? closeInput.value : "";
  try {
    const res = await api("/api/symbols", {
      method: "POST",
      body: { symbol: name, group: g, broker_symbol: brokerSymbol || "" },
    });
    SYMBOLS = res.symbols || [];
    if (res.system) STATE.system = res.system;
    cardsBuilt = false;
    const addedSymbol = (res.config && res.config.symbol) || name.toUpperCase().replace(/ /g, "_");
    let extra = "";
    if (openHour || closeHour) {
      const cfg = res.config || {};
      const windows = Array.isArray(cfg.sessions) && cfg.sessions.length ? cfg.sessions : [{ start: "00:00", end: "23:59" }];
      const last = windows[windows.length - 1];
      const patched = {
        ...last,
        ...(openHour ? { start: openHour } : {}),
        ...(closeHour ? { end: closeHour } : {}),
      };
      const updated = windows.slice(0, -1).concat([patched]);
      await api(`/api/symbols/${encodeURIComponent(addedSymbol)}`, {
        method: "POST", body: { sessions: updated },
      });
      extra += `, seans ${patched.start}-${patched.end}`;
    }
    toast(`${addedSymbol} eklendi${extra} - kapali; optimizasyon sonrasi acabilirsiniz`, "ok");
    const symInput = $("#portfolio-symbol");
    const brInput = $("#portfolio-broker");
    if (symInput) symInput.value = "";
    if (brInput) brInput.value = "";
    if (openInput) openInput.value = "";
    if (closeInput) closeInput.value = "";
    refresh();
  } catch (e) {
    if (String(e.message || "").includes("zaten") && brokerSymbol) {
      try {
        await api(`/api/symbols/${encodeURIComponent(name.toUpperCase().replace(/ /g, "_"))}`, {
          method: "POST", body: { broker_symbol: brokerSymbol },
        });
        toast(`${name} eslemesi guncellendi`, "ok");
        refresh();
        return;
      } catch (err) { toast(err.message, "err"); return; }
    }
    toast(e.message, "err");
  }
}

async function searchBrokerSymbols() {
  const q = $("#broker-search").value.trim();
  const box = $("#broker-results");
  box.innerHTML = '<div class="panel-note">Araniyor...</div>';
  try {
    const res = await api(`/api/broker-symbols?q=${encodeURIComponent(q)}&limit=60`);
    if (!res.connected) { box.innerHTML = '<div class="panel-note neg">MT5 bagli degil.</div>'; return; }
    if (!res.symbols.length) { box.innerHTML = '<div class="panel-note">Eslesen sembol yok.</div>'; return; }
    box.innerHTML = `<div class="panel-note">${res.symbols.length} sonuc - tiklayinca portfoye eklenir</div>`;
    const chips = el("div", { class: "chip-row" });
    res.symbols.forEach((s) => {
      chips.appendChild(el("div", {
        class: "chip", text: s.name, title: `${s.description || ""} | ${s.path || ""}`,
        onclick: () => addPortfolioSymbol(s.name, s.name, guessGroup(s.name)),
      }));
    });
    box.appendChild(chips);
  } catch (e) {
    box.innerHTML = `<div class="panel-note neg">${esc(e.message)}</div>`;
  }
}

async function saveSystem(patch, flashNode) {
  try {
    const res = await api("/api/system", { method: "POST", body: patch });
    STATE.system = res.system;
    if (flashNode) {
      flashNode.classList.add("saved-flash");
      setTimeout(() => flashNode.classList.remove("saved-flash"), 900);
    }
    if ("mt5_terminal_path" in patch) {
      if (res.mt5_reconnect) {
        const t = res.terminal || {};
        toast(`Yol kaydedildi ve baglandi: ${t.company || "MT5"}`, "ok");
      } else {
        toast(res.mt5_error || "Yol kaydedildi ama baglanti kurulamadi", "err");
      }
      refresh();
    }
  } catch (e) { toast(e.message, "err"); }
}

/* ------------------------------------------------------------------- log */

function logMatches(level, symbol, hay) {
  if (!logFilter.has(level)) return false;
  // Symbol-less rows stay visible under a symbol filter (system context).
  if (logSymbolFilter.size && symbol && !logSymbolFilter.has(symbol)) return false;
  if (logSearch && !(hay || "").includes(logSearch)) return false;
  return true;
}

function logEntryMatches(e) {
  const sym = e.symbol || "";
  const hay = `${e.time} ${e.level} ${sym} ${e.message}`.toLowerCase();
  return logMatches(e.level, sym, hay);
}

function logLineMatches(line) {
  return logMatches(
    line.dataset.level || "",
    line.dataset.symbol || "",
    line.dataset.hay || "",
  );
}

function applyLogFilters() {
  const view = $("#logview");
  if (!view) return;
  $$(".logline", view).forEach((line) => {
    line.classList.toggle("hidden", !logLineMatches(line));
  });
}

function bumpLogSymbols(sym) {
  if (!sym || logSeenSymbols.has(sym)) return;
  logSeenSymbols.add(sym);
  renderLogSymbols();
}

function renderLogSymbols() {
  const wrap = $("#log-symbols-wrap");
  const box = $("#log-symbols");
  if (!wrap || !box) return;
  const names = Array.from(logSeenSymbols).sort();
  wrap.hidden = names.length === 0;
  const sep = $("#log-symbols-sep");
  if (sep) sep.hidden = wrap.hidden;
  box.innerHTML = "";
  names.forEach((sym) => {
    const on = !logSymbolFilter.size || logSymbolFilter.has(sym);
    let clickTimer = null;
    box.appendChild(el("div", {
      class: "chip" + (on ? " sel" : ""),
      text: sym,
      onclick: () => {
        clearTimeout(clickTimer);
        clickTimer = setTimeout(() => {
          if (!logSymbolFilter.size) {
            logSymbolFilter = new Set([sym]);
          } else if (logSymbolFilter.has(sym)) {
            logSymbolFilter.delete(sym);
          } else {
            logSymbolFilter.add(sym);
          }
          renderLogSymbols();
          applyLogFilters();
        }, 220);
      },
      ondblclick: (ev) => {
        ev.preventDefault();
        clearTimeout(clickTimer);
        logSymbolFilter = new Set([sym]);
        renderLogSymbols();
        applyLogFilters();
      },
    }));
  });
}

function renderLogLevels() {
  const box = $("#log-levels");
  if (!box) return;
  box.innerHTML = "";
  LOG_LEVELS.forEach((level) => {
    let clickTimer = null;
    box.appendChild(el("div", {
      class: "chip" + (logFilter.has(level) ? " sel" : ""), text: level,
      onclick: () => {
        clearTimeout(clickTimer);
        clickTimer = setTimeout(() => {
          if (logFilter.has(level)) {
            if (logFilter.size === 1) return;
            logFilter.delete(level);
          } else {
            logFilter.add(level);
          }
          renderLogLevels();
          applyLogFilters();
        }, 220);
      },
      ondblclick: (ev) => {
        ev.preventDefault();
        clearTimeout(clickTimer);
        logFilter = new Set([level]);
        renderLogLevels();
        applyLogFilters();
      },
    }));
  });
}

function ticketHtml(msg) {
  // Split the RAW message, escape each piece, then join. The tempting
  // shortcut - esc() first, then regex /#(\d+)/ over the result - is wrong:
  // esc("'") yields "&#39;", so that regex would match "#39" inside the
  // entity and cut it in half. Splitting before escaping cannot see an
  // entity, because none exists yet.
  const parts = String(msg ?? "").split(/(#\d{4,})/g);
  return parts.map(
    (part, i) => (i % 2 ? `<span class="tk">${esc(part)}</span>` : esc(part))
  ).join("");
}

function makeLogLine(e) {
  const sym = e.symbol || "";
  const line = el("div", { class: `logline lv-${e.level}` });
  line.dataset.level = e.level;
  line.dataset.symbol = sym;
  line.dataset.hay = `${e.time} ${e.level} ${sym} ${e.message}`.toLowerCase();
  line.innerHTML = `<span class="t">${esc(e.time)}</span><span class="l">${esc(e.level)}</span>` +
    `<span class="s">${esc(sym)}</span><span class="m">${ticketHtml(e.message)}</span>`;
  if (!logLineMatches(line)) line.classList.add("hidden");
  bumpLogSymbols(sym);
  return line;
}

function pruneLogView(view) {
  let removedH = 0;
  while (view.childElementCount > 1200) {
    const first = view.firstChild;
    removedH += first.getBoundingClientRect().height || 0;
    view.removeChild(first);
  }
  if (removedH > 0 && view.scrollTop > 0) {
    view.scrollTop = Math.max(0, view.scrollTop - removedH);
  }
}

function updateLogJump() {
  const btn = $("#btn-log-jump");
  if (!btn) return;
  if (logUnseen > 0) {
    btn.hidden = false;
    btn.textContent = `${logUnseen} yeni satir \u2193`;
  } else {
    btn.hidden = true;
  }
}

function appendLogEntries(entries) {
  if (!entries.length) return;
  const view = $("#logview");
  const follow = $("#log-follow") && $("#log-follow").checked;
  const atBottom = view.scrollTop + view.clientHeight >= view.scrollHeight - 40;
  const visibleNew = entries.reduce((n, e) => n + (logEntryMatches(e) ? 1 : 0), 0);
  entries.forEach((e) => {
    logAfter = Math.max(logAfter, e.id);
    view.appendChild(makeLogLine(e));
  });
  pruneLogView(view);
  if (follow && atBottom) {
    view.scrollTop = view.scrollHeight;
    logUnseen = 0;
  } else {
    logUnseen += visibleNew;
  }
  updateLogJump();
}

async function pollLogs() {
  const epoch = logEpoch;
  try {
    // Fetch every level; chips/search/symbol filter client-side so toggles
    // never wipe the DOM or race an in-flight response.
    const levels = LOG_LEVELS.join(",");
    const res = await api(`/api/logs?after=${logAfter}&limit=400&levels=${levels}`);
    if (epoch !== logEpoch) return;
    if (!res.entries.length) return;
    if (logPaused) {
      res.entries.forEach((e) => {
        logAfter = Math.max(logAfter, e.id);
        logPending.push(e);
      });
      logUnseen += res.entries.reduce((n, e) => n + (logEntryMatches(e) ? 1 : 0), 0);
      updateLogJump();
      return;
    }
    appendLogEntries(res.entries);
  } catch (_) { /* transient */ }
}

/* ----------------------------------------------------------------- poll */

function viewPulse(s) {
  const pos = (s.positions || []).map(
    (p) => `${p.ticket}:${p.sl}:${p.profit}:${p.volume}:${p.r_open}`).join("|");
  const st = s.states || {};
  const notes = Object.keys(st).sort().map(
    (k) => `${k}:${st[k].signal || ""}:${st[k].note || ""}:${st[k].k}:${st[k].atr}`
  ).join("|");
  const day = s.day || {};
  const acc = s.account || {};
  const bot = s.bot || {};
  const mt5 = s.mt5 || {};
  const hv = s.harvest || {};
  const opt = s.opt || {};
  return [bot.last_cycle_at, bot.running, mt5.connected, acc.equity, acc.profit,
          day.realised, day.halted, pos, notes, s.ai && s.ai.last_review,
          hv.left_on_table_r, (hv.partial_on || []).join(","),
          opt.state, opt.busy, opt.combo_done, opt.done, opt.current].join("\0");
}

async function refresh() {
  if (refreshBusy) {
    refreshQueued = true;
    return;
  }
  refreshBusy = true;
  try {
    STATE = await api("/api/state");
    const sig = STATE.symbols_sig || "";
    if (sig !== symbolsSig || !SYMBOLS.length) {
      symbolsSig = sig;
      await loadSymbols();
    }
    const pulse = $("#pulse");
    if (pulse) {
      pulse.className = "pulse on";
      setTimeout(() => { pulse.className = "pulse"; }, 250);
    }

    const vp = viewPulse(STATE);
    const same = vp === lastViewPulse && activeTab === lastViewTab;
    lastViewPulse = vp;
    lastViewTab = activeTab;
    if (!same) {
      renderTop();
      if (activeTab === "panel") {
        renderCapacity(); renderPositions(); renderHarvest(); renderDayTable();
      }
      if (activeTab === "panel" || activeTab === "tani") {
        renderExecution(); renderLive();
      }
      if (!cardsBuilt && SYMBOLS.length) buildSymbolCards();
      if (activeTab === "semboller") updateSymbolCards();
      if (activeTab === "opt") { renderOptJob(); syncOptPicker(); }
      if (activeTab === "ai") renderAI();
      if (activeTab === "sistem") renderSystem();
    }
    if (activeTab === "log") pollLogs();
  } catch (e) {
    const pulse = $("#pulse");
    if (pulse) pulse.className = "pulse err";
  } finally {
    refreshBusy = false;
    clearTimeout(pollTimer);
    if (refreshQueued) {
      refreshQueued = false;
      refresh();
    } else {
      const hidden = typeof document !== "undefined" && document.hidden;
      // Do not drop to 1.5s while a search is running: that is when the
      // engine, workers, and this poll already share one MT5 lock.
      const delay = hidden ? 6000 : 3000;
      pollTimer = setTimeout(refresh, delay);
    }
  }
}

/* ------------------------------------------------------------------ wire */

function confirmThen(message, fn) {
  return async () => { if (confirm(message)) await fn(); };
}

function wire() {
  applyStaticHelp();
  $$(".tab").forEach((t) => t.addEventListener("click", () => selectTab(t.dataset.tab)));

  const gatesBtn = $("#btn-gates-refresh");
  if (gatesBtn) gatesBtn.onclick = () => loadGates();
  const blocksBtn = $("#btn-blocks-refresh");
  if (blocksBtn) blocksBtn.onclick = () => loadBlocks();
  const ratioBtn = $("#btn-ratio-refresh");
  if (ratioBtn) ratioBtn.onclick = () => loadSpreadRatio();
  const autopsyBtn = $("#btn-autopsy-refresh");
  if (autopsyBtn) autopsyBtn.onclick = () => loadAutopsies();
  const blocksReset = $("#btn-blocks-reset");
  if (blocksReset) blocksReset.onclick = async () => {
    try {
      const res = await api("/api/analysis/entry-blocks/reset", { method: "POST" });
      toast(res.message || "Sifirlandi", "ok");
      loadBlocks();
    } catch (e) { toast(e.message, "err"); }
  };

  const call = async (path, body) => {
    try {
      const res = await api(path, { method: "POST", body });
      if (res.message) toast(res.message, res.ok ? "ok" : "err");
      else if (res.closed !== undefined) {
        const msg = res.remaining < 0
          ? "MT5 baglantisi dogrulanamadi - pozisyon durumu bilinmiyor, elle kontrol edin"
          : res.remaining
            ? `${res.closed} pozisyon kapatildi, ${res.remaining} HALA ACIK - elle kontrol edin`
            : `${res.closed} pozisyon kapatildi`;
        toast(msg, res.remaining ? "err" : "ok");
      }
      refresh();
    } catch (e) { toast(e.message, "err"); }
  };

  $("#btn-start").onclick = () => call("/api/bot/start");
  // No `close` field: let the backend default to Sistem > "Durdurunca
  // pozisyonlari kapat" instead of hardcoding it off - sending `close: false`
  // here made that setting permanently inert no matter how it was set.
  $("#btn-stop").onclick = () => call("/api/bot/stop");
  $("#btn-panic").onclick = confirmThen("Bot durdurulacak ve TUM pozisyonlar kapatilacak. Onayliyor musunuz?",
    () => call("/api/bot/panic"));

  $("#sys-start").onclick = () => call("/api/bot/start");
  $("#sys-stop").onclick = () => call("/api/bot/stop");
  $("#sys-stop-close").onclick = confirmThen("Bot durdurulup pozisyonlar kapatilacak. Onayliyor musunuz?",
    () => call("/api/bot/stop", { close: true }));
  $("#sys-panic").onclick = confirmThen("ACIL DURDURMA. Onayliyor musunuz?", () => call("/api/bot/panic"));
  $("#sys-reconnect").onclick = async () => {
    try {
      const res = await api("/api/mt5/reconnect", { method: "POST" });
      if (res.ok) {
        const t = res.terminal || {};
        toast(`Baglandi: ${t.company || "MT5"} | ${res.configured_path || ""}`, "ok");
      } else {
        toast(res.error || "Baglanti basarisiz", "err");
      }
      refresh();
    } catch (e) { toast(e.message, "err"); }
  };
  const lockBtn = $("#sys-lock-confirm");
  if (lockBtn) {
    lockBtn.onclick = async () => {
      const acc = STATE.account || {};
      const login = acc.login;
      const server = acc.server || "";
      if (!login) {
        toast("Bagli hesap yok", "err");
        return;
      }
      const typed = window.prompt(
        `Bagli hesabi kilitlemek icin hesap numarasini yazin (${login}):`,
        "",
      );
      if (typed == null) return;
      if (String(typed).trim() !== String(login)) {
        toast("Hesap numarasi eslesmedi - kilit degismedi", "err");
        return;
      }
      const serverTyped = window.prompt(
        `Sunucu adini yazin (${server}):`,
        "",
      );
      if (serverTyped == null) return;
      if (String(serverTyped).trim() !== String(server)) {
        toast("Sunucu adi eslesmedi - kilit degismedi", "err");
        return;
      }
      try {
        const res = await api("/api/account-lock", {
          method: "POST",
          body: { confirm_login: Number(login), confirm_server: server },
        });
        if (res.system) STATE.system = res.system;
        toast(`Hesap kilidi: ${login} @ ${server}`, "ok");
        refresh();
      } catch (e) { toast(e.message, "err"); }
    };
  }
  $("#btn-broker-search").onclick = searchBrokerSymbols;
  $("#broker-search").addEventListener("keydown", (e) => {
    if (e.key === "Enter") searchBrokerSymbols();
  });
  $("#sys-close-all").onclick = confirmThen("Tum pozisyonlar kapatilacak. Onayliyor musunuz?",
    () => call("/api/positions-close-all"));
  $("#sys-resume-day").onclick = () => call("/api/day/resume");
  const pfAdd = $("#btn-portfolio-add");
  if (pfAdd) {
    pfAdd.onclick = () => {
      addPortfolioSymbol($("#portfolio-symbol")?.value || "", $("#portfolio-broker")?.value || "");
    };
    $("#portfolio-symbol")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") pfAdd.click();
    });
    $("#portfolio-broker")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") pfAdd.click();
    });
  }
  const pfFill = $("#btn-portfolio-fill");
  if (pfFill) {
    // Non-destructive: adds only symbols missing from the portfolio and leaves
    // every existing config and optimization result untouched.
    pfFill.onclick = async () => {
      try {
        const res = await api("/api/symbols-seed?overwrite=false", { method: "POST" });
        SYMBOLS = res.symbols || [];
        if (res.system) STATE.system = res.system;
        cardsBuilt = false;
        optPickerSig = "";
        portfolioSig = "";
        toast(res.seeded ? `${res.seeded} urun eklendi` : "Eksik urun yok", "ok");
        refresh();
      } catch (e) { toast(e.message, "err"); }
    };
  }
  const pfSort = $("#btn-portfolio-sort");
  if (pfSort) {
    pfSort.onclick = async () => {
      try {
        const res = await api("/api/symbols-sort", { method: "POST" });
        SYMBOLS = res.symbols || [];
        cardsBuilt = false;
        optPickerSig = "";
        portfolioSig = "";
        toast("Sembol sirasi grup + alfabetik yapildi", "ok");
        refresh();
      } catch (e) { toast(e.message, "err"); }
    };
  }
  const pfDefaults = $("#btn-portfolio-defaults");
  if (pfDefaults) {
    pfDefaults.onclick = confirmThen(
      "Portfoy silinip varsayilan FX listesine donecek. Onayliyor musunuz?",
      async () => {
        const res = await api("/api/symbols-seed?overwrite=true", { method: "POST" });
        SYMBOLS = res.symbols || [];
        if (res.system) STATE.system = res.system;
        cardsBuilt = false;
        optPickerSig = "";
        portfolioSig = "";
        toast("Varsayilan urun listesi yuklendi", "ok");
        refresh();
      },
    );
  }
  $("#sys-shutdown").onclick = confirmThen("Uygulama kapatilacak. Onayliyor musunuz?", async () => {
    await api("/api/app/shutdown", { method: "POST" });
    toast("Kapaniyor...", "ok");
  });

  $("#sys-restart").onclick = confirmThen("Uygulama yeniden baslatilacak. Onayliyor musunuz?", async () => {
    await api("/api/app/restart", { method: "POST" });
    toast("Yeniden baslatiliyor...", "ok");
  });

  $("#btn-close-all").onclick = confirmThen("Tum pozisyonlar kapatilacak. Onayliyor musunuz?",
    () => call("/api/positions-close-all"));

  $$("[data-bulk]").forEach((btn) => {
    btn.onclick = async () => {
      const enabled = btn.dataset.bulk === "enable";
      try {
        const res = await api("/api/symbols-bulk", { method: "POST", body: { patch: { enabled } } });
        SYMBOLS = res.symbols;
        cardsBuilt = false;
        toastBulkResult(res, enabled ? "acildi" : "kapatildi");
        refresh();
      } catch (e) { toast(e.message, "err"); }
    };
  });

  $("#symbol-filter").addEventListener("input", applySymbolFilter);
  $("#group-filter").addEventListener("change", applySymbolFilter);
  $("#btn-opt-all").onclick = () => runOptimizer(null);
  $("#btn-opt-run").onclick = () => runOptimizer(Array.from(optSelection));
  $("#btn-opt-cancel").onclick = async () => {
    toast("Iptal isteniyor...", "ok");
    $("#btn-opt-cancel").disabled = true;
    await call("/api/opt/cancel");
  };
  $("#btn-opt-save").onclick = saveOptParams;
  $("#btn-opt-history").onclick = loadOptHistory;
  $("#opt-history-sort").onchange = loadOptHistory;
  $("#btn-opt-history-clear").onclick = confirmThen(
    "Tum optimizasyon gecmisi silinecek (uygulanmis ayarlar etkilenmez). Onayliyor musunuz?",
    async () => {
      const res = await api("/api/opt/history", { method: "DELETE" });
      toast(`Gecmis temizlendi (${res.deleted} kayit)`, "ok");
      loadOptHistory();
    },
  );

  $("#ai-enabled").onchange = (e) => saveAI({ enabled: e.target.checked }, e.target);
  $("#btn-ai-review").onclick = async () => {
    try {
      await api("/api/ai/review", { method: "POST" });
      toast("AI degerlendirmesi tamamlandi", "ok");
      refresh();
    } catch (e) { toast(e.message, "err"); }
  };
  // Same caveat as the per-row release: this clears verdicts, not the deal
  // history they are derived from, so anything that still meets the criteria
  // is flagged again on the next review.
  $("#btn-ai-clear").onclick = confirmThen(
    "Tum AI kararlari sifirlanacak.\n\n"
    + "DIKKAT: karantina ve kapali saatler son islemlerden yeniden hesaplanir - "
    + "esikleri hala asan semboller bir sonraki degerlendirmede geri gelir. "
    + "Kalici cozum icin sembolu yeniden optimize edin ya da AI ayarlarindaki "
    + "esikleri degistirin.\n\nOnayliyor musunuz?", async () => {
    await api("/api/ai/clear", { method: "POST" });
    toast("AI kararlari sifirlandi", "ok");
    refresh();
  });
  $("#btn-log-clear").onclick = () => {
    // View-only: the shared ring and the log file stay; this tab's DOM does not.
    logEpoch += 1;
    $("#logview").innerHTML = "";
    logPending = [];
    logUnseen = 0;
    logSeenSymbols = new Set();
    logSymbolFilter = new Set();
    renderLogSymbols();
    updateLogJump();
  };
  const search = $("#log-search");
  if (search) {
    search.addEventListener("input", () => {
      clearTimeout(logSearchTimer);
      logSearchTimer = setTimeout(() => {
        logSearch = (search.value || "").trim().toLowerCase();
        applyLogFilters();
      }, 150);
    });
  }
  const pauseBtn = $("#btn-log-pause");
  if (pauseBtn) {
    pauseBtn.onclick = () => {
      logPaused = !logPaused;
      pauseBtn.textContent = logPaused ? "Devam" : "Duraklat";
      pauseBtn.classList.toggle("btn-stop", logPaused);
      if (!logPaused && logPending.length) {
        const batch = logPending;
        logPending = [];
        appendLogEntries(batch);
      }
    };
  }
  const densBtn = $("#btn-log-density");
  if (densBtn) {
    densBtn.onclick = () => {
      logCompact = !logCompact;
      $("#logview").classList.toggle("compact", logCompact);
      densBtn.textContent = logCompact ? "Ferah" : "Sik";
    };
  }
  const jumpBtn = $("#btn-log-jump");
  if (jumpBtn) {
    jumpBtn.onclick = () => {
      if (logPaused && logPending.length) {
        const batch = logPending;
        logPending = [];
        appendLogEntries(batch);
      }
      const view = $("#logview");
      view.scrollTop = view.scrollHeight;
      logUnseen = 0;
      updateLogJump();
      if ($("#log-follow")) $("#log-follow").checked = true;
    };
  }
  const lvlAll = $("#btn-log-levels-all");
  if (lvlAll) {
    lvlAll.onclick = () => {
      logFilter = new Set(LOG_LEVELS);
      renderLogLevels();
      applyLogFilters();
    };
  }
  const symAll = $("#btn-log-symbols-all");
  if (symAll) {
    symAll.onclick = () => {
      logSymbolFilter = new Set();
      renderLogSymbols();
      applyLogFilters();
    };
  }
  // Same-origin <a href> sends the HttpOnly session cookie; the secret
  // must not go in the URL (history, Referer, access logs).

  renderLogLevels();
}

wire();
fillGroupSelects();
loadSymbols().then(refresh);

