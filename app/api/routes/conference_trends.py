from __future__ import annotations

from pydantic import ValidationError

from app.api.routes.research_runs import RouteHTTPError
from app.schemas.conference_trends import ConferenceTrackListRequest, ConferenceTrendRunCreate
from app.services.research_service import ResearchService


def register_conference_trend_routes(app, service: ResearchService) -> None:
    app_name = type(app).__name__

    if app_name == "FastAPI":
        from fastapi import HTTPException

        async def create_run(payload: ConferenceTrendRunCreate) -> dict[str, object]:
            try:
                result = service.start_conference_trend_run(
                    conference=payload.conference,
                    year=payload.year,
                    limit=payload.limit,
                    tracks=payload.tracks,
                    openai_api_key=payload.openai_api_key,
                    openai_model=payload.openai_model,
                    openai_base_url=payload.openai_base_url,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            return _serialize_run(result)

        async def list_tracks(payload: ConferenceTrackListRequest) -> dict[str, object]:
            try:
                tracks = service.list_conference_tracks(conference=payload.conference, year=payload.year)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            return {
                "conference": payload.conference,
                "year": payload.year,
                "tracks": tracks,
            }

        async def get_run(run_id: str) -> dict[str, object]:
            result = service.get_run(run_id)
            if result is None or result.get("run_kind") != "conference_trend":
                raise HTTPException(status_code=404, detail="Conference trend run not found.")
            return _serialize_run(result)

        app.add_api_route("/conference-trends/tracks", list_tracks, methods=["POST"], status_code=200)
        app.add_api_route("/conference-trends/runs", create_run, methods=["POST"], status_code=201)
        app.add_api_route("/conference-trends/runs/{run_id}", get_run, methods=["GET"])
        return

    def create_run(payload: dict | None = None) -> dict[str, object]:
        try:
            request = ConferenceTrendRunCreate.model_validate(payload)
        except ValidationError as exc:
            raise RouteHTTPError(status_code=422, detail=str(exc)) from exc
        try:
            result = service.start_conference_trend_run(
                conference=request.conference,
                year=request.year,
                limit=request.limit,
                tracks=request.tracks,
                openai_api_key=request.openai_api_key,
                openai_model=request.openai_model,
                openai_base_url=request.openai_base_url,
            )
        except ValueError as exc:
            raise RouteHTTPError(status_code=422, detail=str(exc)) from exc
        return _serialize_run(result)

    def list_tracks(payload: dict | None = None) -> dict[str, object]:
        try:
            request = ConferenceTrackListRequest.model_validate(payload)
        except ValidationError as exc:
            raise RouteHTTPError(status_code=422, detail=str(exc)) from exc
        try:
            tracks = service.list_conference_tracks(conference=request.conference, year=request.year)
        except Exception as exc:
            raise RouteHTTPError(status_code=502, detail=str(exc)) from exc
        return {
            "conference": request.conference,
            "year": request.year,
            "tracks": tracks,
        }

    def get_run(run_id: str) -> dict[str, object]:
        result = service.get_run(run_id)
        if result is None or result.get("run_kind") != "conference_trend":
            raise RouteHTTPError(status_code=404, detail="Conference trend run not found.")
        return _serialize_run(result)

    app.add_api_route("/conference-trends/tracks", list_tracks, methods=["POST"], status_code=200)
    app.add_api_route("/conference-trends/runs", create_run, methods=["POST"], status_code=201)
    app.add_api_route("/conference-trends/runs/{run_id}", get_run, methods=["GET"])


def _serialize_run(result: dict[str, object]) -> dict[str, object]:
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "current_message": result.get("current_message", ""),
        "conference": result.get("conference", ""),
        "year": result.get("year"),
        "stages": result.get("stages", []),
        "papers": result.get("papers", []),
        "trend_snapshot": result.get("trend_snapshot"),
        "errors": result.get("errors", []),
        "error_count": len(result.get("errors", [])),
    }
