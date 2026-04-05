/**
 * Jarvis AI Dashboard – Client-Side JavaScript
 * Handles live system stats, process list, and command execution.
 */

"use strict";

/* ============================================================
   Utility helpers
   ============================================================ */

/**
 * Format bytes to a human-readable string.
 * @param {number} bytes
 * @param {number} [decimals=1]
 * @returns {string}
 */
function formatBytes(bytes, decimals = 1) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/**
 * Format a timestamp as HH:MM:SS.
 * @param {number} [ts] Unix epoch seconds; defaults to now.
 * @returns {string}
 */
function formatTime(ts) {
  const d = ts ? new Date(ts * 1000) : new Date();
  return d.toLocaleTimeString("en-US", { hour12: false });
}

/**
 * Animate a numeric element from its current displayed value to target.
 * @param {HTMLElement} el
 * @param {number} target
 * @param {string} [suffix=""]
 * @param {number} [decimals=0]
 */
function animateNumber(el, target, suffix = "", decimals = 0) {
  if (!el) return;
  const current = parseFloat(el.dataset.value || el.textContent) || 0;
  const diff = target - current;
  const steps = 20;
  let step = 0;
  const timer = setInterval(() => {
    step++;
    const val = current + (diff * step) / steps;
    el.textContent = val.toFixed(decimals) + suffix;
    if (step >= steps) {
      el.textContent = target.toFixed(decimals) + suffix;
      el.dataset.value = target;
      clearInterval(timer);
    }
  }, 16);
}

/**
 * Set the width and colour-class of a progress bar fill element.
 * @param {HTMLElement} fill
 * @param {number} pct  0–100
 */
function updateProgressBar(fill, pct) {
  if (!fill) return;
  fill.style.width = Math.min(pct, 100) + "%";
  fill.classList.remove("warning", "danger");
  if (pct >= 90) fill.classList.add("danger");
  else if (pct >= 70) fill.classList.add("warning");
}

/* ============================================================
   System stats
   ============================================================ */

/**
 * Fetch /api/system and update all stat card UI elements.
 */
async function updateSystemStats() {
  try {
    const res = await fetch("/api/system");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // CPU
    const cpuEl = document.getElementById("cpu-value");
    animateNumber(cpuEl, data.cpu_percent, "%", 1);
    updateProgressBar(document.getElementById("cpu-bar"), data.cpu_percent);
    const cpuSub = document.getElementById("cpu-sub");
    if (cpuSub) cpuSub.textContent = `${data.cpu_count} logical cores`;

    // Memory
    const memPct = data.memory.percent;
    animateNumber(document.getElementById("mem-value"), memPct, "%", 1);
    updateProgressBar(document.getElementById("mem-bar"), memPct);
    const memSub = document.getElementById("mem-sub");
    if (memSub) {
      memSub.textContent =
        `${formatBytes(data.memory.used)} / ${formatBytes(data.memory.total)}`;
    }

    // Disk
    const diskPct = data.disk.percent;
    animateNumber(document.getElementById("disk-value"), diskPct, "%", 1);
    updateProgressBar(document.getElementById("disk-bar"), diskPct);
    const diskSub = document.getElementById("disk-sub");
    if (diskSub) {
      diskSub.textContent =
        `${formatBytes(data.disk.used)} / ${formatBytes(data.disk.total)}`;
    }

    // Uptime
    const uptimeEl = document.getElementById("uptime-value");
    if (uptimeEl) uptimeEl.textContent = data.uptime;

    // Network
    const netSentEl = document.getElementById("net-sent");
    const netRecvEl = document.getElementById("net-recv");
    if (netSentEl) netSentEl.textContent = formatBytes(data.network.bytes_sent);
    if (netRecvEl) netRecvEl.textContent = formatBytes(data.network.bytes_recv);

    // Last updated
    const lastEl = document.getElementById("last-updated");
    if (lastEl) lastEl.textContent = `Updated ${formatTime()}`;
  } catch (err) {
    console.warn("Failed to update system stats:", err);
  }
}

/* ============================================================
   Process list
   ============================================================ */

/**
 * Fetch /api/processes and re-render the process table body.
 */
