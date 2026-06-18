from __future__ import annotations

from app.services.research_service import ResearchService


def register_paper_routes(app, service: ResearchService) -> None:
    def list_papers() -> list[dict[str, object]]:
        return service.list_papers()

    app.add_api_route("/papers", list_papers, methods=["GET"])
