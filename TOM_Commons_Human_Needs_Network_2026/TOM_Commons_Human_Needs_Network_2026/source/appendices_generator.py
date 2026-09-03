from pathlib import Path
p=Path('/mnt/data/TOM_Commons_Human_Needs_2026/TOM_Commons_Human_Needs_Network_2026.md')

categories={
'Consumer operating systems and devices':[
('Android','TOM Client','Open, portable client runtime with explicit app permissions and provider choice.'),
('Android Auto','TOM Mobility Client','Vehicle interface using portable routes, communications and permissions.'),
('Android TV','TOM Media Client','Open media client with selectable catalogues and recommendation profiles.'),
('Cars with Google built-in','TOM Vehicle Node','Manufacturer-independent map, voice and service interfaces.'),
('Chrome','TOM Browser','Standards-first browser with local vault, query receipts and agent permissions.'),
('Chromebook / ChromeOS','TOM Client OS','Reproducible, portable workspace client rather than mandatory cloud identity.'),
('Pixel phones, tablet, watch and buds','TOM Reference Devices','Optional open reference hardware; no device line is required by the protocol.'),
('Wear OS','TOM Wearable Client','Portable health, identity and notification services with local-first data.'),
('Gboard','TOM Input','Multilingual input and translation that records model/provider and stays replaceable.'),
('Files','TOM Vault Client','Local and remote file access over user-controlled stores.'),
('Find Hub','TOM Asset Finder','User-authorised device and product-location graph.'),
('Digital Wellbeing','TOM Attention Profile','User-defined attention budgets and transparent notification rules.'),
],
'Search, AI and knowledge':[
('Google Search','TOM Query','Federated indexes, evidence bundles, visible ranking profiles and sponsorship separation.'),
('AI Mode / Circle to Search / Lens','TOM Multimodal Query','Image, screen and natural-language queries interpreted as editable need records.'),
('Gemini','TOM Agent','Selectable AI proposal layer under explicit data, tool and action permissions.'),
('Google Assistant','TOM Agent Voice','Voice interface to the same permissioned service graph.'),
('Gemini Notebook / NotebookLM','TOM Research Notebook','Source-bounded synthesis with claim receipts and portable project data.'),
('Scholar','TOM Scholar','Open research graph with datasets, methods, replication and contradiction lineage.'),
('Google Trends','TOM Public Trends','Transparent aggregate query and event statistics with privacy controls.'),
('Finance','TOM Market Data','Multiple attributed financial-data providers and explicit update times.'),
('Translate','TOM Translate','Plural human/model translation with source text, alternatives and terminology packs.'),
('Arts & Culture','TOM Culture Commons','Institution- and community-governed cultural collections with provenance.'),
],
'Communication, identity and time':[
('Gmail','TOM Link Mail','Standards-based mail with portable identity, contacts, history and provider migration.'),
('Google Chat','TOM Link Rooms','Federated message rooms with community governance and export.'),
('Google Meet','TOM Link Meetings','Interoperable meetings linked to portable rooms, calendars and decisions.'),
('Google Messages','TOM Link Messaging','Cross-provider messaging with explicit encryption and retention profiles.'),
('Google Voice','TOM Link Voice','Portable calling identity and provider-independent communication records.'),
('Contacts','TOM Relationship Vault','User-owned relationship graph with selective sharing.'),
('Google Calendar','TOM Time','Portable calendar, availability, negotiation and event lineage.'),
('Google Tasks','TOM Work Graph','Typed goals, tasks, dependencies and verified outcomes.'),
('Google Keep','TOM Notes','Local-first notes linked to projects and evidence.'),
('Google Authenticator','TOM Auth','Open standards authentication and recovery; passkeys/WebAuthn preferred where suitable.'),
('Google Account / Identity Platform','TOM Identity Federation','Plural identifiers and verifiable credentials, no mandatory single global account.'),
],
'Workspace and storage':[
('Google Drive','TOM Vault Storage','User-controlled files and provider-portable storage.'),
('Google Docs','TOM Document','Open collaborative document objects with edit and publication lineage.'),
('Google Sheets','TOM Table','Open structured tables with formula, data-source and decision lineage.'),
('Google Slides','TOM Presentation','Portable presentation documents with cited media and version history.'),
('Google Forms','TOM Intake','Typed consent-aware data collection and validation.'),
('Google Sites','TOM Publish','Portable websites and service pages hosted by competing operators.'),
('Google Workspace','TOM Workspace','Unified projects, documents, communication and time over open interfaces.'),
('Google One','TOM Membership + Storage','Cooperative or commercial storage/support plans without ecosystem captivity.'),
('Google Fonts','TOM Design Commons','Open design assets with licence and provenance records.'),
],
'Maps, mobility and travel':[
('Google Maps','TOM Atlas','Open geographic graph with source, recency, accessibility and selectable routing.'),
('Google Earth','TOM Earth','Public geospatial, environmental and historical layers with provenance.'),
('Street View','TOM Street Evidence','Attributed street imagery with capture time, privacy and community correction.'),
('Waze','TOM Live Mobility','Federated traffic and hazard observations with confidence and expiry.'),
('Flights','TOM Travel Search','Schedule, price, accessibility, reliability and fee comparison from multiple providers.'),
('Travel','TOM Journey','Portable itinerary and booking plan under explicit permissions.'),
('Google Maps Platform','TOM Atlas APIs','Open map and routing interfaces backed by plural data/operators.'),
],
'Media, entertainment and publishing':[
('YouTube','TOM Video Commons','Portable creator identity, hosting competition and user-selected recommendation profiles.'),
('YouTube Kids','TOM Youth Media','Age-appropriate catalogues with guardian/community governance and no behavioural ad default.'),
('YouTube Music','TOM Music Commons','Portable libraries, artist support, catalogue federation and transparent recommendations.'),
('YouTube TV','TOM Live Media','Federated channel and event discovery with rights/licence metadata.'),
('Google TV','TOM Media Guide','Cross-provider catalogue and device-neutral playback routing.'),
('Google Play Books','TOM Books','Portable purchases, loans, public-library integration and open annotations.'),
('Google Play Games','TOM Games','Portable identity, saves, achievements and community governance.'),
('Google Photos','TOM Memory Vault','User-owned media with local/permissioned AI organisation.'),
('Google News','TOM News Graph','Event, source, claim, correction and ownership graph with selectable editorial profiles.'),
('Blogger','TOM Publish','Federated long-form publishing with portable audience and archive.'),
('Google Cast','TOM Device Media','Open local device-discovery and media-control interfaces.'),
],
'Education, family, home and wellbeing':[
('Google Classroom','TOM Learn Classroom','Portable courses, assignments, evidence and credentials across institutions.'),
('Learning / Grow with Google','TOM Learn Commons','Open learning paths linked to demonstrated competence.'),
('Family Link','TOM Family Permissions','Child-sensitive delegated permissions and transparent controls.'),
('Fitbit / Google Fit','TOM Personal Health Vault','User-controlled activity observations; care claims remain clinically governed.'),
('Google Home / Nest','TOM Home','Portable device capabilities, local automation, firmware and repair lineage.'),
('Accessibility support','TOM Access Layer','Accessibility is a cross-cutting conformance requirement, not a separate afterthought.'),
('Crisis Response','TOM Crisis','Public-authority and community emergency data with low-bandwidth/offline modes.'),
],
'Market, payments and business':[
('Google Pay','TOM Pay Broker','External regulated payment services under explicit permission and receipt.'),
('Google Wallet','TOM Wallet','Portable credentials, tickets, receipts, warranties and payment references.'),
('Shopping','TOM Market','Product comparison including cost, provenance, repairability, compatibility and sponsorship status.'),
('Business Profile','TOM Service Profile','Portable verified business/service identity independent of one map operator.'),
('Merchant Center','TOM Supplier Registry','Open product, stock, price and policy feeds with seller identity.'),
('Manufacturer Center','TOM Product Passport Registry','Design, manufacturing, certification, repair and recall records.'),
('Local Services Ads','TOM Local Sponsorship','Clearly separated paid placement that cannot rewrite organic service eligibility.'),
('Google Ads / Search Ads / Shopping Ads','TOM Disclosed Sponsorship','Optional labelled promotion with public rules and no covert ranking mutation.'),
('AdSense / AdMob / Ad Manager','TOM Publisher Funding Exchange','Transparent sponsorship/subscription/membership options controlled by publishers and communities.'),
('Google Analytics / Tag Manager','TOM Outcome Analytics','Purpose-limited service quality and outcome metrics instead of cross-service behavioural enclosure.'),
('Marketing Platform / Demand Gen / Performance Max','TOM Campaign Exchange','Commercial campaign tools separated from public search and personal data by explicit consent.'),
],
'Cloud and developer platforms':[
('Google Cloud / Cloud Computing','TOM Compute Federation','Portable reproducible workloads across public, cooperative and commercial operators.'),
('Firebase','TOM App Services','Replaceable identity, data, notifications and serverless services with export contracts.'),
('Flutter','TOM Client Toolkit','Cross-platform open client toolkit; not required by the protocol.'),
('TensorFlow','TOM Model Adapter','External model runtime whose outputs remain typed proposals/evidence.'),
('AI for Developers','TOM Agent SDK','Model and tool adapters with permissions, receipts and tests.'),
('Google for Developers','TOM Builder Commons','Open SDKs, schemas, conformance suites and example services.'),
('Search Console','TOM Publisher Index Console','Transparent indexing, provenance, errors and appeals across index operators.'),
('Android Enterprise / Chrome Enterprise','TOM Organisation Client','Portable device, application and policy management with auditable rules.'),
('Google Play / Play Protect / Play Pass','TOM App Commons','Open signed package catalogues, reproducible builds, safety evidence and portable purchases.'),
('Google Identity Platform','TOM Identity APIs','Interoperable identity and credential verification without one account authority.'),
('Interactive Media Ads','TOM Media Sponsorship','Clearly labelled media sponsorship handled outside organic recommendation.'),
],
}

