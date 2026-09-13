from .models import RetrievedChunk


DEMO_CHUNKS = [
    RetrievedChunk(
        source_id="DEMO-PD-01",
        chunk_id="DEMO-PD-01-intro-1",
        document_id="DEMO-PD-01",
        title="Parkinson's Disease: Overview",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="Parkinson's disease",
        url="https://www.ninds.nih.gov/health-information/disorders/parkinsons-disease",
        license="Public information page; bundled text is a project-authored summary",
        section="Overview",
        excerpt=(
            "Parkinson's disease is a progressive neurological disorder. Its movement features commonly "
            "include tremor at rest, slowness of movement, muscular rigidity, and impaired balance. "
            "Non-motor features can include sleep, mood, autonomic, and cognitive changes."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-PD-02",
        chunk_id="DEMO-PD-02-management-1",
        document_id="DEMO-PD-02",
        title="Parkinson's Disease: Treatment Concepts",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="Parkinson's disease",
        url="https://www.ninds.nih.gov/health-information/disorders/parkinsons-disease",
        license="Public information page; bundled text is a project-authored summary",
        section="Treatment",
        excerpt=(
            "There is no single cure for Parkinson's disease, but medicines, rehabilitation, exercise, "
            "and selected surgical approaches can help manage symptoms. Management is individualized and "
            "usually involves ongoing assessment of benefits and adverse effects."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-EP-01",
        chunk_id="DEMO-EP-01-overview-1",
        document_id="DEMO-EP-01",
        title="Epilepsy and Seizures: Overview",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="epilepsy",
        url="https://www.ninds.nih.gov/health-information/disorders/epilepsy-and-seizures",
        license="Public information page; bundled text is a project-authored summary",
        section="Overview",
        excerpt=(
            "Epilepsy is a neurological disorder characterized by an enduring tendency to have unprovoked "
            "seizures. Seizures can produce motor, sensory, cognitive, autonomic, or awareness changes, and "
            "their presentation depends on the brain networks involved."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-EP-02",
        chunk_id="DEMO-EP-02-diagnosis-1",
        document_id="DEMO-EP-02",
        title="Epilepsy: Diagnostic Concepts",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="epilepsy",
        url="https://www.ninds.nih.gov/health-information/disorders/epilepsy-and-seizures",
        license="Public information page; bundled text is a project-authored summary",
        section="Diagnosis",
        excerpt=(
            "Evaluation of suspected epilepsy integrates the event history, witness descriptions, neurological "
            "assessment, electroencephalography, and often brain imaging. A single provoked seizure does not "
            "automatically establish epilepsy."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-ST-01",
        chunk_id="DEMO-ST-01-types-1",
        document_id="DEMO-ST-01",
        title="Stroke: Types and Mechanisms",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="stroke",
        url="https://www.ninds.nih.gov/health-information/disorders/stroke",
        license="Public information page; bundled text is a project-authored summary",
        section="Types",
        excerpt=(
            "An ischemic stroke results from interrupted blood flow to brain tissue, while a hemorrhagic "
            "stroke results from bleeding in or around the brain. Both can injure neurons and require urgent "
            "assessment, although their acute treatments differ."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-ST-02",
        chunk_id="DEMO-ST-02-warning-1",
        document_id="DEMO-ST-02",
        title="Stroke: Warning Signs",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="stroke",
        url="https://www.ninds.nih.gov/health-information/disorders/stroke",
        license="Public information page; bundled text is a project-authored summary",
        section="Warning signs",
        excerpt=(
            "Sudden facial weakness, arm weakness, speech difficulty, visual loss, severe imbalance, or a "
            "sudden severe headache can be warning signs of stroke. Rapid emergency assessment matters because "
            "some treatments are time-dependent."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-MS-01",
        chunk_id="DEMO-MS-01-overview-1",
        document_id="DEMO-MS-01",
        title="Multiple Sclerosis: Overview",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="multiple sclerosis",
        url="https://www.ninds.nih.gov/health-information/disorders/multiple-sclerosis",
        license="Public information page; bundled text is a project-authored summary",
        section="Overview",
        excerpt=(
            "Multiple sclerosis is an immune-mediated disorder of the central nervous system in which "
            "inflammation and damage to myelin disrupt communication along nerve pathways. Symptoms vary "
            "according to the location and extent of nervous-system injury."
        ),
        relevance=0.0,
        demo=True,
    ),
    RetrievedChunk(
        source_id="DEMO-MS-02",
        chunk_id="DEMO-MS-02-course-1",
        document_id="DEMO-MS-02",
        title="Multiple Sclerosis: Clinical Course",
        authors=["National Institute of Neurological Disorders and Stroke"],
        year=2024,
        journal="NINDS Health Information",
        topic="multiple sclerosis",
        url="https://www.ninds.nih.gov/health-information/disorders/multiple-sclerosis",
        license="Public information page; bundled text is a project-authored summary",
        section="Clinical course",
        excerpt=(
            "Multiple sclerosis can follow relapsing or progressive patterns. Disease-modifying therapies aim "
            "to reduce inflammatory disease activity or progression, while rehabilitation and symptomatic "
            "treatments address function and quality of life."
        ),
        relevance=0.0,
        demo=True,
    ),
]

