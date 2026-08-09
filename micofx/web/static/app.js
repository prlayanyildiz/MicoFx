"use strict";

/* ------------------------------------------------------------------ utils */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const GROUP_LABEL = { forex: "Forex", index: "Endeks", commodity: "Emtia", crypto: "Kripto" };
const DAY_LABEL = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"];
const LOG_LEVELS = ["TRADE", "SIGNAL", "OPT", "AI", "INFO", "WARN", "ERROR"];
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
const OPT_TF_OPTIONS = ["M5", "M10", "M15", "M30", "H1"];
let logAfter = 0;
let logFilter = new Set(LOG_LEVELS);
let cardsBuilt = false;
let pollTimer = null;
let optPickerSig = "";
let portfolioSig = "";
let aiTableSig = "";
let refreshBusy = false;

const API_TOKEN = document.querySelector('meta[name="mico-api-token"]')?.content || "";

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (API_TOKEN) headers["X-Mico-Token"] = API_TOKEN;
  const res = await fetch(path, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
  return data;
}

// Symbol names (broker_symbol is user/API-settable), broker/account strings
// and log/error text all land in innerHTML template literals verbatim
// elsewhere in this file - a symbol saved with a name like
// "<img src=x onerror=...>" would otherwise execute. Escaping matters even
// more now that the API token sits in a <meta> tag on this same page: an
// XSS here could read and exfiltrate it, defeating the token entirely.
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

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
    else if (k === "html") node.innerHTML = v;
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
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`));
  if (name === "opt") {
    if (!OPT_PARAMS) loadOptParams().then(loadOptHistory);
    else syncOptPicker();
  }
  if (name === "log") pollLogs();
}

/* ----------------------------------------------------------- panel: cards */

function renderTop() {
  const acc = STATE.account || {};
  const bot = STATE.bot || {};
  const mt5 = STATE.mt5 || {};
  const day = STATE.day || {};
  const cap = STATE.capacity || {};

  const botText = bot.running ? "CALISIYOR" : (bot.watching ? "IZLIYOR" : "DURDU");
  const items = [
    ["Bot", botText, bot.running ? "pos" : (bot.watching ? "muted" : "dim")],
    ["MT5", mt5.connected ? "BAGLI" : "KOPUK", mt5.connected ? "pos" : "neg"],
    ["Saat", (mt5.server_time || "").slice(11, 16), ""],
    ["Bakiye", num(acc.balance), ""],
    ["Varlik", num(acc.equity), ""],
    ["Acik K/Z", signed(acc.profit), cls(acc.profit)],
    ["Gun", `${signed(day.realised)} (${signed(day.pnl_pct, 2)}%)`, cls(day.realised)],
    ["Pozisyon", `${cap.open_total ?? 0} / ${cap.max_total_positions ?? 0}`, ""],
  ];
  if (acc.netting) {
    items.push(["Hesap modu", "NETTING - ISLEM DURDU", "neg"]);
  }

  $("#topstats").innerHTML = items.map(([lbl, val, klass]) =>
    `<div class="tstat"><div class="lbl">${lbl}</div><div class="val ${klass}">${val}</div></div>`
  ).join("");

  $("#btn-start").disabled = !!bot.running;
  $("#btn-stop").disabled = !bot.running;
}

function renderCards() {
  const acc = STATE.account || {};
  const day = STATE.day || {};
  const cap = STATE.capacity || {};
  const sys = STATE.system || {};

  const marginPct = cap.margin_usage_pct || 0;
  const marginMax = cap.max_margin_usage_pct || 100;
  const marginRatio = Math.min(100, (marginPct / Math.max(1, marginMax)) * 100);

  const lossLimit = sys.daily_loss_pct || 0;
  const dayPct = day.pnl_pct || 0;
  const lossRatio = lossLimit > 0 ? Math.min(100, Math.max(0, (-dayPct / lossLimit) * 100)) : 0;

  const cards = [
    { lbl: "Bakiye", val: num(acc.balance), foot: `${esc(acc.currency || "")} | kaldirac 1:${acc.leverage || "-"}`, accent: "blue" },
    { lbl: "Varlik", val: num(acc.equity), foot: `acik k/z ${signed(acc.profit)}`, accent: Number(acc.profit) >= 0 ? "green" : "red" },
    { lbl: "Serbest Marj", val: num(acc.margin_free), foot: `kullanilan ${num(acc.margin)}`, accent: "blue" },
    {
      lbl: "Marj Kullanimi", val: `%${num(marginPct, 1)}`, foot: `limit %${num(marginMax, 0)}`,
      bar: marginRatio, barClass: marginRatio > 85 ? "bad" : marginRatio > 60 ? "warn" : "",
    },
    {
      lbl: "Gunluk Sonuc", val: signed(day.realised), accent: Number(day.realised) >= 0 ? "green" : "red",
      foot: `${day.closed_trades || 0} islem | %${num(day.win_rate, 0)} basari`,
    },
    {
      lbl: "Gunluk Limit", val: `${signed(dayPct, 2)}%`, foot: lossLimit > 0 ? `zarar limiti %${num(lossLimit, 1)}` : "limit kapali",
      bar: lossRatio, barClass: lossRatio > 80 ? "bad" : lossRatio > 50 ? "warn" : "",
      accent: day.halted ? "red" : "",
    },
    {
      lbl: "Acilabilir Islem", val: `${cap.global_free_slots ?? 0}`,
      foot: `${cap.open_total ?? 0}/${cap.max_total_positions ?? 0} dolu | butce ${num(cap.margin_budget)}`,
      accent: "amber",
    },
    {
      lbl: "Beklenen Aylik", val: signed(cap.projected_monthly),
      foot: `%${num(cap.projected_monthly_pct, 2)} | gunluk ${signed(cap.projected_daily)} | OPT dogrulamasindan`,
      accent: (cap.projected_monthly ?? 0) >= 0 ? "green" : "red",
    },
  ];

  $("#account-cards").innerHTML = cards.map((c) => `
    <div class="card ${c.accent ? "accent-" + c.accent : ""}">
      <div class="lbl">${c.lbl}</div>
      <div class="val">${c.val}</div>
      <div class="foot">${c.foot || ""}</div>
      ${c.bar !== undefined ? `<div class="bar"><i class="${c.barClass}" style="width:${c.bar}%"></i></div>` : ""}
    </div>`).join("");

  if (day.halted) {
    $("#day-note").innerHTML = `<span class="pill bad">DURDURULDU</span> ${esc(day.halt_reason || "")}`;
  } else {
    $("#day-note").textContent = `${day.day_key || ""} | baslangic ${num(day.start_balance)}`;
  }
}

function renderCapacity() {
  const cap = STATE.capacity || {};
  const rows = (cap.rows || []).map((r) => {
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td><span class="pill ${esc(r.group)}">${esc(GROUP_LABEL[r.group] || r.group)}</span></td>
      <td><span class="pill ${r.enabled ? "on" : "off"}">${r.enabled ? "aktif" : "kapali"}</span></td>
      <td class="num">${num(r.lot, 2)}</td>
      <td class="num ${r.edge_scale > 1 ? "pos" : (r.edge_scale < 1 ? "neg" : "dim")}">${r.edge_scale != null ? "x" + num(r.edge_scale, 2) : "-"}</td>
      <td class="num dim">${esc(r.lot_note || r.lot_mode)}</td>
      <td class="num ${r.open_positions ? "pos" : "dim"}">${r.open_positions}</td>
      <td class="num dim">${r.max_positions}</td>
      <td class="num ${r.free_slots > 0 ? "pos" : "neg"}"><b>${r.free_slots}</b></td>
      <td class="num">${num(r.margin_per_trade)}</td>
      <td class="num">${r.risk_per_trade ? num(r.risk_per_trade) : "-"}</td>
      <td class="num ${r.cost_pct_of_risk > 15 ? "neg" : "dim"}">${r.risk_per_trade ? num(r.cost_per_trade) + " (%" + num(r.cost_pct_of_risk, 0) + ")" : "-"}</td>
      <td class="num ${cls(r.expected_per_trade)}">${r.expectancy_r ? signed(r.expected_per_trade, 3) : '<span class="dim">-</span>'}</td>
      <td class="num ${cls(r.open_profit)}">${r.open_positions ? signed(r.open_profit) : "-"}</td>`;
    return tr;
  });
  rowsInto($("#capacity-table"), rows, "Sembol yok", 13);

  const enabled = (cap.rows || []).filter((r) => r.enabled);
  const openable = enabled.filter((r) => r.free_slots > 0).length;
  $("#capacity-summary").innerHTML =
    `${enabled.length} aktif sembol | ${cap.open_total ?? 0}/${cap.max_total_positions ?? 0} pozisyon dolu | ` +
    `${cap.global_free_slots ?? 0} slot bos | lot carpani <b>x${num(cap.lot_multiplier, 2)}</b>` +
    `${cap.size_by_edge ? " + avantaj agirligi" : ""} | ` +
    `hepsi acilirsa toplam risk ${num(cap.total_risk_per_trade)} (%${num(cap.total_risk_pct, 2)}) | ` +
    `slot limitinde en kotu risk ${num(cap.concurrent_risk)} (%${num(cap.concurrent_risk_pct, 2)}), ` +
    `marj ${num(cap.concurrent_margin)} | ` +
    `guvenli ust sinir <b>x${num(cap.safe_multiplier, 2)}</b>`;
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
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(p.symbol)}${p.managed ? "" : ' <span class="pill off">harici</span>'}</td>
      <td><span class="pill ${p.side}">${p.side === "buy" ? "AL" : "SAT"}</span></td>
      <td class="num">${num(p.volume, 2)}</td>
      <td class="num">${price(p.price_open, digits)}</td>
      <td class="num">${price(p.price_current, digits)}</td>
      <td class="num ${p.sl ? "" : "dim"}">${price(p.sl, digits)}</td>
      <td class="num ${p.tp ? "" : "dim"}">${price(p.tp, digits)}</td>
      <td class="num ${cls(p.profit + p.swap)}">${signed(p.profit + p.swap)}</td>
      <td class="dim mono">${duration(now - p.time)}</td>`;
    tr.appendChild(el("td", {}, el("button", {
      class: "btn btn-sm btn-danger",
      text: "Kapat",
      onclick: async (e) => {
        e.target.disabled = true;
        try { await api(`/api/positions/${p.ticket}/close`, { method: "POST" }); refresh(); }
        catch (err) { toast(err.message, "err"); e.target.disabled = false; }
      },
    })));
    return tr;
  });
  rowsInto($("#positions-table"), rows, "Acik pozisyon yok", 10);
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
    const sig = st.signal ? `<span class="pill ${st.signal}">${st.signal === "buy" ? "AL" : "SAT"}</span>` : '<span class="dim">-</span>';
    const htf = !cfg.htf_factor ? '<span class="dim">kapali</span>'
      : st.htf > 0 ? '<span class="pos">yukari</span>'
      : st.htf < 0 ? '<span class="neg">asagi</span>' : '<span class="dim">-</span>';
    const tr = el("tr");
    tr.innerHTML = `
      <td class="sym">${esc(cfg.symbol)}</td>
      <td class="dim" title="${esc(STRATEGY_LABEL[cfg.strategy] || cfg.strategy)}">${esc(cfg.strategy)}</td>
      <td class="dim">${esc(cfg.timeframe)}</td>
      <td>${sessionCell}</td>
      <td class="${st.t3_rising ? "pos" : "neg"}">${st.bars_ready ? (st.t3_rising ? "yukari" : "asagi") : '<span class="dim">-</span>'}</td>
      <td>${htf}</td>
      <td class="num">${st.k != null ? num(st.k, 1) : "-"}</td>
      <td class="num">${st.d != null ? num(st.d, 1) : "-"}</td>
      <td class="num ${st.adx >= (cfg.adx_min || 0) ? "" : "dim"}">${st.adx != null ? num(st.adx, 0) : "-"}</td>
      <td class="num dim">${st.atr ? st.atr.toFixed(cfg.digits ?? 5) : "-"}</td>
      <td class="num ${st.spread_atr > cfg.max_spread_atr ? "neg" : "dim"}">${st.spread_atr ? num(st.spread_atr, 2) + "x" : "-"}</td>
      <td>${cfg.enabled ? sig : '<span class="pill off">kapali</span>'}</td>
      <td class="dim">${esc(st.note || "")}</td>`;
    return tr;
  });
  rowsInto($("#live-table"), rows, "Sembol yok", 13);
}

/* --------------------------------------------------------- symbols: spec */

const STRATEGY_LABEL = {
  t3_stoch: "T3 + Stochastic RSI",
  orb: "Acilis Araligi Kirilimi",
  vwap_rev: "VWAP Ortalamaya Donus",
  donchian: "Donchian Kirilimi",
  squeeze_brk: "Bollinger/Keltner Sikisma Kirilimi",
  flow_rev: "Emir Akisi Tukenme Donusu",
  mtf_pullback: "Ust TF Trend Geri Cekilmesi",
  micro_rev: "Mikro Ortalamaya Donus (maliyet olcekli)",
  burst: "Momentum Patlamasi Devami",
  t3_ribbon: "Tillson T3 Seridi (hizli/yavas kesisim)",
  dual_t3: "Ikili T3 + ATR (sade cekirdek)",
  st_trend: "SuperTrend Donusu (hedefsiz, sadece trail)",
  t3_flip: "Tek Tillson T3 Yon Donusu (tek cizgi)",
};

// Visible on every symbol card without expanding anything: pure risk/sizing
// dials someone actually turns by hand. Everything the optimizer tunes for
// you (strategy choice, entry-signal internals, exit/ATR mechanics, filters)
// lives in ADVANCED_SECTIONS instead, collapsed by default.
const POSITION_SECTION = {
  title: "Pozisyon Boyutu",
  fields: [
    { k: "lot_mode", t: "select", label: "Lot modu", opts: [["fixed", "Sabit lot"], ["risk", "Risk yuzdesi"]] },
    { k: "fixed_lot", t: "num", label: "Sabit lot", step: 0.01, min: 0.01, max: 20 },
    { k: "risk_percent", t: "num", label: "Risk %", step: 0.05, min: 0.05 },
    { k: "max_lot", t: "num", label: "Maks lot", step: 0.01, min: 0.01, max: 20 },
    { k: "max_positions", t: "int", label: "Maks pozisyon", min: 1, max: 50 },
    { k: "symbol_daily_loss_pct", t: "num", label: "Sembol gunluk zarar limiti % (0=kapali)", step: 0.1, min: 0,
      hint: "Bu sembol bugun bakiyenin bu kadarini kaybedince, hesabin genel gunluk limiti dolmasa bile "
          + "sadece bu sembolde yeni giris durur." },
  ],
};

const SECTIONS = [
  {
    title: "Strateji (optimizer ayarlar)",
    fields: [
      {
        k: "strategy", t: "select", label: "Strateji ailesi",
        opts: [["t3_stoch", "T3 + Stochastic RSI"], ["orb", "Acilis Araligi (ORB)"],
               ["vwap_rev", "VWAP Ortalamaya Donus"], ["donchian", "Donchian Kirilimi"],
               ["squeeze_brk", "Bollinger/Keltner Sikisma Kirilimi"],
               ["flow_rev", "Emir Akisi Tukenme Donusu"],
               ["mtf_pullback", "Ust TF Trend Geri Cekilmesi"],
               ["micro_rev", "Mikro Ortalamaya Donus (maliyet olcekli)"],
               ["burst", "Momentum Patlamasi Devami"],
               ["t3_ribbon", "Tillson T3 Seridi (hizli/yavas kesisim)"],
               ["dual_t3", "Ikili T3 + ATR (sade cekirdek)"],
               ["st_trend", "SuperTrend Donusu (hedefsiz, sadece trail)"],
               ["t3_flip", "Tek Tillson T3 Yon Donusu (tek cizgi)"]],
      },
      { k: "timeframe", t: "select", label: "Zaman dilimi", opts: [["M5", "M5"], ["M10", "M10"], ["M15", "M15"], ["M30", "M30"], ["H1", "H1"]] },
    ],
  },
  {
    title: "Ikinci Sinyal (Ensemble)",
    fields: [
      {
        k: "ensemble_enabled", t: "bool",
        label: "Optimizasyonun sakladigi ikinci (farkli aile) sinyali de kullan",
      },
    ],
  },
  {
    title: "Sinyal (T3 + Stochastic RSI)",
    fields: [
      { k: "t3_length", t: "int", label: "T3 uzunluk", min: 2, max: 60 },
      { k: "t3_volume_factor", t: "num", label: "T3 hacim faktoru", step: 0.05, min: 0.1, max: 1 },
      { k: "rsi_length", t: "int", label: "RSI periyot", min: 2, max: 60 },
      { k: "stoch_length", t: "int", label: "Stoch periyot", min: 2, max: 60 },
      { k: "smooth_k", t: "int", label: "%K yumusatma", min: 1, max: 20 },
      { k: "smooth_d", t: "int", label: "%D yumusatma", min: 1, max: 20 },
      { k: "stoch_band", t: "num", label: "Kesisim bandi", step: 1, min: 1, max: 50 },
      { k: "stoch_extreme", t: "num", label: "Asiri bolge", step: 1, min: 50, max: 100 },
      {
        k: "htf_factor", t: "int", label: "Ust TF carpani (0=kapali)",
        min: 0, max: 24,
      },
    ],
  },
  {
    title: "Risk ve Cikis (ATR)",
    fields: [
      { k: "atr_period", t: "int", label: "ATR periyot", min: 2, max: 100 },
      { k: "sl_atr_mult", t: "num", label: "SL x ATR", step: 0.1, min: 0.1 },
      { k: "tp_atr_mult", t: "num", label: "TP x ATR (0=hedef yok, sadece trail)", step: 0.1, min: 0 },
      { k: "trail_start_atr", t: "num", label: "Trail baslangic x ATR", step: 0.1, min: 0 },
      { k: "trail_step_atr", t: "num", label: "Trail mesafe x ATR", step: 0.1, min: 0.1 },
      {
        k: "trail_mode", t: "select", label: "Trail modu",
        opts: [["atr", "ATR (klasik)"], ["structure", "Yapisal (swing H/L)"], ["hybrid", "Hibrit (en siki)"]],
      },
      { k: "trail_lookback", t: "int", label: "Yapisal trail geriye bakis (bar)", min: 3, max: 100 },
      { k: "breakeven_atr", t: "num", label: "Maliyete cekme x ATR", step: 0.1, min: 0 },
      { k: "max_bars_in_trade", t: "int", label: "Maks bar (0=kapali)", min: 0, max: 2000 },
      { k: "stale_exit_ratio", t: "num", label: "Erken zarar kapanisi (max bar orani, 0=kapali)", step: 0.05, min: 0, max: 1 },
    ],
  },
  {
    title: "Acilis Araligi (ORB)",
    fields: [
      { k: "orb_minutes", t: "int", label: "Aralik suresi (dk)", min: 5, max: 240 },
      { k: "orb_buffer_atr", t: "num", label: "Kirilim payi x ATR", step: 0.05, min: 0, max: 2 },
      { k: "orb_retest", t: "bool", label: "Sadece geri test (retest) sonrasi gir" },
    ],
  },
  {
    title: "Donchian Kirilimi",
    fields: [
      { k: "don_length", t: "int", label: "Kanal uzunlugu (bar)", min: 5, max: 300 },
      { k: "don_buffer_atr", t: "num", label: "Kirilim payi x ATR", step: 0.05, min: 0, max: 2 },
      { k: "don_squeeze", t: "num", label: "Maks kanal genisligi yuzdeligi (0=kapali)", step: 0.05, min: 0, max: 1 },
    ],
  },
  {
    title: "VWAP Ortalamaya Donus",
    fields: [
      { k: "vwap_sd", t: "num", label: "Uzama esigi (std sapma)", step: 0.25, min: 0.5, max: 6 },
      { k: "adx_max", t: "num", label: "Maks ADX (0=kapali)", step: 1, min: 0, max: 60 },
    ],
  },
  {
    title: "Bollinger/Keltner Sikisma Kirilimi",
    fields: [
      { k: "sqz_length", t: "int", label: "Bant uzunlugu (BB ve KC)", min: 5, max: 100 },
      { k: "sqz_bb_sd", t: "num", label: "Bollinger std sapma", step: 0.1, min: 0.5, max: 4 },
      { k: "sqz_kc_atr", t: "num", label: "Keltner x ATR", step: 0.1, min: 0.5, max: 4 },
      { k: "sqz_momentum_len", t: "int", label: "Yon icin regresyon penceresi", min: 3, max: 60 },
    ],
  },
  {
    title: "Emir Akisi Tukenme Donusu",
    fields: [
      { k: "flow_length", t: "int", label: "Akis penceresi (bar)", min: 3, max: 120 },
      { k: "flow_z", t: "num", label: "Tukenme esigi (z skor)", step: 0.1, min: 0.5, max: 5 },
      { k: "flow_divergence", t: "bool", label: "Fiyat/akis uyumsuzlugu da sart" },
    ],
  },
  {
    title: "Ust TF Trend Geri Cekilmesi",
    fields: [
      { k: "pull_fast", t: "int", label: "Hizli EMA uzunlugu", min: 2, max: 60 },
      { k: "pull_depth_atr", t: "num", label: "Geri cekilme derinligi x ATR", step: 0.1, min: 0, max: 3 },
      { k: "pull_max_bars", t: "int", label: "Geri cekilme penceresi (bar)", min: 2, max: 40 },
    ],
  },
  {
    title: "Mikro Ortalamaya Donus (maliyet olcekli)",
    fields: [
      { k: "mr_fast", t: "int", label: "Hizli ortalama (bar)", min: 2, max: 60 },
      { k: "mr_stretch_cost", t: "num", label: "Uzama esigi x islem maliyeti", step: 0.5, min: 1, max: 40 },
      { k: "mr_confirm", t: "bool", label: "Bar ortalamaya donmus olsun" },
    ],
  },
  {
    title: "Momentum Patlamasi Devami",
    fields: [
      { k: "brst_lookback", t: "int", label: "Menzil penceresi (bar)", min: 5, max: 120 },
      { k: "brst_range_z", t: "num", label: "Menzil genislemesi (z skor)", step: 0.1, min: 0.5, max: 5 },
      { k: "brst_close_pct", t: "num", label: "Kapanis barin ucunda (oran)", step: 0.05, min: 0.5, max: 0.99 },
    ],
  },
  {
    title: "Tillson T3 Seridi (hizli/yavas kesisim)",
    fields: [
      { k: "t3_fast", t: "int", label: "Hizli T3 uzunluk", min: 2, max: 60 },
      { k: "t3_slow_mult", t: "num", label: "Yavas T3 carpani", step: 0.5, min: 1.2, max: 10 },
      { k: "t3_slope_atr", t: "num", label: "Min yavas T3 egimi x ATR (0=kapali)", step: 0.01, min: 0, max: 1 },
      { k: "t3_fast_vf", t: "num", label: "Hizli T3 hacim faktoru (0=yavas ile ayni)", step: 0.001, min: 0, max: 1 },
      { k: "t3_accel_min", t: "num", label: "Min T3 ivmesi x ATR (0=kapali, T3 aileleri)", step: 0.01, min: 0, max: 1 },
    ],
  },
  {
    title: "Ikili T3 + ATR (sade cekirdek)",
    fields: [
      { k: "t3_fast", t: "int", label: "Hizli T3 uzunluk", min: 2, max: 60 },
      { k: "t3_slow_mult", t: "num", label: "Yavas T3 carpani", step: 0.5, min: 1.2, max: 10 },
      { k: "t3_volume_factor", t: "num", label: "Yavas T3 hacim faktoru", step: 0.05, min: 0.1, max: 1 },
      { k: "t3_fast_vf", t: "num", label: "Hizli T3 hacim faktoru (0=yavas ile ayni)", step: 0.001, min: 0, max: 1 },
      { k: "st_period", t: "int", label: "SuperTrend ATR periyodu", min: 2, max: 100 },
      { k: "st_mult", t: "num", label: "SuperTrend x ATR onayi (0=kapali)", step: 0.1, min: 0, max: 10 },
    ],
  },
  {
    title: "SuperTrend Donusu (hedefsiz, sadece trail)",
    fields: [
      // Same two fields as the dual_t3 block above - there they are an optional
      // confirmation, here they are the entire signal. The regime gate is the
      // shared adx_min in "Giris Filtreleri"; the exit is TP x ATR = 0 plus the
      // trail settings in "Risk ve Cikis (ATR)".
      { k: "st_period", t: "int", label: "SuperTrend ATR periyodu", min: 2, max: 100 },
      { k: "st_mult", t: "num", label: "SuperTrend x ATR bant genisligi (sinyal)", step: 0.1, min: 0, max: 10 },
    ],
  },
  {
    title: "Tek Tillson T3 Yon Donusu (tek cizgi)",
    fields: [
      // The whole signal is these two fields: one T3 line, and the bar its own
      // direction changes. The third is the only optional filter - the same
      // line's curvature at the flip bar - and 0 turns it off completely. The
      // exit is TP x ATR = 0 (no target) plus the trail in "Risk ve Cikis (ATR)".
      { k: "t3_length", t: "int", label: "T3 uzunluk", min: 2, max: 60 },
      { k: "t3_volume_factor", t: "num", label: "T3 hacim faktoru", step: 0.05, min: 0.1, max: 1 },
      { k: "t3_accel_min", t: "num", label: "Min T3 ivmesi x ATR (0=kapali, yatay piyasa filtresi)", step: 0.01, min: 0, max: 1 },
    ],
  },
  {
    title: "Giris Filtreleri",
    fields: [
      { k: "adx_period", t: "int", label: "ADX periyot", min: 2, max: 100 },
      { k: "adx_min", t: "num", label: "Min ADX (0=kapali)", step: 1, min: 0, max: 60 },
      { k: "max_spread_atr", t: "num", label: "Maks spread x ATR (0=kapali)", step: 0.05, min: 0 },
      { k: "cost_rank_max", t: "num", label: "Maks maliyet yuzdeligi (0=kapali, scalp aileleri)", step: 0.05, min: 0, max: 1 },
      { k: "min_atr_ratio", t: "num", label: "Min ATR/fiyat", step: 0.0001, min: 0 },
      { k: "min_body_ratio", t: "num", label: "Min mum govdesi (0=kapali)", step: 0.05, min: 0, max: 1 },
      { k: "atr_pct_min", t: "num", label: "Min ATR yuzdeligi (0=kapali)", step: 0.05, min: 0, max: 1 },
      { k: "cooldown_sec", t: "int", label: "Bekleme (sn)", min: 0, max: 86400 },
    ],
  },
  {
    title: "Maliyet ve Kismi Kar",
    fields: [
      { k: "commission_per_lot", t: "num", label: "Komisyon (1 lot gidis-donus)", step: 0.5, min: 0 },
      { k: "partial_tp_r", t: "num", label: "Kismi kar seviyesi (xR, 0=kapali)", step: 0.25, min: 0, max: 5 },
      { k: "partial_tp_fraction", t: "num", label: "Kismi kar orani", step: 0.05, min: 0.1, max: 0.9 },
      { k: "partial2_tp_r", t: "num", label: "2. kademe kar seviyesi (xR, 0=kapali)", step: 0.25, min: 0, max: 8 },
      { k: "partial2_fraction", t: "num", label: "2. kademe orani (ilk lot uzerinden)", step: 0.05, min: 0, max: 0.9 },
    ],
  },
];

function buildField(cfg, spec) {
  let input;
  if (spec.t === "bool") {
    input = el("input", { type: "checkbox" });
    input.dataset.key = spec.k;
    input.checked = !!cfg[spec.k];
    input.addEventListener("change", () => {
      saveSymbol(cfg.symbol, { [spec.k]: input.checked }, input);
    });
    return el("div", { class: "field" }, [
      el("label", { class: "chk" }, [input, el("span", { text: spec.label })]),
    ]);
  }
  if (spec.t === "select") {
    input = el("select", {}, spec.opts.map(([v, l]) => el("option", { value: v, text: l })));
  } else {
    input = el("input", {
      type: "number", step: spec.t === "int" ? 1 : (spec.step ?? 0.01),
      min: spec.min, max: spec.max,
    });
  }
  input.dataset.key = spec.k;
  input.value = cfg[spec.k];
  input.addEventListener("change", () => {
    const raw = input.value;
    const value = spec.t === "select" ? raw : (spec.t === "int" ? parseInt(raw, 10) : parseFloat(raw));
    if (spec.t !== "select" && !isFinite(value)) { input.value = cfg[spec.k]; return; }
    saveSymbol(cfg.symbol, { [spec.k]: value }, input);
  });
  return el("div", { class: "field" }, [el("label", { text: spec.label }), input]);
}

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

function secondaryNote(cfg) {
  if (!cfg.secondary_strategy || !cfg.secondary_timeframe) {
    return "Dogrulanmis ikinci aday yok. Bir optimizasyon kosusu birincil ayarlari "
      + "uyguladiginda, farkli bir strateji ailesinden ve ayni OOS kapilarini gecen "
      + "en iyi aday buraya yazilir.";
  }
  const h = (cfg.secondary_summary || {}).holdout || {};
  const when = cfg.secondary_updated_at
    ? new Date(cfg.secondary_updated_at * 1000).toLocaleDateString("tr-TR")
    : "-";
  return `Aday: <b>${esc(STRATEGY_LABEL[cfg.secondary_strategy] || cfg.secondary_strategy)}</b>`
    + ` / ${esc(cfg.secondary_timeframe)} - skor ${num(cfg.secondary_score, 2)}`
    + ` | dokunulmamis test ${h.trades != null ? h.trades : "-"} islem`
    + ` PF ${num(h.profit_factor, 2)} net ${signed(h.net_r, 1)}R (${when}).`
    + " Acikken iki sinyal de giris uretebilir; ayni anda ters yone bakarlarsa bar atlanir.";
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

  // Strateji secimi, sinyal ic parametreleri, ATR cikis mekanigi, filtreler,
  // kismi kar - hepsi optimizer'in ayarladigi seyler. Elle mudahale edilmeyecekse
  // gorunumde gurultu; katlanir blokta duruyor, silinmedi.
  const advDetails = el("details", { class: "subgrid" });
  advDetails.appendChild(el("summary", { class: "title", text: "Ileri duzey / Strateji Parametreleri" }));
  SECTIONS.forEach((section) => {
    const grid = el("div", { class: "subgrid" }, [
      el("div", { class: "title", text: section.title }),
      el("div", { class: "form-grid" }, section.fields.map((f) => buildField(cfg, f))),
    ]);
    if (section.title === "Ikinci Sinyal (Ensemble)") {
      grid.appendChild(el("div", { class: "panel-note", "data-sec-note": cfg.symbol }));
    }
    advDetails.appendChild(grid);
  });
  body.appendChild(advDetails);

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
      el("div", { class: "field" }, [
        el("label", { text: "Saat filtresi" }),
        el("label", { class: "chk" }, [useSessions, el("span", { text: "Sadece belirtilen saatlerde islem ac" })]),
      ]),
      el("div", { class: "field" }, [el("label", { text: "Araliklar" }), buildSessionEditor(cfg)]),
      el("div", { class: "field" }, [el("label", { text: "Gunler" }), buildDayPicker(cfg)]),
      el("div", { class: "field" }, [el("label", { text: "Kapanistan X dk once kapat" }), flat]),
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
    el("button", {
      class: "btn btn-sm btn-ghost", text: "Varsayilana Don",
      onclick: async () => {
        if (!confirm(`${cfg.symbol} ayarlari varsayilana donsun mu?`)) return;
        try {
          await api(`/api/symbols/${cfg.symbol}/reset`, { method: "POST" });
          toast(`${cfg.symbol} sifirlandi`, "ok");
          cardsBuilt = false;
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

    const secNote = $(`[data-sec-note="${cfg.symbol}"]`, card);
    if (secNote) secNote.innerHTML = secondaryNote(cfg);

    const st = states[cfg.symbol] || {};
    const sess = st.session || {};
    const optAge = cfg.opt_updated_at
      ? new Date(cfg.opt_updated_at * 1000).toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" })
      : "-";
    const sig = st.signal
      ? `<span class="pill ${st.signal}">${st.signal === "buy" ? "AL" : "SAT"}${st.signal_source === "secondary" ? " (2)" : ""}</span>`
      : (st.signal_source === "conflict" ? '<span class="pill">CAPRAZ</span>' : "");
    $(".scard-live", card).innerHTML = `
      <span><b>strateji</b> ${esc(STRATEGY_LABEL[cfg.strategy] || cfg.strategy)} <span class="dim">${esc(cfg.timeframe)}</span></span>
      <span><b>seans</b> ${sess.open ? '<span class="pos">acik</span>' : '<span class="dim">kapali</span>'} ${esc(cfg.session_text)}</span>
      <span><b>lot</b> ${num(cfg.lot_mode === "risk" ? cfg.max_lot : cfg.fixed_lot, 2)}${cfg.lot_mode === "risk" ? " (risk)" : ""}</span>
      <span><b>T3</b> ${st.bars_ready ? (st.t3_rising ? '<span class="pos">yukari</span>' : '<span class="neg">asagi</span>') : "-"}</span>
      <span><b>K/D</b> ${st.k != null ? num(st.k, 0) + "/" + num(st.d, 0) : "-"}</span>
      <span><b>opt</b> <span class="opt-badge ${cfg.opt_score > 0 ? "pos" : "dim"}">${num(cfg.opt_score, 1)}</span> <span class="dim">${optAge}</span></span>
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
// this far (opt speed vs. depth). Everything below is statistical-gate
// internals nobody hand-tunes day to day; kept in OPT_SETTING_FIELDS_ADVANCED.
const OPT_SETTING_FIELDS = [
  { k: "lookback_days", label: "Gecmis penceresi (gun)", step: 10, min: 20 },
  { k: "refine_rounds", label: "Yerel iyilestirme turu", step: 1, min: 0, max: 5 },
  { k: "max_combos", label: "Maks kombinasyon", step: 100, min: 20 },
];

