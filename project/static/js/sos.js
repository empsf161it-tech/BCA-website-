/* sos.js - SOS countdown, cancel, location, dispatch and per-step status.
 * Loaded on every logged-in page so the floating SOS button always works. */
"use strict";

(function () {
  const overlay = $("#sosOverlay");
  if (!overlay) return;

  const COUNTDOWN_SECONDS = 5;
  const views = {
    countdown: $("#sosViewCountdown"),
    progress: $("#sosViewProgress"),
    cancelled: $("#sosViewCancelled"),
  };
  const countdownEl = $("#sosCountdown");
  const closeBtn = $("#sosCloseBtn");
  let timer = null;
  let active = false;           // true while an SOS flow is open (blocks double-triggers)

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function showView(name) {
    Object.entries(views).forEach(([key, el]) => { el.hidden = key !== name; });
  }

  /** Set one step's state: run (spinner) | ok | warn | fail, with optional new text. */
  function setStep(step, state, text) {
    const li = $(`#sosSteps li[data-step="${step}"]`);
    li.className = state;
    if (text) $("span", li).textContent = text;
  }

  function resetSteps() {
    $$("#sosSteps li").forEach((li) => { li.className = ""; });
    $("#sosResult").hidden = true;
    closeBtn.hidden = true;
  }

  function openSOS() {
    if (active) return;
    active = true;
    overlay.hidden = false;
    showView("countdown");
    let remaining = COUNTDOWN_SECONDS;
    countdownEl.textContent = remaining;
    timer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(timer);
        runSOS();
      } else {
        countdownEl.textContent = remaining;
      }
    }, 1000);
  }

  function closeSOS() {
    clearInterval(timer);
    overlay.hidden = true;
    active = false;
    // On the SOS page, reload so the "Recent SOS events" list is up to date.
    if (document.body.dataset.page === "sos") window.location.reload();
  }

  async function cancelSOS() {
    clearInterval(timer);
    await api("/api/sos/cancel", "POST", {});      // records a 'cancelled' event
    showView("cancelled");
  }

  /** Countdown finished: confirm -> location -> contacts -> dispatch -> record. */
  async function runSOS() {
    showView("progress");
    resetSteps();

    // Step 1 - the user didn't cancel, so the emergency is confirmed.
    setStep("confirmed", "ok");
    await sleep(350);

    // Step 2 - one-time location lookup (resolves with {error} if denied/unavailable).
    setStep("location", "run");
    const pos = await getPosition();
    const payload = {};
    if (pos.error) {
      setStep("location", "warn", "Location unavailable - alert sent without it");
    } else {
      Object.assign(payload, pos);
      setStep("location", "ok", `Location captured (±${Math.round(pos.accuracy)} m)`);
    }

    // Steps 3-5 happen on the server in a single request.
    setStep("contacts", "run");
    const res = await api("/api/sos", "POST", payload);

    if (!res.ok) {
      setStep("contacts", "fail", "Could not reach the server");
      setStep("dispatch", "fail", "Alert not dispatched");
      setStep("record", "fail", "Event not recorded");
      toast((res.data && res.data.error) || "SOS request failed. Call your local emergency number!", "error");
      closeBtn.hidden = false;
      return;
    }

    const d = res.data, s = d.steps;
    await sleep(350);
    setStep("contacts", s.contacts_found ? "ok" : "warn",
            s.contacts_found ? `${s.contacts_found} emergency contact(s) retrieved`
                             : "No emergency contacts saved");
    setStep("dispatch", "run");
    await sleep(450);
    setStep("dispatch", s.alerts_sent ? "ok" : "fail",
            s.alerts_sent ? `Alert dispatched to ${s.alerts_sent} contact(s)` : "Alert could not be dispatched");
    await sleep(350);
    setStep("record", s.recorded ? "ok" : "fail", `Event #${d.event_id} recorded (${d.status})`);

    // Show exactly what was "sent" (demo: logged to DB, not SMS/email).
    $("#sosMessage").textContent = d.message;           // textContent = safe from HTML injection
    const list = $("#sosRecipients");
    list.replaceChildren();
    (d.recipients || []).forEach((r) => {
      const li = document.createElement("li");
      li.textContent = `→ ${r.contact_name}${r.relationship ? " (" + r.relationship + ")" : ""} · ${r.phone} · via ${r.channel}`;
      list.appendChild(li);
    });
    $("#sosResult").hidden = false;
    closeBtn.hidden = false;
  }

  // Every element with .sos-trigger starts the flow (floating button, big buttons).
  $$(".sos-trigger").forEach((btn) => btn.addEventListener("click", openSOS));
  $("#sosCancelBtn").addEventListener("click", cancelSOS);
  $("#sosCancelledClose").addEventListener("click", closeSOS);
  closeBtn.addEventListener("click", closeSOS);
})();
