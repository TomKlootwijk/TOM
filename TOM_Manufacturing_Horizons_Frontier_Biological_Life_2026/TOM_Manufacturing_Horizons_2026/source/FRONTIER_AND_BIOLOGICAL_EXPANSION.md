
\newpage
# Part II - Expanded manufacturing horizon

# 1. What changes when the substrate is treated as complete

For this report, "complete" means **complete for the frozen deterministic authority contract**: exact seed identity, content-addressed definitions, explicit operator order, bounded evaluation, support and compatibility gates, event/transition semantics, lineage, fixed TOMAGI execution and authenticated finite output. It does not mean that the substrate contains all scientific knowledge, all machine models, all biological developmental laws, or every future manufacturing process.

That distinction shifts the development problem. Instead of repeatedly redesigning the kernel for every new domain, a future programme builds four things around it:

1. a **domain pack** that states product, material, process, evidence and acceptance definitions;
2. a **mechanical adapter** that transports data and invokes machines or external models without deciding semantic truth;
3. an **independent oracle**--a simulator, theorem prover, measurement system, clinical assay or second implementation--that can falsify the formal authority; and
4. a **phenotype system** that turns accepted definitions into software, motion, matter, tissue, organisms, habitats or other artifacts.

The completed substrate therefore behaves less like a universal factory and more like a universal **manufacturing constitution**. It determines how identities are named, how proposals enter, how evidence is evaluated, how a state changes, how revisions inherit, and how claims can be reconstructed. Domain science still determines whether a turbine blade survives, a catalyst works, a kidney filters blood, or a synthetic organism remains ecologically contained.

## 1.1 The proof-carrying object

A conventional product may have a drawing, serial number, certificate and scattered quality documents. A proof-carrying product has an executable and queryable causal envelope:

```text
product identity
+ parent design and authorised substitutions
+ material and component lots
+ machine capability and calibration state
+ process events and environmental conditions
+ sensor and metrology observations
+ explicit deviations and concessions
+ acceptance / rejection / ambiguity certificate
+ repair, update and end-of-life lineage
```

For a software image, the envelope can end in exact bytes. For a machined part, it ends in a physical object plus metrology evidence. For a tissue or organ, it ends in a living construct plus biological measurements, clinical constraints and longitudinal follow-up. The physical phenotype is never reducible to the certificate, but the certificate makes every admitted claim inspectable.

## 1.2 Manufacturing as parent-bound evolution

A future TOM-governed factory can treat every released design as a parent commit. A proposed change must identify its parent, declare affected definitions, run the required regressions, preserve counterexamples and publish atomically. That is a powerful general model for:

- firmware and machine configurations;
- mechanical design revisions;
- material formulations;
- cell lines and differentiation protocols;
- tissue architectures;
- therapeutic product batches;
- synthetic-organism designs;
- off-world habitat modules;
- self-repair rules for long-lived infrastructure.

The analogy to biological inheritance is structural rather than rhetorical: stable identity, versioned genes/definitions, bounded developmental programmes, environmental context, viability gates, expressed phenotype and retained lineage.

# 2. A general architecture for literal manufacturing

A complete TOM manufacturing deployment can be expressed as six interlocking planes.

| Plane | Authoritative objects | External or physical counterparts |
|---|---|---|
| **Definition plane** | Product, material, machine, process, support, compatibility, guard and policy definitions | Standards, CAD, recipes, biological specifications, approved operating envelopes |
| **Proposal plane** | Candidate design, model, schedule, protocol, mutation, repair or intervention | AI output, human design, simulation result, robot plan, lab result |
| **Execution plane** | Compiled state machine, expected events, permitted transitions | CNC/AM machine, robot, bioreactor, laboratory instrument, organ perfusion system |
| **Observation plane** | Typed measurement records, uncertainty, provenance and calibration | Sensors, microscopy, imaging, sequencing, metrology, assays, operator reports |
| **Authority plane** | Support, compatibility, guard, acceptance/rejection/ambiguity and publication | Quality decision, clinical release, process continuation, quarantine, recall |
| **Lineage plane** | Immutable ancestry, supersession, repair, maintenance and retirement | Digital product passport, batch history, organ follow-up, ecological monitoring |

This architecture remains viable when the external world is noisy. Determinism applies to how a declared observation and uncertainty record is processed, not to whether nature produces the same measurement every time. A TOM-compatible uncertainty model must therefore be explicit: intervals, distributions, calibration records, confidence evidence and unresolved ambiguity remain first-class objects rather than hidden thresholds.

## 2.1 The smallest deployable stack

A practical first system needs no new silicon:

```text
ordinary workstation or server
+ content-addressed local store
+ repaired Python/C TOMAGI pair
+ domain schemas and definitions
+ command adapter to an existing simulator or machine
+ imported measurement files
+ explicit release certificate
```

This already supports reproducible research, virtual manufacturing, configuration release, material-screening governance, 3D-print workflows, digital twins and laboratory evidence systems.

## 2.2 The later physical stack

A production-grade embodiment could add:

```text
secure boot and measured software
hardware key and monotonic counter
isolated industrial network gateway
calibrated sensor acquisition
real-time machine interface
independent safety PLC or interlock
read-only authority mirrors
signed immutable export bundles
```

None of those additions changes the frozen TOMAGI semantics. They strengthen the physical chain of custody and the ability to associate a machine event with the correct formal state.

# 3. Digital and software manufacturing beyond ordinary DevOps

Software is the first domain where the phenotype can be compared byte-for-byte with its formal artifact. That makes it the ideal proving ground for manufacturing authority.

## 3.1 Proof-carrying software factory

A mature TOM software factory can manufacture:

- reproducible operating-system images;
- verified firmware and bootloaders;
- FPGA bitstreams;
- container and virtual-machine images;
- database migrations;
- machine-control recipes;
- protocol and authorization state machines;
- AI model releases and benchmark datasets;
- scientific workflow bundles;
- safety-case evidence packages.

Every release would include the exact source graph, toolchain identity, dependency bytes, build environment, test results, security analyses, exception records and parent-bound publication certificate. A field device could reject an update whose lineage does not descend from an authorised parent or whose required evidence is missing.

## 3.2 Definition-manufacturing as a new industry

The product may be a **definition pack** rather than an executable. Examples include:

| Definition product | Function |
|---|---|
| Machine capability pack | Declares axes, work volume, materials, tolerances, sensing, calibration and permitted commands |
| Material identity pack | Declares composition ranges, processing history, property evidence and compatibility constraints |
| Organ manufacturing pack | Declares cell sources, architecture, maturation milestones, release assays and clinical boundary conditions |
| Synthetic-organism pack | Declares genome/design identity, containment, dependencies, lifecycle, permitted environment and kill-independent external controls |
| Habitat pack | Declares structural modules, resources, maintenance rules, biological loops and emergency states |
| Regulatory pack | Encodes explicit applicability, evidence and approval conditions for one jurisdiction and version |

Definition manufacturing could itself become a regulated profession. A pack is reviewed, tested against counterexamples, compared with independent baselines and promoted only when its scope is explicit.