const OPT_SETTING_FIELDS_ADVANCED = [
  { k: "max_bars", label: "Maks bar (hiz siniri)", step: 5000, min: 2000 },
  { k: "segments", label: "Segment sayisi (son= dogrulama)", step: 1, min: 3, max: 8 },
  { k: "min_trades", label: "Min islem sayisi", step: 1, min: 5 },
  { k: "min_positive_ratio", label: "Min pozitif segment orani", step: 0.05, min: 0.3, max: 1 },
  { k: "plateau_weight", label: "Plato agirligi", step: 0.05, min: 0, max: 0.8 },
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
    const input = el("input", { type: "number", step: f.step, min: f.min, max: f.max });
    input.value = OPT_PARAMS[f.k];
    input.dataset.optKey = f.k;
    $("#opt-settings").appendChild(el("div", { class: "field" }, [el("label", { text: f.label }), input]));
  });

  $("#opt-settings-advanced").innerHTML = "";
  OPT_SETTING_FIELDS_ADVANCED.forEach((f) => {
    const input = el("input", { type: "number", step: f.step, min: f.min, max: f.max });
    input.value = OPT_PARAMS[f.k];
    input.dataset.optKey = f.k;
    $("#opt-settings-advanced").appendChild(el("div", { class: "field" }, [el("label", { text: f.label }), input]));
  });

  const grid = OPT_PARAMS.grid || {};
  $("#opt-grid").innerHTML = "";
  Object.keys(grid).forEach((key) => {
    const input = el("input", { type: "text", value: (grid[key] || []).join(", ") });
    input.dataset.gridKey = key;
    $("#opt-grid").appendChild(el("div", { class: "field" }, [el("label", { text: key }), input]));
  });
}

