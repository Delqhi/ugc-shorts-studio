"use strict";

// Keine externen Requests: MP4s liegen neben dieser Seite, Ergebnisse nur im Browser.
const catalog = {
  cv5: {
    baseline: "../out/short_carvertical_v5.mp4",
    v1: "previews/cv5_v1_SILENT_PREVIEW.mp4",
    v2: "previews/cv5_v2_SILENT_PREVIEW.mp4",
    v3: "previews/cv5_v3_SILENT_PREVIEW.mp4"
  },
  app: {
    baseline: "../out/short_einfachhausen_app_v4.mp4",
    v1: "previews/app_v1_SILENT_PREVIEW.mp4",
    v2: "previews/app_v2_SILENT_PREVIEW.mp4",
    v3: "previews/app_v3_SILENT_PREVIEW.mp4"
  },
  yt: {
    baseline: "../out/short_nvidia_robots_v4.mp4",
    v1: "previews/yt_v1_SILENT_PREVIEW.mp4",
    v2: "previews/yt_v2_SILENT_PREVIEW.mp4",
    v3: "previews/yt_v3_SILENT_PREVIEW.mp4"
  }
};

const $ = id => document.getElementById(id);
const KEY = "ugc-shorts-studio:hook-tests:v1";
let session = [];
let sessionId = "";
let index = 0;
let isRunning = false;
let choice = { stay: null, understood: null };
let results = [];
const availableV1 = {};
try { results = JSON.parse(localStorage.getItem(KEY) || "[]"); }
catch (_) { results = []; }

// Ein echter V1-Take wird erst angeboten, wenn daraus tatsächlich ein MP4 gerendert ist.
// Fehlende Datei = bewusst kein synthetisches Creator-Gesicht im Blindtest.
$("play").disabled = true;
Promise.all(Object.keys(catalog).map(async short => {
  try {
    const response = await fetch(catalog[short].v1, { method: "HEAD", cache: "no-store" });
    availableV1[short] = response.ok;
  } catch (_) { availableV1[short] = false; }
})).finally(() => { $("play").disabled = false; updateScores(); });

