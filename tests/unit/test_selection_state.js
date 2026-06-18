const test = require("node:test");
const assert = require("node:assert/strict");

const {
  normalizeSelectionDraft,
  toggleSelection,
} = require("../../app/static/selection-state.js");

test("normalizeSelectionDraft preserves local checkbox draft across polling refresh", () => {
  const run = {
    papers: [
      { source_id: "paper-1" },
      { source_id: "paper-2" },
      { source_id: "paper-3" },
    ],
    selected_source_ids: ["paper-1", "paper-2", "paper-3"],
  };

  const nextSelection = normalizeSelectionDraft(run, ["paper-2"]);

  assert.deepEqual(nextSelection, ["paper-2"]);
});

test("normalizeSelectionDraft falls back to server selection when draft is missing", () => {
  const run = {
    papers: [{ source_id: "paper-1" }, { source_id: "paper-2" }],
    selected_source_ids: ["paper-2"],
  };

  const nextSelection = normalizeSelectionDraft(run, null);

  assert.deepEqual(nextSelection, ["paper-2"]);
});

test("toggleSelection removes and adds papers without duplicating ids", () => {
  const removed = toggleSelection(["paper-1", "paper-2"], "paper-1", false);
  const added = toggleSelection(removed, "paper-2", true);
  const appended = toggleSelection(added, "paper-3", true);

  assert.deepEqual(removed, ["paper-2"]);
  assert.deepEqual(added, ["paper-2"]);
  assert.deepEqual(appended, ["paper-2", "paper-3"]);
});