with p.open('a',encoding='utf-8') as f:
    f.write('\n# Appendix A - Functional mapping from the present Google surface to TOM Commons\n\n')
    f.write('Google\'s official products page is the source for the product names in this appendix. [G1] The mapping is an architectural proposal, not a claim that equivalent TOM services already exist. Product availability and naming can change over time.\n\n')
    for cat, rows in categories.items():
        f.write(f'## {cat}\n\n')
        f.write('| Present Google product or surface | Proposed TOM Commons module | Replacement principle |\n')
        f.write('|---|---|---|\n')
        for a,b,c in rows:
            f.write(f'| {a} | {b} | {c} |\n')
        f.write('\n')

    f.write('''# Appendix B - Human Needs Genome taxonomy

The following taxonomy is intended as a first versioned registry. It is deliberately broad so that no single ministry, corporation or app category owns a life event.

| Domain ID | Human need | Representative records and services |
|---|---|---|
| HN.01 | Air and environmental quality | air observations, alerts, exposure guidance, emissions, indoor systems |
| HN.02 | Water | drinking water, sanitation, supply, quality, flood and drought information |
| HN.03 | Food | availability, affordability, nutrition, production, allergies, cultural needs |
| HN.04 | Shelter | housing, tenancy, ownership, accessibility, energy, maintenance, emergency shelter |
| HN.05 | Health | care navigation, records, prevention, disability, mental health, medicines information |
| HN.06 | Physical safety | emergency response, workplace safety, product safety, violence support |
| HN.07 | Identity | identifiers, credentials, pseudonyms, guardianship, recovery and delegation |
| HN.08 | Privacy | consent, selective disclosure, retention, correction, deletion and audit |
| HN.09 | Communication | mail, messaging, calls, meetings, public conversation and translation |
| HN.10 | Relationships | family, friendship, care, community, association and mutual aid |
| HN.11 | Mobility | walking, cycling, public transport, driving, travel, accessibility and logistics |
| HN.12 | Time | calendars, commitments, deadlines, routines, care and resource scheduling |
| HN.13 | Money | payments, income, budgeting, benefits, credit, tax, insurance and receipts |
| HN.14 | Work | jobs, projects, skills, conditions, cooperatives, labour rights and livelihood |
| HN.15 | Learning | curricula, prerequisites, tutoring, assessment, credentials and lifelong learning |
| HN.16 | Knowledge | search, evidence, libraries, archives, research, claims and contradictions |
| HN.17 | Creativity | writing, art, music, design, performance, tools, publication and attribution |
| HN.18 | Culture | language, heritage, religion, tradition, media, local memory and access |
| HN.19 | Recreation | sport, games, travel, events, nature, social activities and rest |
| HN.20 | Home | household assets, devices, energy, maintenance, security and automation |
| HN.21 | Family and care | childcare, education, elder care, delegated decisions and shared records |
| HN.22 | Legal capacity | rights, obligations, documents, representation, dispute and appeal |
| HN.23 | Civic participation | elections, consultation, public meetings, budgets, petitions and representation |
| HN.24 | Public services | eligibility, applications, case status, reasons, correction and redress |
| HN.25 | Justice | legal information, due process, evidence, decisions and rehabilitation |
| HN.26 | Community resilience | local services, mutual aid, emergency plans, public assets and volunteers |
| HN.27 | Infrastructure | transport, energy, water, communications, maintenance and investment |
| HN.28 | Environment | ecosystems, climate, biodiversity, pollution, conservation and adaptation |
| HN.29 | Science | hypotheses, methods, datasets, experiments, replication and open problems |
| HN.30 | Software | source, builds, dependencies, tests, deployment, security and maintenance |
| HN.31 | Manufacturing | requirements, design, materials, process, machines, inspection and product lineage |
| HN.32 | Repair and circularity | diagnostics, parts, skills, warranties, reuse, remanufacture and recycling |
| HN.33 | Biological research | protocols, biosafety, organisms, tissues, measurements and research lineage |
| HN.34 | Functional organs | research, consent, manufacturing evidence, regulation and outcomes |
| HN.35 | Habitat | buildings, settlements, resilience, accessibility and living infrastructure |
| HN.36 | Space and long-term stewardship | missions, off-world manufacturing, archives, governance and intergenerational continuity |

# Appendix C - Standards and open-data adapter matrix

| Foundation | Existing role | TOM Commons use | Boundary |
|---|---|---|---|
| W3C Verifiable Credentials 2.0 | Issuer-holder-verifier model for tamper-evident claims | Qualifications, licences, membership, eligibility and selective presentations | Does not define all trust or governance policy |
| W3C Decentralized Identifiers | Identifiers for people, organisations, physical and digital things | Portable identities for people, services, products, sensors and datasets | Does not by itself create a trusted issuer or consensus system |
| WebAuthn / passkeys | Public-key authentication | Phishing-resistant user and operator login | Recovery and device loss still need governance |
| Solid Pods | User-controlled online data stores and interoperable app access | Personal vault and provider migration model | TOM must add domain schemas, evidence and action authority |
| Matrix | Open federated real-time communication APIs | Messages, rooms, meetings, IoT events and bridgeable communication | Moderation, abuse operations and usability remain institutional work |
| ActivityPub | Federated actors, inboxes, outboxes and social activities | Publishing, following and community media federation | Does not supply TOM evidence or ranking semantics |
| OpenStreetMap | Community-maintained open map data | Geographic base, local services and community correction | Routing, service quality and real-time data need additional operators |
| Wikidata | Collaborative multilingual structured knowledge | Entity and claim graph with source links | Quality and completeness vary by domain |
| Common Crawl | Open web-crawl corpus | Seed data for public-interest web indexes | A high-quality search engine still needs crawling, parsing, ranking and anti-spam work |
| OpenAlex | Open research graph | Papers, authors, institutions, topics and citations | Reproducibility and claim-level evidence need additional layers |
| FHIR | Healthcare data exchange standard | Adapter for patient-controlled and institutional health records | Clinical authority, privacy and regulation remain external |
| DICOM | Medical imaging standard | Imaging identity and provenance adapter | Interpretation remains clinical/model evidence |
| OPC UA | Industrial interoperability and information models | Factory, machine and sensor adapters | Physical safety remains with certified industrial controls |
| FMI | Model exchange and co-simulation | Digital-twin and engineering simulation adapter | Solver correctness remains independently validated |
| ROS 2 / Matrix/other messaging | Robot and distributed component communication | Non-authoritative sensor/action transport | Does not replace certified motion and emergency controls |
| PROV-O | General provenance vocabulary | Exchange provenance with external systems | TOM retains its own canonical authority records |

# Appendix D - Sample proof-carrying query receipts

## D.1 Public information query

```json
{
  "type": "tom.answer.bundle",
  "need_id": "sha256:...",
  "question": "What public transport is accessible to this address after 21:00?",
  "context_fields_used": ["approximate_origin", "wheelchair_access"],
  "indexes": ["osm-regional-v42", "transit-authority-feed-v8"],
  "ranking_profile": "accessible-reliable-low-transfer-v3",
  "eligible_routes": 4,
  "selected_routes": 2,
  "known_conflicts": ["one lift status feed is stale"],
  "ai_summary": {
    "status": "proposal",
    "model": "selected-provider/model-version",
    "source_claims": ["claim:route-a", "claim:route-b"]
  },
  "action_authority": "human-confirmation-required",
  "receipt_hash": "sha256:..."
}
```

## D.2 Public-service application

```json
{
  "type": "tom.service.application.plan",
  "need": "income_support",
  "jurisdiction": "declared-local-authority",
  "rule_version": "benefit-rule-2026-09",
  "facts_requested": ["residency", "household_income", "dependants"],
  "possible_eligibility": "requires_authority_decision",
  "missing_evidence": ["latest_income_statement"],
  "submission_steps": 3,
  "appeal_route": "service:appeals-office",
  "data_retention": "jurisdiction-policy-id",
  "ai_role": "plain-language-explanation-only"
}
```

## D.3 Manufacturing query

```json
{
  "type": "tom.manufacturing.candidate",
  "need": "replacement_appliance_bracket",
  "product_passport": "product:...",
  "part_definition": "definition:...",
  "candidate_fabricator": "service:...",
  "material_compatibility": "pass",
  "machine_capability": "pass",
  "inspection_plan": "inspection:...",
  "simulation": {"status": "external-evidence", "result": "pass"},
  "physical_order": "not-authorised",
  "required_confirmation": ["price", "liability", "fabrication"],
  "lineage_parent": "product:original-appliance"
}
```

# Appendix E - Institutional transition map

| Present institution or platform role | TOM Commons transition | Human role preserved |
|---|---|---|
| Search company | Becomes one of several index/ranking operators | Editors, engineers, librarians, researchers and local contributors |
| Email provider | Becomes a replaceable communication host | Support, security, abuse response and community administration |
| Social platform | Becomes federated hosting and recommendation services | Creators, moderators, communities and journalists |
| Cloud provider | Becomes a portable workload operator | Infrastructure engineering, support and specialist services |
| Advertising network | Becomes a visibly separated sponsorship exchange | Marketing can continue without controlling organic public search |
| Government portal | Becomes a standards-compatible public service node | Accountable officials and case workers remain responsible |
| School platform | Becomes a learning and credential provider | Teachers, institutions and learners retain pedagogical authority |
| Hospital portal | Becomes a regulated health-data and care service node | Clinicians and institutions retain clinical accountability |
| Bank/payment app | Becomes a regulated payment/credential provider | Financial institutions retain legal obligations and risk controls |
| Marketplace | Becomes an open supplier and transaction service | Sellers, buyers, cooperatives and dispute resolvers |
| Manufacturer | Publishes capabilities and proof-carrying products | Engineers, operators, inspectors and safety professionals |
| Research publisher | Becomes one node in an open evidence graph | Peer review, editorial judgement and scholarly communities |
| AI company | Supplies models and agents under explicit scopes | Researchers, reviewers, users and accountable service owners |
| Library | Operates public query, archive, literacy and local data services | Librarians become core stewards of the commons |
| Municipality | Operates local services, maps, notices and appeals | Democratic institutions remain accountable to residents |
| Standards body | Publishes schemas, conformance tests and revisions | Expert consensus and public review remain essential |

# Appendix F - The first twelve deliverables

A serious programme should produce concrete artifacts in this order:

1. `TOM-HUMAN-NEEDS-1.0.schema.json` - typed need, rights, service, evidence, ranking, action and outcome records.
2. `tom-vault` - encrypted local personal data store with export and provider migration.
3. `tom-query-receipt` - deterministic record of indexes, filters, ranking, AI use and sources.
4. `tom-ranking-public-interest-v1` - first inspectable ranking profile.
5. `tom-open-research-index` - bounded OpenAlex/Wikidata research explorer.
6. `tom-local-atlas` - one-region OpenStreetMap service and accessibility directory.
7. `tom-link-bridge` - Matrix/email bridge with portable contacts and rooms.
8. `tom-service-registry` - one municipality or community's machine-readable services.
9. `tom-agent-gate` - local/API model proposals with source receipts and action confirmation.
10. `tom-repair-foundry-demo` - need-to-proof-carrying replacement part workflow.
11. `tom-commons-conformance` - interoperability, portability, security and accessibility tests.
12. `tom-commons-cooperative-constitution` - governance, funding, audit, appeals and forkability.

# References

## Supplied TOM materials

- **[T1]** `TOM_seed_genome_2026-09-01.txt`. Exact 244-byte canonical seed, supplied by the requester.
- **[T2]** *TOMAGI: Topological Operator Machine for Analytic Geometric Inference*, version 1.0.0, 1 September 2026. Supplied project specification.
- **[T3]** *TOM Topological Open Modular Seeded Referential Substrate*, TOM-SRS 1.0. Supplied project specification.
- **[T4]** `CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md` and proof JSON. Supplied corrective authority boundary.
- **[T5]** *TOM Manufacturing Horizons: From a Frozen Deterministic Kernel to Frontier Physical, Biochemical and Biological Fabrication*, 3 September 2026. Companion source document.

## Current platform and financial sources

- **[G1]** Google, "Google's products and services - About Google." Product directory accessed 3 September 2026. https://about.google/products/
- **[G2]** Alphabet Inc., Annual Report on Form 10-K for the year ended 31 December 2025, filed 2026. Product and revenue descriptions, advertising dependence and disaggregated revenues. https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm

## Open protocols and commons foundations

- **[W1]** World Wide Web Consortium, *Verifiable Credentials Data Model v2.0*, W3C Recommendation, 15 May 2025. https://www.w3.org/TR/vc-data-model-2.0/
- **[W2]** World Wide Web Consortium, *Decentralized Identifiers (DIDs) v1.0*. https://www.w3.org/TR/did/
- **[W3]** World Wide Web Consortium, *ActivityPub*. https://www.w3.org/TR/activitypub/
- **[W4]** Solid Project, "About Solid." https://solidproject.org/about
- **[W5]** Matrix.org Foundation, *Matrix Specification*. https://spec.matrix.org/latest/
- **[W6]** OpenStreetMap, "About OpenStreetMap." https://www.openstreetmap.org/about
- **[W7]** Wikidata, "Wikidata: Introduction." https://www.wikidata.org/wiki/Wikidata:Introduction
- **[W8]** Common Crawl, "Overview." https://commoncrawl.org/overview
- **[W9]** OpenAlex, open research graph. https://openalex.org/
- **[W10]** World Wide Web Consortium, *Web Authentication: An API for accessing Public Key Credentials*. https://www.w3.org/TR/webauthn-3/

## Human rights and digital public infrastructure

- **[H1]** United Nations, *Universal Declaration of Human Rights*. https://www.un.org/en/about-us/universal-declaration-of-human-rights
- **[H2]** United Nations Development Programme, "Digital public infrastructure." https://www.undp.org/digital/digital-public-infrastructure

# Appendix G - Closing note

TOM Commons is intentionally described as a replacement architecture rather than a finished brand. The word "Google" in this report names the breadth of functions to be replaced: discovery, interpretation, identity, communication, work, maps, media, commerce, cloud, AI and the route from information to action. A credible successor cannot be built by copying one interface while retaining the same centralised control structure.

The evolutionary move is from:

```text
one company account
one hidden ranking economy
one behavioural profile
one integrated service enclosure
```

To:

```text
portable human context
plural indexes and models
visible evidence and ranking
interoperable services
permissioned action
proof-carrying outcomes
right to exit and appeal
```

That transition can begin with ordinary computers and open protocols. The most futuristic manufacturing and biological horizons remain downstream research programmes. The fixed TOM substrate contributes deterministic identity, bounded authority, replay and lineage; society still has to build the institutions, science, care and democratic judgement that make those capabilities humane.
''')

print('appended appendices to',p)
