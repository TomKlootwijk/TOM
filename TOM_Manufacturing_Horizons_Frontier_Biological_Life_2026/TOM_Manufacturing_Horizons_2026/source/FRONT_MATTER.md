---
title: ""
author: ""
date: ""
lang: en-GB
papersize: a4
fontsize: 9.5pt
geometry:
  - top=20mm
  - bottom=21mm
  - left=19mm
  - right=19mm
mainfont: "TeX Gyre Pagella"
sansfont: "TeX Gyre Heros"
monofont: "DejaVu Sans Mono"
colorlinks: true
linkcolor: tomteal
urlcolor: tomteal
toc: false
header-includes:
  - |
    \usepackage{microtype}
    \usepackage{xurl}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{tabularx}
    \usepackage{graphicx}
    \usepackage{float}
    \usepackage{fancyhdr}
    \usepackage{xcolor}
    \usepackage[most]{tcolorbox}
    \usepackage{etoolbox}
    \usepackage{enumitem}
    \usepackage{titlesec}
    \definecolor{tomnavy}{HTML}{103847}
    \definecolor{tomteal}{HTML}{149B9B}
    \definecolor{tomgold}{HTML}{BE8A00}
    \definecolor{tompurple}{HTML}{6E3E86}
    \definecolor{tomred}{HTML}{B3413B}
    \definecolor{tomgreen}{HTML}{3D7334}
    \definecolor{tomlight}{HTML}{EDF5F6}
    \definecolor{tomink}{HTML}{17252B}
    \pagestyle{fancy}
    \fancyhf{}
    \fancyhead[L]{\small\sffamily\textcolor{tomnavy}{TOM Manufacturing Horizons}}
    \fancyhead[R]{\small\sffamily\textcolor{tomnavy}{Frontier physical and biological manufacturing}}
    \fancyfoot[L]{\scriptsize\sffamily Requester-supplied attribution: Tom Klootwijk}
    \fancyfoot[R]{\scriptsize\sffamily\thepage}
    \setlength{\headheight}{14pt}
    \setlength{\parindent}{0pt}
    \setlength{\parskip}{3.2pt}
    \setlength{\tabcolsep}{3pt}
    \renewcommand{\arraystretch}{1.13}
    \AtBeginEnvironment{longtable}{\footnotesize\sffamily}
    \AtBeginEnvironment{table}{\footnotesize\sffamily}
    \titleformat{\section}{\Large\bfseries\sffamily\color{tomnavy}}{\thesection}{0.7em}{}
    \titleformat{\subsection}{\large\bfseries\sffamily\color{tomteal}}{\thesubsection}{0.7em}{}
    \titleformat{\subsubsection}{\normalsize\bfseries\sffamily\color{tompurple}}{\thesubsubsection}{0.7em}{}
    \newtcolorbox{boundarybox}[1][]{enhanced,breakable,colback=red!3,colframe=tomred,boxrule=0.8pt,arc=2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,title=Evidence boundary,fonttitle=\bfseries\sffamily,#1}
    \newtcolorbox{tomprinciple}[1][]{enhanced,breakable,colback=cyan!3,colframe=tomteal,boxrule=0.8pt,arc=2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,title=TOM principle,fonttitle=\bfseries\sffamily,#1}
    \newtcolorbox{futurebox}[1][]{enhanced,breakable,colback=violet!3,colframe=tompurple,boxrule=0.8pt,arc=2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,title=Physically grounded future concept,fonttitle=\bfseries\sffamily,#1}
    \newtcolorbox{statusbox}[1][]{enhanced,breakable,colback=green!3,colframe=tomgreen,boxrule=0.8pt,arc=2mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,title=Status,fonttitle=\bfseries\sffamily,#1}
---

\thispagestyle{empty}
\begin{center}
\vspace*{13mm}
{\Huge\bfseries\sffamily\textcolor{tomnavy}{TOM Manufacturing Horizons}}\\[3mm]
{\LARGE\sffamily\textcolor{tomteal}{From a frozen deterministic kernel to frontier physical, biochemical and biological fabrication}}\\[8mm]
\rule{0.86\textwidth}{1.2pt}\\[8mm]
\begin{minipage}{0.87\textwidth}
\large\centering
The complete preceding manufacturing exchange, expanded into an evidence-graded map of present-day systems, advanced organ manufacturing, engineered living materials, synthetic organisms, molecular factories, off-world industry and science-fiction-scale futures that remain compatible with known physics.
\end{minipage}\\[11mm]
\includegraphics[width=0.50\textwidth]{figures/stack.png}\\[8mm]
{\large\sffamily Tom Klootwijk}\\[1.5mm]
Requester-supplied attribution: 10-07-1990 | NL200678942\\[1.5mm]
3 September 2026\\[10mm]
\begin{minipage}{0.86\textwidth}
\small
This report distinguishes (1) claims made by the supplied TOM/TOMAGI documents, (2) results demonstrated in external scientific literature, (3) engineering extrapolations, (4) known-physics-compatible but unbuilt systems, and (5) ideas that remain unestablished. It is not a medical, biosafety, chemical-synthesis, clinical, regulatory, or manufacturing instruction manual. Biological sections stay at architecture and evidence-governance level and intentionally omit operational wet-lab protocols.
\end{minipage}
\end{center}

\newpage
\tableofcontents
\newpage

# Executive synthesis

The preceding exchange proposed a broad manufacturing future built around one central idea: a manufactured object should be inseparable from the exact definitions, process states, evidence, decisions, revisions and lineage that admitted it. The supplied TOM documents support that architecture at the computational level. TOM-SRS describes a 244-byte canonical root that expands through typed definitions, support, compatibility, a guarded event, transition and lineage, while treating rendering, learned behaviour and physical embodiments as downstream phenotypes rather than substrate authority. The TOMAGI reference machine supplies a fixed 128-byte header, 64-byte state, 48-byte cell and sixteen-opcode deterministic execution model. The CODEX handoff further insists that future capability expansion must preserve defined arithmetic, bounded formal values, replay-authenticated output and a strict separation among formal authority, independent oracle and mechanical host services.

The manufacturing consequence is not that TOM itself knows physics or biology. It is that a product or living construct can be governed as a **proof-carrying causal object**:

```text
canonical design and process definitions
-> external simulation, laboratory, machine or biological phenotype
-> typed observations and proposals
-> support / compatibility / guard
-> explicit accept, reject or ambiguous result
-> atomic transition and parent-bound publication
-> immutable product, tissue, organism or habitat lineage
```

This architecture can be applied now to software releases, machine configurations, industrial digital threads, automated laboratories, quality systems and evidence vaults. It can plausibly extend to proof-carrying factories, semiconductor accelerators, vascularized tissue modules, organ foundries, engineered living materials, cell-based biological machines, molecular robotics and in-space microfactories. Some farther concepts--whole replacement organs, novel synthetic symbionts, self-growing habitats and self-reproducing industrial ecosystems--are compatible with known physics but require major scientific breakthroughs. Fully autonomous de novo life assembled from nonliving chemistry, a general molecular nanofactory, and AGI emerging from the kernel alone are not established.

\begin{tomprinciple}
The kernel should remain frozen. Capability expands through content-addressed domain packs, external instruments and simulators, independent oracles, and explicit promotion transactions. A robot, bioreactor, tissue, organ or organism may express TOM-governed definitions, but it does not retroactively become the source of those definitions.
\end{tomprinciple}

![Frozen kernel, expanding manufacturing stack. The authority path stays deterministic; external machines and living systems remain measured phenotypes and proposal sources.](figures/stack.png){width=66%}

# Sources, status and evidence boundary

## Supplied TOM sources

This report is grounded in the following supplied materials:

- **[S1] Canonical TOM seed.** The root is the exact one-line 244-byte string `TOM_seed_genome_2026-09-01.txt`, SHA-256 `d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5`.
- **[S2] TOMAGI 1.0.** The reference machine defines literal SDF-zero membership inside a finite LUT, deterministic one-bit jitter/branching, fixed-width state and cell records, sixteen opcodes, output and lineage. The page-one execution-chain graphic depicts one stored `Cell48` executing per tick and selecting the next cell.
- **[S3] TOM-SRS 1.0.** The page-four expansion diagram places the canonical seed upstream of parsing, a content-addressed world, a typed query/event evaluator, state/event/transition/lineage, and only then an optional phenotype such as projection, control, AI or hardware. Its canonicalization section says hardware changes scheduling and throughput, not seed meaning.
- **[S4] CODEX kernel repair handoff.** It freezes the current kernel boundary, requires defined integer arithmetic, reserved-header rejection, bounded recursive values, same-host publication locking and reproducible packaging, and explicitly declines unsupported GPU and AGI claims.
- **[S5] CODEX repair proof.** It records a passing literal TOMAGI artifact chain with equal Python/C traces and 1,032 authenticated `EMIT` records.
- **[S6] Roadmap discipline.** It separates formal authority, an independent oracle and mechanical host services, and prohibits hidden domain decisions in host code.
- **[S7] Repository authority rule.** Every delivered artifact must retain a literal source -> `.tmg` -> ordered execution/`EMIT` -> materialized-bytes chain.

## Scientific and engineering sources

The expansion uses peer-reviewed primary research, standards bodies and official agency material. The references are listed at the end. They include synthetic-genome cells, minimal genomes, alternative genetic polymers, xenobots and anthrobots, engineered living materials, tissue vascularization, high-cell-density biomanufacturing, bioprinted cardiac constructs, organoids, stem-cell islets, xenotransplantation, automated materials laboratories, molecular machines, in-space manufacturing and genome-editing governance.

## Evidence classes

![Evidence and maturity scale used throughout the report.](figures/maturity.png){width=100%}

| Class | Meaning | Appropriate wording |
|---|---|---|
| **A. Demonstrated now** | A peer-reviewed or operational example exists, although not necessarily as a mature product | "has been demonstrated," "is available," "can be prototyped" |
| **B. Engineering extrapolation** | Required mechanisms exist separately; integration is a demanding but conventional engineering programme | "plausible engineering target," "requires integration and certification" |
| **C. Major research frontier** | Critical mechanisms remain unresolved at scientifically important scale | "research frontier," "not yet reliable or general" |
| **D. Known-physics-compatible speculation** | No known physical law forbids the system, but there is no complete demonstration and major unknowns remain | "physically conceivable," "distant," "scenario, not forecast" |
| **E. Not established** | The core capability has not been achieved or may rest on an unresolved scientific assumption | "not achieved," "no present evidence" |

\begin{boundarybox}
"Physically possible" is not equivalent to "practical," "safe," "ethical," "economical," "clinically effective," "manufacturable," or "demonstrated." Known physics only rules out obvious impossibilities; it does not supply a viable design, materials, developmental programme, control law, or evidence of benefit.
\end{boundarybox}

