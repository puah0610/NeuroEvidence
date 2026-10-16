import csv
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


def test_candidate_helpers_and_deduplication(tmp_path: Path) -> None:
    from app.ingestion import _collect_known_identifiers, _get_next_source_id_start

    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "source_id,pmcid,pmid,doi,title\n"
        "PD-001,PMC111111,1001,10.1000/1,Alpha Synuclein Mechanisms\n",
        encoding="utf-8",
    )
    candidates = tmp_path / "candidates.csv"
    candidates.write_text(
        "source_id,pmcid,pmid,doi,title\n"
        "PD-002,PMC222222,1002,10.1000/2,Tremor and Dopamine\n"
        "EP-005,PMC333333,1003,10.1000/3,Epilepsy Focal Seizures\n",
        encoding="utf-8",
    )

    known_pmcids, known_pmids, known_dois, known_titles = _collect_known_identifiers(manifest, candidates)
    assert "PMC111111" in known_pmcids
    assert "111111" in known_pmcids
    assert "PMC222222" in known_pmcids
    assert "1001" in known_pmids
    assert "10.1000/2" in known_dois

    existing_rows = [
        {"source_id": "PD-001"},
        {"source_id": "PD-002"},
        {"source_id": "EP-005"},
    ]
    assert _get_next_source_id_start(existing_rows, "PD") == 3
    assert _get_next_source_id_start(existing_rows, "EP") == 6
    assert _get_next_source_id_start(existing_rows, "ST") == 1


def test_accept_candidates(tmp_path: Path) -> None:
    from app.ingestion import accept_candidates

    manifest_file = tmp_path / "manifest.csv"
    manifest_file.write_text(
        "source_id,pmcid,pmid,doi,title,authors,year,journal,topic,url,license,included,layer,layer_name,layer_source,subtopic\n"
        "PD-001,PMC111111,1001,10.1000/1,Alpha Synuclein Mechanisms,Author A,2024,Journal A,Parkinson's disease,https://example.test/1,CC BY,yes,1,Layer 1,Bookshelf,\n",
        encoding="utf-8",
    )

    candidates_file = tmp_path / "candidates.csv"
    candidates_file.write_text(
        "source_id,pmcid,pmid,doi,title,authors,year,journal,topic,url,license,included\n"
        "PD-002,PMC222222,1002,10.1000/2,Tremor and Dopamine,Author B,2024,Journal B,Parkinson's disease,https://example.test/2,CC BY,no\n"
        "PD-003,,1003,10.1000/3,Missing PMCID Trial,Author C,2024,Journal C,Parkinson's disease,https://example.test/3,CC BY,no\n"
        "EP-001,PMC333333,1004,10.1000/4,Epilepsy Clinical Trial,Author D,2024,Journal D,epilepsy,https://example.test/4,CC BY,no\n"
        "PD-004,PMC111111,1001,10.1000/1,Duplicate Article,Author A,2024,Journal A,Parkinson's disease,https://example.test/1,CC BY,no\n",
        encoding="utf-8",
    )

    # Accept candidates with topic filter for epilepsy only
    accepted_ep = accept_candidates(
        manifest_path=manifest_file,
        candidates_path=candidates_file,
        topic="epilepsy",
    )
    assert accepted_ep == 1

    with manifest_file.open("r", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        assert rows[1]["source_id"] == "EP-001"
        assert rows[1]["included"] == "yes"
        assert rows[1]["layer"] == "3"
        assert rows[1]["layer_name"] == "Layer 3: Empirical Evidence & Trials"

    # Accept remaining candidates across all topics
    accepted_all = accept_candidates(
        manifest_path=manifest_file,
        candidates_path=candidates_file,
    )
    # PD-002 should be accepted, PD-003 skipped (no PMCID), PD-004 skipped (duplicate of PD-001), EP-001 already accepted
    assert accepted_all == 1

    with manifest_file.open("r", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 3
        source_ids = [r["source_id"] for r in rows]
        assert "PD-002" in source_ids



