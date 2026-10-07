/* reminders.js - reminder form behaviour */
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const typeSelect = $("#reminder_type");
  const ruleRow = $("#recurrenceRow");
  const dueInput = $("#due_at");
  const form = $("#reminderForm");
  if (!typeSelect || !form) return;

  // Show the "Repeats" dropdown only for recurring reminders.
  function syncRecurrence() {
    ruleRow.hidden = typeSelect.value !== "recurring";
  }
  typeSelect.addEventListener("change", syncRecurrence);
  syncRecurrence();

  // Quick time preset buttons (+5 min, +10 min, +15 min, etc.)
  $$(".quick-time-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mins = parseInt(btn.dataset.min, 10);
      const d = new Date(Date.now() + mins * 60 * 1000);
      const pad = (n) => String(n).padStart(2, "0");
      dueInput.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
      const notifyInput = $("#notify_before_min");
      if (notifyInput) notifyInput.value = 0;
      toast(`Due time set to ${mins} min from now. Alarm will ring when time completes.`, "info", "⏰ Time Set");
    });
  });

  // Pre-fill the due date with "one hour from now" for new reminders.
  if (!dueInput.value) {
    const d = new Date(Date.now() + 60 * 60 * 1000);
    d.setMinutes(0, 0, 0);
    const pad = (n) => String(n).padStart(2, "0");
    dueInput.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  // Quick client-side check (the server validates again - never trust the browser).
  form.addEventListener("submit", (e) => {
    const title = $("#title").value.trim();
    if (!title) {
      e.preventDefault();
      toast("Please enter a title.", "error");
      $("#title").focus();
    } else if (!dueInput.value) {
      e.preventDefault();
      toast("Please choose a due date and time.", "error");
    }
  });
});
