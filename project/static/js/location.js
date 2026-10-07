/* location.js - on-demand location sharing (no continuous tracking).
 * Works with every .loc-widget on the page (dashboard card + location page). */
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  $$(".loc-widget").forEach((widget) => {
    const btn = $(".loc-btn", widget);
    const out = $(".loc-result", widget);
    if (!btn || !out) return;

    function showError(message) {
      out.className = "loc-result error";
      out.textContent = message;
      out.hidden = false;
    }

    btn.addEventListener("click", async () => {
      btn.disabled = true;
      const original = btn.textContent;
      btn.textContent = "Locating…";
      out.hidden = true;

      // Single, user-initiated lookup (getCurrentPosition - never watchPosition).
      const pos = await getPosition(10000);
      if (pos.error) {
        showError(pos.error + " You can allow location access in your browser settings and try again.");
      } else {
        // Server re-validates coordinates and builds the map link.
        const res = await api("/api/location", "POST", pos);
        if (!res.ok) {
          showError((res.data && res.data.error) || "Could not create the location link.");
        } else {
          renderResult(res.data);
        }
      }
      btn.disabled = false;
      btn.textContent = original;
    });

    function renderResult(d) {
      out.className = "loc-result";
      out.replaceChildren();

      const title = document.createElement("strong");
      title.textContent = "✔ Location captured";
      const info = document.createElement("div");
      info.className = "muted";
      info.textContent = `${d.latitude.toFixed(5)}, ${d.longitude.toFixed(5)}` +
        (d.accuracy != null ? ` · accuracy ±${Math.round(d.accuracy)} m` : "");

      const row = document.createElement("div");
      row.className = "loc-link";
      const input = document.createElement("input");
      input.type = "text";
      input.readOnly = true;
      input.value = d.link;
      input.setAttribute("aria-label", "Map link");
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "btn btn-soft btn-sm";
      copy.textContent = "Copy Link";
      copy.addEventListener("click", async () => {
        const ok = await copyText(d.link);
        toast(ok ? "Link copied to clipboard." : "Could not copy - select the link and copy it manually.",
              ok ? "success" : "error");
      });
      const open = document.createElement("a");
      open.className = "btn btn-ghost btn-sm";
      open.href = d.link;
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      open.textContent = "Open map";
      row.append(input, copy, open);

      out.append(title, info, row);
      out.hidden = false;
    }
  });
});
