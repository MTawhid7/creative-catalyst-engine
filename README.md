# Creative Catalyst Engine

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/MTawhid7/creative-catalyst-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

---

**Creative Catalyst Engine** — an opinionated, composable AI pipeline that converts a short creative brief into a complete fashion intelligence package: a validated trend report (JSON), art-directed narrative prompts, and editorial-quality images. The design balances creative intent with engineering rigor: schema-validated outputs, semantic caching, and a robust fallback path when web-synthesis is weak.

> Elegant, reproducible, and built for iteration — from early concepting to polished outputs.

---

## Table of contents

- [Creative Catalyst Engine](#creative-catalyst-engine)
  - [Table of contents](#table-of-contents)
  - [Why this project](#why-this-project)
  - [Key features](#key-features)
  - [Architecture (high level)](#architecture-high-level)
  - [Repository layout](#repository-layout)
  - [Quickstart](#quickstart)
    - [Clone](#clone)
    - [Create a virtual environment](#create-a-virtual-environment)
    - [Install dependencies](#install-dependencies)
    - [Environment variables](#environment-variables)
    - [Run (example)](#run-example)
  - [Outputs \& workflow](#outputs--workflow)
  - [Cache management](#cache-management)
  - [Configuration](#configuration)
  - [Troubleshooting](#troubleshooting)
  - [Testing \& development tips](#testing--development-tips)
  - [Contributing](#contributing)
  - [License \& acknowledgments](#license--acknowledgments)
    - [Contact](#contact)

---

## Why this project

This engine is built for teams who want reproducible, high-quality creative outputs while keeping costs and iteration time predictable. It blends:

* **Structured generation** (schema-first JSON outputs)
* **Semantic caching** (fast re-runs for similar briefs)
* **Resilient synthesis** (web research with a knowledge-only fallback)

Use cases: trend scouting, design sprint ideation, editorial brief expansion, and automated moodboard/prompt generation for image pipelines.

---

## Key features

* **Intelligent briefing:** Expand terse user input into a full, structured brief (brand, audience, mood, constraints).
* **Ethos analysis:** Infer unspoken creative values to guide tone and aesthetic choices.
* **Web synthesis + fallback:** Prefer live research; gracefully fall back to knowledge-only synthesis when necessary.
* **Schema-driven reports:** Pydantic models validate and type outputs (`FashionTrendReport`).
* **L1 semantic cache:** ChromaDB-backed cache for cost & latency savings.
* **Automatic run management:** Timestamped result folders + `latest` symlink and configurable retention.
* **Clear separation of concerns:** Small processors, single-responsibility, orchestrated pipeline.

---

## Architecture (high level)

A composable pipeline of discrete processors coordinated by an `Orchestrator`.

```
User Passage
    │
    ▼
[Brief Deconstruction] → [Ethos Clarification] → [Brief Enrichment]
    │                                   │
    └──► [Cache Check] —(hit)──► [Final Output Generator]
           │
         (miss)
           │
           ▼
     [Web Research] → [Context Structuring] → [Report Synthesis]
           │
        (if weak)
           ▼
    [Direct Knowledge Synthesis] (fallback)
```

**Primary processors**: `BriefDeconstructionProcessor`, `EthosClarificationProcessor`, `BriefEnrichmentProcessor`, `WebResearchProcessor`, `ContextStructuringProcessor`, `ReportSynthesisProcessor`, `DirectKnowledgeSynthesisProcessor`, `FinalOutputGeneratorProcessor`.

---

## Repository layout

```
creative-catalyst-engine/
├── .env                     # secrets (ignored)
├── sources.yaml             # optional: curated research sources
├── requirements.txt         # pinned dependencies
├── clear_cache.py           # purge L1 cache utility
└── catalyst/                # app source
    ├── __init__.py
    ├── main.py              # entry point (simple runner)
    ├── settings.py          # configuration (env-driven)
    ├── context.py           # RunContext
    ├── clients/
    │   └── gemini_client.py # resilient model + search client
    ├── models/
    │   └── trend_report.py  # Pydantic models (FashionTrendReport)
    ├── prompts/
    │   └── prompt_library.py# curated prompts by processor
    ├── caching/
    │   ├── cache_manager.py
    │   └── report_cache.py
    └── pipeline/
        ├── base_processor.py
        ├── orchestrator.py
        └── processors/
            ├── briefing.py
            ├── synthesis.py
            └── reporting.py
```

---

## Quickstart

### Clone

```bash
git clone https://github.com/MTawhid7/creative-catalyst-engine.git
cd creative-catalyst-engine
```

### Create a virtual environment

```bash
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows (PowerShell)
# .\venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
pip install -r requirements.txt
```

> Tip: consider pinning dependency versions in `requirements.txt` for reproducible CI runs.

### Environment variables

Create a `.env` file in the project root (never commit secrets):

```env
GEMINI_API_KEY="your_gemini_api_key_here"
GEMINI_MODEL_NAME="alloy"          # optional override
RESULTS_DIR=./results
KEEP_N_RESULTS=10
```

`catalyst/settings.py` reads environment variables at startup. Use environment-specific overrides for CI or production.

### Run (example)

Edit `USER_PASSAGE` in `catalyst/main.py` or pass a CLI wrapper (future improvement). Then run:

```bash
python -m catalyst.main
```

---

## Outputs & workflow

Each run writes a timestamped folder under `./results/` and updates a `latest` symlink. A typical run contains:

* `itemized_fashion_trends.json` — validated `FashionTrendReport` (primary artifact)
* `generated_prompts.json` — structured narrative/image prompts
* `debug_run_artifacts.json` — full run dump for debugging and reproducibility

Example:

```
results/
├── 20250826-114512_bohemian-desert-style/
└── latest -> 20250826-114512_bohemian-desert-style/
```

Retention of prior runs is controlled by `KEEP_N_RESULTS`.

---

## Cache management

The L1 semantic cache reduces repeated work for similar briefs.

* **Purge cache:**

```bash
python clear_cache.py
```

* **Behavior:** On a cache hit the orchestrator skips web research + synthesis and proceeds to output-generation. Keys are derived deterministically from stable parts of the deconstructed brief (brand, theme, constraints).

---

## Configuration

Key knobs live in `catalyst/settings.py`:

* `GEMINI_MODEL_NAME` — model identifier
* `RESULTS_DIR`, `LOGS_DIR` — I/O
* `KEEP_N_RESULTS` — retention
* `CACHE_DISTANCE_THRESHOLD` — semantic cache sensitivity
* `SOURCES_YAML` — optional curated research sources

Prefer environment variables for secrets and environment-specific values.

---

## Troubleshooting

* **No output / empty research** — check `GEMINI_API_KEY` and that the account allows tool usage. On weak web results the pipeline will automatically fallback to the knowledge-only synthesis.

* **Rate limits / timeouts** — client has retries; if persistent, check usage/quota and consider backoff tuning.

* **`latest` symlink not created (Windows)** — Windows may not support symlinks without admin privileges. Inspect the most recent timestamped folder in `results/` instead.

* **Cache didn't change after prompt edits** — purge the cache. The cache key is semantically driven; small rewording that preserves meaning can still hit the cache.

If you need more verbose diagnostics: enable debug logging in `settings.py` and inspect `debug_run_artifacts.json`.

---

## Testing & development tips

* Add unit tests around processors that focus on pure logic (no live API calls).
* Use dependency injection / mock clients for `gemini_client` during tests.
* Keep processors single-responsibility: small functions are easier to test and reason about.
* Consider a lightweight CLI wrapper (e.g. `typer`) for passing briefs programmatically.

---

## Contributing

Thanks for considering a contribution! To keep things tidy please:

1. Open an issue to discuss larger changes.
2. Keep PRs focused and small.
3. Add docstrings and type hints for new modules.
4. Include unit tests or reproducible examples for behavior changes.

---

## License & acknowledgments

Creative Catalyst Engine is released under the **MIT License** — see `LICENSE`.

Acknowledgments:

* Modern prompt-engineering and divide-and-conquer generation strategies.
* Open-source libraries powering caching, prompting, and orchestration.

---

### Contact

If you want a hand integrating this into a CI pipeline, adding an HTTP wrapper, or generating demo datasets, ping **MTawhid7** via GitHub.

---

*Last updated: 2025-08-25*
