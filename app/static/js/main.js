/**
 * CloudShare – main.js
 * Client-side interactions: sidebar toggle, password visibility,
 * auto-dismiss alerts, file icon mapping.
 */

"use strict";

// ── Sidebar Toggle (mobile) ─────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  if (!sidebar) return;
  const isOpen = sidebar.classList.toggle("open");
  overlay && overlay.classList.toggle("open", isOpen);
  document.body.style.overflow = isOpen ? "hidden" : "";
}

// ── Password Visibility Toggle ──────────────────────────────────────
function togglePwVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isText = input.type === "text";
  input.type = isText ? "password" : "text";
  const icon = btn.querySelector("i");
  if (icon) {
    icon.className = isText ? "bi bi-eye" : "bi bi-eye-slash";
  }
}

// ── Auto-dismiss Flash Alerts ───────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Dismiss success / info alerts after 4 s
  document.querySelectorAll(".alert.alert-success, .alert.alert-info").forEach((el) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert && bsAlert.close();
    }, 4000);
  });

  // Animate stat numbers on dashboard
  document.querySelectorAll(".stat-number").forEach((el) => {
    const raw = el.textContent.trim();
    const num = parseFloat(raw.replace(/[^0-9.]/g, ""));
    if (!isNaN(num) && num > 0) {
      let current = 0;
      const step = num / 30;
      const suffix = raw.replace(/[0-9.]/g, "");
      const prefix = raw.match(/^[^0-9]*/)[0];
      const iv = setInterval(() => {
        current = Math.min(current + step, num);
        el.textContent = prefix + (Number.isInteger(num) ? Math.round(current) : current.toFixed(1)) + suffix;
        if (current >= num) clearInterval(iv);
      }, 30);
    }
  });
});

// ── File extension → Bootstrap Icon mapping ─────────────────────────
window.fileIconMap = {
  pdf:  "bi-file-earmark-pdf",
  doc:  "bi-file-earmark-word",
  docx: "bi-file-earmark-word",
  xls:  "bi-file-earmark-excel",
  xlsx: "bi-file-earmark-excel",
  ppt:  "bi-file-earmark-ppt",
  pptx: "bi-file-earmark-ppt",
  png:  "bi-file-earmark-image",
  jpg:  "bi-file-earmark-image",
  jpeg: "bi-file-earmark-image",
  gif:  "bi-file-earmark-image",
  bmp:  "bi-file-earmark-image",
  svg:  "bi-file-earmark-image",
  zip:  "bi-file-earmark-zip",
  tar:  "bi-file-earmark-zip",
  gz:   "bi-file-earmark-zip",
  mp3:  "bi-file-earmark-music",
  mp4:  "bi-file-earmark-play",
  mov:  "bi-file-earmark-play",
  avi:  "bi-file-earmark-play",
  mkv:  "bi-file-earmark-play",
  txt:  "bi-file-earmark-text",
  csv:  "bi-file-earmark-spreadsheet",
  json: "bi-file-earmark-code",
  xml:  "bi-file-earmark-code",
  html: "bi-file-earmark-code",
  css:  "bi-file-earmark-code",
  js:   "bi-file-earmark-code",
  py:   "bi-file-earmark-code",
  java: "bi-file-earmark-code",
  c:    "bi-file-earmark-code",
  cpp:  "bi-file-earmark-code",
};

function getFileIcon(ext) {
  return window.fileIconMap[ext.toLowerCase()] || "bi-file-earmark";
}
