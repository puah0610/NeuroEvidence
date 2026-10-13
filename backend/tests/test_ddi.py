import pytest

from app.ddi.checker import DDIChecker
from app.ddi.client import ExternalDDIClient
from app.ddi.models import DDISeverity, InteractionMechanism


@pytest.fixture
def ddi_checker():
    return DDIChecker()


def test_drug_entity_extraction(ddi_checker):
    # Test generic names
    drugs = ddi_checker.extract_drugs("Can sodium valproate be prescribed alongside lamotrigine?")
    canonical_ids = {d.canonical_id for d in drugs}
    assert "valproate" in canonical_ids
    assert "lamotrigine" in canonical_ids

    # Test brand names
    drugs_brand = ddi_checker.extract_drugs("Patient taking Sinemet and requires an antiemetic like Maxolon.")
    canonical_brand_ids = {d.canonical_id for d in drugs_brand}
    assert "levodopa" in canonical_brand_ids
    assert "metoclopramide" in canonical_brand_ids


@pytest.mark.asyncio
async def test_valproate_lamotrigine_interaction(ddi_checker):
    report = await ddi_checker.analyze_query(
        "Can a patient on sodium valproate take lamotrigine?",
        check_live_api=False,
    )
    assert report.has_interaction is True
    assert "valproate" in report.drugs_detected
    assert "lamotrigine" in report.drugs_detected
    assert report.highest_severity == DDISeverity.major

    interaction = report.interactions_found[0]
    assert interaction.mechanism_type == InteractionMechanism.pharmacokinetic
    assert "UGT" in interaction.mechanism_detail
    assert "Stevens-Johnson" in interaction.clinical_effect
    assert "halved" in interaction.actionable_guidance or "50%" in interaction.actionable_guidance or "25 mg" in interaction.actionable_guidance


@pytest.mark.asyncio
async def test_levodopa_metoclopramide_contraindication(ddi_checker):
    report = await ddi_checker.analyze_query(
        "Is metoclopramide safe for nausea in a patient on levodopa?",
        check_live_api=False,
    )
    assert report.has_interaction is True
    assert report.highest_severity == DDISeverity.contraindicated
    assert any("domperidone" in g.lower() for g in report.actionable_guidance)


@pytest.mark.asyncio
async def test_single_drug_mention_advisory(ddi_checker):
    report = await ddi_checker.analyze_query("What are the drug interactions with carbamazepine?", check_live_api=False)
    assert report.has_interaction is False
    assert "carbamazepine" in report.drugs_detected
    assert "Specify a second medication" in report.clinical_summary


@pytest.mark.asyncio
async def test_external_ddi_client_resilience():
    # Test client handles offline/nonexistent responses gracefully without throwing
    client = ExternalDDIClient(timeout=0.01)
    res = await client.fetch_fda_interaction("nonexistentdrug123", "fakechemical456")
    assert res is None
