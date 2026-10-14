import pytest
from app.config import Settings
from app.database import Database
from app.decomposition import QueryDecomposer, retrieve_with_decomposition
from app.llm import DemoGenerator
from app.models import ChatMode, ChatRequest, RetrievedChunk
from app.retrieval import DemoRetriever
from app.service import ChatService


def test_atomic_query_not_decomposed():
    settings = Settings(enable_query_decomposition=True)
    decomposer = QueryDecomposer(settings)

    # Atomic foundational definition query
    plan = decomposer.decompose("What are the cardinal motor symptoms of Parkinson's disease?", topic="Parkinson's disease")
    assert not plan.is_decomposed
    assert len(plan.subqueries) == 1
    assert plan.subqueries[0].target_layer == 1
    assert "Atomic query" in plan.rationale


def test_atomic_guideline_query_not_decomposed():
    settings = Settings(enable_query_decomposition=True)
    decomposer = QueryDecomposer(settings)

    # Atomic guideline recommendation query
    plan = decomposer.decompose("What are NICE guidelines recommendations for Parkinson's disease?", topic="Parkinson's disease")
    assert not plan.is_decomposed
    assert len(plan.subqueries) == 1
    assert plan.subqueries[0].target_layer == 2


def test_user_example_question_decomposition():
    settings = Settings(enable_query_decomposition=True, max_decomposition_subqueries=3)
    decomposer = QueryDecomposer(settings)

    # Exact user example:
    # "What causes Parkinson's disease, and what evidence supports the treatments described in guidelines?"
    question = "What causes Parkinson's disease, and what evidence supports the treatments described in guidelines?"
    plan = decomposer.decompose(question, topic="Parkinson's disease")

    assert plan.is_decomposed
    assert 2 <= len(plan.subqueries) <= 3

    # Check constraint preservation: all subqueries preserve "Parkinson"
    for sq in plan.subqueries:
        assert "parkinson" in sq.query_text.lower(), f"Subquery {sq.subquery_id} did not preserve condition: {sq.query_text}"

    # Check target layers cover distinct Triad facets
    layers = [sq.target_layer for sq in plan.subqueries if sq.target_layer is not None]
    assert 1 in layers  # Foundational cause / etiology
    assert 2 in layers or 3 in layers  # Guidelines or Empirical Evidence


def test_retrieve_with_decomposition_deduplication():
    settings = Settings(enable_query_decomposition=True, retrieval_top_k=5)
    decomposer = QueryDecomposer(settings)
    retriever = DemoRetriever(settings)

    question = "What causes Parkinson's disease, and what evidence supports the treatments described in guidelines?"
    plan = decomposer.decompose(question, topic="Parkinson's disease")
    assert plan.is_decomposed

    chunks, subquery_results = retrieve_with_decomposition(
        retriever, plan, topic="Parkinson's disease", settings=settings
    )

    assert len(chunks) > 0
    # Verify no duplicate chunk_ids
    chunk_ids = [c.chunk_id for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))

    # Verify subquery results populated
    assert len(subquery_results) == len(plan.subqueries)
    for sq_res in subquery_results:
        assert sq_res.subquery_id.startswith("SQ-")
        assert sq_res.chunks_found >= 0


def test_explicit_unanswered_gap_detection():
    settings = Settings(enable_query_decomposition=True)
    decomposer = QueryDecomposer(settings)

    # Create a mock retriever that only returns chunks for foundational queries
    class MockSelectiveRetriever:
        def search(self, query: str, topic: str | None = None) -> list[RetrievedChunk]:
            if "cause" in query.lower() or "pathophysiology" in query.lower():
                return [
                    RetrievedChunk(
                        source_id="src-1",
                        chunk_id="chunk-1",
                        document_id="doc-1",
                        topic="Parkinson's disease",
                        url="https://example.com/pd",
                        layer=1,
                        layer_name="Layer 1: Foundational Knowledge",
                        layer_source="StatPearls",
                        title="PD Etiology",
                        excerpt="Degeneration of dopaminergic neurons in the substantia nigra pars compacta.",
                        relevance=0.85,
                    )
                ]
            # No evidence found for other subqueries
            return []

    question = "What causes Parkinson's disease, and what evidence supports the treatments described in guidelines?"
    plan = decomposer.decompose(question, topic="Parkinson's disease")
    chunks, sq_results = retrieve_with_decomposition(
        MockSelectiveRetriever(), plan, topic="Parkinson's disease", settings=settings
    )

    # Foundational has evidence, other subqueries have explicit missing statements
    has_evidence_list = [sq.has_evidence for sq in sq_results]
    assert True in has_evidence_list
    assert False in has_evidence_list

    missing_parts = [sq.missing_evidence_statement for sq in sq_results if not sq.has_evidence]
    assert len(missing_parts) >= 1
    assert any("No indexed evidence" in stmt for stmt in missing_parts)

    # Test that DemoGenerator incorporates explicit evidence gap into grounded answer
    gen = DemoGenerator()
    output = gen.generate_grounded(question, chunks, unanswered_parts=missing_parts)
    assert "Unanswered Requested Dimension" in output.text or "Evidence Gap" in output.text


@pytest.mark.asyncio
async def test_full_service_decomposition_integration(tmp_path):
    db_path = tmp_path / "test_decomp.db"
    database = Database(db_path)
    settings = Settings(
        demo_mode=True,
        enable_query_decomposition=True,
        enable_bounded_answer_revision=True,
    )
    service = ChatService(settings, database)

    req = ChatRequest(
        question="What causes Parkinson's disease, and what evidence supports the treatments described in guidelines?",
        mode=ChatMode.rag_verified,
        session_id="test-session-decomp",
    )
    res = await service.chat(req)

    assert res.trace_id
    assert res.subqueries is not None
    assert len(res.subqueries) >= 2

    # Check condition preserved in all subqueries
    for sq in res.subqueries:
        assert "parkinson" in sq.query_text.lower()

    # Check trace persisted to database with subqueries_json
    with database._connect() as conn:
        row = conn.execute("SELECT subqueries_json FROM traces WHERE trace_id = ?", (res.trace_id,)).fetchone()
        assert row is not None
        assert row["subqueries_json"] is not None
        assert "SQ-" in row["subqueries_json"]