function shuffle(items) {
  // Fisher–Yates; kein Variantencode oder Dateiname wird dem Tester angezeigt.
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function updateScores() {
  const current = $("campaign").value;
  const list = $("scores");
  list.replaceChildren();
  for (const key of ["baseline", "v1", "v2", "v3"]) {
    const items = results.filter(r => r.short === current && r.variant === key);
    if (key === "v1" && !availableV1[current] && !items.length) continue;
    const yes = items.filter(r => r.stay === "yes").length;
    const understood = items.filter(r => r.understood === "yes").length;
    const li = document.createElement("li");
    li.textContent = `${key === "baseline" ? "bisheriger Hook" : key}: ${yes}/${items.length} würden bleiben · ${understood}/${items.length} verstanden`;
    list.append(li);
  }
}

function resetAnswers() {
  choice = { stay: null, understood: null };
  for (const group of ["stay", "understood"]) {
    for (const button of $(group).querySelectorAll("button")) button.setAttribute("aria-pressed", "false");
  }
  $("interpretation").value = "";
  $("next").disabled = true;
  $("vote").hidden = true;
}

function stopAtHook(force = false) {
  if (!isRunning) return;
  $("progress").style.width = `${Math.min(100, ($("video").currentTime / 1.5) * 100)}%`;
  if (!force && $("video").currentTime < 1.5) return;
  isRunning = false;
  $("video").pause();
  $("vote").hidden = false;
  $("play").disabled = false;
  $("play").textContent = "1,5 s erneut sehen";
  $("status").textContent = "Erster Impuls zählt. Nicht raten, welcher Code hinter dem Clip steckt.";
  if (matchMedia("(max-width: 860px)").matches) $("vote").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function playCurrent() {
  if (!session.length) {
    startSession();
    return;
  }
  if (index >= session.length) return;
  resetAnswers();
  const trial = session[index];
  const video = $("video");
  video.pause();
  isRunning = false;
  if (!video.src.endsWith(trial.path)) video.src = trial.path;
  video.muted = true;
  video.playsInline = true;
  try {
    video.currentTime = 0;
    await video.play();
    isRunning = true;
    $("mask").classList.add("hidden");
    $("play").disabled = true;
    $("status").textContent = "Jetzt sofort urteilen: Würdest du weiterschauen?";
    if (matchMedia("(max-width: 860px)").matches) $("video").scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (err) {
    isRunning = false;
    $("play").disabled = false;
    $("mask").classList.remove("hidden");
    $("status").textContent = `Playback blockiert: ${err.message}. Klicke erneut auf Start.`;
  }
}

function startSession() {
  const short = $("campaign").value;
  session = shuffle(Object.entries(catalog[short])
    .filter(([variant]) => variant !== "v1" || availableV1[short])
    .map(([variant, path]) => ({ short, variant, path })));
  sessionId = (globalThis.crypto && crypto.randomUUID) ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  index = 0;
  $("counter").textContent = `Clip 1 / ${session.length} · Reihenfolge zufällig`;
  $("stage-number").textContent = `01 / ${String(session.length).padStart(2, "0")}`;
  $("play").textContent = "1,5 s ansehen";
  $("progress").style.width = "0";
  resetAnswers();
  playCurrent();
}

function nextTrial() {
  if (choice.stay === null || choice.understood === null || !session[index]) return;
  results.push({
    tested_at: new Date().toISOString(),
    session_id: sessionId,
    short: session[index].short,
    variant: session[index].variant,
    stay: choice.stay,
    understood: choice.understood,
    interpretation: $("interpretation").value.trim()
  });
  try { localStorage.setItem(KEY, JSON.stringify(results)); }
  catch (_) { $("status").textContent = "Lokaler Speicher gesperrt; CSV vor dem Schließen exportieren."; }
  updateScores();
  index += 1;
  resetAnswers();
  $("progress").style.width = "0";
  $("mask").classList.remove("hidden");
  $("video").pause();
  $("video").removeAttribute("src");
  $("video").load();
  if (index >= session.length) {
    $("counter").textContent = "Durchlauf abgeschlossen · exportiere die Stimmen";
    $("stage-number").textContent = `${String(index).padStart(2, "0")} / ${String(index).padStart(2, "0")}`;
    $("play").textContent = "Nächsten Durchlauf starten";
    $("status").textContent = "Mini-Stichprobe, kein Nachweis für Viralität. Exportiere die CSV und teste mit weiteren Personen.";
    session = [];
    return;
  }
  $("counter").textContent = `Clip ${index + 1} / ${session.length} · Reihenfolge zufällig`;
  $("stage-number").textContent = `${String(index + 1).padStart(2, "0")} / ${String(session.length).padStart(2, "0")}`;
  $("play").textContent = "Nächsten Hook ansehen";
  $("status").textContent = "Nächster Clip steht bereit.";
}

function csvCell(value) {
  const text = String(value ?? "");
  const safe = /^[=+@-]/.test(text) ? `'${text}` : text; // keine Tabellen-Formeln aus Freitext
  return `"${safe.replaceAll('"', '""')}"`;
}
function exportResults() {
  if (!results.length) { $("status").textContent = "Noch keine Antworten zum Exportieren."; return; }
  const keys = ["tested_at", "session_id", "short", "variant", "stay", "understood", "interpretation"];
  const csv = [keys.join(","), ...results.map(r => keys.map(k => csvCell(r[k])).join(","))].join("\r\n") + "\r\n";
  const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `ugc-hook-blindtest-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("video").addEventListener("timeupdate", () => stopAtHook());
$("video").addEventListener("ended", () => stopAtHook(true));
$("video").addEventListener("error", () => { isRunning = false; $("play").disabled = false; $("status").textContent = "Datei fehlt. Erzeuge Previews mit tools/render_hook_trials.py --all."; });
$("play").addEventListener("click", playCurrent);
$("restart").addEventListener("click", startSession);
$("campaign").addEventListener("change", () => { session = []; index = 0; isRunning = false; $("video").pause(); $("video").removeAttribute("src"); $("video").load(); $("mask").classList.remove("hidden"); $("vote").hidden = true; $("play").textContent = "Durchlauf starten"; $("counter").textContent = "Noch kein Durchlauf"; $("stage-number").textContent = "— / 3"; updateScores(); });
for (const group of ["stay", "understood"]) {
  $(group).addEventListener("click", event => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    choice[group] = button.dataset.value;
    for (const item of $(group).querySelectorAll("button")) item.setAttribute("aria-pressed", String(item === button));
    $("next").disabled = choice.stay === null || choice.understood === null;
  });
}
$("next").addEventListener("click", nextTrial);
$("export").addEventListener("click", exportResults);
updateScores();
