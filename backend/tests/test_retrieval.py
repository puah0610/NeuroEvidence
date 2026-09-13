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

