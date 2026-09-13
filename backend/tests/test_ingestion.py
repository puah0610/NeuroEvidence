import csv
from pathlib import Path

from app.ingestion import ManifestRecord, export_asreview, parse_jats, sync_asreview


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


def test_asreview_export_and_sync(tmp_path: Path) -> None:
    candidates_file = tmp_path / "candidates.csv"
    manifest_file = tmp_path / "manifest.csv"
    asreview_pool = tmp_path / "asreview_pool.csv"
    asreview_export = tmp_path / "asreview_export.csv"

    # Write mock candidates
    candidates_content = (
        "source_id,pmcid,pmid,doi,title,authors,year,journal,topic,url,license,included\n"
        "PD-001,PMC100,1234,10.1/pd1,Parkinson Motor Symptoms,Author A,2024,Neurology,Parkinson's disease,https://example.test/1,CC BY,no\n"
        "EP-001,PMC200,5678,10.1/ep1,Epilepsy Seizure Types,Author B,2024,Epilepsia,epilepsy,https://example.test/2,CC BY,no\n"
    )
    candidates_file.write_text(candidates_content, encoding="utf-8")

    # Export to ASReview pool (no network fetch)
    export_asreview(candidates_file, asreview_pool, fetch_abstracts=False)
    assert asreview_pool.exists()
    with asreview_pool.open("r", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        assert "abstract" in rows[0]
        assert "title" in rows[0]

    # Mock ASReview user screening decision (include PD-001, exclude EP-001)
    asreview_export_content = (
        "source_id,title,included\n"
        "PD-001,Parkinson Motor Symptoms,1\n"
        "EP-001,Epilepsy Seizure Types,0\n"
    )
    asreview_export.write_text(asreview_export_content, encoding="utf-8")

    # Sync back to manifest
    sync_asreview(asreview_export, manifest_file, candidates_file)
    assert manifest_file.exists()
    with manifest_file.open("r", encoding="utf-8-sig") as handle:
        synced = list(csv.DictReader(handle))
        assert len(synced) == 1
        assert synced[0]["source_id"] == "PD-001"
        assert synced[0]["included"] == "yes"


