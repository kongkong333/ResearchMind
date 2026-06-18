const settingsFieldIds = ["apiKey", "modelName", "baseUrl", "reportDir"];
const MAX_RESULTS_LIMIT = 20;

let activeRunId = null;
let pollHandle = null;
let analysisStarted = false;
let draftSelectionRunId = null;
let draftSelectedSourceIds = null;

function syncDraftSelection(run) {
  if (!run || !run.run_id) {
    draftSelectionRunId = null;
    draftSelectedSourceIds = null;
    return [];
  }

  if (draftSelectionRunId !== run.run_id) {
    draftSelectionRunId = run.run_id;
    draftSelectedSourceIds = null;
  }

  draftSelectedSourceIds = window.ResearchSelection.normalizeSelectionDraft(run, draftSelectedSourceIds);
  return draftSelectedSourceIds;
}

function updateDraftSelectionFromInput(input) {
  const sourceId = input.getAttribute("data-paper-id");
  if (!sourceId) {
    return;
  }
  draftSelectedSourceIds = window.ResearchSelection.toggleSelection(
    draftSelectedSourceIds,
    sourceId,
    input.checked,
  );
}

function formatPublishedDate(paper) {
  const publishedAt = typeof paper.published_at === "string" ? paper.published_at.trim() : "";
  if (publishedAt) {
    const parts = publishedAt.split("-");
    if (parts.length === 3) {
      const [year, month, day] = parts;
      return `${year}年${Number(month)}月${Number(day)}日`;
    }
  }
  if (paper.year) {
    return `${paper.year}年`;
  }
  return "未知";
}