## 3.3 Deterministic AI governance as manufacturing

Generative models can manufacture candidate code, CAD, molecules, protocols and process plans, but they should remain proposal systems. TOM can provide the gate:

```text
model and prompt identity
-> candidate bytes or structured proposal
-> schema and policy validation
-> independent simulation/tests
-> contradiction and regression checks
-> accept / reject / ambiguous
-> parent-bound release
```

This permits rapid AI-assisted design without allowing a model's hidden state to become manufacturing authority.

# 4. Computing hardware and cyber-physical embodiments

## 4.1 FPGA reference accelerator

The clearest near-term hardware is a literal TOMAGI step engine on an FPGA. The hardware pipeline can read one `State64`, fetch one `Cell48`, execute one of sixteen integer opcodes, select a successor and write the next state. A reference design could expose a memory-mapped command queue and support many independent state lanes sharing one read-only cell table.

The engineering proof burden is strict:

1. synthesize the logic from a pinned HDL source;
2. generate a reproducible bitstream where the toolchain permits it;
3. run canonical `.tmg` vectors through Python, C and FPGA;
4. compare every state word and lineage transition;
5. retain timing and power measurements as performance evidence only;
6. keep CPU replay as authority until equivalence is demonstrated across corner cases.

## 4.2 RISC-V co-processor and custom silicon

A later co-processor could implement:

- exact contiguous and Morton key codecs;
- sorted LUT lookup or associative key search;
- `mix32`, rotations and lineage update;
- cyclic signed differences;
- one complete `Cell48` transition;
- authenticated `EMIT` stream generation;
- immutable-record hashing and verification.

Custom instructions should accelerate existing semantics, not create new domain meaning. An ASIC or chiplet becomes valuable when millions of independent states, event candidates or product records must be evaluated with bounded latency and energy.

## 4.3 Sensor and actuator authority modules

Physical manufacturing requires interfaces to imperfect instruments. A TOM sensor hub would not claim that a measurement is correct merely because it was hashed. It would bind:

```text
sensor model and serial
firmware and calibration version
sampling schedule
environment and mounting
raw bytes
conversion and uncertainty model
quality flags
clock source
chain of custody
```

An actuator-command gate would perform the inverse: a formally accepted action becomes a typed command, but a certified safety controller, hard limits and emergency stop remain separate. This respects the no-hidden-failsafe kernel while providing physical safety outside it.

# 5. Conventional physical manufacturing transformed

## 5.1 Additive and subtractive manufacturing

A TOM-governed additive build can treat each layer or exposure block as a finite event, while preserving the identities of powder/resin/filament, machine state, scan strategy, atmosphere, thermal history and in-situ sensing. The final release certificate can link dimensional inspection, porosity evidence, mechanical coupons and any accepted deviation.

For CNC manufacture, the same model binds stock, fixture, tool, tool-life state, offsets, tool path, spindle/load observations, probing, coordinate-measuring-machine data and final inspection. A repair produced years later can descend from the original definition and state exactly which interfaces and performance assumptions remain valid.

## 5.2 Proof-carrying metamaterials

Mechanical metamaterials and architected lattices derive behaviour from geometry as much as composition. A TOM domain pack can keep candidate topology, unit-cell family, boundary conditions, numerical solver, mesh convergence, print orientation, defects and measured response in one lineage.

Near-term products include lightweight absorbers, compliant mechanisms, tuned acoustic structures, auxetic components and graded thermal/mechanical lattices. Farther systems include reconfigurable structures whose topology changes under explicit event rules. The substrate would govern the accepted configuration graph and evidence, while mechanics remains external.

## 5.3 Remanufacture and circular industry

A particularly strong use is product afterlife. Every component can carry an identity and permitted state transitions:

```text
in service
-> inspected
-> fit for continued use | repairable | remanufacturable | recyclable | rejected
-> authorised process
-> new child product
```

The system can answer which material lot, firmware version, process deviation or supplier affects a population of descendants. This creates a practical foundation for high-integrity spare-part networks, refurbishment, recycling and materials passports.

# 6. Chemical and materials manufacturing

## 6.1 Autonomous laboratories with formal authority

Robotic chemistry has already demonstrated autonomous movement, experiment execution and goal-driven materials workflows. A mobile robotic chemist was reported in 2020, and the A-Lab autonomous materials platform in 2023 combined computation, literature data, machine learning and robotics for inorganic synthesis [R13, R14]. These systems illustrate the phenotype/oracle layer that TOM could govern.

A TOM materials foundry would separate:

```text
candidate generator        external ML, literature mining or human scientist
experimental planner       external optimizer, constrained by a formal domain pack
robotic execution          mechanical service
measurement                diffraction, spectroscopy, microscopy, thermal or mechanical assay
acceptance authority       explicit support / compatibility / guard and regression evidence
publication                immutable material definition and batch lineage
```

The formal layer can ensure that a discovery claim names the exact precursors, equipment, environmental conditions, analysis software and counterexamples. It does not replace chemical expertise or laboratory safety.

## 6.2 New materials enabled by a long deterministic evidence chain

The chain can support research and eventual manufacture of:

| Material family | Plausible target | Principal unresolved evidence |
|---|---|---|
| Architected composites | High stiffness-to-weight, impact absorption, thermal management | Defect sensitivity, fatigue, scalable quality control |
| Self-healing polymers | Damage-triggered repair cycles | Long-term durability, repeatability, toxicity, process integration |
| Shape-memory systems | Programmed deployment or actuation | Cycling stability, hysteresis, environmental robustness |
| High-entropy alloys | Extreme temperature, wear or radiation performance | Predictive process-structure-property models |
| Solid electrolytes | Safer, higher-energy storage | Interfaces, dendrites, manufacturability, lifetime |
| Catalytic porous materials | Selective conversion, carbon capture, separations | Stability, poisoning, synthesis reproducibility |
| Living-mineral composites | Self-grown or self-repairing structural matter | Containment, environmental dependence, certification |
| Biohybrid conductive materials | Sensing or adaptive interfaces | Integration, degradation, immune/ecological effects |
| Radiation-resistant composites | Spacecraft and reactor components | Multiscale damage evidence and long-duration testing |
| Recyclable thermosets | Circular high-performance structures | Industrial processing and property retention |

## 6.3 Molecular and nanoscale machines

Artificial molecular motors and DNA-based walkers show that directed nanoscale motion and track-following are physically real, while DNA nanotechnology demonstrates programmable assembly and robotic interaction [R15, R16]. These are not general-purpose molecular factories, but they establish several ingredients:

- molecular components can change state in response to chemical or optical energy;
- tracks and binding sites can encode local routes;
- strand-displacement logic can implement finite decisions;
- DNA origami can position nanoscale components;
- populations can perform massively parallel operations.

A future TOM mapping could compile a bounded state graph into a molecular device, then compare measured ensemble behaviour with the electronic authority. The molecular phenotype would likely be stochastic at the individual level; deterministic authority would operate over declared distributions, intervals and acceptance criteria.

