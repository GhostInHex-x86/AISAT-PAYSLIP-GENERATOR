/* ══════════════════════════════════════════════════════════
   AISAT Payslip Generator — dashboard.js
   SSE-based real-time progress + drag-and-drop upload
   ══════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {

  /* ── Element refs ── */
  const dropZone      = document.getElementById("drop-zone");
  const fileInput     = document.getElementById("excel-file");
  const dropText      = document.getElementById("drop-text");
  const fileName      = document.getElementById("file-name");
  const generateBtn   = document.getElementById("generate-btn");

  const uploadCard    = document.getElementById("upload-card");
  const progressCard  = document.getElementById("progress-card");

  const progressFill  = document.getElementById("progress-fill");
  const progressPct   = document.getElementById("progress-pct");
  const progressLabel = document.getElementById("progress-label");
  const logPanel      = document.getElementById("log-panel");

  const downloadSec   = document.getElementById("download-section");
  const downloadBtn   = document.getElementById("download-btn");
  const downloadInfo  = document.getElementById("download-info-text");

  /* ── Drag-and-drop ── */
  ["dragenter", "dragover"].forEach(evt =>
    dropZone.addEventListener(evt, e => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    })
  );
  ["dragleave", "dragend", "drop"].forEach(evt =>
    dropZone.addEventListener(evt, () => dropZone.classList.remove("drag-over"))
  );

  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) applyFile(file);
  });

  /* Clicking anywhere in the zone triggers the hidden file input */
  dropZone.addEventListener("click", e => {
    if (e.target !== fileInput) fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) applyFile(fileInput.files[0]);
  });

  function applyFile(file) {
    // Validate extension
    if (!/\.(xlsx|xls)$/i.test(file.name)) {
      showUploadError("Please select an Excel file (.xlsx or .xls).");
      return;
    }

    // Update DataTransfer so the input reflects the dragged file
    if (file !== fileInput.files[0]) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
    }

    dropText.classList.add("hidden");
    fileName.textContent = "📄 " + file.name;
    fileName.classList.remove("hidden");
    dropZone.classList.add("has-file");
    generateBtn.disabled = false;
  }

  function showUploadError(msg) {
    const div = document.createElement("div");
    div.className = "alert alert-error";
    div.textContent = msg;
    uploadCard.insertBefore(div, uploadCard.children[1]);
    setTimeout(() => div.remove(), 5000);
  }

  /* ── Generate button ── */
  generateBtn.addEventListener("click", async () => {
    if (!fileInput.files[0]) return;

    // Reset progress UI
    resetProgress();
    progressCard.classList.remove("hidden");
    progressCard.scrollIntoView({ behavior: "smooth", block: "start" });

    generateBtn.disabled = true;
    generateBtn.textContent = "⏳ Uploading…";

    // POST the file
    const formData = new FormData();
    formData.append("excel_file", fileInput.files[0]);

    let jobId;
    try {
      const resp = await fetch("/generate", { method: "POST", body: formData });
      const data = await resp.json();
      if (data.error) {
        appendLog("✗ " + data.error, "error");
        generateBtn.disabled = false;
        generateBtn.textContent = "⚡ Generate Payslips";
        return;
      }
      jobId = data.job_id;
    } catch (err) {
      appendLog("✗ Upload failed: " + err.message, "error");
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Payslips";
      return;
    }

    generateBtn.textContent = "⏳ Generating…";
    appendLog("⚡ Starting generation…", "info");
    connectSSE(jobId);
  });

  /* ── SSE ── */
  function connectSSE(jobId) {
    const evtSrc = new EventSource("/progress/" + jobId);

    evtSrc.onmessage = e => {
      let data;
      try { data = JSON.parse(e.data); } catch { return; }

      if (data.keepalive) return;

      // Update progress bar
      if (typeof data.progress === "number") {
        setProgress(data.progress);
      }

      // Append log line
      if (data.log) {
        const type = data.log.startsWith("✓") || data.log.startsWith("✅") ? "success"
                   : data.log.startsWith("⚠")                             ? "warning"
                   : data.log.startsWith("✗")                             ? "error"
                   : "info";
        appendLog(data.log, type);
      }

      // Completion
      if (data.done) {
        evtSrc.close();
        generateBtn.disabled = false;
        generateBtn.textContent = "⚡ Generate Payslips";
        progressLabel.textContent = "Complete!";

        if (!data.error) {
          downloadBtn.href = "/download/" + jobId;
          const name = data.zip_filename || "payslips.zip";
          downloadBtn.textContent = "⬇ Download " + name;
          downloadInfo.textContent = name + " is ready.";
          downloadSec.classList.remove("hidden");
        }
      }
    };

    evtSrc.onerror = () => {
      evtSrc.close();
      appendLog("⚠ Connection lost. Refresh and try again.", "warning");
      generateBtn.disabled = false;
      generateBtn.textContent = "⚡ Generate Payslips";
    };
  }

  /* ── UI helpers ── */
  function setProgress(pct) {
    progressFill.style.width = pct + "%";
    progressPct.textContent = pct + "%";
    progressLabel.textContent = pct < 100 ? "Generating payslips…" : "Finalising ZIP…";
  }

  function appendLog(message, type = "info") {
    // Remove placeholder if present
    const ph = logPanel.querySelector(".log-placeholder");
    if (ph) ph.remove();

    const line = document.createElement("div");
    line.className = "log-line log-" + type;
    line.textContent = message;
    logPanel.appendChild(line);

    // Auto-scroll to bottom
    logPanel.scrollTop = logPanel.scrollHeight;
  }

  function resetProgress() {
    progressFill.style.width = "0%";
    progressPct.textContent = "0%";
    progressLabel.textContent = "Starting…";
    logPanel.innerHTML = '<div class="log-placeholder">Generation log will appear here…</div>';
    downloadSec.classList.add("hidden");
  }
});