function formatDateValueForDisplay(isoValue) {
  const normalized = String(isoValue || "").trim();
  const match = normalized.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return "";
  }
  const [, year, month, day] = match;
  return `${year.slice(2)}/${month}/${day}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeDateInputValue(rawValue) {
  const normalized = String(rawValue || "").trim();
  if (!normalized) {
    return { iso: "", display: "" };
  }

  const match = normalized.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/);
  if (!match) {
    return { iso: "", display: normalized };
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return { iso: "", display: normalized };
  }

  const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  return {
    iso,
    display: formatDateValueForDisplay(iso),
  };
}

function statusLabel(status) {
  if (status === "completed") return "已完成";
  if (status === "running") return "进行中";
  if (status === "failed") return "失败";
  return "等待中";
}

function meterWidth(stage) {
  if (stage.total && stage.total > 0) {
    return Math.min(100, Math.round((stage.current / stage.total) * 100));
  }
  return stage.status === "completed" ? 100 : 0;
}

function renderStages(stages) {
  const grid = document.getElementById("stage-grid");
  grid.innerHTML = stages.map((stage) => `
    <article class="stage-card stage-${stage.status}">
      <div class="stage-top">
        <h3>${stage.stage_label}</h3>
        <span class="badge">${statusLabel(stage.status)}</span>
      </div>
      <p>${stage.message || "等待开始..."}</p>
      <div class="meter"><span style="width:${meterWidth(stage)}%"></span></div>
    </article>
  `).join("");
}

function renderResult(run) {
  const panel = document.getElementById("result-panel");
  const selectedSourceIds = syncDraftSelection(run);
  const title = run.status === "completed"
    ? "报告已生成"
    : run.status === "failed"
      ? "运行失败"
      : "准备开始";
  const paperCards = (run.papers || []).map((paper, index) => {
    const keywords = Array.isArray(paper.keywords) && paper.keywords.length
      ? paper.keywords
      : [];
    const keywordChips = keywords.length
      ? keywords.map((keyword) => `<span class="paper-chip">${escapeHtml(keyword)}</span>`).join("")
      : '<span class="paper-chip paper-chip-muted">暂无关键词</span>';
    const publicationDate = formatPublishedDate(paper);
    const venue = paper.venue ? escapeHtml(paper.venue) : "未知期刊/会议";
    const translatedTitle = typeof paper.title_zh === "string" ? paper.title_zh.trim() : "";
    return `
      <article class="paper-card">
        <label class="paper-check">
          <input type="checkbox" data-paper-id="${paper.source_id}" ${selectedSourceIds.includes(paper.source_id) ? "checked" : ""}>
          <span>纳入分析</span>
        </label>
        <div class="paper-card-head">
          <h3>${index + 1}. ${paper.title || "未命名论文"}</h3>
          <span class="paper-date">${publicationDate}</span>
        </div>
        ${translatedTitle ? `<div class="paper-title-zh">${escapeHtml(translatedTitle)}</div>` : ""}
        <div class="paper-meta-row">
          <span class="paper-venue">${venue}</span>
        </div>
        <div class="paper-chip-list">${keywordChips}</div>
      </article>
    `;
  }).join("");
  const reportLine = run.latest_report_path
    ? `<div>报告文件：<code>${run.latest_report_path}</code></div>`
    : "";
  const artifactLine = run.report_artifact_path
    ? `<div>归档文件：<code>${run.report_artifact_path}</code></div>`
    : "";
  const errors = run.errors && run.errors.length
    ? `<div class="error-list">${run.errors.map((error) => `<p>${error}</p>`).join("")}</div>`
    : "";
  const canConfirm = (run.status === "awaiting_selection" || run.status === "running") && (run.papers || []).length;
  const actionRow = canConfirm
    ? `
      <div class="analysis-actions">
        <button id="confirmAnalysisButton" type="button">确认并开始分析</button>
      </div>
    `
    : "";

  panel.innerHTML = `
    <p class="eyebrow">执行结果</p>
    <h2>${title}</h2>
    <p class="result-summary ${run.status === "pending" ? "status-idle" : ""}">${run.current_message || "填写主题后即可开始生成。"}</p>
    <details class="paper-overview" ${(run.papers || []).length ? "open" : ""}>
      <summary class="section-head paper-overview-summary">
        <p class="eyebrow">论文概述</p>
        <span class="section-note">${(run.papers || []).length ? `已抓取 ${(run.papers || []).length} 篇论文，展开后可下滑查看` : "等待抓取结果"}</span>
      </summary>
      <div class="paper-grid-scroll">
      <div class="paper-grid">
        ${paperCards || '<div class="empty-state">暂无论文概述。</div>'}
      </div>
      </div>
    </details>
    ${actionRow}
    <div class="result-meta">
      ${reportLine}
      ${artifactLine}
    </div>
    ${errors}
  `;

  const confirmButton = document.getElementById("confirmAnalysisButton");
  if (confirmButton) {
    confirmButton.addEventListener("click", startAnalysisFromSelection);
  }
  document.querySelectorAll('.paper-check input[type="checkbox"]').forEach((input) => {
    input.addEventListener("change", () => updateDraftSelectionFromInput(input));
  });
}

async function loadSettings() {
  const response = await fetch("/settings");
  const settings = await response.json();
  document.getElementById("apiKey").value = settings.openai_api_key || "";
  document.getElementById("modelName").value = settings.openai_model || "";
  document.getElementById("baseUrl").value = settings.openai_base_url || "";
  document.getElementById("reportDir").value = settings.report_output_dir || "reports";
}

async function saveSettings() {
  const hint = document.getElementById("saveHint");
  hint.textContent = "正在保存...";
  const payload = {
    openai_api_key: document.getElementById("apiKey").value.trim(),
    openai_model: document.getElementById("modelName").value.trim(),
    openai_base_url: document.getElementById("baseUrl").value.trim(),
    report_output_dir: document.getElementById("reportDir").value.trim() || "reports",
  };
  await fetch("/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  hint.textContent = "已自动保存";
}

async function fetchRun(runId) {
  const response = await fetch(`/research-runs/${runId}`);
  const payload = await response.json();
  renderStages(payload.stages || []);
  renderResult(payload);
  if (payload.status === "completed" || payload.status === "failed" || payload.status === "awaiting_selection") {
    window.clearInterval(pollHandle);
    pollHandle = null;
    document.getElementById("runButton").disabled = false;
    analysisStarted = false;
  }
}

async function startAnalysisFromSelection() {
  if (!activeRunId || analysisStarted) {
    return;
  }
  analysisStarted = true;
  const selectedSourceIds = Array.isArray(draftSelectedSourceIds)
    ? [...draftSelectedSourceIds]
    : Array.from(document.querySelectorAll('.paper-check input[type="checkbox"]:checked'))
      .map((input) => input.getAttribute("data-paper-id"))
      .filter(Boolean);

  if (!selectedSourceIds.length) {
    analysisStarted = false;
    renderResult({
      status: "awaiting_selection",
      current_message: "请至少勾选一篇论文后再开始分析。",
      papers: [],
      selected_source_ids: [],
      latest_report_path: "",
      report_artifact_path: "",
      errors: [],
    });
    return;
  }

  await fetch(`/research-runs/${activeRunId}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      selected_source_ids: selectedSourceIds,
      openai_api_key: document.getElementById("apiKey").value.trim(),
      openai_model: document.getElementById("modelName").value.trim(),
      openai_base_url: document.getElementById("baseUrl").value.trim(),
    }),
  });
}