\begin{futurebox}
A **molecular assembly line** compatible with known chemistry could move a substrate through a finite sequence of binding, reaction and release stations. A TOM definition pack would specify the route, permitted intermediates and analytical acceptance evidence. What does not yet exist is a universal atom-by-atom factory able to manufacture arbitrary macroscopic objects from raw feedstock.
\end{futurebox}

# 7. Biochemical manufacturing and programmable living matter

Biomanufacturing introduces a fundamental asymmetry: the controller and evidence graph can be deterministic, while the phenotype develops through noisy, context-dependent cellular processes. TOM is therefore most valuable as a **developmental and release authority**, not as a claim that life behaves like fixed software.

## 7.1 The biochemical manufacturing stack

```text
biological design identity
-> donor, cell line, strain or molecular construct identity
-> protocol and instrument definitions
-> culture or reaction observations
-> intermediate identity and purity evidence
-> functional assays and counterexamples
-> explicit release or rejection
-> batch, patient or environmental lineage
```

The same stack applies to fermentation, enzymes, antibodies, cell-free systems, diagnostics, cell therapies, engineered tissues and living materials.

## 7.2 Cell-free biomanufacturing

Cell-free systems use extracted or reconstituted biological machinery rather than a reproducing organism. They are attractive for proof-carrying manufacture because the reaction can be defined as a finite set of components, conditions and measurements. Future uses include on-demand proteins, enzymes, diagnostics, biomaterials and distributed production in constrained environments.

TOM could govern reagent identity, template identity, reaction programme, measurement schedule, yield and activity criteria, contamination checks and batch publication. It would not determine biochemical correctness without experimental assays.

## 7.3 Engineered living materials

Research has demonstrated materials grown from engineered microbial co-cultures and printable microbial inks made from engineered protein nanofibres [R9, R10]. These systems point toward materials that can grow, sense, secrete catalysts, respond to their environment or repair damage.

Potential manufactured classes include:

| Living-material class | Function | Maturity |
|---|---|---|
| Self-grown catalytic membranes | Produce or immobilize enzymes for conversion and sensing | Early research |
| Living filtration media | Detect or transform target chemicals under containment | Early research |
| Self-repairing concrete or composites | Biological mineral deposition at cracks | Engineering/research |
| Printable microbial structures | Shape-retaining living inks with programmed secretion | Early research |
| Responsive biosensing surfaces | Change optical/electrical signal when exposed to a target | Research |
| Carbon-fixing building skins | Couple structural substrate with contained photosynthetic modules | Major research frontier |
| Self-growing habitat panels | Grow local structural or insulating material from feedstock | Known-physics-compatible, distant |
| Living radiation shields | Maintain or regenerate protective biomaterial in high-radiation environments | Research/speculative |

The central challenge is containment. A living material must have a defined permitted environment, nutrient dependence, reproductive behaviour, failure modes, sterilization/deactivation pathway, ecological monitoring and end-of-life rule.

# 8. Functional tissue and organ manufacturing

The word "organ" should be used carefully. A printed shape resembling a heart is not a transplantable heart. A clinically functional organ requires architecture, cell diversity, vascular and lymphatic networks, electrical or neural integration, mechanical competence, immune compatibility, maturation, sterile manufacture and long-term performance.

![A proof-carrying organ requires a chain from cell identity through architecture, integration, maturation, release and lifelong monitoring.](figures/organ_chain.png){width=100%}

## 8.1 What has already been demonstrated

Several important precursors are real:

- multivascular networks have been fabricated in biocompatible hydrogels [R5];
- dense organ-specific tissues with embedded vascular channels have been biomanufactured [R6];
- personalized thick and perfusable cardiac patches and heart-shaped constructs have been printed [R7];
- organoids can model aspects of brain, liver, kidney, intestine and other tissues, and scalable cortical-organoid production has been reported [R17];
- stem-cell-derived islet-cell therapies have reached clinical reports for type 1 diabetes [R18, R19];
- gene-edited porcine kidney xenotransplantation in a living recipient has been reported in the clinical literature [R20];
- an extra-uterine system sustained extremely premature lambs in a research setting [R8].

None of these equals general replacement-organ manufacture. Together, however, they show that the frontier has moved from inert scaffolds toward perfused tissue, organized cell populations, functional endocrine cell replacement, cross-species organ engineering and physiological life-support environments.

## 8.2 The organ-foundry chain

A TOM-compatible organ foundry would need explicit state and evidence at each stage:

```text
1. clinical need and recipient context
2. source-cell identity, consent and genomic/epigenetic characterization
3. differentiation and expansion records
4. component tissue modules and spatial architecture
5. perfusable vascular hierarchy and endothelial integrity
6. lymphatic, immune and stromal support
7. innervation or electrical conduction where required
8. mechanical, metabolic and endocrine maturation
9. sterility, identity, potency and tumorigenicity evidence
10. compatibility and implantation plan
11. post-implant monitoring, revision and lineage
```

TOM's contribution is a literal acceptance graph that prevents a failed or ambiguous stage from being silently averaged away. Each organ can carry the exact identities of cell populations, scaffold materials, bioreactor conditions, assays, imaging, model predictions and clinical decisions.

## 8.3 Organ classes by increasing difficulty

| Organ/tissue class | Why it is comparatively tractable or difficult | Plausible horizon class |
|---|---|---|
| Skin, cornea, cartilage | Thin or avascular/low-vascular structures; simpler geometry and integration | A/B |
| Bone, tendon, ligament | Mechanical load and vascular integration matter, but architecture is comparatively constrained | B/C |
| Vascular grafts | Luminal integrity, thrombosis, compliance and long-term remodeling dominate | B/C |
| Cardiac patches | Local contractility and vascularization without replacing the whole organ | A/B/C |
| Endocrine cell implants | Function may come from dispersed or encapsulated cells rather than full organ geometry | A/B/C |
| Liver support tissue | Complex metabolism and vascular exchange; partial support may precede replacement | C |
| Kidney support modules | Filtration, reabsorption, secretion, vascular pressure and urinary outflow must be integrated | C |
| Lung tissue | Huge gas-exchange area, thin barrier, vascular coupling and mechanical cycling | C/D |
| Whole heart | Electromechanical architecture, conduction, valves, perfusion and immediate load | C/D |
| Whole kidney/liver/lung | Multiscale vascular and functional architecture plus integration | C/D |
| Brain replacement | Identity, connectivity, development, consciousness and ethics make the concept qualitatively different | E for replacement; organoids remain research models |

## 8.4 New functional organs not present in natural anatomy

The combination of tissue engineering, synthetic biology, implantable electronics and external computation makes **novel auxiliary organs** physically conceivable. These are research concepts, not medical proposals.

