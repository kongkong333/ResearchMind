# Topic Analysis Navigation And Databases Design

## Goal

Rework the single-page shell into a left-navigation workspace with a settings modal, and expand topic-based paper collection from a single PubMed source to selectable `PubMed`, `arXiv`, and `Semantic Scholar`.

## Scope

- Replace the current left-side always-visible LLM settings card with a narrow sidebar.
- Add sidebar entries for `主题论文分析` and `会议论文近期趋势`.
- Keep the current research workflow under `主题论文分析`.
- Show an empty-state panel for `会议论文近期趋势` with "即将上线 / 暂无内容".
- Move LLM configuration into a modal opened by a `设置` button in the sidebar footer.
- Add database tabs in `主题论文分析` and send the selected database with each run request.
- Restrict each run to exactly one source database.

## Frontend Design

### Layout

- `#app` becomes a two-column shell with a narrow sidebar and a main workspace.
- The sidebar contains brand text, module navigation buttons, and a footer settings button.
- The main workspace renders one active module at a time.

### Module Behavior

- `主题论文分析` remains the default active module.
- `会议论文近期趋势` renders a simple empty-state panel and does not trigger any backend call.

### Settings

- A modal overlays the current page and contains the existing LLM fields:
  - API Key
  - 模型名称
  - API Base URL
  - 报告输出目录
- Existing auto-save behavior stays in place.

### Database Selection

- Add a visible single-select tab row above the topic form.
- Tabs: `PubMed`, `arXiv`, `Semantic Scholar`.
- The chosen database is included in run creation payloads and reflected in the result panel.

## Backend Design

### Request/Run State

- Extend the run creation schema with a `database` field.
- Persist the selected database in in-memory run state and response serialization.
- Default database stays `pubmed` for backward compatibility.

### Collection Layer

- Introduce a database-aware source selection helper that maps:
  - `pubmed` -> `PubMedPaperSource`
  - `arxiv` -> `ArxivPaperSource`
  - `semantic_scholar` -> `SemanticScholarPaperSource`
- `collect_papers` uses the selected source only.

### New Sources

- `ArxivPaperSource` fetches from the arXiv Atom API and converts entries into `CollectedPaper`.
- `SemanticScholarPaperSource` fetches from the Semantic Scholar Graph API and converts entries into `CollectedPaper`.
- Both sources honor topic, date range when practical, and limit.

## Testing

- Frontend shell tests for:
  - sidebar module labels
  - settings modal markup
  - database tabs
  - upcoming-state copy
- API/service tests for:
  - request payload accepting `database`
  - selected source class being used
  - serialized run including `database`

## Non-Goals

- No mixed multi-database aggregation in one run.
- No implementation yet for `会议论文近期趋势`.
