/* app.js - shared helpers + notification polling (loaded on every page) */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const csrfToken = ($('meta[name="csrf-token"]') || {}).content || "";
const isLoggedIn = document.body.dataset.auth === "1";

/** Escape text before putting it in innerHTML (we mostly use textContent instead). */
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

/** Small pop-up message in the top-right corner. */
function toast(message, type = "info", title = "") {
  const box = $("#toasts");
  if (!box) return;
  const el = document.createElement("div");
  el.className = "toast " + type;
  if (title) {
    const t = document.createElement("strong");
    t.textContent = title;
    el.appendChild(t);
  }
  el.appendChild(document.createTextNode(message));
  box.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

/** fetch() wrapper: sends JSON + CSRF header, always resolves to {ok, status, data}. */
async function api(url, method = "GET", body = null) {
  const options = { method, headers: { "X-CSRF-Token": csrfToken }, credentials: "same-origin" };
  if (body !== null) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(url, options);
    let data = {};
    try { data = await res.json(); } catch (e) { /* non-JSON response */ }
    return { ok: res.ok && data.ok !== false, status: res.status, data };
  } catch (err) {
    return { ok: false, status: 0, data: { error: "Network error. Is the server running?" } };
  }
}

/** Copy text to the clipboard (with a fallback for older browsers). */
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }
}

/** One-time geolocation request. Resolves to {latitude, longitude, accuracy} or {error}.
 *  Never rejects - so SOS keeps working even if permission is denied. */
function getPosition(timeoutMs = 8000) {
  return new Promise((resolve) => {
    if (!("geolocation" in navigator)) {
      resolve({ error: "Geolocation is not supported by this browser." });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      }),
      (err) => resolve({
        error: err.code === 1 ? "Location permission was denied."
             : err.code === 3 ? "Location request timed out."
             : "Location is unavailable.",
      }),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 0 }
    );
  });
}

/* ---------- Generic UI wiring ---------- */
document.addEventListener("DOMContentLoaded", () => {
  // Mobile sidebar toggle
  const sidebar = $("#sidebar"), scrim = $("#scrim"), menuBtn = $("#menuBtn");
  if (sidebar && menuBtn) {
    const toggle = (open) => {
      sidebar.classList.toggle("open", open);
      scrim.classList.toggle("show", open);
    };
    menuBtn.addEventListener("click", () => toggle(!sidebar.classList.contains("open")));
    scrim.addEventListener("click", () => toggle(false));
  }

  // Confirm dialogs: <form data-confirm="Are you sure?">
  document.addEventListener("submit", (e) => {
    const msg = e.target.dataset ? e.target.dataset.confirm : null;
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // Auto-hide flash messages after a while
  $$(".flashes .alert").forEach((el) => setTimeout(() => {
    el.style.transition = "opacity .5s"; el.style.opacity = "0";
    setTimeout(() => el.remove(), 500);
  }, 7000));

  if (isLoggedIn) initNotifications();
});

/* ---------- Notifications & Alarms (poll every 5 s) ---------- */
const POLL_MS = 5000;
// IDs already shown in this browser session -> prevents duplicate pop-ups.
const shown = new Set(JSON.parse(sessionStorage.getItem("shownNotifs") || "[]"));

function rememberShown(id) {
  shown.add(id);
  sessionStorage.setItem("shownNotifs", JSON.stringify(Array.from(shown)));
}

function initNotifications() {
  const btn = $("#enableAlertsBtn");
  if (btn && "Notification" in window && Notification.permission === "default") {
    btn.hidden = false;
    btn.addEventListener("click", async () => {
      const result = await Notification.requestPermission();
      btn.hidden = true;
      toast(result === "granted" ? "Browser alerts enabled." : "Browser alerts blocked; in-app alarms still work.",
            result === "granted" ? "success" : "info");
    });
  }

  // Wire test alarm button
  const testBtn = $("#testAlarmBtn");
  if (testBtn) {
    testBtn.addEventListener("click", () => {
      unlockAudio();
      playAlarmSound();
      toast("Alarm sound is playing! That's what you will hear when time completes.", "success", "🔊 Alarm Test");
    });
  }

  // Wire alarm modal dismiss button
  const dismissBtn = $("#alarmDismissBtn");
  if (dismissBtn) {
    dismissBtn.addEventListener("click", () => {
      const modal = $("#alarmModal");
      if (modal) modal.hidden = true;
    });
  }

  pollNotifications();
  setInterval(pollNotifications, POLL_MS);
}

function showAlarmModal(title, dueAt) {
  const modal = $("#alarmModal");
  if (!modal) return;
  const titleEl = $("#alarmTitle");
  const subEl = $("#alarmSubtext");
  if (titleEl) titleEl.textContent = title;
  if (subEl) subEl.textContent = `Scheduled time (${dueAt}) has completed!`;
  modal.hidden = false;
}

async function pollNotifications() {
  const res = await api("/api/notifications");
  if (!res.ok) return;
  const items = res.data.notifications || [];
  renderNotificationList(items);

  let playAlarm = false;
  let playChime = false;

  for (const n of items) {
    // Only 'pending' ones haven't been delivered to the browser yet.
    if (n.status !== "pending" || shown.has(n.notification_id)) continue;
    rememberShown(n.notification_id);

    if (n.is_due_alarm) {
      // The scheduled time (e.g. 5 minutes) is completed -> Trigger FULL ALARM!
      playAlarm = true;
      showAlarmModal(n.title, n.due_at);
      const text = `Time's up! Completed for: ${n.due_at}`;
      toast(text, "reminder", "⏰ ALARM: " + n.title);
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification("⏰ ALARM: " + n.title, {
          body: `Time is up! Scheduled for ${n.due_at}`,
          tag: "alarm-" + n.notification_id,
          silent: true
        });
      }
    } else {
      // Early notice before due time
      playChime = true;
      const text = `Upcoming at ${n.due_at}`;
      toast(text, "info", "🔔 Upcoming: " + n.title);
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification("Upcoming: " + n.title, { body: text, tag: "reminder-" + n.notification_id, silent: true });
      }
    }
    api(`/api/notifications/${n.notification_id}/ack`, "POST");
  }

  // Trigger sound (Alarm takes precedence if both arrived)
  if (playAlarm) {
    playAlarmSound();
  } else if (playChime) {
    playChimeSound();
  }
}

