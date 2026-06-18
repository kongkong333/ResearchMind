(function (global) {
  function listPaperSourceIds(run) {
    if (!run || !Array.isArray(run.papers)) {
      return [];
    }
    return run.papers
      .map((paper) => (paper && typeof paper.source_id === "string" ? paper.source_id : ""))
      .filter(Boolean);
  }

  function normalizeSelectionDraft(run, draftSelectedSourceIds) {
    const paperSourceIds = listPaperSourceIds(run);
    const availableIds = new Set(paperSourceIds);
    const serverSelectedSourceIds = Array.isArray(run && run.selected_source_ids)
      ? run.selected_source_ids.filter((sourceId) => availableIds.has(sourceId))
      : [];

    if (Array.isArray(draftSelectedSourceIds)) {
      return draftSelectedSourceIds.filter((sourceId) => availableIds.has(sourceId));
    }
    if (serverSelectedSourceIds.length) {
      return serverSelectedSourceIds;
    }
    return paperSourceIds;
  }

  function toggleSelection(draftSelectedSourceIds, sourceId, checked) {
    const nextSelectedIds = Array.isArray(draftSelectedSourceIds)
      ? [...draftSelectedSourceIds]
      : [];
    const existingIndex = nextSelectedIds.indexOf(sourceId);

    if (checked && existingIndex === -1) {
      nextSelectedIds.push(sourceId);
    }
    if (!checked && existingIndex !== -1) {
      nextSelectedIds.splice(existingIndex, 1);
    }

    return nextSelectedIds;
  }

  const api = {
    normalizeSelectionDraft,
    toggleSelection,
  };

  global.ResearchSelection = api;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
