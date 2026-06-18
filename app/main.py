from __future__ import annotations

from pathlib import Path

from app.api.routes.papers import register_paper_routes
from app.api.routes.research_runs import RouteHTTPError, register_research_run_routes
from app.api.routes.settings import register_settings_routes
from app.core.config import get_settings
from app.services.research_service import ResearchService

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:
    FastAPI = None  # type: ignore[assignment]
    HTMLResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]


STATIC_DIR = Path(__file__).resolve().parent / "static"


class SimpleResponse:
    def __init__(self, status_code: int, payload) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class SimpleState:
    pass


class SimpleApp:
    def __init__(self, title: str) -> None:
        self.title = title
        self.state = SimpleState()
        self._routes: list[tuple[str, str, object, int]] = []

    def add_api_route(self, path: str, endpoint, methods: list[str], status_code: int = 200) -> None:
        for method in methods:
            self._routes.append((method.upper(), path, endpoint, status_code))

    def handle(self, method: str, path: str, json: dict | None = None) -> SimpleResponse:
        clean_method = method.upper()
        for route_method, route_path, endpoint, status_code in self._routes:
            params = _match_path(route_path, path)
            if route_method == clean_method and params is not None:
                try:
                    if clean_method in {"POST", "PUT"}:
                        payload = endpoint(**params, payload=json)
                    else:
                        payload = endpoint(**params)
                except RouteHTTPError as exc:
                    return SimpleResponse(exc.status_code, {"detail": exc.detail})
                return SimpleResponse(status_code, payload)
        return SimpleResponse(404, {"detail": "Not found."})


class SimpleTestClient:
    def __init__(self, app: SimpleApp) -> None:
        self._app = app

    def get(self, path: str) -> SimpleResponse:
        return self._app.handle("GET", path)

    def post(self, path: str, json: dict | None = None) -> SimpleResponse:
        return self._app.handle("POST", path, json=json)

    def put(self, path: str, json: dict | None = None) -> SimpleResponse:
        return self._app.handle("PUT", path, json=json)


def _match_path(route_path: str, actual_path: str) -> dict[str, str] | None:
    route_parts = route_path.strip("/").split("/")
    actual_parts = actual_path.strip("/").split("/")
    if route_parts == [""] and actual_parts == [""]:
        return {}
    if len(route_parts) != len(actual_parts):
        return None
    params: dict[str, str] = {}
    for route_part, actual_part in zip(route_parts, actual_parts):
        if route_part.startswith("{") and route_part.endswith("}"):
            params[route_part[1:-1]] = actual_part
            continue
        if route_part != actual_part:
            return None
    return params


def _read_index_html() -> str:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    asset_urls = {
        "styles_css_url": _versioned_static_asset_url("styles.css"),
        "selection_state_js_url": _versioned_static_asset_url("selection-state.js"),
        "app_js_url": _versioned_static_asset_url("app.js"),
    }
    for placeholder, value in asset_urls.items():
        html = html.replace(f"{{{{ {placeholder} }}}}", value)
    return html


def _versioned_static_asset_url(filename: str) -> str:
    asset_path = STATIC_DIR / filename
    version = int(asset_path.stat().st_mtime) if asset_path.exists() else 0
    return f"/static/{filename}?v={version}"


def create_app():
    settings = get_settings()
    service = ResearchService(report_output_dir=settings.report_output_dir)
    if FastAPI is None:
        app = SimpleApp(title=settings.app_name)
        app.add_api_route("/", lambda: {"html": _read_index_html()}, methods=["GET"])
    else:
        app = FastAPI(title=settings.app_name)
        if not hasattr(app, "state"):
            class _State:
                pass
            app.state = _State()
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/")
        async def index():
            return HTMLResponse(_read_index_html())

    app.state.research_service = service
    register_settings_routes(app, service)
    register_research_run_routes(app, service)
    register_paper_routes(app, service)
    return app


app = create_app()
