from __future__ import annotations

from app.services.collectors.crossref_source import CrossrefProceedingsSource
from app.services.collectors.dblp_icme_source import DblpIcmeProceedingsSource


class IcmeProceedingsSource:
    def __init__(
        self,
        crossref_source: CrossrefProceedingsSource | None = None,
        dblp_source: DblpIcmeProceedingsSource | None = None,
    ) -> None:
        self._crossref = crossref_source or CrossrefProceedingsSource()
        self._dblp = dblp_source or DblpIcmeProceedingsSource()

    def fetch(self, *, year: int, limit: int | None = None):
        crossref_error: Exception | None = None
        try:
            papers = self._crossref.fetch_icme(year=year, limit=limit)
            if papers:
                return papers
        except RuntimeError as exc:
            crossref_error = exc
        papers = self._dblp.fetch(year=year, limit=limit)
        if papers:
            return papers
        if crossref_error is not None:
            raise RuntimeError(f"ICME fetch failed after Crossref timeout and DBLP fallback: {crossref_error}") from crossref_error
        return []
