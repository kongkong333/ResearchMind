from __future__ import annotations

from pydantic import ValidationError

from app.api.routes.research_runs import RouteHTTPError
from app.schemas.settings import FrontendSettingsUpdate
from app.services.research_service import ResearchService


def register_settings_routes(app, service: ResearchService) -> None:
    app_name = type(app).__name__

    if app_name == "FastAPI":
        from fastapi import HTTPException

        async def get_settings() -> dict[str, str]:
            return service.get_settings()

        async def put_settings(payload: FrontendSettingsUpdate) -> dict[str, str]:
            try:
                return service.save_settings(payload.model_dump())
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        app.add_api_route("/settings", get_settings, methods=["GET"])
        app.add_api_route("/settings", put_settings, methods=["PUT"])
        return

    def get_settings() -> dict[str, str]:
        return service.get_settings()

    def put_settings(payload: dict | None = None) -> dict[str, str]:
        try:
            request = FrontendSettingsUpdate.model_validate(payload)
        except ValidationError as exc:
            raise RouteHTTPError(status_code=422, detail=str(exc)) from exc
        return service.save_settings(request.model_dump())

    app.add_api_route("/settings", get_settings, methods=["GET"])
    app.add_api_route("/settings", put_settings, methods=["PUT"])