| Novel organ concept | Intended function | Physical basis | Critical barriers |
|---|---|---|---|
| **Therapeutic gland** | Sense a biomarker and secrete a regulated therapeutic molecule | Engineered endocrine cells, encapsulation, feedback control | Immune escape, drift, overdose, reversibility |
| **Detoxification organ** | Bind or metabolize a narrow toxin class | Hepatic/enzymatic modules, adsorption matrices, perfusion | Selectivity, by-products, saturation, clotting |
| **Metabolic buffer organ** | Smooth glucose, lactate, ammonia or lipid excursions | Engineered cell populations with controlled uptake/release | Whole-body feedback, energy supply, long-term stability |
| **Synthetic immune sentinel** | Detect a defined pathogen or cancer marker and trigger a local response | Engineered immune or stromal cells, biosensors | Off-target activation, evolution, autoimmunity |
| **Regeneration-support organ** | Secrete timed growth and immune-modulating signals after injury | Programmed cell modules with external shutoff/removal | Fibrosis, tumor risk, spatial control |
| **Auxiliary oxygenator** | Supplement gas exchange during disease or extreme environments | Vascularized thin membranes, oxygen-carrying fluids | Surface area, thrombosis, mechanics, infection |
| **Radioprotective organ** | Produce protective metabolites or repair-support factors during radiation exposure | Engineered metabolic tissue or symbiont | Efficacy, mutation, systemic side effects |
| **Nutrient-synthesis symbiont** | Manufacture a limited essential nutrient from available substrates | Contained microbial or engineered cellular compartment | Containment, dosing, ecological interaction |
| **Electro-biological interface organ** | Translate neural/physiological signals to electronic or optical output | Neuron/muscle/electrode interfaces, optogenetic or electrochemical transduction | Stable interfaces, interpretation, ethics |
| **Magneto/chemical sensory organ** | Add a narrow new sensory channel | Engineered receptors plus neural/electronic transduction | Brain integration, signal meaning, long-term safety |
| **Internal dialysis support organ** | Continuously process a restricted waste stream | Microfluidic membranes, renal cells, sorbents | Fouling, vascular access, regeneration |
| **Drug-manufacturing implant** | Produce a medicine locally under an explicit control policy | Cell factory, microfluidics, biosensors | Dose authority, mutation, immune isolation, recall |

\begin{boundarybox}
A new organ cannot be certified by software alone. It would require preclinical evidence, manufacturing controls, long-term animal studies where ethically justified, clinical trials, regulatory approval, informed consent and continuous surveillance. Heritable human modification and enhancement raise additional governance questions; WHO recommendations emphasize safety, effectiveness, ethics, registries and international oversight [R21].
\end{boundarybox}

## 8.5 Organs as distributed systems

A farther but plausible shift is that an "organ" need not be one implant. It could be a distributed system of:

- implanted cell modules;
- external or wearable perfusion hardware;
- biosensors;
- replaceable cartridges;
- software supervision;
- periodic regenerative infusions;
- a longitudinal evidence and lineage record.

The replacement kidney of the future might first be a hybrid: living transport tissue plus microfluidics and external regeneration, gradually reducing machine dependence as biological modules improve. TOM is well suited to governing the versioned ensemble because it can treat every cartridge, cell batch, software update, assay and adverse event as a parent-bound state transition.

# 9. New biological life and synthetic organisms

The phrase "new life" spans several very different achievements. Some have been demonstrated; others have not. A physically grounded roadmap must keep them separate.

![Evidence ladder from synthetic genomes and living biobots to the still-unachieved goal of fully autonomous de novo life from nonliving components.](figures/life_ladder.png){width=72%}

## 9.1 Demonstrated layers

### A chemically synthesized genome controlling an existing cell

In 2010, researchers reported a bacterial cell controlled by a chemically synthesized genome [R1]. The cytoplasm, membranes, ribosomes and much of the cellular machinery came from an existing biological cell; the achievement was not bottom-up creation of an entire cell from nonliving ingredients. It nevertheless established that a designed, synthesized genome could become the controlling hereditary programme of a cellular chassis.

### A minimal synthetic bacterial genome

A 2016 study reported a minimal bacterial genome produced through iterative design-build-test cycles [R2]. It identified a small genome compatible with growth under laboratory conditions, while also showing that many essential functions were not fully understood. This is a crucial lesson for TOM: exact control over identity and process does not imply complete semantic understanding of the resulting biology.

### Alternative genetic polymers

Synthetic nucleic-acid analogues have demonstrated heredity and evolution in vitro [R3]. This supports the physical possibility of life-like information systems whose hereditary polymer is not ordinary DNA or RNA. It does not yet establish a complete organism using such a system.

### Reconfigurable multicellular biobots

Xenobots were designed from frog cells as reconfigurable living constructs, and later work reported kinematic self-replication under specific in-vitro conditions [R4, R11]. Anthrobots made from adult human somatic progenitor cells have also been reported as self-constructing motile biobots [R12]. These systems demonstrate that existing cells can express morphologies and behaviours outside their usual organismal context.

### Engineered living materials

Microbial co-cultures and living inks demonstrate programmable material growth and secretion [R9, R10]. These are not independent organisms in the ordinary ecological sense, but they are manufactured living systems with designed material functions.

## 9.2 The major frontier: designed multicellular organisms

A truly designed multicellular organism would require more than selecting a shape. It would need:

```text
stable hereditary identity
+ developmental programme
+ metabolic and energetic closure
+ tissue differentiation
+ morphogenesis and repair
+ sensory and behavioural regulation
+ reproduction or a deliberately nonreproductive lifecycle
+ ecological dependencies and containment
+ evolutionary stability
+ intergenerational evidence
```

The most plausible route is not writing every cell position. It is designing **developmental constraints** that cause cells to build and maintain the target form. TOM could represent the intended developmental states, admissible variations, terminal structures, failure classes and lineage, while external biological models and experiments supply observations.

## 9.3 Synthetic symbionts

One physically plausible future product is a designed symbiont that cannot thrive outside a host or engineered environment and performs one narrow service:

- manufacture a vitamin or therapeutic metabolite;
- neutralize one toxin;
- sense inflammation and emit a measurable signal;
- reinforce a living material;
- maintain a closed ecological life-support loop;
- repair damage in a contained bioreactor or habitat wall.

A responsible design would include multiple independent containment layers, nutrient dependence, finite lifetime or reversible removal, evolutionary monitoring and external kill/sterilization systems. The deterministic TOM authority could govern what design is permitted and how evidence is recorded, but it cannot prevent mutation by decree.

## 9.4 Orthogonal biology

Alternative genetic alphabets, recoded genomes, nonstandard amino acids and engineered translation systems suggest the possibility of organisms that operate partly outside ordinary terrestrial biochemistry. Such orthogonal systems could reduce biological cross-talk, enable new polymers or create containment dependencies. They remain a major research frontier because evolution, metabolism, replication fidelity and ecological interaction are difficult to predict.

## 9.5 De novo life from nonliving components

The strongest interpretation of "creating new life" is a system assembled from nonliving chemicals that autonomously maintains itself, grows, reproduces, evolves and persists without borrowing an already living cellular chassis. That has not been achieved.

A bottom-up artificial cell would need at least:

```text
boundary formation and controlled transport
energy capture and metabolism
information storage and replication
translation or another route from information to function
homeostasis
growth and division
error management
adaptation and evolution
```

Individual modules exist in research, but their integration into a robust autonomous organism is an open problem. TOM could provide an exact design/evidence framework, yet the missing science is biochemical organization, not bookkeeping.