/* ---------- Audio Engine: Digital Alarm & Chimes ---------- */
let audioCtx = null;
let soundWaiting = null;   // "alarm" | "chime" if blocked by browser autoplay policy

function getAudioContext() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) audioCtx = new Ctx();
  return audioCtx;
}

/** Browsers only allow audio after a user gesture, so unlock on the first click/key. */
function unlockAudio() {
  const ctx = getAudioContext();
  if (!ctx) return;
  const finish = () => {
    if (soundWaiting === "alarm") { soundWaiting = null; playDigitalAlarm(ctx); }
    else if (soundWaiting === "chime") { soundWaiting = null; playChimeNotes(ctx); }
  };
  if (ctx.state === "suspended") ctx.resume().then(finish).catch(() => {});
  else finish();
}
["click", "keydown", "touchstart"].forEach((evt) =>
  document.addEventListener(evt, unlockAudio, { once: true, passive: true }));

/** Classic digital alarm tone: 3 bursts of 3 sharp beeps (~2.2 seconds). */
function playDigitalAlarm(ctx) {
  const start = ctx.currentTime + 0.05;
  const bursts = [0, 0.7, 1.4]; // 3 bursts
  bursts.forEach((burstOffset) => {
    [0, 0.12, 0.24].forEach((beepOffset) => {
      const t = start + burstOffset + beepOffset;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();

      osc.type = "square";
      osc.frequency.setValueAtTime(960, t); // Crisp 960Hz digital alarm pitch

      // Filter to shape raw square wave into realistic digital watch/timer buzzer
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(2600, t);

      // Sharp, distinct beep envelope
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.linearRampToValueAtTime(0.35, t + 0.015);
      gain.gain.setValueAtTime(0.35, t + 0.075);
      gain.gain.linearRampToValueAtTime(0.0001, t + 0.09);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc.start(t);
      osc.stop(t + 0.095);
    });
  });
}

/** Gentle two-note chime for early notifications. */
function playChimeNotes(ctx) {
  const start = ctx.currentTime + 0.02;
  [[880, 0], [1175, 0.28]].forEach(([freq, offset]) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, start + offset);
    gain.gain.exponentialRampToValueAtTime(0.35, start + offset + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + offset + 0.6);
    osc.connect(gain).connect(ctx.destination);
    osc.start(start + offset);
    osc.stop(start + offset + 0.65);
  });
}

function playAlarmSound() {
  const ctx = getAudioContext();
  if (!ctx) return;
  if (ctx.state === "running") {
    playDigitalAlarm(ctx);
    return;
  }
  soundWaiting = "alarm";
  ctx.resume().then(() => {
    if (soundWaiting === "alarm") { soundWaiting = null; playDigitalAlarm(ctx); }
  }).catch(() => {});
}

function playChimeSound() {
  const ctx = getAudioContext();
  if (!ctx) return;
  if (ctx.state === "running") {
    playChimeNotes(ctx);
    return;
  }
  soundWaiting = "chime";
  ctx.resume().then(() => {
    if (soundWaiting === "chime") { soundWaiting = null; playChimeNotes(ctx); }
  }).catch(() => {});
}

function renderNotificationList(items) {
  const list = $("#notifList");
  if (!list) return;
  list.replaceChildren();
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No notifications yet. They appear when a reminder is about to be due.";
    list.appendChild(li);
    return;
  }
  for (const n of items) {
    const li = document.createElement("li");
    if (n.status === "pending") li.className = "new";
    const icon = document.createElement("span");
    icon.className = "notif-icon";
    icon.textContent = "🔔";
    const body = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = n.title;                    // textContent = automatically escaped
    const meta = document.createElement("small");
    meta.className = "muted";
    meta.textContent = `Due ${n.due_at} · notified for ${n.scheduled_at}`;
    body.append(title, meta);
    li.append(icon, body);
    list.appendChild(li);
  }
}
