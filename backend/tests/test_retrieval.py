from app.retrieval import DemoRetriever


def test_demo_retrieval_filters_topic_and_limits(settings) -> None:
    retriever = DemoRetriever(settings)
    results = retriever.search("How is an ischemic stroke different?", "stroke")
    assert results
    assert all(item.topic == "stroke" for item in results)
    assert len(results) <= settings.retrieval_top_k
    assert results[0].relevance >= results[-1].relevance


def test_get_source(settings) -> None:
    source = DemoRetriever(settings).get_source("DEMO-MS-01")
    assert source is not None
    assert source.topic == "multiple sclerosis"


def test_retrieval_prioritizes_medications_for_pharmacotherapy_query(settings) -> None:
    retriever = DemoRetriever(settings)
    query = "What kind of medication should I use to control parkinson disease and the reason behind it"
    results = retriever.search(query, "Parkinson's disease")
    assert len(results) >= 3

    top_chunk_ids = [r.chunk_id for r in results[:3]]
    # Must retrieve NICE NG71 First-Line Pharmacotherapy and Core Pharmacology
    assert "TRIAD-PD-L2-02-firstline-1" in top_chunk_ids
    assert "TRIAD-PD-L1-03-pharm-1" in top_chunk_ids