\begin{futurebox}
A **TOM artificial-cell foundry** is physically conceivable as a closed robotic laboratory that assembles protocell candidates from approved modules, tests energy balance, information replication, membrane growth, division and ecological dependence, and publishes only bounded evidence. It would still require independent biosafety oversight, and it would not begin with an autonomous environmental release.
\end{futurebox}

# 10. Physically grounded science-fiction manufacturing

This chapter intentionally moves beyond demonstrated engineering. Every concept is labelled by evidence class and by the missing chain that separates it from reality.

## 10.1 Proof-carrying organ foundries - Class C

Imagine a regional organ foundry that maintains banks of consented induced pluripotent stem cells, prints vascularized tissue modules, matures them under individualized physiological loads, and assembles a replacement organ only after every module passes identity, potency, sterility, mechanics and integration tests.

A TOM authority graph could bind:

```text
recipient model and clinical indication
-> cell source and edits
-> tissue-module genealogy
-> vascular network and architecture
-> bioreactor trajectory
-> nondestructive imaging and secreted biomarkers
-> functional load tests
-> independent release review
-> implantation event
-> lifelong organ lineage
```

The far-future foundry might manufacture organs as modular systems: a replaceable endocrine cartridge, a perfused detox module, a vascularized tissue graft and an external maturation controller. Whole-organ replacement would emerge through gradual integration, not one magical print.

## 10.2 New human-compatible auxiliary organs - Class C/D

A civilization with mature tissue engineering could add carefully bounded biological functions without rewriting the whole body. Candidate systems include:

- an auxiliary glucose-control gland;
- a removable detox and drug-metabolism organ;
- an immune sentinel compartment that samples blood but remains physically isolated;
- a regenerative cytokine organ activated only after injury;
- a radiation-response organ for space crews;
- a nutrient-synthesis symbiont in a sealed implant;
- an electro-biological interface that communicates with prostheses or computers;
- an implant that produces scarce hormones or enzymes on demand.

The safest architecture is modular, retrievable and externally observable. Permanently altering germline development would be far less governable than implanting a removable, lineage-tracked organ.

## 10.3 Living spacecraft and self-growing habitats - Class D

A "living spacecraft" need not be a giant organism. A realistic interpretation is a hybrid habitat whose structural shell is conventional, while contained living subsystems grow insulation, recycle carbon, repair coatings, produce food, transform waste or signal damage.

Possible layers:

| Layer | Conventional component | Living component | TOM-governed evidence |
|---|---|---|---|
| Pressure shell | Metal/composite vessel | None or passive biomaterial | structural analysis, inspection, fatigue lineage |
| Radiation layer | Water, regolith, polymer | radiation-tolerant biomass or melanin-rich material | composition, growth, shielding measurements |
| Air/water loop | Pumps, membranes, sensors | algae, microbes, plant modules | species/strain identity, containment, gas and contaminant measurements |
| Repair skin | Replaceable panels | contained mineralizing or polymer-secreting organisms | damage event, repair response, coupon tests |
| Food system | Controlled-environment hardware | crops, fungi, cultured-cell modules | growth recipe, nutrient and contamination evidence |
| Waste loop | Mechanical/chemical treatment | microbial conversion stages | mass balance, pathogen control, residuals |

The habitat could slowly manufacture replacement biopolymers, sealants and low-load components from local carbon, water and mineral feedstock. The key is not making the whole spacecraft alive; it is using living manufacturing where self-renewal is advantageous and isolating it where failure would be catastrophic.

## 10.4 Orbital and planetary microfactories - Class B/C/D

NASA has already studied and demonstrated additive manufacturing in microgravity as a way to make tools and replacement parts for long missions [R22, R23]. A farther TOM-governed orbital microfactory could combine:

```text
asteroid, lunar or recycled feedstock characterization
-> robotic beneficiation and refining
-> additive or subtractive fabrication
-> in-process metrology
-> independent structural simulation
-> acceptance certificate
-> assembly into habitat, antenna, shield or vehicle component
```

A closed-loop factory on the Moon or an asteroid is compatible with known physics, but the economics, reliability, autonomous maintenance, power, dust management and quality assurance remain difficult. TOM's contribution would be to make every resource conversion and manufactured descendant reconstructable across long communication delays.

## 10.5 Self-repairing cities - Class D

A self-repairing city is more plausible as an ecosystem of machines and living materials than as one monolithic intelligence. Buildings and infrastructure could carry embedded sensors, robot-access interfaces, replaceable modules and materials that seal small cracks. Local microfactories would manufacture certified parts from recycled feedstock. Repair robots would propose interventions, and a formal authority would determine whether each intervention is permitted.

The city-scale lineage graph could connect:

```text
material batch -> component -> building -> inspection -> damage event
-> repair design -> robot action -> verification -> revised asset state
```

The primary scientific challenge is reliable diagnosis and long-term materials behaviour; the governance challenge is deciding who may change shared infrastructure.

## 10.6 Distributed self-reproducing industrial ecosystems - Class D

A general self-reproducing factory need not copy every component locally. A physically plausible version is an industrial ecosystem that can reproduce most of its own mass and gradually expand while importing a small set of high-complexity components.

A replication-closure analysis would list every dependency:

- energy generation and storage;
- mining and material purification;
- structural manufacturing;
- motors, bearings and power electronics;
- sensors and computation;
- calibration tools;
- maintenance robots;
- software and definition authority;
- biological life-support modules;
- scarce imported catalysts or semiconductors.

As the imported fraction falls, the system approaches practical self-reproduction. Absolute closure is not required for extraordinary capability. TOM could maintain the dependency graph and refuse to call the system self-replicating unless its declared boundary and imported dependencies are explicit.

## 10.7 Programmable molecular factories - Class D/E

A genuine molecular factory would accept molecular feedstock and execute a long sequence of positional reactions with error detection and product release. Molecular motors, DNA walkers, ribosomes and enzyme complexes show that nanoscale machines can perform directed operations. What is missing is a general architecture that is programmable, scalable, error-tolerant, supplied with energy and able to build diverse products.

A nearer future is **special-purpose molecular manufacturing**:

- programmable drug-delivery capsules;
- molecular diagnostic circuits;
- DNA-origami assembly jigs;
- enzyme cascades for one product family;
- self-assembling electronic or photonic structures;
- nanoscale repair or sensing modules in tightly controlled environments.

A TOM definition would describe the permitted state sequence and analytical evidence, while chemistry determines yields and error rates.

## 10.8 Synthetic ecosystems for closed habitats - Class C/D

A space settlement, underground city or remote terrestrial facility may need an intentionally assembled ecosystem rather than a copy of a natural one. The system could combine plants, microbes, fungi, insects or cultured-food modules with physical filtration and chemical backup.

A TOM world would model functional roles rather than pretending to predict every ecological interaction:

```text
carbon fixation
oxygen generation
nutrient recycling
waste conversion
food production
pathogen monitoring
population bounds
backup stores
quarantine and reset states
```

The system would remain an adaptive, evolutionary phenotype. Continuous observation and conservative control would be necessary because ecological dynamics cannot be frozen into exact deterministic rules.