async function startRun() {
  const topic = document.getElementById("topicInput").value.trim();
  const startDateField = document.getElementById("startDatePicker");
  const endDateField = document.getElementById("endDatePicker");
  const normalizedStartDate = normalizeDateInputValue(startDateField.value);
  const normalizedEndDate = normalizeDateInputValue(endDateField.value);
  const maxResultsValue = Number.parseInt(document.getElementById("maxResultsInput").value, 10);
  const maxResults = Number.isFinite(maxResultsValue)
    ? Math.min(Math.max(maxResultsValue, 1), MAX_RESULTS_LIMIT)
    : 5;
  if (!topic) {
    renderResult({
      status: "failed",
      current_message: "请先输入研究主题。",
      latest_report_path: "",
      report_artifact_path: "",
      errors: [],
    });
    return;
  }

  if (startDateField.value.trim() && !normalizedStartDate.iso) {
    renderResult({
      status: "failed",
      current_message: "起始日期请选择有效日期。",
      latest_report_path: "",
      report_artifact_path: "",
      errors: [],
    });
    return;
  }

  if (endDateField.value.trim() && !normalizedEndDate.iso) {
    renderResult({
      status: "failed",
      current_message: "终止日期请选择有效日期。",
      latest_report_path: "",
      report_artifact_path: "",
      errors: [],
    });
    return;
  }

  if (normalizedStartDate.iso && normalizedEndDate.iso && normalizedStartDate.iso > normalizedEndDate.iso) {
    renderResult({
      status: "failed",
      current_message: "终止日期不能早于起始日期。",
      latest_report_path: "",
      report_artifact_path: "",
      errors: [],
    });
    return;
  }

  document.getElementById("startDateInput").value = normalizedStartDate.display;
  document.getElementById("endDateInput").value = normalizedEndDate.display;

  await saveSettings();
  document.getElementById("runButton").disabled = true;
  draftSelectionRunId = null;
  draftSelectedSourceIds = null;
  if (pollHandle) {
    window.clearInterval(pollHandle);
    pollHandle = null;
  }

  const response = await fetch("/research-runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic,
      start_date: normalizedStartDate.iso || null,
      end_date: normalizedEndDate.iso || null,
      max_results: maxResults,
      openai_api_key: document.getElementById("apiKey").value.trim(),
      openai_model: document.getElementById("modelName").value.trim(),
      openai_base_url: document.getElementById("baseUrl").value.trim(),
      venues: [],
    }),
  });
  const payload = await response.json();
  activeRunId = payload.run_id;
  renderStages(payload.stages || []);
  renderResult(payload);
  analysisStarted = false;
  pollHandle = window.setInterval(() => {
    fetchRun(activeRunId);
  }, 1200);
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();

  settingsFieldIds.forEach((id) => {
    const input = document.getElementById(id);
    input.addEventListener("change", saveSettings);
    input.addEventListener("blur", saveSettings);
  });
  const startDateInput = document.getElementById("startDateInput");
  const startDatePicker = document.getElementById("startDatePicker");
  const endDateInput = document.getElementById("endDateInput");
  const endDatePicker = document.getElementById("endDatePicker");
  const syncStartDateDisplay = () => {
    startDateInput.value = formatDateValueForDisplay(startDatePicker.value);
  };
  const syncEndDateDisplay = () => {
    endDateInput.value = formatDateValueForDisplay(endDatePicker.value);
  };
  startDateInput.addEventListener("click", () => {
    if (typeof startDatePicker.showPicker === "function") {
      startDatePicker.showPicker();
      return;
    }
    startDatePicker.focus();
    startDatePicker.click();
  });
  endDateInput.addEventListener("click", () => {
    if (typeof endDatePicker.showPicker === "function") {
      endDatePicker.showPicker();
      return;
    }
    endDatePicker.focus();
    endDatePicker.click();
  });
  startDatePicker.addEventListener("change", syncStartDateDisplay);
  startDatePicker.addEventListener("blur", syncStartDateDisplay);
  endDatePicker.addEventListener("change", syncEndDateDisplay);
  endDatePicker.addEventListener("blur", syncEndDateDisplay);
  document.getElementById("runButton").addEventListener("click", startRun);

  renderStages([
    { stage_label: "抓取论文", status: "pending", message: "", current: 0, total: 0 },
    { stage_label: "分析论文", status: "pending", message: "", current: 0, total: 0 },
    { stage_label: "统计趋势", status: "pending", message: "", current: 0, total: 0 },
    { stage_label: "汇总研究机会与空白", status: "pending", message: "", current: 0, total: 0 },
    { stage_label: "生成报告", status: "pending", message: "", current: 0, total: 0 },
  ]);
  renderResult({
    status: "pending",
    current_message: "填写主题后即可开始生成。",
    latest_report_path: "",
    report_artifact_path: "",
    errors: [],
  });
});