function renderOptPicker() {
  const box = $("#opt-picker");
  if (!box) return;
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
  const body = { grid: {} };
  $$("[data-opt-key]").forEach((i) => { body[i.dataset.optKey] = parseFloat(i.value); });
  $$("[data-grid-key]").forEach((i) => {
    const values = i.value.split(",").map((x) => parseFloat(x.trim())).filter((x) => isFinite(x));
    if (values.length) body.grid[i.dataset.gridKey] = values;
  });
  try {
    const res = await api("/api/opt/params", { method: "POST", body });
    OPT_PARAMS = res.params;
    renderOptForm();
    toast("Optimizasyon ayarlari kaydedildi", "ok");
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
  $("#btn-opt-run").disabled = job.state === "running";
  $("#btn-opt-cancel").disabled = job.state !== "running";

  // Best score first; failed symbols sink to the bottom.
  const results = (job.results || []).slice().sort((a, b) => {
    const sa = a.ok && a.best ? a.best.score : -Infinity;
    const sb = b.ok && b.best ? b.best.score : -Infinity;
    return sb - sa;
  });

  const rows = results.map((r) => {
    const tr = el("tr");
    if (!r.ok || !r.best) {
      tr.innerHTML = `<td class="sym">${esc(r.symbol)}</td><td colspan="15" class="neg">${esc(r.error || "sonuc yok")}</td>`;
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
    const incText = kept
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
      : kept ? `<span class="pill warn" title="${incText}">mevcut ayar korundu</span>`
      : r.validated ? `<span class="pill warn" title="${incText}">dogrulandi, uygulanmadi</span>`
      : `<span class="pill bad" title="${incText}">dogrulanmadi</span>`;
    tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}</td>
      <td class="dim">${esc(r.strategy || "-")}</td>
      <td class="dim">${esc(r.timeframe)}${r.exit_style ? ` <span class="dim" title="cikis modu">${r.exit_style === "trail" ? "iz" : "hdf"}</span>` : ""}</td>
      <td class="num ${r.best.score > 0 ? "pos" : "neg"}"><b>${num(r.best.score, 2)}</b></td>
      <td class="num dim">${num(r.best.positive_ratio * 100, 0)}%</td>
      <td class="num">${s.trades}</td>
      <td class="num ${s.profit_factor >= 1.2 ? "pos" : ""}">${num(s.profit_factor, 2)}</td>
      <td class="num dim">${v.profit_factor != null ? num(v.profit_factor, 2) : "-"}</td>
      <td class="num dim">${v.net_r != null ? signed(v.net_r, 1) + "R" : "-"}</td>
      <td class="num">${h.trades}</td>
      <td class="num ${h.profit_factor >= 1.1 ? "pos" : "neg"}">${num(h.profit_factor, 2)}</td>
      <td class="num ${cls(h.net_r)}"><b>${signed(h.net_r, 1)}R</b></td>
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
            await api("/api/opt/apply", {
              method: "POST",
              body: { symbol: r.symbol, params: r.best.params, score: r.best.score,
                      timeframe: r.timeframe, strategy: r.strategy },
            });
            toast(`${r.symbol} parametreleri uygulandi (${r.strategy} ${r.timeframe})`, "ok");
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
      tr.appendChild(el("td", {}, el("button", {
        class: "btn btn-sm", text: "Uygula",
        onclick: async (e) => {
          e.target.disabled = true;
          try {
            await api("/api/opt/apply", { method: "POST", body: { symbol: h.symbol, run_id: h.id } });
            toast(`${h.symbol} parametreleri uygulandi`, "ok");
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
  { k: "auto_reoptimize", label: "Bozulanlari otomatik optimize et", t: "bool" },
  { k: "reopt_on_decay", label: "Kenari dusenleri de yeniden optimize et", t: "bool" },
  { k: "prefer_strong_on_dd", label: "Gunluk kayipta guclu sembole oncelik", t: "bool" },
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
      lbl: "Global Lot Carpani", val: num(ai.risk_scale ?? 1, 2),
      foot: (ai.risk_scale ?? 1) < 1 ? "gunluk zarar nedeniyle kisildi" : "normal",
      accent: (ai.risk_scale ?? 1) < 1 ? "amber" : "green",
    },
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

  const notes = (ai.notes || []).join(" | ");
  const queue = (ai.reopt_queue || []).length
    ? ` | yeniden optimize kuyrugu: ${ai.reopt_queue.join(", ")}` : "";
  $("#ai-note").textContent = ai.enabled
    ? (notes ? notes + queue : "Tum semboller normal calisiyor." + queue)
    : "Denetleyici kapali - kararlar uygulanmiyor.";

  const aiRows = ai.symbols || [];
  const nextAiSig = aiRows.map((r) =>
    [r.symbol, r.state, r.trades, r.net, r.profit_factor, r.priority, r.effective_scale,
      r.consecutive_losses, r.quarantine_left_min, (r.blocked_hours || []).join(",")].join("|")).join(";");
  if (nextAiSig !== aiTableSig) {
    aiTableSig = nextAiSig;
    const rows = aiRows.map((r) => {
      const [pill, label] = AI_STATE[r.state] || ["off", r.state];
      const tr = el("tr");
      tr.innerHTML = `
      <td class="sym">${esc(r.symbol)}${r.enabled ? "" : ' <span class="pill off">kapali</span>'}</td>
      <td><span class="pill ${pill}">${esc(label)}</span>${r.quarantine_left_min ? ` <span class="dim mono">${r.quarantine_left_min}dk</span>` : ""}</td>
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
      <td class="dim mono" title="${Object.entries(r.hour_risk_scales || {}).map(([h, s]) => String(h).padStart(2, "0") + ":00 x" + num(s, 2)).join(", ") || "yumusak kisitlama yok"}">${(r.blocked_hours || []).map((h) => String(h).padStart(2, "0") + ":00").join(" ") || "-"}${Object.keys(r.hour_risk_scales || {}).length ? ` <span class="dim">(${Object.keys(r.hour_risk_scales).length} saat kisitli)</span>` : ""}</td>`;
      tr.appendChild(el("td", {}, r.state === "quarantine" || r.blocked_hours.length
        ? el("button", {
          class: "btn btn-sm btn-ghost", text: "Serbest birak",
          onclick: async () => {
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

  const box = $("#ai-settings");
  if (box.childElementCount !== AI_SETTING_FIELDS.length) {
    box.innerHTML = "";
    AI_SETTING_FIELDS.forEach((f) => {
      let input;
      if (f.t === "bool") {
        input = el("input", { type: "checkbox" });
        input.addEventListener("change", () => saveAI({ [f.k]: input.checked }, input));
      } else {
        input = el("input", { type: "number", step: f.t === "int" ? 1 : (f.step ?? 1), min: f.min, max: f.max });
        input.addEventListener("change", () => {
          const value = f.t === "int" ? parseInt(input.value, 10) : parseFloat(input.value);
          if (isFinite(value)) saveAI({ [f.k]: value }, input);
        });
      }
      input.dataset.aiKey = f.k;
      box.appendChild(el("div", { class: "field" }, [
        el("label", { text: f.label }),
        f.t === "bool" ? el("label", { class: "chk" }, [input, el("span", { text: "Aktif" })]) : input,
      ]));
    });
  }
  $$("[data-ai-key]", box).forEach((input) => {
    const key = input.dataset.aiKey;
    if (input === document.activeElement || !(key in settings)) return;
    if (input.type === "checkbox") input.checked = !!settings[key];
    else if (String(input.value) !== String(settings[key])) input.value = settings[key];
  });
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
  { k: "max_total_positions", label: "Maks toplam pozisyon", t: "int", min: 1, max: 50 },
  { k: "lot_multiplier", label: "Global lot carpani", t: "num", step: 0.25, min: 0.1, max: 20 },
  { k: "size_by_edge", label: "Kaniti guclu sembole buyuk lot", t: "bool" },
  { k: "daily_loss_pct", label: "Gunluk zarar limiti % (0=kapali)", t: "num", step: 0.25, min: 0 },
  { k: "daily_loss_flatten", label: "Limit asilinca acik pozisyonlari da kapat", t: "bool",
    hint: "Hesap genelindeki gunluk limit icin - ve sembol bazli 'Gunluk zarar limiti %' asilinca o "
          + "sembolun pozisyonu icin de. Kapaliysa limit(ler) sadece yeni islemi durdurur." },
  { k: "daily_profit_pct", label: "Gunluk kar hedefi % (0=kapali)", t: "num", step: 0.25, min: 0 },
  { k: "trade_all_hours", label: "Tum saatlerde islem (sembol seanslarini yoksay)", t: "bool",
    hint: "Semboller sekmesindeki seans pencerelerini ve islem gunlerini devre disi birakir. "
        + "Piyasa kapali / fiyat akmiyor kontrolu yerinde kalir. Dikkat: optimizasyon sonuclari "
        + "yalnizca seans saatlerinde olculdu, acik birakinca o rakamlar gecerli olmaz." },
  { k: "day_end_flatten_min", label: "Gun sonu kapanis (dk, 0=kapali)", t: "int", min: 0, max: 720,
    hint: "Brokerin gun sonuna (00:00) kalan son N dakikada yeni giris yok, acik pozisyonlar kapatilir. "
        + "Seans penceresinden bagimsiz calisir, tum saatlerde islem acikken de gecerlidir. Kripto dahil tum semboller." },
  { k: "close_on_stop", label: "Durdurunca pozisyonlari kapat", t: "bool" },
  { k: "autostart_bot", label: "Acilista botu baslat", t: "bool" },
  { k: "auto_reopt", label: "Otomatik periyodik yeniden optimizasyon", t: "bool" },
  { k: "auto_reopt_days", label: "Yeniden optimizasyon araligi (gun, 0=kapali)", t: "num", step: 0.5, min: 0, max: 90 },
  { k: "auto_reopt_weekday", label: "Tercih edilen gun", t: "select",
    opts: [["-1", "Farketmez"], ["0", "Pazartesi"], ["1", "Sali"], ["2", "Carsamba"],
           ["3", "Persembe"], ["4", "Cuma"], ["5", "Cumartesi"], ["6", "Pazar"]],
    hint: "Varsayilan Cumartesi: agir walk-forward piyasa sakinken kosar. Saat filtresiyle birlikte bilgisayarin yerel (Windows) saatine bakar." },
  { k: "auto_reopt_hour", label: "Tercih edilen saat (bilgisayarin yerel/Windows saati)", t: "select",
    opts: [["-1", "Farketmez"], ...Array.from({ length: 24 }, (_, h) => [String(h), `${String(h).padStart(2, "0")}:00`])] },
];

// Set-once / rarely-touched: connection plumbing and safety valves that are
// fine at their shipped defaults for a single-tier portfolio. Kept editable
// (nothing here was deleted) but tucked behind a collapsed <details> so the
// main list is the dozen dials someone actually turns day to day.
const SYS_FIELDS_ADVANCED = [
  { k: "max_scalp_positions", label: "Maks scalp pozisyon (M5, 0=ayri limit yok)", t: "int", min: 0, max: 50,
    hint: "micro_rev/burst pozisyonlarini toplam icinde ayri bir kovaya koyar, boylece bir seri scalp doldurmasi swing icin yer birakmaz." },
  { k: "max_swing_positions", label: "Maks swing pozisyon (M15+, 0=ayri limit yok)", t: "int", min: 0, max: 50 },
  { k: "block_high_cost", label: "Yuksek maliyetli girisi engelle (opsiyonel)", t: "bool" },
  { k: "max_cost_pct_of_risk", label: "Maks maliyet / risk % (engel acikken)", t: "num", step: 1, min: 5, max: 80 },
  { k: "max_margin_usage_pct", label: "Maks marj kullanimi %", t: "num", step: 1, min: 1, max: 100 },
  { k: "min_free_margin", label: "Min serbest marj", t: "num", step: 10, min: 0 },
  { k: "slippage_points", label: "Slippage (point)", t: "int", min: 0, max: 500 },
  { k: "poll_interval_sec", label: "Dongu araligi (sn)", t: "num", step: 0.5, min: 0.5 },
  { k: "opt_max_workers", label: "Maks optimizasyon paralel surec (0=otomatik)", t: "int", min: 0, max: 32,
    hint: "Zayif/paylasimli bir bulut sunucuda dusuk tut, optimizasyon calisirken canli motoru ve MT5'i yormasin." },
  { k: "mt5_terminal_path", label: "MT5 terminal yolu (terminal64.exe - hangi platform olursa)", t: "text", wide: true },
  { k: "autostart_mt5", label: "Acilista MT5 terminalini baslat (yol ayarliysa ve kapaliysa)", t: "bool" },
  { k: "autostart_mt5_wait_sec", label: "MT5 baglanti bekleme (sn)", t: "int", min: 15, max: 300 },
  { k: "backup_dir", label: "Yedek konumu (aksam otomatik yedek buraya gider)", t: "text", wide: true },
  { k: "backup_keep", label: "Tutulacak yedek sayisi", t: "int", min: 1, max: 30 },
];

function buildSysField(f) {
  let input;
  if (f.t === "bool") {
    input = el("input", { type: "checkbox" });
    input.addEventListener("change", () => saveSystem({ [f.k]: input.checked }, input));
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
  if (f.hint) field.appendChild(el("div", { class: "dim small", text: f.hint }));
  if (f.wide) field.classList.add("field-wide");
  return field;
}

function renderSystem() {
  const sys = STATE.system || {};
  const box = $("#sys-settings");

  if (!box.dataset.built) {
    box.innerHTML = "";
    SYS_FIELDS.forEach((f) => box.appendChild(buildSysField(f)));
    const details = el("details", { class: "field-wide" });
    details.appendChild(el("summary", { text: "Ileri duzey (nadiren degisir)" }));
    const advGrid = el("div", { class: "form-grid" });
    SYS_FIELDS_ADVANCED.forEach((f) => advGrid.appendChild(buildSysField(f)));
    details.appendChild(advGrid);
    box.appendChild(details);
    box.dataset.built = "1";
  }

  $$("[data-sys-key]", box).forEach((input) => {
    const key = input.dataset.sysKey;
    if (input === document.activeElement || !(key in sys)) return;
    if (input.type === "checkbox") input.checked = !!sys[key];
    else if (String(input.value) !== String(sys[key])) input.value = sys[key];
  });

  const mt5 = STATE.mt5 || {};
  const acc = STATE.account || {};
  const bot = STATE.bot || {};
  const rows = [
    ["Durum", mt5.connected ? "Bagli" : `Kopuk - ${mt5.error || ""}`],
    ["Broker", mt5.company || "-"],
    ["Hesap", `${acc.login || "-"} @ ${acc.server || "-"}`],
    ["Isim", acc.name || "-"],
    ["AutoTrading", mt5.trade_allowed ? "Acik" : "KAPALI"],
    ["Terminal build", mt5.build || "-"],
    ["Terminal saati", mt5.server_time || "-"],
    ["Ayarlanan yol", sys.mt5_terminal_path || "(bos - baglanmaz)"],
    ["Bagli terminal", mt5.path || "-"],
  ];
  $("#sys-mt5").innerHTML = rows.map(([k, v]) => `<div><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join("");

  $("#sys-bot-note").textContent =
    (bot.running ? "Islem aciyor" : bot.watching ? "Sadece izliyor - islem acmiyor" : "Motor durdu") +
    ` | dongu ${bot.cycle || 0} | son tur ${num(bot.last_cycle_ms, 0)} ms | ` +
    `${bot.last_cycle_at ? new Date(bot.last_cycle_at * 1000).toLocaleTimeString("tr-TR") : "-"}` +
    (bot.last_error ? ` | HATA: ${bot.last_error}` : "");

  const day = STATE.day || {};
  $("#sys-day-note").innerHTML = day.halted
    ? `<span class="pill bad">DURDURULDU</span> ${esc(day.halt_reason)} - devam etmek icin asagidaki butona basin`
    : `Gunluk limit normal (${signed(day.pnl_pct, 2)}%)`;
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

    const lotMode = el("select", {}, [
      el("option", { value: "fixed", text: "Sabit" }),
      el("option", { value: "risk", text: "Risk %" }),
    ]);
    lotMode.value = cfg.lot_mode || "fixed";
    lotMode.addEventListener("change", async () => {
      try {
        await api(`/api/symbols/${encodeURIComponent(cfg.symbol)}`, {
          method: "POST", body: { lot_mode: lotMode.value },
        });
        toast(`${cfg.symbol} lot modu: ${lotMode.value === "fixed" ? "sabit" : "risk %"}`, "ok");
        refresh();
      } catch (e) { toast(e.message, "err"); }
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
      <td></td><td></td><td></td>
      <td class="mono ${ok ? "" : "dim"}">${esc(cfg.resolved_symbol || "-")}</td>
      <td>${status}</td><td></td>`;
    tr.children[2].appendChild(enable);
    tr.children[3].appendChild(lotMode);
    tr.children[4].appendChild(broker);
    tr.children[7].appendChild(remove);
    body.appendChild(tr);
  });
}

function guessGroup(name) {
  const n = String(name || "").toUpperCase();
  if (/BTC|ETH|XRP|LTC|SOL|ADA|DOGE|CRYPTO/.test(n)) return "crypto";
  if (/XAU|XAG|BRENT|WTI|OIL|SILVER|GOLD|NATGAS|GAS/.test(n)) return "commodity";
  if (/GER|FRA|UK100|NAS|US30|US500|SPX|DAX|CAC|NDX|DJ|HK50|HSTECH|JPN|AUS200|NIKKEI/.test(n)) return "index";
  return "forex";
}

async function addPortfolioSymbol(symbol, brokerSymbol = "", group = "") {
  const name = String(symbol || "").trim();
  if (!name) { toast("Sembol adi yazin", "err"); return; }
  const g = group || ($("#portfolio-group") && $("#portfolio-group").value) || guessGroup(name);
  const minLotInput = $("#portfolio-minlot");
  const openInput = $("#portfolio-openhour");
  const closeInput = $("#portfolio-closehour");
  const minLot = minLotInput && minLotInput.value ? parseFloat(minLotInput.value) : null;
  const openHour = openInput && openInput.value ? openInput.value : "";
  const closeHour = closeInput && closeInput.value ? closeInput.value : "";
  try {
    const res = await api("/api/symbols", {
      method: "POST",
      body: { symbol: name, group: g, broker_symbol: brokerSymbol || "", enabled: true },
    });
    SYMBOLS = res.symbols || [];
    if (res.system) STATE.system = res.system;
    cardsBuilt = false;
    const addedSymbol = (res.config && res.config.symbol) || name.toUpperCase().replace(/ /g, "_");
    let extra = "";
    if (minLot && minLot > 0) {
      await api(`/api/symbols/${encodeURIComponent(addedSymbol)}`, {
        method: "POST", body: { lot_mode: "fixed", fixed_lot: minLot },
      });
      extra += `, min lot ${minLot} sabit referans`;
    }
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
    toast(`${addedSymbol} eklendi${extra}`, "ok");
    const symInput = $("#portfolio-symbol");
    const brInput = $("#portfolio-broker");
    if (symInput) symInput.value = "";
    if (brInput) brInput.value = "";
    if (minLotInput) minLotInput.value = "";
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

function renderLogLevels() {
  const box = $("#log-levels");
  box.innerHTML = "";
  LOG_LEVELS.forEach((level) => {
    box.appendChild(el("div", {
      class: "chip" + (logFilter.has(level) ? " sel" : ""), text: level,
      onclick: () => {
        logFilter.has(level) ? logFilter.delete(level) : logFilter.add(level);
        renderLogLevels();
        $("#logview").innerHTML = "";
        logAfter = 0;
        pollLogs();
      },
    }));
  });
}

async function pollLogs() {
  try {
    const levels = Array.from(logFilter).join(",");
    const res = await api(`/api/logs?after=${logAfter}&limit=400&levels=${levels}`);
    if (!res.entries.length) return;
    const view = $("#logview");
    const atBottom = view.scrollTop + view.clientHeight >= view.scrollHeight - 40;
    res.entries.forEach((e) => {
      logAfter = Math.max(logAfter, e.id);
      const line = el("div", { class: `logline lv-${e.level}` });
      line.innerHTML = `<span class="t">${esc(e.time)}</span><span class="l">${esc(e.level)}</span>` +
        `<span class="s">${esc(e.symbol || "")}</span><span>${esc(e.message)}</span>`;
      view.appendChild(line);
    });
    while (view.childElementCount > 1200) view.removeChild(view.firstChild);
    if ($("#log-follow").checked && atBottom) view.scrollTop = view.scrollHeight;
  } catch (_) { /* transient */ }
}

/* ----------------------------------------------------------------- poll */

async function refresh() {
  if (refreshBusy) return;
  refreshBusy = true;
  try {
    STATE = await api("/api/state");
    SYMBOLS = STATE.symbols || [];
    const pulse = $("#pulse");
    if (pulse) {
      pulse.className = "pulse on";
      setTimeout(() => { pulse.className = "pulse"; }, 250);
    }

    renderTop();
    if (activeTab === "panel") {
      renderCards(); renderCapacity(); renderExecution(); renderPositions();
      renderDayTable(); renderLive();
    }
    if (!cardsBuilt && SYMBOLS.length) buildSymbolCards();
    if (activeTab === "semboller") updateSymbolCards();
    if (activeTab === "opt") { renderOptJob(); syncOptPicker(); }
    if (activeTab === "ai") renderAI();
    if (activeTab === "sistem") renderSystem();
    if (activeTab === "log") pollLogs();
  } catch (e) {
    const pulse = $("#pulse");
    if (pulse) pulse.className = "pulse err";
  } finally {
    refreshBusy = false;
    clearTimeout(pollTimer);
    const fast = (STATE.opt || {}).state === "running";
    const hidden = typeof document !== "undefined" && document.hidden;
    const delay = hidden ? 6000 : (fast ? 1500 : 3000);
    pollTimer = setTimeout(refresh, delay);
  }
}

/* ------------------------------------------------------------------ wire */

function confirmThen(message, fn) {
  return async () => { if (confirm(message)) await fn(); };
}

function wire() {
  $$(".tab").forEach((t) => t.addEventListener("click", () => selectTab(t.dataset.tab)));

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

  $("#btn-lotmode-check").onclick = async () => {
    try {
      toast("Risk modu kontrol ediliyor...", "ok");
      const res = await api("/api/symbols/lot-mode-check");
      const flagged = (res.rows || []).filter((r) => r.flagged);
      if (!flagged.length) {
        toast("Risk modundaki semboller temiz, min lot asimi yok", "ok");
        return;
      }
      const list = flagged.map((r) => `${r.symbol} (${r.overshoot}x)`).join(", ");
      const ok = confirm(
        `Min lot risk% ayarini 2x+ asan semboller: ${list}\n\n`
        + `Bunlari Sabit lot moduna cevireyim mi?`,
      );
      if (!ok) return;
      const res2 = await api("/api/symbols-bulk", {
        method: "POST",
        body: { symbols: flagged.map((r) => r.symbol), patch: { lot_mode: "fixed" } },
      });
      SYMBOLS = res2.symbols;
      cardsBuilt = false;
      toastBulkResult(res2, "sabit lota cevrildi");
      refresh();
    } catch (e) { toast(e.message, "err"); }
  };

  $$("[data-lotmode-bulk]").forEach((btn) => {
    btn.onclick = confirmThen(
      `Tum semboller "${btn.dataset.lotmodeBulk === "fixed" ? "Sabit" : "Risk %"}" lot moduna gececek. Onayliyor musunuz?`,
      async () => {
        const lot_mode = btn.dataset.lotmodeBulk;
        const res = await api("/api/symbols-bulk", { method: "POST", body: { patch: { lot_mode } } });
        SYMBOLS = res.symbols;
        cardsBuilt = false;
        toastBulkResult(res, `lot modu ${lot_mode === "fixed" ? "sabit" : "risk %"} yapildi`);
        refresh();
      },
    );
  });

  $("#btn-maxpos-bulk").onclick = confirmThen(
    "Tum sembollerin maks pozisyonu bu deger olacak. Onayliyor musunuz?",
    async () => {
      const val = parseInt($("#portfolio-maxpos-bulk").value, 10);
      if (!(val > 0) || val > 50) { toast("Maks pozisyon 1-50 arasinda olmali", "err"); return; }
      const res = await api("/api/symbols-bulk", { method: "POST", body: { patch: { max_positions: val } } });
      SYMBOLS = res.symbols;
      cardsBuilt = false;
      toastBulkResult(res, `maks pozisyon ${val} yapildi`);
      refresh();
    },
  );

  $("#symbol-filter").addEventListener("input", applySymbolFilter);
  $("#group-filter").addEventListener("change", applySymbolFilter);
  $("#btn-opt-all").onclick = () => runOptimizer(null);
  $("#btn-opt-run").onclick = () => runOptimizer(Array.from(optSelection));
  $("#btn-opt-cancel").onclick = () => call("/api/opt/cancel");
  $("#btn-opt-save").onclick = saveOptParams;
  $("#btn-opt-reset").onclick = confirmThen("Izgara varsayilana donecek. Onayliyor musunuz?", async () => {
    const res = await api("/api/opt/params/reset", { method: "POST" });
    OPT_PARAMS = res.params;
    renderOptForm();
    toast("Varsayilana donuldu", "ok");
  });
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
  $("#btn-ai-clear").onclick = confirmThen("Tum AI kararlari sifirlanacak. Onayliyor musunuz?", async () => {
    await api("/api/ai/clear", { method: "POST" });
    toast("AI kararlari sifirlandi", "ok");
    refresh();
  });
  $("#btn-log-clear").onclick = async () => {
    await api("/api/logs/clear", { method: "POST" });
    $("#logview").innerHTML = "";
    logAfter = 0;
  };
  // A plain <a href> navigation cannot set the X-Mico-Token header the way
  // api() does for fetch calls - when a token is configured (non-localhost
  // bind) this download would otherwise 401. The gate already accepts
  // ?token= as a fallback (see create_app()'s middleware), so appending it
  // here is enough - no need to turn this into a fetch+blob download.
  if (API_TOKEN) {
    const dl = $("#btn-log-download");
    if (dl) dl.href = `/api/logs/download?token=${encodeURIComponent(API_TOKEN)}`;
  }

  renderLogLevels();
}

wire();
refresh();
