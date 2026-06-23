(function () {
  const conferenceOptions = [
    { id: "iclr", label: "ICLR" },
    { id: "neurips", label: "NeurIPS" },
    { id: "icml", label: "ICML" },
    { id: "colm", label: "COLM" },
    { id: "aaai", label: "AAAI" },
    { id: "coling", label: "COLING" },
    { id: "icme", label: "ICME" },
  ];

  let activeConferenceRunId = null;
  let conferencePollHandle = null;
  let selectedConference = conferenceOptions[0].id;
  let activeTracks = [];

  function isAaaISelected() {
    return selectedConference === "aaai";
  }

  function stopConferencePolling() {
    if (conferencePollHandle) {
      window.clearInterval(conferencePollHandle);
      conferencePollHandle = null;
    }
    if (document.getElementById("conferenceRunButton")) {
      document.getElementById("conferenceRunButton").disabled = false;
    }
  }

  function renderConferenceFailure(message) {
    renderConferenceStages([
      { stage_label: "抓取 Accepted 论文", status: "failed", message, current: 0, total: 0 },
      { stage_label: "归纳热点趋势", status: "pending", message: "", current: 0, total: 0 },
    ]);
    renderConferenceResult({
      status: "failed",
      current_message: message,
      trend_snapshot: null,
      papers: [],
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
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

  function renderConferenceStages(stages) {
    const grid = document.getElementById("conference-stage-grid");
    if (!grid) {
      return;
    }
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

  function renderConferenceResult(run) {
    const panel = document.getElementById("conference-result-panel");
    if (!panel) {
      return;
    }
    const snapshot = run.trend_snapshot || {};
    const papers = Array.isArray(run.papers) ? run.papers : [];
    const methodTags = Array.isArray(snapshot.hot_methods)
      ? snapshot.hot_methods.map((item) => `<span class="paper-chip">${escapeHtml(item)}</span>`).join("")
      : "";
    const applicationTags = Array.isArray(snapshot.hot_applications)
      ? snapshot.hot_applications.map((item) => `<span class="paper-chip">${escapeHtml(item)}</span>`).join("")
      : "";
    const signalTags = Array.isArray(snapshot.emerging_signals)
      ? snapshot.emerging_signals.map((item) => `<span class="paper-chip">${escapeHtml(item)}</span>`).join("")
      : "";
    const paperItems = papers.map((paper, index) => `
      <li class="conference-paper-item">
        <span class="conference-paper-index">${index + 1}.</span>
        <a class="paper-title-link" href="${escapeHtml(paper.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(paper.title || "未命名论文")}</a>
      </li>
    `).join("");
    panel.innerHTML = `
      <p class="eyebrow">趋势结果</p>
      <h2>${run.status === "completed" ? "会议趋势已生成" : "等待趋势分析"}</h2>
      <p class="result-summary ${run.status === "pending" ? "status-idle" : ""}">${escapeHtml(run.current_message || "选择会议和年份后开始。")}</p>
      <div class="conference-summary-grid">
        <article class="trend-card">
          <div class="paper-chip-label">摘要</div>
          <p class="trend-summary-text">${escapeHtml(snapshot.summary || "结果生成后会在这里展示会议趋势摘要。")}</p>
        </article>
        <article class="trend-card">
          <div class="paper-chip-label">方法热点</div>
          <div class="paper-chip-list">${methodTags || '<span class="paper-chip paper-chip-muted">暂无</span>'}</div>
        </article>
        <article class="trend-card">
          <div class="paper-chip-label">应用热点</div>
          <div class="paper-chip-list">${applicationTags || '<span class="paper-chip paper-chip-muted">暂无</span>'}</div>
        </article>
        <article class="trend-card">
          <div class="paper-chip-label">新信号</div>
          <div class="paper-chip-list">${signalTags || '<span class="paper-chip paper-chip-muted">暂无</span>'}</div>
        </article>
      </div>
      <details class="paper-overview" ${papers.length ? "open" : ""}>
        <summary class="section-head paper-overview-summary">
          <p class="eyebrow">Accepted 标题</p>
          <span class="section-note">${papers.length ? `共抓取 ${papers.length} 篇` : "等待抓取结果"}</span>
        </summary>
        <ol class="conference-paper-list">
          ${paperItems || '<li class="empty-state">暂无标题结果。</li>'}
        </ol>
      </details>
    `;
  }

  function trackNumberLabel(title) {
    const match = String(title || "").match(/Technical Tracks?\s+(\d+)/i);
    return match ? `Track ${match[1]}` : "AAAI Track";
  }

  function primaryTrackLabel(track) {
    return track.theme || track.title || "未命名 AAAI Track";
  }

  function secondaryTrackLabel(track) {
    const parts = [track.series, track.title].filter(Boolean);
    return parts.join(" · ");
  }

  function renderTrackSection(message = "") {
    const section = document.getElementById("conferenceTrackSection");
    const list = document.getElementById("conferenceTrackList");
    const hint = document.getElementById("conferenceTrackHint");
    if (!section || !list || !hint) {
      return;
    }
    if (!isAaaISelected()) {
      section.classList.add("hidden");
      list.innerHTML = "";
      hint.textContent = "";
      return;
    }
    section.classList.remove("hidden");
    hint.textContent = message || "优先按主题选择 AAAI track；没有主题信息的年份会回退到 track 标题。";
    list.innerHTML = activeTracks.map((track, index) => `
      <label class="conference-track-item">
        <input class="conference-track-check" type="checkbox" data-track-id="${escapeHtml(track.track_id)}" ${index === 0 ? "checked" : ""}>
        <span class="conference-track-copy">
          <span class="conference-track-badge">${escapeHtml(trackNumberLabel(track.title))}</span>
          <span class="conference-track-title">${escapeHtml(primaryTrackLabel(track))}</span>
          <span class="conference-track-meta">${escapeHtml(secondaryTrackLabel(track))}</span>
        </span>
      </label>
    `).join("") || '<div class="empty-state">当前年份暂无可用 track。</div>';
  }

  function selectedTrackIds() {
    return Array.from(document.querySelectorAll("#conferenceTrackList input[data-track-id]:checked"))
      .map((input) => input.getAttribute("data-track-id") || "")
      .filter(Boolean);
  }

  async function readResponsePayload(response) {
    const raw = await response.text();
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        return JSON.parse(raw);
      } catch (error) {
        throw new Error("服务器返回了无效 JSON。");
      }
    }
    return { detail: raw.trim() };
  }

  async function loadConferenceTracks() {
    if (!isAaaISelected()) {
      activeTracks = [];
      renderTrackSection("");
      return;
    }
    const yearValue = Number.parseInt(document.getElementById("conferenceYearInput").value, 10);
    if (!Number.isFinite(yearValue) || yearValue < 2013 || yearValue > 2100) {
      activeTracks = [];
      renderTrackSection("请输入有效年份后再加载 AAAI track。");
      return;
    }
    renderTrackSection("正在加载 AAAI track...");
    try {
      const response = await fetch("/conference-trends/tracks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conference: selectedConference,
          year: yearValue,
        }),
      });
      const payload = await readResponsePayload(response);
      if (!response.ok) {
        throw new Error(payload.detail || "加载 AAAI track 失败。");
      }
      activeTracks = Array.isArray(payload.tracks) ? payload.tracks : [];
      renderTrackSection(activeTracks.length ? "" : "该年份未找到可用 AAAI track。");
    } catch (error) {
      activeTracks = [];
      renderTrackSection(error instanceof Error ? error.message : "加载 AAAI track 失败。");
    }
  }

  async function fetchConferenceTrendRun(runId) {
    try {
      const response = await fetch(`/conference-trends/runs/${runId}`);
      const payload = await readResponsePayload(response);
      if (!response.ok) {
        throw new Error(payload.detail || "获取会议趋势运行状态失败。");
      }
      renderConferenceStages(payload.stages || []);
      renderConferenceResult(payload);
      if (payload.status === "completed" || payload.status === "failed") {
        stopConferencePolling();
      }
    } catch (error) {
      stopConferencePolling();
      renderConferenceFailure(error instanceof Error ? error.message : "获取会议趋势运行状态失败。");
    }
  }

  async function startConferenceTrendRun() {
    if (typeof window.ResearchMindSaveSettings === "function") {
      await window.ResearchMindSaveSettings();
    }
    const yearValue = Number.parseInt(document.getElementById("conferenceYearInput").value, 10);
    const limitValue = Number.parseInt(document.getElementById("conferenceLimitInput").value, 10);
    if (!Number.isFinite(yearValue) || yearValue < 2013 || yearValue > 2100) {
      renderConferenceResult({
        status: "failed",
        current_message: "请输入有效年份。",
        trend_snapshot: null,
        papers: [],
      });
      return;
    }
    if (!Number.isFinite(limitValue) || limitValue < 1 || limitValue > 500) {
      renderConferenceResult({
        status: "failed",
        current_message: "请输入 1 到 500 之间的有效论文数量。",
        trend_snapshot: null,
        papers: [],
      });
      return;
    }
    const tracks = isAaaISelected() ? selectedTrackIds() : [];
    if (isAaaISelected() && !tracks.length) {
      renderConferenceResult({
        status: "failed",
        current_message: "请至少选择一个 AAAI track。",
        trend_snapshot: null,
        papers: [],
      });
      return;
    }

    document.getElementById("conferenceRunButton").disabled = true;
    if (conferencePollHandle) {
      window.clearInterval(conferencePollHandle);
      conferencePollHandle = null;
    }

    try {
      const response = await fetch("/conference-trends/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conference: selectedConference,
          year: yearValue,
          limit: limitValue,
          tracks,
          openai_api_key: document.getElementById("apiKey").value.trim(),
          openai_model: document.getElementById("modelName").value.trim(),
          openai_base_url: document.getElementById("baseUrl").value.trim(),
        }),
      });
      const payload = await readResponsePayload(response);
      if (!response.ok) {
        throw new Error(payload.detail || "启动会议趋势分析失败。");
      }
      activeConferenceRunId = payload.run_id;
      renderConferenceStages(payload.stages || []);
      renderConferenceResult(payload);
      conferencePollHandle = window.setInterval(() => {
        fetchConferenceTrendRun(activeConferenceRunId);
      }, 1200);
    } catch (error) {
      stopConferencePolling();
      renderConferenceFailure(error instanceof Error ? error.message : "启动会议趋势分析失败。");
    }
  }

  function init() {
    const conferenceSelect = document.getElementById("conferenceSelect");
    const conferenceRunButton = document.getElementById("conferenceRunButton");
    const conferenceLimitInput = document.getElementById("conferenceLimitInput");
    const conferenceYearInput = document.getElementById("conferenceYearInput");
    if (!conferenceSelect || !conferenceRunButton || !conferenceLimitInput || !conferenceYearInput) {
      return;
    }
    conferenceSelect.addEventListener("change", async (event) => {
      selectedConference = event.target.value || conferenceOptions[0].id;
      await loadConferenceTracks();
    });
    conferenceYearInput.addEventListener("change", async () => {
      await loadConferenceTracks();
    });
    conferenceRunButton.addEventListener("click", startConferenceTrendRun);
    renderConferenceStages([
      { stage_label: "抓取 Accepted 论文", status: "pending", message: "", current: 0, total: 0 },
      { stage_label: "归纳热点趋势", status: "pending", message: "", current: 0, total: 0 },
    ]);
    renderConferenceResult({
      status: "pending",
      current_message: "选择会议和年份后开始。",
      trend_snapshot: null,
      papers: [],
    });
    renderTrackSection("");
  }

  window.ResearchMindConferenceTrends = { init };
})();
