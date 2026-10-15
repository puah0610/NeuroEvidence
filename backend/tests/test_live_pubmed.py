import xml.etree.ElementTree as ET
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import Settings
from app.live_pubmed import (
    PRE_RULE_FILTERS,
    LivePubMedRetriever,
    build_clinical_pubmed_query,
    extract_clinical_entities,
    parse_pubmed_xml_article,
)
from app.models import ChatMode, ChatRequest, RetrievedChunk


SAMPLE_PUBMED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID Version="1">38501234</PMID>
      <Article PubModel="Print-Electronic">
        <Journal>
          <Title>Movement Disorders</Title>
          <JournalIssue>
            <PubDate>
              <Year>2024</Year>
              <Month>Apr</Month>
            </PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Efficacy of Amantadine Extended-Release in Parkinson's Disease Patients With Levodopa-Induced Dyskinesia: A Phase 3 Randomized Trial.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Levodopa-induced dyskinesia remains a major therapeutic challenge in advanced Parkinson's disease.</AbstractText>
          <AbstractText Label="METHODS">A double-blind, placebo-controlled, randomized clinical trial across 40 clinical centers evaluated amantadine vs placebo.</AbstractText>
          <AbstractText Label="RESULTS">Amantadine extended-release significantly reduced dyskinesia severity scores compared to placebo (p &lt; 0.001) without worsening off-time.</AbstractText>
          <AbstractText Label="CONCLUSION">Amantadine is effective and well-tolerated for managing levodopa-induced dyskinesias in Parkinson's disease.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Johnson</LastName>
            <ForeName>Mark</ForeName>
          </Author>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>Sarah</ForeName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">38501234</ArticleId>
        <ArticleId IdType="doi">10.1002/mds.29999</ArticleId>
        <ArticleId IdType="pmc">PMC11002234</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_extract_clinical_entities_parkinsons():
    question = "Can amantadine reduce levodopa-induced dyskinesia in advanced Parkinson's disease?"
    condition, interventions, outcomes = extract_clinical_entities(question)
    assert "Parkinson Disease" in condition
    assert "amantadine" in interventions
    assert "levodopa" in interventions
    assert "dyskinesia" in outcomes


def test_extract_clinical_entities_epilepsy():
    question = "Is lamotrigine effective for focal seizures in newly diagnosed epilepsy?"
    condition, interventions, outcomes = extract_clinical_entities(question)
    assert "Epilepsy" in condition
    assert "lamotrigine" in interventions
    assert "focal seizures" in outcomes


def test_build_clinical_pubmed_query_structure():
    question = "Does levetiracetam cause psychiatric adverse events in epilepsy trials?"
    query = build_clinical_pubmed_query(question, topic="epilepsy")

    assert '"Epilepsy"[MeSH Terms]' in query
    assert '"levetiracetam"[Title/Abstract]' in query
    assert PRE_RULE_FILTERS in query
    assert "humans[Filter]" in query
    assert "2015:3000[dp]" in query
    assert "clinical trial[Filter]" in query


def test_parse_pubmed_xml_article():
    root = ET.fromstring(SAMPLE_PUBMED_XML)
    article_elem = root.find(".//PubmedArticle")
    assert article_elem is not None

    chunk = parse_pubmed_xml_article(article_elem, fallback_topic="Parkinson's disease")
    assert chunk is not None
    assert chunk.source_id == "PUBMED-LIVE-38501234"
    assert chunk.pmid == "38501234"
    assert chunk.pmcid == "PMC11002234"
    assert chunk.doi == "10.1002/mds.29999"
    assert chunk.year == 2024
    assert chunk.journal == "Movement Disorders"
    assert chunk.layer == 3
    assert chunk.layer_source == "PubMed Central / Clinical Trials (Live API)"
    assert "Amantadine" in chunk.title
    assert "significantly reduced dyskinesia" in chunk.excerpt
    assert chunk.authors == ["Johnson Mark", "Smith Sarah"]