## 10.9 Controlled planetary ecology and terraforming support - Class D/E

Large-scale planetary modification is not a near-term manufacturing programme. However, several subproblems are physically meaningful: producing habitats from local materials, recycling air and water, manufacturing soil analogues, growing radiation-protective biomass and establishing contained ecological modules.

A responsible progression would be:

```text
sealed laboratory ecosystem
-> closed terrestrial analog
-> orbital demonstration
-> isolated lunar/Martian habitat module
-> replicated contained modules
-> only then any discussion of open-environment intervention
```

Uncontrolled biological release on another world would raise planetary-protection, scientific and ethical concerns. TOM could preserve provenance and permissions, but cannot legitimize a release that lacks governance.

## 10.10 Artificial gestational support - Class C

The extra-uterine lamb system demonstrated that a carefully engineered environment can support some aspects of extreme prematurity in an animal model [R8]. A future human application, if ever achieved, would be an extension of neonatal care rather than a simple artificial womb. It would require gas exchange, circulation, fluid environment, infection control, endocrine support, neurodevelopmental monitoring and stringent ethics.

TOM could govern device configuration, physiological observations, intervention rules and longitudinal lineage. It must not turn a highly uncertain clinical decision into an automatic machine decision.

## 10.11 Biocomputational organs - Class C/D

Living neural cultures, organoids and bioelectronic interfaces suggest a future in which living tissue performs adaptive sensing or control. A biocomputational organ might be an external, replaceable module containing neurons or other excitable cells coupled to electronics. It could learn a narrow mapping, control a prosthesis or serve as a disease model.

The deterministic TOM authority would sit around the living learner:

```text
stimulus and training history
-> living-tissue response
-> calibration and drift evidence
-> permitted output envelope
-> explicit human or formal approval
```

The tissue's internal adaptation would not be represented as deterministic TOM semantics unless it was separately modeled and validated.

## 10.12 Morphogenetic fabrication - Class C/D

Instead of printing final geometry, future factories may create boundary conditions that cause cells or active materials to grow the geometry. The manufacturing instruction becomes a developmental programme:

```text
seed cell/material population
+ spatial signals
+ mechanical constraints
+ nutrient and energy gradients
+ timed events
+ maturation and stop conditions
```

This resembles embryonic development, wound healing and self-assembly. It may be the only practical way to create highly complex vascular or hierarchical structures. TOM can represent the intended developmental phases, admissible states and evidence, but the morphogenetic rules remain a major scientific frontier.

# 11. Three complete future chains

## 11.1 Chain A - TOM organ foundry

### Stage A0: digital-only design

- Define one organ function and clinical indication.
- Use published anatomy, physiology and cell-atlas data.
- Build a content-addressed architecture model.
- Simulate transport, mechanics and electrical/metabolic function.
- Preserve model uncertainty and failed designs.

### Stage A1: nonimplantable research tissue

- Manufacture small organoids or tissue modules in a qualified laboratory.
- Compare measured morphology and function against predictions.
- Record batch variation, contamination checks and counterexamples.
- Publish no clinical claim.

### Stage A2: perfused functional module

- Add vascular channels and controlled perfusion.
- Demonstrate stable function at larger scale.
- Use nondestructive imaging and longitudinal assays.
- Keep the product external or in preclinical research.

### Stage A3: hybrid bioartificial support

- Combine living tissue with an external device.
- Permit cartridge replacement and direct measurement.
- Conduct regulated preclinical and clinical evaluation.
- Publish each revision through explicit parent-bound authority.

### Stage A4: implantable auxiliary organ

- Use retrievable, bounded function rather than full replacement.
- Demonstrate integration, immune compatibility and long-term control.
- Require independent regulatory and clinical authority.

### Stage A5: whole replacement or novel organ

- Manufacture hierarchical vasculature, multiple tissues, innervation/communication and mature function.
- Prove sustained performance in realistic load conditions.
- Maintain lifelong product/recipient lineage.

## 11.2 Chain B - TOM living-material habitat factory

```text
local feedstock analysis
-> conventional structural shell
-> contained microbial or plant production modules
-> grown insulation, binders, coatings or repair materials
-> periodic mechanical and biological inspection
-> component replacement and sterilization pathways
-> closed-loop water, air, nutrient and waste accounting
-> habitat lineage
```

Near-term terrestrial analogues could use engineered living materials only in noncritical, replaceable panels. Later orbital or planetary habitats could exploit growth to reduce launched mass. The authority system would maintain a strict boundary between life-support-critical hardware and experimental biological components.

## 11.3 Chain C - TOM orbital microfactory

```text
1. receive authoritative design and permitted process pack
2. characterize recycled or local feedstock
3. select a machine path compatible with actual material evidence
4. simulate thermal, structural and dimensional behaviour
5. manufacture under remote supervision
6. inspect with machine vision and metrology
7. run proof loads or nondestructive tests
8. accept, reject or quarantine
9. publish product lineage and permitted installation context
10. monitor in service and feed observations into later revisions
```

The long communication delay makes deterministic local authority useful, but political and mission authority must still define what the factory is allowed to make.

# 12. A civilization-scale manufacturing vision

A mature TOM ecosystem could form a **planetary library of executable physical knowledge**. Each entry would be narrower than a natural-language claim and stronger than a static data record:

```text
this geometry
with these materials
under these processes
measured by these instruments
in this environment
produced these properties
within these uncertainties
and passed these explicit acceptance relations
```

Such a library could support local factories, hospitals, laboratories, disaster response, spacecraft and education. It could allow a design to travel while retaining evidence, rather than requiring blind trust in a vendor. It could also preserve disagreement: two material definitions or medical models could coexist with explicit domains and counterexamples rather than being merged into a false consensus.

## 12.1 Manufacturing knowledge as a commons

An open network could publish:

- canonical test coupons and measurement methods;
- machine capability definitions;
- material property evidence;
- reproducible simulation workflows;
- verified repair procedures;
- organoid and tissue characterization standards;
- ecological containment models;
- failure cases and negative results.

The difficult social question is governance: who may promote a definition, whose evidence counts, how liability is allocated, and when local adaptations diverge into new branches. TOM supplies mechanisms for identity and lineage, not the political answer.

## 12.2 Interstellar relevance without faster-than-light assumptions

A deterministic, self-describing manufacturing library is especially valuable for distant missions because communication is slow and physical resupply is expensive. An interstellar probe or generation habitat would need:

```text
repair and manufacturing definitions
+ local resource models
+ independent diagnostics
+ conservative acceptance rules
+ adaptation under bounded authority
+ long-term lineage across centuries
```

The probe would still require extraordinary power, propulsion, radiation tolerance and self-maintenance. TOM cannot solve those technologies, but its compact seed-plus-definition architecture is conceptually compatible with sending an authority system that expands locally from a verified library.

# 13. What TOM contributes and what remains outside TOM