async function updateProcessList() {
  const tbody = document.getElementById("process-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/processes?limit=20");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { processes } = await res.json();

    if (!processes || processes.length === 0) {
      tbody.innerHTML =
        `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px">
           No process data available
         </td></tr>`;
      return;
    }

    tbody.innerHTML = processes
      .map((p) => {
        const statusClass = p.status === "running"
          ? "running"
          : p.status === "sleeping" ? "sleeping" : "stopped";
        const cpuColor = p.cpu_percent > 50
          ? "var(--danger)"
          : p.cpu_percent > 20
          ? "var(--warning)"
          : "var(--accent)";

        return `<tr>
          <td class="pid">${p.pid}</td>
          <td class="name" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</td>
          <td><span class="cpu-badge" style="color:${cpuColor}">${p.cpu_percent.toFixed(1)}%</span></td>
          <td style="color:var(--text-secondary)">${p.memory_percent.toFixed(2)}%</td>
          <td><span class="status-badge ${statusClass}">${escapeHtml(p.status)}</span></td>
        </tr>`;
      })
      .join("");
  } catch (err) {
    console.warn("Failed to update process list:", err);
    tbody.innerHTML =
      `<tr><td colspan="5" style="text-align:center;color:var(--danger);padding:14px">
         Error loading processes
       </td></tr>`;
  }
}

/* ============================================================
   Command execution
   ============================================================ */

/** Append a line to the console output area. */
function appendConsole(text, type = "resp") {
  const output = document.getElementById("console-output");
  if (!output) return;

  const line = document.createElement("p");
  line.className = `console-line ${type}`;
  line.textContent = text;
  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}

/**
 * Escape special HTML characters.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * POST a command to /api/command, display prompt + response in console.
 * @param {string} command
 */
async function executeCommand(command) {
  if (!command.trim()) return;

  appendConsole(command, "cmd");
  const sendBtn = document.getElementById("send-btn");
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      appendConsole(data.error || `Error: HTTP ${res.status}`, "error");
    } else {
      appendConsole(data.response, "resp");
    }

    appendConsole(
      new Date().toLocaleTimeString("en-US", { hour12: false }),
      "ts"
    );
  } catch (err) {
    appendConsole(`Network error: ${err.message}`, "error");
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

/* ============================================================
   Clock
   ============================================================ */

function startClock() {
  const el = document.getElementById("current-time");
  if (!el) return;
  const tick = () => {
    el.textContent = new Date().toLocaleTimeString("en-US", { hour12: false });
  };
  tick();
  setInterval(tick, 1000);
}

/* ============================================================
   Auto-refresh
   ============================================================ */

let _refreshInterval = null;

function startAutoRefresh(intervalMs = 5000) {
  stopAutoRefresh();
  updateSystemStats();
  updateProcessList();
  _refreshInterval = setInterval(() => {
    updateSystemStats();
    updateProcessList();
  }, intervalMs);
}

function stopAutoRefresh() {
  if (_refreshInterval) {
    clearInterval(_refreshInterval);
    _refreshInterval = null;
  }
}

/* ============================================================
   DOM wiring
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  /* Clock */
  startClock();

  /* Initial data load + auto-refresh every 5 s */
  startAutoRefresh(5000);

  /* Command input – Enter key */
  const cmdInput = document.getElementById("cmd-input");
  if (cmdInput) {
    cmdInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const cmd = cmdInput.value.trim();
        if (cmd) {
          executeCommand(cmd);
          cmdInput.value = "";
        }
      }
    });
  }

  /* Send button */
  const sendBtn = document.getElementById("send-btn");
  if (sendBtn) {
    sendBtn.addEventListener("click", () => {
      if (!cmdInput) return;
      const cmd = cmdInput.value.trim();
      if (cmd) {
        executeCommand(cmd);
        cmdInput.value = "";
        cmdInput.focus();
      }
    });
  }

  /* Clear console button */
  const clearBtn = document.getElementById("clear-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      const output = document.getElementById("console-output");
      if (output) {
        output.innerHTML = "";
        appendConsole("Console cleared.", "info");
      }
    });
  }

  /* Welcome message */
  appendConsole("Jarvis AI Dashboard ready. Type a command below.", "info");
  appendConsole(new Date().toLocaleString(), "ts");
});