@pytest.mark.asyncio
async def test_live_pubmed_retriever_mocked():
    settings = Settings(demo_mode=True)
    retriever = LivePubMedRetriever(settings)

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Mock esearch response
    mock_esearch_resp = MagicMock()
    mock_esearch_resp.status_code = 200
    mock_esearch_resp.json.return_value = {
        "esearchresult": {
            "count": "1",
            "idlist": ["38501234"],
        }
    }

    # Mock efetch response
    mock_efetch_resp = MagicMock()
    mock_efetch_resp.status_code = 200
    mock_efetch_resp.text = SAMPLE_PUBMED_XML

    async def mock_get(url, params=None):
        if "esearch.fcgi" in url:
            return mock_esearch_resp
        return mock_efetch_resp

    mock_client.get.side_effect = mock_get

    chunks, query = await retriever.search_and_rerank(
        question="Is amantadine effective for dyskinesia in Parkinson's?",
        topic="Parkinson's disease",
        top_k=2,
        client=mock_client,
    )

    assert len(chunks) == 1
    assert chunks[0].source_id == "PUBMED-LIVE-38501234"
    assert chunks[0].layer == 3
    assert "Live API" in chunks[0].layer_source
    assert query is not None

    # Test source lookup
    source = retriever.get_source("PUBMED-LIVE-38501234")
    assert source is not None
    assert source.pmid == "38501234"

    # Test cache retrieval (mock client should not be called again)
    mock_client.get.reset_mock()
    cached_chunks, _ = await retriever.search_and_rerank(
        question="Is amantadine effective for dyskinesia in Parkinson's?",
        topic="Parkinson's disease",
        top_k=2,
        client=mock_client,
    )
    assert len(cached_chunks) == 1
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_live_pubmed_service_integration(service):
    # Verify that live pubmed fallback initializes properly
    assert hasattr(service, "live_pubmed")

    # Mock live_pubmed search_and_rerank to return a synthetic live chunk
    fake_live_chunk = RetrievedChunk(
        chunk_id="PUBMED-LIVE-99999999",
        document_id="PUBMED-LIVE-99999999",
        source_id="PUBMED-LIVE-99999999",
        title="Brivaracetam Monotherapy for Focal Onset Seizures: A Multicenter RCT",
        authors=["Neurologist A"],
        year=2025,
        journal="Epilepsia",
        topic="epilepsy",
        url="https://pubmed.ncbi.nlm.nih.gov/99999999/",
        license="Open Access",
        section="Clinical Trial Abstract",
        excerpt="The multicenter double-blind trial demonstrated that brivaracetam achieved 72% seizure freedom in focal onset seizures.",
        relevance=0.88,
        demo=False,
        layer=3,
        layer_name="Layer 3: Empirical Evidence & Trials",
        layer_source="PubMed Central / Clinical Trials (Live API)",
    )

    mock_search = AsyncMock(return_value=([fake_live_chunk], "mocked_query"))
    with patch.object(service.live_pubmed, "search_and_rerank", new=mock_search):
        request = ChatRequest(
            session_id="test-live-pubmed-session",
            question="What are the clinical trial outcomes of brivaracetam in focal onset seizures in epilepsy?",
            mode=ChatMode.rag_verified,
            enable_live_pubmed=True,
        )
        
        # 1. First Query: Local corpus lacks brivaracetam Layer 3 evidence -> triggers Live PubMed
        response1 = await service.chat(request)
        assert response1.live_pubmed_triggered is True
        assert response1.live_pubmed_query == "mocked_query"
        assert any("Live PubMed fallback active" in w for w in response1.warnings)
        assert mock_search.call_count == 1

        # Verify source retrieval from service
        source = service.get_source("PUBMED-LIVE-99999999")
        assert source is not None
        assert source.source_id == "PUBMED-LIVE-99999999"

        # 2. Subsequent Query: Evidence was auto-saved into knowledge base -> does NOT trigger Live PubMed again!
        response2 = await service.chat(request)
        assert response2.live_pubmed_triggered is False
        assert mock_search.call_count == 1  # Not called again!
        assert any(c.source_id == "PUBMED-LIVE-99999999" for c in response2.citations)


def test_chroma_retriever_add_chunks(tmp_path):
    from app.retrieval import ChromaRetriever
    
    settings = Settings(
        demo_mode=True,
        chroma_path=tmp_path / "chroma_test",
        chroma_collection="test_live_collection",
        enable_reranker=False,
        enable_hyde=False,
    )
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.05] * 384]

    chroma = ChromaRetriever(settings, mock_embedder)

    fake_chunk = RetrievedChunk(
        chunk_id="PUBMED-LIVE-12345678",
        document_id="PUBMED-LIVE-12345678",
        source_id="PUBMED-LIVE-12345678",
        title="Amantadine vs Placebo for Parkinson Dyskinesia: Multicenter Trial",
        authors=["Author One", "Author Two"],
        year=2024,
        journal="Movement Disorders",
        topic="Parkinson's disease",
        url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        section="Clinical Trial Abstract",
        excerpt="Amantadine extended-release significantly reduced dyskinesia severity scores.",
        relevance=0.92,
        layer=3,
        layer_name="Layer 3: Empirical Evidence & Trials",
        layer_source="PubMed Central / Clinical Trials",
    )

    # 1. Initial insert
    inserted = chroma.add_chunks([fake_chunk])
    assert inserted == 1
    assert chroma.collection.count() == 1

    # 2. Lookup source
    retrieved = chroma.get_source("PUBMED-LIVE-12345678")
    assert retrieved is not None
    assert retrieved.title == fake_chunk.title
    assert retrieved.layer == 3
    assert retrieved.authors == ["Author One", "Author Two"]

    # 3. Deduplication: adding the same chunk again should insert 0 new items
    reinserted = chroma.add_chunks([fake_chunk])
    assert reinserted == 0
    assert chroma.collection.count() == 1