| TOM can govern | TOM cannot establish by itself |
|---|---|
| Exact identity and version | Whether the scientific model is true |
| Definition and dependency order | Whether a material will survive untested environments |
| Bounded deterministic evaluation | Whether a living system will mutate safely |
| Support and compatibility predicates | Clinical efficacy or benefit-risk balance |
| Explicit event and transition | Ethical legitimacy of an experiment |
| Accepted/rejected/ambiguous decisions | Physical safety of machinery without external safety systems |
| Immutable evidence and lineage | Complete ecological consequences |
| Parent-bound updates and regressions | AGI, consciousness or biological understanding |
| Replay across conforming runtimes | General molecular manufacturing or de novo life |

\begin{tomprinciple}
The strongest TOM claim is procedural: the same explicit evidence under the same formal definitions yields the same authority trace. The strongest scientific claim must still come from independent experiments, measurements, models and critical review.
\end{tomprinciple}

# 14. A no-capital path from laptop to frontier programme

The user explicitly noted that custom hardware, actuators, sensors, biological tissue, materials and chemical compounds are not presently affordable. The correct path is therefore to manufacture **evidence, definitions and digital twins first**.

## Phase 1 - Laptop evidence foundry

Deliverables:

- TOM manufacturing ontology and schemas;
- proof-carrying product template;
- machine, material, process and inspection definition packs;
- simulator adapter contract;
- synthetic-data benchmark;
- immutable evidence vault;
- human-readable and machine-readable release certificates.

Cost: ordinary computing and time.

## Phase 2 - Public-data and open-simulator laboratory

Use public materials databases, biological atlases, structural data, NASA/Earth data and open simulators. Candidate domains:

- finite-element mechanical parts;
- battery-material evidence comparisons;
- protein or molecular simulation provenance;
- organ transport and perfusion digital twins;
- robot manufacturing cells in simulation;
- habitat mass and resource-flow models.

The purpose is to prove the authority chain, not the physical result.

## Phase 3 - Service-bureau physical prototypes

Order low-risk external prototypes:

- 3D-printed coupons;
- CNC parts;
- simple PCBs;
- material test specimens;
- microfluidic chips without biological use;
- optical or mechanical calibration artifacts.

Bind quotes, manufacturing files, supplier declarations, measurements and deviations to one lineage.

## Phase 4 - Academic or industrial partnerships

Approach an existing laboratory with a narrow falsifiable project. Examples:

- reproduce a published living-material result under a TOM evidence graph;
- compare two bioprinting or perfusion models without implanting tissue;
- run a materials-screening campaign where TOM controls publication authority;
- implement an FPGA step engine and compare it with Python/C.

The collaboration provides physical infrastructure; TOM provides reproducibility and authority design.

## Phase 5 - Regulated translational programme

Only after independent validation should the chain enter medical, ecological or high-energy physical domains. This phase requires institutional biosafety, research ethics, quality systems, clinical or environmental regulation and professional engineering.

# 15. Safety, ethics and governance

## 15.1 Biological boundaries

This report does not provide laboratory procedures for genome editing, organism construction, tissue culture, organ printing, pathogen engineering or environmental release. Future biological manufacturing must distinguish:

- somatic therapy from heritable modification;
- contained research from ecological release;
- patient-specific care from enhancement;
- therapeutic benefit from military or coercive use;
- reversible implants from permanent developmental change;
- model-organism evidence from human clinical evidence.

WHO's human-genome-editing governance work emphasizes safety, effectiveness, ethics, registries, international coordination and mechanisms to address unsafe or unregistered research [R21]. TOM can help encode and audit those governance conditions, but should not be used to bypass them.

## 15.2 Ecological boundaries

Living materials and organisms should begin in sealed, monitorable environments with explicit nutrient dependence, reproductive constraints, deactivation and recovery plans. A deterministic design does not guarantee evolutionary stability. Environmental release would require ecosystem-level evidence and public governance.

## 15.3 Physical safety boundaries

The no-hidden-failsafe TOMAGI profile means physical interlocks must remain separate and conventional:

- certified emergency stops;
- hard motion and pressure limits;
- safe electrical design;
- containment and ventilation;
- radiation and chemical controls;
- human authorization;
- independent fault detection.

A formal action certificate can be one input to a safety controller, not a replacement for it.

## 15.4 Authority and human rights

A system capable of manufacturing organs, organisms or habitats would concentrate power. Governance must address consent, ownership, access, privacy, disability rights, enhancement inequality, indigenous and community interests, ecological stewardship and liability. Content addressing can prove who changed what; it does not prove that the change was just.

# 16. Recommended programme: ten escalating demonstrators

| Demonstrator | What it proves | Required physical infrastructure |
|---|---|---|
| 1. Proof-carrying software release | Exact end-to-end authority and replay | Laptop |
| 2. Digital product passport | Product/query/repair lineage | Laptop, QR/NFC optional |
| 3. Simulated manufacturing cell | Event, action and inspection governance | Gazebo/industrial simulator |
| 4. Service-bureau part | Digital-to-physical evidence chain | External printer/CNC and basic metrology |
| 5. FPGA TOMAGI step engine | Hardware equivalence without kernel expansion | Development FPGA board |
| 6. Autonomous materials-workflow mock | Proposal/oracle/authority separation | Simulated or partner robotic lab |
| 7. Living-material evidence model | Biological batch identity and containment definitions | No wet lab initially; public literature/data |
| 8. Vascularized-organ digital twin | Organ architecture and release ontology | Open multiphysics simulation |
| 9. Partner-lab tissue module | Real observation and batch lineage | Qualified tissue-engineering lab |
| 10. Closed habitat digital twin | Physical, biological and manufacturing loops in one world | Simulation, later analog facility |

This sequence creates useful products at every step and avoids requiring a speculative breakthrough before the architecture can be evaluated.

# 17. Final synthesis

The completed TOM substrate makes one expansive but defensible future possible: **manufacturing in which every important physical or biological claim has an explicit, replayable authority chain**.

At the near end, this means software factories, proof-carrying parts, automated laboratory governance, digital twins, repair networks and hardware accelerators. At the research frontier, it means vascularized tissue modules, bioartificial support systems, engineered living materials, cell-based robots, synthetic symbionts and controlled morphogenetic fabrication. Farther out, but still compatible with known physics, lie modular organ foundries, living habitat subsystems, orbital microfactories, self-repairing infrastructure, special-purpose molecular assembly lines and distributed industrial ecosystems that reproduce much of their own capacity.

The scientific limits are equally important. TOM does not create matter, infer unknown biology, guarantee safety, make a model true, prevent mutation, establish clinical benefit, or generate AGI merely because execution is deterministic. The frozen kernel is the authority spine. The future is built through better domain definitions, independent oracles, physical measurements, cautious promotion and long-term lineage.

The most ambitious outcome is not a magic universal constructor. It is a civilization in which software, machines, materials, organs, organisms and habitats are **proof-carrying descendants of explicit knowledge**, and where every revision can be questioned, reproduced, rejected, repaired or superseded without losing the history that made it possible.

\newpage
# References

## Supplied TOM materials

**[S1]** `TOM_seed_genome_2026-09-01.txt`. Canonical 244-byte TOM genome string, requester-supplied, 1 September 2026.

