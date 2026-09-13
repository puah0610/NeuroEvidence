from pathlib import Path

from app.ingestion import ManifestRecord, parse_jats


def test_jats_parsing_is_deterministic(tmp_path: Path) -> None:
    xml = """
    <article><body><sec><title>Results</title>
    <p>First neurological result with enough words for a useful paragraph.</p>
    <p>Second paragraph preserves its section and source metadata.</p>
    </sec><sec><title>References</title><p>This must be removed.</p></sec></body></article>
    """
    path = tmp_path / "article.xml"
    path.write_text(xml, encoding="utf-8")
    record = ManifestRecord(
        source_id="TEST-1", pmcid="PMC1", pmid="1", doi="10.1/test", title="Test",
        authors="A. Author", year="2024", journal="Journal", topic="stroke",
        url="https://example.test", license="CC BY", included="yes",
    )
    first = parse_jats(path, record)
    second = parse_jats(path, record)
    assert first
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert all(item.section == "Results" for item in first)
    assert "References" not in " ".join(item.text for item in first)

