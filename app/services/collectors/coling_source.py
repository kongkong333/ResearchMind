from __future__ import annotations

from app.services.collectors.acl_anthology_source import AclAnthologyProceedingsSource
from app.services.collectors.crossref_source import CrossrefProceedingsSource


class ColingProceedingsSource:
    def __init__(
        self,
        anthology_source: AclAnthologyProceedingsSource | None = None,
        crossref_source: CrossrefProceedingsSource | None = None,
    ) -> None:
        self._anthology = anthology_source or AclAnthologyProceedingsSource()
        self._crossref = crossref_source or CrossrefProceedingsSource()

    def fetch(self, *, year: int, limit: int | None = None):
        try:
            papers = self._anthology.fetch_coling(year=year, limit=limit)
            if papers:
                return papers
        except RuntimeError:
            pass
        return self._crossref.fetch_coling(year=year, limit=limit)
