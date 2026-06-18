from __future__ import annotations

from pydantic import ValidationError

from app.schemas.research_runs import ResearchRunCreate
from app.services.research_service import ResearchService


class RouteHTTPError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def register_research_run_routes(app, service: ResearchService) -> None:
    app_name = type(app).__name__

    if app_name == "FastAPI":
        from fastapi import HTTPException

        async def create_run(payload: ResearchRunCreate) -> dict[str, object]:
            try:
                result = service.start_run(
                    topic=payload.topic,
                    venues=payload.venues,
                    date_range=(payload.start_date, payload.end_date),
                    max_results=payload.max_results,
                    openai_api_key=payload.openai_api_key,
                    openai_model=payload.openai_model,
                    openai_base_url=payload.openai_base_url,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            return _serialize_run(result)

        async def get_run(run_id: str) -> dict[str, object]:
            result = service.get_run(run_id)
            if result is None:
                raise HTTPException(status_code=404, detail="Research run not found.")
            return _serialize_run(result)

        async def get_report(run_id: str) -> dict[str, object]:
            result = service.get_report(run_id)
            if result is None:
                raise HTTPException(status_code=404, detail="Research run not found.")
            return result

        async def analyze_run(run_id: str, payload: dict | None = None) -> dict[str, object]:
            if payload is None:
                payload = {}
            selected_source_ids = [str(item) for item in payload.get("selected_source_ids", []) if str(item).strip()]
            request = service.set_selected_papers(run_id, selected_source_ids)
            if request is None:
                raise HTTPException(status_code=404, detail="Research run not found.")
            result = service.analyze_selected_run(
                run_id,
                openai_api_key=payload.get("openai_api_key"),
                openai_model=payload.get("openai_model"),
                openai_base_url=payload.get("openai_base_url"),
            )
            if result is None:
                raise HTTPException(status_code=404, detail="Research run not found.")
            return _serialize_run(result)

        app.add_api_route("/research-runs", create_run, methods=["POST"], status_code=201)
        app.add_api_route("/research-runs/{run_id}", get_run, methods=["GET"])
        app.add_api_route("/research-runs/{run_id}/report", get_report, methods=["GET"])
        app.add_api_route("/research-runs/{run_id}/analyze", analyze_run, methods=["POST"], status_code=200)
        return

    def create_run(payload: dict | None = None) -> dict[str, object]:
        try:
            request = ResearchRunCreate.model_validate(payload)
        except ValidationError as exc:
            raise RouteHTTPError(status_code=422, detail=str(exc)) from exc
        try:
            result = service.start_run(
                topic=request.topic,
                venues=request.venues,
                date_range=(request.start_date, request.end_date),
                max_results=request.max_results,
                openai_api_key=request.openai_api_key,
                openai_model=request.openai_model,
                openai_base_url=request.openai_base_url,
            )
        except ValueError as exc:
            raise RouteHTTPError(status_code=422, detail=str(exc)) from exc
        return _serialize_run(result)

    def get_run(run_id: str) -> dict[str, object]:
        result = service.get_run(run_id)
        if result is None:
            raise RouteHTTPError(status_code=404, detail="Research run not found.")
        return _serialize_run(result)

    def get_report(run_id: str) -> dict[str, object]:
        result = service.get_report(run_id)
        if result is None:
            raise RouteHTTPError(status_code=404, detail="Research run not found.")
        return result

    def analyze_run(run_id: str, payload: dict | None = None) -> dict[str, object]:
        payload = payload or {}
        selected_source_ids = [str(item) for item in payload.get("selected_source_ids", []) if str(item).strip()]
        request = service.set_selected_papers(run_id, selected_source_ids)
        if request is None:
            raise RouteHTTPError(status_code=404, detail="Research run not found.")
        result = service.analyze_selected_run(
            run_id,
            openai_api_key=payload.get("openai_api_key"),
            openai_model=payload.get("openai_model"),
            openai_base_url=payload.get("openai_base_url"),
        )
        if result is None:
            raise RouteHTTPError(status_code=404, detail="Research run not found.")
        return _serialize_run(result)

    app.add_api_route("/research-runs", create_run, methods=["POST"], status_code=201)
    app.add_api_route("/research-runs/{run_id}", get_run, methods=["GET"])
    app.add_api_route("/research-runs/{run_id}/report", get_report, methods=["GET"])
    app.add_api_route("/research-runs/{run_id}/analyze", analyze_run, methods=["POST"], status_code=200)


def _serialize_run(result: dict[str, object]) -> dict[str, object]:
    return {
        "run_id": result["run_id"],
        "topic": result["topic"],
        "status": result["status"],
        "current_message": result.get("current_message", ""),
        "stages": result.get("stages", []),
        "papers": result.get("papers", []),
        "selected_source_ids": result.get("selected_source_ids", []),
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "max_results": result.get("max_results", 5),
        "report_path": result.get("latest_report_path"),
        "report_artifact_path": result.get("report_path"),
        "latest_report_path": result.get("latest_report_path"),
        "errors": result.get("errors", []),
        "error_count": len(result.get("errors", [])),
    }
