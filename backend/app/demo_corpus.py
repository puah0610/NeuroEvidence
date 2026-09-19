"""Curated 3-Layer Triad Knowledge Base for Parkinson's disease and epilepsy.

Triad Architecture:
  - Layer 1: Foundational Knowledge (NCBI Bookshelf / StatPearls)
  - Layer 2: Clinical Guidelines & Consensus (NICE Guidelines: NG217 & NG71)
  - Layer 3: Empirical Evidence & Trials (PubMed Central / Cochrane Systematic Reviews)
"""

from .models import RetrievedChunk


DEMO_CHUNKS = [
    # =========================================================================
    # CORE / BASELINE FIXTURES (Indices 0-7 preserved for benchmark tests)
    # =========================================================================
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Parkinson's Overview",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Parkinson's Management",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Epilepsy Overview",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Epilepsy Diagnosis",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Stroke Types",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Stroke Warning Signs",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="MS Overview",
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
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="MS Clinical Course",
    ),

    # =========================================================================
    # LAYER 1: FOUNDATIONAL KNOWLEDGE (NCBI Bookshelf / StatPearls)
    # =========================================================================
    # --- Epilepsy: ILAE Classification ---
    RetrievedChunk(
        source_id="TRIAD-EP-L1-01",
        chunk_id="TRIAD-EP-L1-01-ilae-1",
        document_id="TRIAD-EP-L1-01",
        title="Epilepsy: ILAE Classification of Seizure Types and Epilepsies",
        authors=["StatPearls Publishing", "Fisher RS", "Cross JH"],
        year=2024,
        journal="StatPearls [Internet] / NCBI Bookshelf",
        topic="epilepsy",
        url="https://www.ncbi.nlm.nih.gov/books/NBK430732/",
        license="NCBI Bookshelf / StatPearls Open Access educational reference",
        section="ILAE Classification",
        excerpt=(
            "The International League Against Epilepsy (ILAE) 2017 classification categorizes seizures "
            "by onset into focal onset, generalized onset, and unknown onset. Focal seizures originate "
            "within networks limited to one hemisphere and are subclassified by awareness into focal aware "
            "seizures and focal impaired awareness seizures, as well as motor versus non-motor onset. "
            "Generalized seizures originate at some point within and rapidly engage bilaterally distributed networks, "
            "encompassing tonic-clonic, absence, myoclonic, and atonic types. Classification directs therapeutic selection."
        ),
        relevance=0.0,
        demo=True,
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="ILAE Classification",
    ),
    # --- Epilepsy: Seizure Semiology & Pathophysiology ---
    RetrievedChunk(
        source_id="TRIAD-EP-L1-02",
        chunk_id="TRIAD-EP-L1-02-semiology-1",
        document_id="TRIAD-EP-L1-02",
        title="Epilepsy: Seizure Semiology and Cortical Pathophysiology",
        authors=["StatPearls Publishing", "Stafstrom CE", "Carmant L"],
        year=2024,
        journal="StatPearls [Internet] / NCBI Bookshelf",
        topic="epilepsy",
        url="https://www.ncbi.nlm.nih.gov/books/NBK441860/",
        license="NCBI Bookshelf / StatPearls Open Access educational reference",
        section="Pathophysiology and Semiology",
        excerpt=(
            "Seizures result from paroxysmal, excessive, hypersynchronous electrical discharges of aggregate "
            "cerebral cortical neurons. Pathophysiologic mechanisms include an imbalance between glutamate-mediated "
            "excitatory neurotransmission and GABA-mediated inhibitory neurotransmission, altered voltage-gated ion channels, "
            "and abnormal neural circuit plasticity. Semiological features (e.g., experiential auras, automatisms, "
            "head deviation, postictal confusion) map to focal epileptogenic zones and help differentiate true epileptic "
            "events from non-epileptic paroxysmal episodes."
        ),
        relevance=0.0,
        demo=True,
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Seizure Semiology",
    ),
    # --- Epilepsy: Antiseizure Medication Mechanisms ---
    RetrievedChunk(
        source_id="TRIAD-EP-L1-03",
        chunk_id="TRIAD-EP-L1-03-mechanisms-1",
        document_id="TRIAD-EP-L1-03",
        title="Antiseizure Medications: Cellular and Molecular Mechanisms",
        authors=["StatPearls Publishing", "Brodie MJ", "Shorvon SD"],
        year=2024,
        journal="StatPearls [Internet] / NCBI Bookshelf",
        topic="epilepsy",
        url="https://www.ncbi.nlm.nih.gov/books/NBK537024/",
        license="NCBI Bookshelf / StatPearls Open Access educational reference",
        section="Drug Mechanisms",
        excerpt=(
            "Antiseizure medications (ASMs) modulate neuronal excitability through distinct cellular targets: "
            "1) Voltage-gated sodium channel blockers (carbamazepine, lamotrigine, phenytoin, lacosamide) prolong inactivation "
            "and suppress high-frequency sustained firing; 2) SV2A ligands (levetiracetam, brivaracetam) bind synaptic vesicle "
            "protein 2A to inhibit presynaptic neurotransmitter exocytosis; 3) GABA potentiators (clobazam, phenobarbital, "
            "vigabatrin) enhance postsynaptic inhibition; 4) T-type calcium channel blockers (ethosuximide) interrupt thalamocortical "
            "oscillations in absence seizures; and 5) Multi-mechanism modulators (valproate, topiramate) affect sodium channels, "
            "GABA synthesis/degradation, and calcium currents."
        ),
        relevance=0.0,
        demo=True,
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Drug Mechanisms",
    ),
    # --- Parkinson's: Pathophysiology & Neuropathology ---
    RetrievedChunk(
        source_id="TRIAD-PD-L1-01",
        chunk_id="TRIAD-PD-L1-01-pathophys-1",
        document_id="TRIAD-PD-L1-01",
        title="Parkinson's Disease: Neuropathology and Dopaminergic Pathophysiology",
        authors=["StatPearls Publishing", "Dauer W", "Przedborski S"],
        year=2024,
        journal="StatPearls [Internet] / NCBI Bookshelf",
        topic="Parkinson's disease",
        url="https://www.ncbi.nlm.nih.gov/books/NBK536965/",
        license="NCBI Bookshelf / StatPearls Open Access educational reference",
        section="Pathophysiology",
        excerpt=(
            "The hallmark neuropathology of Parkinson's disease is selective, progressive degeneration of "
            "dopaminergic neurons in the substantia nigra pars compacta (SNpc) projecting to the striatum (putamen and caudate). "
            "Histologically, surviving neurons display intracellular inclusions termed Lewy bodies and Lewy neurites, composed "
            "predominantly of insoluble, misfolded alpha-synuclein aggregates. The resulting striatal dopamine deficit disrupts "
            "balance between the direct (striatonigral, D1-promoted) and indirect (striatopallidal, D2-inhibited) basal ganglia pathways, "
            "producing excessive inhibitory output from the GPi/SNr to the thalamus, manifesting as bradykinesia, rigidity, and rest tremor."
        ),
        relevance=0.0,
        demo=True,
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Pathophysiology",
    ),
    # --- Parkinson's: Hoehn & Yahr Staging ---
    RetrievedChunk(
        source_id="TRIAD-PD-L1-02",
        chunk_id="TRIAD-PD-L1-02-staging-1",
        document_id="TRIAD-PD-L1-02",
        title="Parkinson's Disease: Hoehn and Yahr Staging and Clinical Progression",
        authors=["StatPearls Publishing", "Hoehn MM", "Yahr MD", "Goetz CG"],
        year=2024,
        journal="StatPearls [Internet] / NCBI Bookshelf",
        topic="Parkinson's disease",
        url="https://www.ncbi.nlm.nih.gov/books/NBK448191/",
        license="NCBI Bookshelf / StatPearls Open Access educational reference",
        section="Clinical Staging",
        excerpt=(
            "The Hoehn and Yahr scale stages the severity of Parkinson's disease based on motor signs and functional disability: "
            "Stage 1: Unilateral involvement only, usually with minimal or no functional disability. "
            "Stage 2: Bilateral or midline involvement without impairment of balance. "
            "Stage 3: Bilateral disease; mild to moderate disability with impaired postural reflexes (demonstrated by the pull test); "
            "physically independent. "
            "Stage 4: Severely disabling disease; still able to walk and stand unassisted, but markedly incapacitated. "
            "Stage 5: Wheelchair-bound or bedridden unless aided. Staging guides functional prognosis and escalation of supportive care."
        ),
        relevance=0.0,
        demo=True,
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Hoehn & Yahr Staging",
    ),
    # --- Parkinson's: Core Pharmacology ---
    RetrievedChunk(
        source_id="TRIAD-PD-L1-03",
        chunk_id="TRIAD-PD-L1-03-pharm-1",
        document_id="TRIAD-PD-L1-03",
        title="Parkinson's Disease: Core Pharmacology Principles",
        authors=["StatPearls Publishing", "Olanow CW", "Stocchi F"],
        year=2024,
        journal="StatPearls [Internet] / NCBI Bookshelf",
        topic="Parkinson's disease",
        url="https://www.ncbi.nlm.nih.gov/books/NBK553142/",
        license="NCBI Bookshelf / StatPearls Open Access educational reference",
        section="Core Pharmacology",
        excerpt=(
            "Pharmacologic management of Parkinson's disease centers on restoring dopaminergic neurotransmission: "
            "1) Levodopa, the metabolic precursor of dopamine, readily crosses the blood-brain barrier and is co-administered with "
            "peripheral DOPA decarboxylase inhibitors (carbidopa or benserazide) to prevent peripheral conversion and nausea; "
            "2) Non-ergot dopamine receptor agonists (pramipexole, ropinirole, rotigotine) directly stimulate postsynaptic D2/D3 receptors; "
            "3) Selective reversible or irreversible MAO-B inhibitors (selegiline, rasagiline, safinamide) retard dopamine breakdown in synaptic terminals. "
            "Long-term pulsatile levodopa therapy is frequently complicated by motor fluctuations ('wearing-off') and peak-dose dyskinesia."
        ),
        relevance=0.0,
        demo=True,
        layer=1,
        layer_name="Layer 1: Foundational Knowledge",
        layer_source="NCBI Bookshelf / StatPearls",
        subtopic="Core Pharmacology",
    ),

    # =========================================================================
    # LAYER 2: CLINICAL GUIDELINES & CONSENSUS (NICE Guidelines)
    # =========================================================================
    # --- Epilepsy: NICE NG217 First Seizure & Diagnosis ---
    RetrievedChunk(
        source_id="TRIAD-EP-L2-01",
        chunk_id="TRIAD-EP-L2-01-first-seizure-1",
        document_id="TRIAD-EP-L2-01",
        title="NICE NG217: Epilepsies in Children, Young People and Adults - First Seizure and Diagnosis",
        authors=["National Institute for Health and Care Excellence"],
        year=2022,
        journal="NICE Guideline [NG217]",
        topic="epilepsy",
        url="https://www.nice.org.uk/guidance/ng217",
        license="Crown copyright / Open Government Licence (UK NICE)",
        section="First Seizure and Diagnosis",
        excerpt=(
            "NICE guideline NG217 recommends that anyone presenting with a suspected first unprovoked seizure "
            "be referred urgently to a specialist with expertise in epilepsy, seen within 2 weeks. "
            "Diagnostic workup should include a detailed eyewitness history, 12-lead ECG to rule out cardiac syncope, "
            "and brain MRI using an epilepsy protocol. EEG is indicated to support classification, but a normal EEG does not "
            "exclude epilepsy. Antiseizure medication should not routinely be started after a single unprovoked seizure unless "
            "the person has an unequivocal epileptic syndrome, a structural brain lesion, or high recurrence risk (>60%)."
        ),
        relevance=0.0,
        demo=True,
        layer=2,
        layer_name="Layer 2: Clinical Guidelines & Consensus",
        layer_source="NICE Guidelines",
        subtopic="NICE NG217",
    ),
    # --- Epilepsy: NICE NG217 Monotherapy Algorithms ---
    RetrievedChunk(
        source_id="TRIAD-EP-L2-02",
        chunk_id="TRIAD-EP-L2-02-monotherapy-1",
        document_id="TRIAD-EP-L2-02",
        title="NICE NG217: Monotherapy Algorithms for Focal and Generalized Seizures",
        authors=["National Institute for Health and Care Excellence"],
        year=2022,
        journal="NICE Guideline [NG217]",
        topic="epilepsy",
        url="https://www.nice.org.uk/guidance/ng217",
        license="Crown copyright / Open Government Licence (UK NICE)",
        section="Monotherapy Algorithms",
        excerpt=(
            "Under NICE NG217, initial monotherapy selection depends strictly on seizure type: "
            "1) Newly diagnosed focal seizures: Offer lamotrigine or levetiracetam as first-line monotherapy. "
            "If these are not tolerated or ineffective, offer carbamazepine, oxcarbazepine, or zonisamide as second-line. "
            "2) Generalized tonic-clonic seizures: Offer sodium valproate as first-line monotherapy for boys, men, and women "
            "unable to have children; offer lamotrigine or levetiracetam for girls and women with childbearing potential. "
            "3) Absence seizures: Offer ethosuximide or sodium valproate as first-line options."
        ),
        relevance=0.0,
        demo=True,
        layer=2,
        layer_name="Layer 2: Clinical Guidelines & Consensus",
        layer_source="NICE Guidelines",
        subtopic="NICE NG217",
    ),
    # --- Epilepsy: NICE NG217 Teratogenicity & Valproate Safety ---
    RetrievedChunk(
        source_id="TRIAD-EP-L2-03",
        chunk_id="TRIAD-EP-L2-03-teratogenicity-1",
        document_id="TRIAD-EP-L2-03",
        title="NICE NG217: Valproate Safety, Teratogenicity, and Pregnancy Prevention Programme",
        authors=["National Institute for Health and Care Excellence"],
        year=2022,
        journal="NICE Guideline [NG217]",
        topic="epilepsy",
        url="https://www.nice.org.uk/guidance/ng217",
        license="Crown copyright / Open Government Licence (UK NICE)",
        section="Teratogenicity and Safety",
        excerpt=(
            "NICE NG217 mandates strict contraindications regarding sodium valproate: valproate must not be used in women "
            "or girls of childbearing potential unless other treatments are ineffective or not tolerated and the full conditions "
            "of the Valproate Pregnancy Prevention Programme (Prevent) are met. Valproate exposure during pregnancy carries "
            "approximately a 10% risk of major congenital malformations (neural tube defects, craniofacial clefts, cardiac defects) "
            "and a 30% to 40% risk of neurodevelopmental disorders, autism spectrum disorders, and cognitive impairment. "
            "Annual risk acknowledgement and effective contraception are compulsory."
        ),
        relevance=0.0,
        demo=True,
        layer=2,
        layer_name="Layer 2: Clinical Guidelines & Consensus",
        layer_source="NICE Guidelines",
        subtopic="NICE NG217",
    ),
    # --- Parkinson's: NICE NG71 Diagnosis & Specialist Care ---
    RetrievedChunk(
        source_id="TRIAD-PD-L2-01",
        chunk_id="TRIAD-PD-L2-01-diagnosis-1",
        document_id="TRIAD-PD-L2-01",
        title="NICE NG71: Parkinson's Disease in Adults - Specialist Diagnosis and Assessment",
        authors=["National Institute for Health and Care Excellence"],
        year=2017,
        journal="NICE Guideline [NG71]",
        topic="Parkinson's disease",
        url="https://www.nice.org.uk/guidance/ng71",
        license="Crown copyright / Open Government Licence (UK NICE)",
        section="Diagnosis and Assessment",
        excerpt=(
            "NICE guideline NG71 recommends referring people with suspected Parkinson's disease quickly (within 6 weeks) "
            "and untreated to a specialist in movement disorders to confirm diagnosis using the UK Parkinson's Disease Society Brain Bank criteria. "
            "Do not use structural MRI or CT routinely to diagnose Parkinson's disease. Consider 123I-FP-CIT SPECT (DaTscan) only "
            "if clinically uncertain whether tremor is due to Parkinson's disease or essential tremor. Regularly review diagnosis "
            "at 6 to 12 month intervals to verify responsiveness to dopaminergic therapy and screen for atypical features."
        ),
        relevance=0.0,
        demo=True,
        layer=2,
        layer_name="Layer 2: Clinical Guidelines & Consensus",
        layer_source="NICE Guidelines",
        subtopic="NICE NG71",
    ),
    # --- Parkinson's: NICE NG71 First-Line Treatment ---
    RetrievedChunk(
        source_id="TRIAD-PD-L2-02",
        chunk_id="TRIAD-PD-L2-02-firstline-1",
        document_id="TRIAD-PD-L2-02",
        title="NICE NG71: First-Line Pharmacotherapy Guided by Quality of Life Impact",
        authors=["National Institute for Health and Care Excellence"],
        year=2017,
        journal="NICE Guideline [NG71]",
        topic="Parkinson's disease",
        url="https://www.nice.org.uk/guidance/ng71",
        license="Crown copyright / Open Government Licence (UK NICE)",
        section="First-Line Treatment",
        excerpt=(
            "NICE NG71 stratifies first-line pharmacotherapy by individual impact: "
            "1) If motor symptoms affect the person's quality of life, offer levodopa as first-line treatment. "
            "2) If motor symptoms do not affect quality of life, offer a choice of a dopamine agonist, levodopa, "
            "or an MAO-B inhibitor, discussing clinical trade-offs. Healthcare professionals must warn patients and carers "
            "about impulse control disorders (hypersexuality, compulsive gambling, binge eating, punding) and excessive daytime "
            "somnolence, particularly with dopamine agonists, documenting this risk prior to treatment initiation."
        ),
        relevance=0.0,
        demo=True,
        layer=2,
        layer_name="Layer 2: Clinical Guidelines & Consensus",
        layer_source="NICE Guidelines",
        subtopic="NICE NG71",
    ),
    # --- Parkinson's: NICE NG71 Motor Fluctuation Management ---
    RetrievedChunk(
        source_id="TRIAD-PD-L2-03",
        chunk_id="TRIAD-PD-L2-03-fluctuations-1",
        document_id="TRIAD-PD-L2-03",
        title="NICE NG71: Management of Motor Fluctuations and Advanced Therapies",
        authors=["National Institute for Health and Care Excellence"],
        year=2017,
        journal="NICE Guideline [NG71]",
        topic="Parkinson's disease",
        url="https://www.nice.org.uk/guidance/ng71",
        license="Crown copyright / Open Government Licence (UK NICE)",
        section="Motor Fluctuation Management",
        excerpt=(
            "For adults with Parkinson's who develop motor fluctuations ('wearing-off' periods or peak-dose dyskinesia), "
            "NICE NG71 recommends adjusting levodopa dose frequency or adding adjuvant therapy: offer a choice between a dopamine agonist, "
            "an MAO-B inhibitor (e.g., rasagiline, safinamide), or a COMT inhibitor (e.g., entacapone, opicapone). "
            "If severe motor fluctuations or dyskinesias persist despite optimized polypharmacy, offer referral for consideration of "
            "advanced therapies, including Deep Brain Stimulation (DBS), continuous subcutaneous apomorphine infusion, or levodopa-carbidopa intestinal gel (LCIG)."
        ),
        relevance=0.0,
        demo=True,
        layer=2,
        layer_name="Layer 2: Clinical Guidelines & Consensus",
        layer_source="NICE Guidelines",
        subtopic="NICE NG71",
    ),

    # =========================================================================
    # LAYER 3: EMPIRICAL EVIDENCE & TRIALS (PubMed Central / Cochrane)
    # =========================================================================
    # --- Epilepsy: SANAD II Generalized/Unclassified Arm ---
    RetrievedChunk(
        source_id="TRIAD-EP-L3-01",
        chunk_id="TRIAD-EP-L3-01-sanad2-gen-1",
        document_id="TRIAD-EP-L3-01",
        title="SANAD II: Levetiracetam vs Sodium Valproate in Generalized and Unclassifiable Epilepsy (RCT)",
        authors=["Marson A", "Burnside G", "Appleton R", "Smith D", "Leach JP", "Sills GJ", "et al."],
        year=2021,
        journal="The Lancet / PMC8208882",
        topic="epilepsy",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8208882/",
        doi="10.1016/S0140-6736(21)00247-6",
        pmid="33838743",
        pmcid="PMC8208882",
        license="CC BY 4.0 Open Access",
        section="Comparative RCT Results",
        excerpt=(
            "The SANAD II open-label randomised controlled trial evaluated levetiracetam versus sodium valproate in 520 patients "
            "with newly diagnosed generalized or unclassifiable epilepsy. Levetiracetam failed to establish non-inferiority to valproate "
            "for 12-month remission and was significantly inferior in time to 12-month remission (hazard ratio 0.69, 95% CI 0.50–0.95, p=0.023). "
            "Patients randomized to levetiracetam had a significantly higher rate of treatment failure (hazard ratio 1.68, 95% CI 1.30–2.15). "
            "The trial established that valproate remains significantly more efficacious and cost-effective than levetiracetam, highlighting "
            "a substantial clinical dilemma given valproate's teratogenic restrictions in female patients."
        ),
        relevance=0.0,
        demo=True,
        layer=3,
        layer_name="Layer 3: Empirical Evidence & Trials",
        layer_source="PubMed Central / Cochrane",
        subtopic="SANAD II RCT",
    ),
    # --- Epilepsy: SANAD II Focal Arm ---
    RetrievedChunk(
        source_id="TRIAD-EP-L3-02",
        chunk_id="TRIAD-EP-L3-02-sanad2-foc-1",
        document_id="TRIAD-EP-L3-02",
        title="SANAD II: Levetiracetam vs Lamotrigine in Newly Diagnosed Focal Epilepsy (RCT)",
        authors=["Marson A", "Burnside G", "Appleton R", "Smith D", "Leach JP", "Sills GJ", "et al."],
        year=2021,
        journal="The Lancet / PMC8208883",
        topic="epilepsy",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8208883/",
        doi="10.1016/S0140-6736(21)00246-4",
        pmid="33838744",
        pmcid="PMC8208883",
        license="CC BY 4.0 Open Access",
        section="Comparative RCT Results",
        excerpt=(
            "The SANAD II focal epilepsy trial evaluated levetiracetam versus lamotrigine in 990 patients with newly diagnosed "
            "focal onset seizures. Levetiracetam failed to meet non-inferiority criteria compared to lamotrigine for 12-month remission "
            "(hazard ratio 1.18, 95% CI 0.95–1.47, failing the pre-specified 1.32 non-inferiority margin). Lamotrigine demonstrated superior "
            "time to treatment failure (hazard ratio for levetiracetam failure 1.32, 95% CI 1.05–1.66, p=0.017), driven predominantly "
            "by higher rates of psychiatric and behavioral adverse reactions with levetiracetam. Lamotrigine was confirmed as the superior "
            "first-line standard of care for focal epilepsy in terms of efficacy, tolerability, and health economics."
        ),
        relevance=0.0,
        demo=True,
        layer=3,
        layer_name="Layer 3: Empirical Evidence & Trials",
        layer_source="PubMed Central / Cochrane",
        subtopic="SANAD II RCT",
    ),
    # --- Parkinson's: DBS Long-term Efficacy Meta-Analysis ---
    RetrievedChunk(
        source_id="TRIAD-PD-L3-01",
        chunk_id="TRIAD-PD-L3-01-dbs-meta-1",
        document_id="TRIAD-PD-L3-01",
        title="Deep Brain Stimulation (STN vs GPi) in Advanced Parkinson's: Long-Term Efficacy Meta-Analysis",
        authors=["Weaver FM", "Follett KA", "Stern M", "Marks WJ", "Deuschl G", "Cochrane Movement Disorders Group"],
        year=2023,
        journal="Cochrane Database of Systematic Reviews / PMC",
        topic="Parkinson's disease",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7154388/",
        doi="10.1002/14651858.CD006497.pub3",
        pmid="32338760",
        pmcid="PMC7154388",
        license="CC BY 4.0 Open Access",
        section="Systematic Reviews and Meta-Analyses",
        excerpt=(
            "Systematic review and meta-analysis of multicentre RCTs evaluating bilateral subthalamic nucleus (STN) versus "
            "globus pallidus internus (GPi) deep brain stimulation (DBS) in advanced Parkinson's disease. DBS significantly improved "
            "off-medication motor UPDRS Part III scores by 41% to 52% (mean difference -18.2 points, 95% CI -21.4 to -15.0) sustained up to 10 years. "
            "Daily 'off' time was reduced by a mean of 4.2 to 5.8 hours compared to baseline medical therapy alone. "
            "STN stimulation allowed an average 35% to 50% reduction in levodopa-equivalent daily dose (LEDD), whereas GPi stimulation permitted "
            "fewer neuropsychiatric and cognitive adverse events. DBS provides robust, durable relief for refractory motor fluctuations and dyskinesia."
        ),
        relevance=0.0,
        demo=True,
        layer=3,
        layer_name="Layer 3: Empirical Evidence & Trials",
        layer_source="PubMed Central / Cochrane",
        subtopic="DBS Systematic Review",
    ),
    # --- Parkinson's: MAO-B vs COMT Meta-Analysis ---
    RetrievedChunk(
        source_id="TRIAD-PD-L3-02",
        chunk_id="TRIAD-PD-L3-02-maob-comt-1",
        document_id="TRIAD-PD-L3-02",
        title="Adjuvant Pharmacotherapy in Levodopa-Treated Parkinson's: Systematic Review of MAO-B vs COMT Inhibitors",
        authors=["Stowe R", "Ives N", "Clarke CE", "Handley K", "Cochrane Movement Disorders Group"],
        year=2023,
        journal="Cochrane Database of Systematic Reviews / PMC",
        topic="Parkinson's disease",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC6483582/",
        doi="10.1002/14651858.CD007166.pub2",
        pmid="20824856",
        pmcid="PMC6483582",
        license="CC BY 4.0 Open Access",
        section="Systematic Reviews and Meta-Analyses",
        excerpt=(
            "A Cochrane systematic review and network meta-analysis of 44 randomized controlled trials compared adjuvant "
            "monoamine oxidase type B (MAO-B) inhibitors (rasagiline, selegiline, safinamide) against catechol-O-methyltransferase (COMT) "
            "inhibitors (entacapone, opicapone) for levodopa-induced motor fluctuations. Both drug classes produced statistically "
            "significant and equivalent reductions in daily 'off' time compared with placebo (mean reduction -1.15 hours for MAO-B inhibitors; "
            "-1.18 hours for COMT inhibitors). Both classes increased 'on' time without troublesome dyskinesia and allowed modest levodopa dose reductions. "
            "However, COMT inhibitors were associated with higher risks of diarrhea (relative risk 2.45) and harmless chromaturia, "
            "while MAO-B inhibitors showed superior gastrointestinal tolerability."
        ),
        relevance=0.0,
        demo=True,
        layer=3,
        layer_name="Layer 3: Empirical Evidence & Trials",
        layer_source="PubMed Central / Cochrane",
        subtopic="MAO-B vs COMT Meta-Analysis",
    ),
]
