from datetime import date

from app.services.collectors.pubmed_source import PubMedPaperSource


def test_pubmed_source_builds_papers_from_pubmed_payloads() -> None:
    source = PubMedPaperSource()

    paper = source._build_paper(
        pmid="12345",
        summary={
            "title": "Agent Planning for Clinical Workflows",
            "pubdate": "2025 Jun 17",
            "source": "Nature",
            "authors": [{"name": "Ada Lovelace"}, {"name": "Alan Turing"}],
            "articleids": [
                {"idtype": "pubmed", "value": "12345"},
                {"idtype": "doi", "value": "10.1000/agent"},
            ],
        },
        abstract="We study agent planning in clinical systems.",
    )

    assert paper is not None
    assert paper.source_id == "12345"
    assert paper.title == "Agent Planning for Clinical Workflows"
    assert paper.authors == ["Ada Lovelace", "Alan Turing"]
    assert paper.abstract == "We study agent planning in clinical systems."
    assert paper.year == 2025
    assert paper.published_at == date(2025, 6, 17)
    assert paper.venue == "Nature"
    assert paper.url == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    assert paper.source == "pubmed"
    assert paper.pdf_url == ""
    assert "agent" in paper.keywords


def test_pubmed_source_extracts_keywords_and_uses_journal_pubdate_for_display_date() -> None:
    source = PubMedPaperSource()

    details = source._fetch_article_details(
        ["12345"],
        xml_text="""
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>12345</PMID>
              <Article>
                <Abstract>
                  <AbstractText>Study abstract.</AbstractText>
                </Abstract>
                <ArticleDate DateType="Electronic">
                  <Year>2026</Year>
                  <Month>06</Month>
                  <Day>17</Day>
                </ArticleDate>
              </Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2025</Year>
                    <Month>Jun</Month>
                    <Day>18</Day>
                  </PubDate>
                </JournalIssue>
              </Journal>
              <KeywordList>
                <Keyword MajorTopicYN="N">Large Language Models</Keyword>
                <Keyword MajorTopicYN="N">Clinical Decision Support</Keyword>
              </KeywordList>
              <MeshHeadingList>
                <MeshHeading>
                  <DescriptorName UI="D000001">Agents, Artificial</DescriptorName>
                </MeshHeading>
              </MeshHeadingList>
            </MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>
        """,
    )

    assert details["12345"]["published_at"] == date(2025, 6, 18)
    assert details["12345"]["keywords"][:3] == [
        "Large Language Models",
        "Clinical Decision Support",
        "Agents, Artificial",
    ]


def test_pubmed_source_build_paper_prefers_summary_pubdate_when_xml_article_date_is_different() -> None:
    source = PubMedPaperSource()

    paper = source._build_paper(
        pmid="12345",
        summary={
            "title": "Agent Planning for Clinical Workflows",
            "pubdate": "2025 Jun 17",
            "source": "Nature",
            "authors": [{"name": "Ada Lovelace"}],
        },
        abstract="We study agent planning in clinical systems.",
        published_at=date(2026, 6, 17),
    )

    assert paper is not None
    assert paper.published_at == date(2025, 6, 17)
    assert paper.year == 2025


def test_pubmed_source_fetch_uses_topic_date_filter_and_limit(monkeypatch) -> None:
    source = PubMedPaperSource(limit=3)

    monkeypatch.setattr(
        source,
        "_search_ids",
        lambda topic, sort, limit, start_date=None, end_date=None: {
            ("(agent[Title/Abstract] AND memory[Title/Abstract])", "relevance", 9, date(2025, 1, 1), None): ["4", "3", "2", "1"],
        }[(topic, sort, limit, start_date, end_date)],
    )
    monkeypatch.setattr(
        source,
        "_fetch_summaries",
        lambda pmids: {
            pmid: {
                "title": f"Paper {pmid}",
                "pubdate": f"{2020 + int(pmid)} Jan",
                "source": "PubMed Journal",
                "authors": [{"name": f"Author {pmid}"}],
                "articleids": [{"idtype": "pubmed", "value": pmid}],
            }
            for pmid in pmids
        },
    )
    monkeypatch.setattr(
        source,
        "_fetch_article_details",
        lambda pmids, xml_text=None: {
            pmid: {
                "abstract": f"Agent memory abstract {pmid}",
                "keywords": [f"Agent Memory {pmid}"],
                "published_at": None,
            }
            for pmid in pmids
        },
    )

    papers = source.fetch("agent memory", start_date=date(2025, 1, 1))

    assert [paper.source_id for paper in papers] == ["4", "3", "2"]
    assert all(paper.source == "pubmed" for paper in papers)


def test_pubmed_source_fetch_uses_only_relevance_search(monkeypatch) -> None:
    source = PubMedPaperSource(limit=3)
    search_calls = []

    def fake_search_ids(topic, sort, limit, start_date=None, end_date=None):
        search_calls.append((topic, sort, limit, start_date, end_date))
        return ["1", "2", "3"]

    monkeypatch.setattr(source, "_search_ids", fake_search_ids)
    monkeypatch.setattr(
        source,
        "_fetch_summaries",
        lambda pmids: {
            pmid: {
                "title": f"Paper {pmid}",
                "pubdate": "2025 Jun 17",
                "source": "PubMed Journal",
                "authors": [{"name": f"Author {pmid}"}],
                "articleids": [{"idtype": "pubmed", "value": pmid}],
            }
            for pmid in pmids
        },
    )
    monkeypatch.setattr(
        source,
        "_fetch_article_details",
        lambda pmids, xml_text=None: {
            pmid: {
                "abstract": f"Abstract {pmid}",
                "keywords": [f"Keyword {pmid}"],
                "published_at": date(2025, 6, 17),
            }
            for pmid in pmids
        },
    )

    source.fetch("agent memory", start_date=date(2025, 1, 1), end_date=date(2025, 6, 17))

    assert search_calls == [
        ("(agent[Title/Abstract] AND memory[Title/Abstract])", "relevance", 9, date(2025, 1, 1), date(2025, 6, 17)),
    ]


def test_pubmed_source_search_query_uses_title_abstract_terms_and_date_filters(monkeypatch) -> None:
    source = PubMedPaperSource()
    captured = []

    def fake_get_json(path, params):
        captured.append((path, params))
        if path == "esearch.fcgi":
            return {"esearchresult": {"idlist": []}}
        return {"result": {}}

    monkeypatch.setattr(source, "_get_json", fake_get_json)

    papers = source.fetch("agent memory", start_date=date(2025, 1, 1), end_date=date(2025, 6, 17))

    assert papers == []
    esearch_calls = [params for path, params in captured if path == "esearch.fcgi"]
    assert esearch_calls
    assert esearch_calls[0]["term"] == "(agent[Title/Abstract] AND memory[Title/Abstract])"
    assert esearch_calls[0]["mindate"] == "2025/01/01"
    assert esearch_calls[0]["maxdate"] == "2025/06/17"
    assert esearch_calls[0]["datetype"] == "pdat"
    assert esearch_calls[0]["sort"] == "relevance"
    assert len(esearch_calls) == 1


def test_pubmed_source_builds_title_abstract_boolean_query() -> None:
    source = PubMedPaperSource()

    assert source._build_topic_query("agent memory") == "(agent[Title/Abstract] AND memory[Title/Abstract])"
    assert source._build_topic_query("  clinical   decision support  ") == (
        "(clinical[Title/Abstract] AND decision[Title/Abstract] AND support[Title/Abstract])"
    )