**[S2]** *TOMAGI: Topological Operator Machine for Analytic Geometric Inference*, Version 1.0.0, requester-supplied attribution Tom Klootwijk, 1 September 2026.

**[S3]** *TOM: Topological Open Modular Seeded Referential Substrate*, TOM-SRS 1.0, requester-supplied attribution Tom Klootwijk, 1 September 2026.

**[S4]** *CODEX handoff - TOM WQK 0.5.2 kernel repair*, 2 September 2026.

**[S5]** `CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json`, status `pass`, equal Python/C traces, 1,032 authenticated `EMIT` records.

**[S6]** *TOM AGI Roadmap - status through WQK 0.5.2*.

**[S7]** *TOM repository instructions* (`AGENTS.md`).

## External primary research and official sources

**[R1]** Gibson, D. G. et al. "Creation of a bacterial cell controlled by a chemically synthesized genome." *Science* 329, 52-56 (2010). DOI: [10.1126/science.1190719](https://doi.org/10.1126/science.1190719).

**[R2]** Hutchison, C. A. III et al. "Design and synthesis of a minimal bacterial genome." *Science* 351, aad6253 (2016). DOI: [10.1126/science.aad6253](https://doi.org/10.1126/science.aad6253).

**[R3]** Pinheiro, V. B. et al. "Synthetic genetic polymers capable of heredity and evolution." *Science* 336, 341-344 (2012). DOI: [10.1126/science.1217622](https://doi.org/10.1126/science.1217622).

**[R4]** Kriegman, S. et al. "Kinematic self-replication in reconfigurable organisms." *Proceedings of the National Academy of Sciences* 118, e2112672118 (2021). DOI: [10.1073/pnas.2112672118](https://doi.org/10.1073/pnas.2112672118).

**[R5]** Grigoryan, B. et al. "Multivascular networks and functional intravascular topologies within biocompatible hydrogels." *Science* 364, 458-464 (2019). DOI: [10.1126/science.aav9750](https://doi.org/10.1126/science.aav9750).

**[R6]** Skylar-Scott, M. A. et al. "Biomanufacturing of organ-specific tissues with high cellular density and embedded vascular channels." *Science Advances* 5, eaaw2459 (2019). DOI: [10.1126/sciadv.aaw2459](https://doi.org/10.1126/sciadv.aaw2459).

**[R7]** Noor, N. et al. "3D Printing of Personalized Thick and Perfusable Cardiac Patches and Hearts." *Advanced Science* 6, 1900344 (2019). DOI: [10.1002/advs.201900344](https://doi.org/10.1002/advs.201900344).

**[R8]** Partridge, E. A. et al. "An extra-uterine system to physiologically support the extreme premature lamb." *Nature Communications* 8, 15112 (2017). DOI: [10.1038/ncomms15112](https://doi.org/10.1038/ncomms15112).

**[R9]** Gilbert, C. et al. "Living materials with programmable functionalities grown from engineered microbial co-cultures." *Nature Materials* 20, 691-700 (2021). DOI: [10.1038/s41563-020-00857-5](https://doi.org/10.1038/s41563-020-00857-5).

**[R10]** Duraj-Thatte, A. M. et al. "Programmable microbial ink for 3D printing of living materials produced from genetically engineered protein nanofibers." *Nature Communications* 12, 6600 (2021). DOI: [10.1038/s41467-021-26791-x](https://doi.org/10.1038/s41467-021-26791-x).

**[R11]** Kriegman, S. et al. "A scalable pipeline for designing reconfigurable organisms." *Proceedings of the National Academy of Sciences* 117, 1853-1859 (2020). DOI: [10.1073/pnas.1910837117](https://doi.org/10.1073/pnas.1910837117).

**[R12]** Gumuskaya, G. et al. "Motile Living Biobots Self-Construct from Adult Human Somatic Progenitor Seed Cells." *Advanced Science* 11, 2303575 (2024). DOI: [10.1002/advs.202303575](https://doi.org/10.1002/advs.202303575).

**[R13]** Burger, B. et al. "A mobile robotic chemist." *Nature* 583, 237-241 (2020). DOI: [10.1038/s41586-020-2442-2](https://doi.org/10.1038/s41586-020-2442-2).

**[R14]** Szymanski, N. J. et al. "An autonomous laboratory for the accelerated synthesis of novel materials." *Nature* 624, 86-91 (2023). DOI: [10.1038/s41586-023-06734-w](https://doi.org/10.1038/s41586-023-06734-w).

**[R15]** Wickham, S. F. J. et al. "A DNA-based molecular motor that can navigate a network of tracks." *Nature Nanotechnology* 7, 169-173 (2012). DOI: [10.1038/nnano.2011.253](https://doi.org/10.1038/nnano.2011.253).

**[R16]** Mao, X. et al. "DNA-Based Molecular Machines." *JACS Au* 2, 2381-2399 (2022). DOI: [10.1021/jacsau.2c00430](https://doi.org/10.1021/jacsau.2c00430).

**[R17]** Narazaki, G. et al. "Scalable production of human cortical organoids using a biocompatible polymer." *Nature Biomedical Engineering* 9, 2115-2123 (2025). DOI: [10.1038/s41551-025-01427-3](https://doi.org/10.1038/s41551-025-01427-3).

**[R18]** Reichman, T. W. et al. "Stem Cell-Derived, Fully Differentiated Islets for Type 1 Diabetes." *New England Journal of Medicine* 393, 858-868 (2025). DOI: [10.1056/NEJMoa2506549](https://doi.org/10.1056/NEJMoa2506549).

**[R19]** Carlsson, P.-O. et al. "Survival of Transplanted Allogeneic Beta Cells with No Immunosuppression." *New England Journal of Medicine* (2025). DOI: [10.1056/NEJMoa2503822](https://doi.org/10.1056/NEJMoa2503822).

**[R20]** Kawai, T. et al. "Xenotransplantation of a Porcine Kidney for End-Stage Kidney Disease." *New England Journal of Medicine* 392, 1933-1940 (2025). DOI: [10.1056/NEJMoa2412747](https://doi.org/10.1056/NEJMoa2412747).

**[R21]** World Health Organization. *Human genome editing: recommendations* and *a framework for governance* (2021). Official overview: [WHO genome-editing recommendations](https://www.who.int/news/item/12-07-2021-who-issues-new-recommendations-on-human-genome-editing-for-the-advancement-of-public-health).

**[R22]** NASA. "Solving the Challenges of Long Duration Space Flight with 3D Printing" (2019), official in-space manufacturing overview. [NASA](https://www.nasa.gov/missions/station/solving-the-challenges-of-long-duration-space-flight-with-3d-printing/).

**[R23]** NASA. "3D Printing: Saving Weight and Space at Launch" (2025), official ISS research overview. [NASA](https://www.nasa.gov/missions/station/iss-research/3d-printing-saving-weight-and-space-at-launch/).

# Appendix - Citation note

The verbatim preceding reply was preserved as written except that platform-specific citation tokens were converted into readable source labels. The expanded analysis adds contemporary external research and clearly separates demonstrated results, engineering extrapolation, research frontiers, known-physics-compatible speculation and unestablished claims.
