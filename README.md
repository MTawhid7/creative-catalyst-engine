### **File: `README.md` (Full and Final Version)**

# Creative Catalyst Engine

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-username/creative-catalyst-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

The **Creative Catalyst Engine** is an AI-powered, idea-to-image pipeline that turns a simple creative brief into a multi-format fashion intelligence package: a structured trend report (JSON), art-directed narrative prompts, and final editorial-quality images.

It uses a composable, multi-stage pipeline to deconstruct and enrich input, synthesize research (via model-assisted web search), and emit validated, typed outputs. With a robust fallback path and a semantic L1 cache, it’s designed for both creative excellence and technical resilience.

---

## Table of Contents

- [Creative Catalyst Engine](#creative-catalyst-engine)
  - [Table of Contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Architecture Overview](#architecture-overview)
  - [Repository Structure](#repository-structure)
  - [Setup](#setup)
    - [1) Clone](#1-clone)
    - [2) Create a Virtual Environment](#2-create-a-virtual-environment)
    - [3) Install Dependencies](#3-install-dependencies)
    - [4) Environment Variables](#4-environment-variables)
  - [Running the Engine](#running-the-engine)
  - [Outputs](#outputs)
  - [Cache Management](#cache-management)
  - [Configuration](#configuration)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [License](#license)
    - [Acknowledgments](#acknowledgments)

---

## Key Features

* **Intelligent Briefing**
  Starts from a vague request and infers a complete, context-aware brief (brand category, audience, attributes).

* **Direct Web Synthesis**
  Uses the model’s built-in search/tooling to perform broad research and synthesize findings—without brittle URL-by-URL scraping.

* **Divide-and-Conquer Structuring**
  Breaks the problem into small, verifiable steps to produce a perfectly structured, validated JSON report.

* **Resilient Fallback**
  If web synthesis is insufficient, auto-pivots to a knowledge-only path to ensure a high-quality report.

* **L1 Report Caching**
  ChromaDB-backed semantic cache makes re-runs of similar briefs near-instant and cost-efficient.

* **End-to-End Image Generation**
  Translates narrative prompts into polished, editorial-style images via a dedicated image client.

---

## Architecture Overview

A modern, modular **Composable Pipeline Architecture**: discrete **Processors** orchestrated by a central **Orchestrator**. Each processor does one thing well and passes typed artifacts downstream.

```
User Passage
    │
    ▼
[ Brief Deconstruction ] → [ Brief Enrichment ]
    │                            │
    └─────────► [ L1 Cache Check (CacheManager) ] ──► (Hit) ─┐
                         │                                    │
                      (Miss)                                  ▼
                         │                          [ Final Output Generation ]
                         ▼                                    │
            [ Web Research ] → [ Context Structuring ] → [ Report Synthesis ]
                         │
                    (if weak)
                         ▼
               [ Direct Knowledge Synthesis ]   (fallback)
```

**Primary Processor Set**

* `BriefDeconstructionProcessor`
* `BriefEnrichmentProcessor`
* `WebResearchProcessor`
* `ContextStructuringProcessor`
* `ReportSynthesisProcessor`
* `DirectKnowledgeSynthesisProcessor` (fallback)
* `FinalOutputGeneratorProcessor`
* `ImageGenerationProcessor`

---

## Repository Structure

```
creative-catalyst-engine/
├── .env                     # Your API keys (not committed)
├── requirements.txt         # Python dependencies
├── clear_cache.py           # Utility to purge L1 cache
│
└── catalyst/                # Application source
    ├── __init__.py
    ├── main.py              # Single entry point
    ├── settings.py          # Central config (reads environment)
    ├── context.py           # RunContext (state for a single run)
    │
    ├── clients/
    │   ├── gemini_client.py # Resilient client for model calls & search tools
    │   └── dalle_client.py  # Client for image generation
    │
    ├── models/
    │   └── trend_report.py  # Pydantic models for FashionTrendReport
    │
    ├── prompts/
    │   └── prompt_library.py# Master prompts for all processors
    │
    ├── caching/
    │   ├── cache_manager.py # Facade over L1 cache
    │   └── report_cache.py  # ChromaDB semantic cache operations
    │
    └── pipeline/
        ├── __init__.py
        ├── base_processor.py# Abstract BaseProcessor
        ├── orchestrator.py  # PipelineOrchestrator
        │
        └── processors/
            ├── __init__.py
            ├── briefing.py   # Deconstruction & Enrichment processors
            ├── synthesis.py  # Web Research, Structuring, Synthesis
            ├── reporting.py  # JSON + narrative prompt generation
            └── imaging.py    # Final image generation
```

---

## Setup

### 1) Clone

```bash
git clone https://github.com/your-username/creative-catalyst-engine.git
cd creative-catalyst-engine
```

### 2) Create a Virtual Environment

```bash
python -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
# .\venv\Scripts\Activate.ps1
```

### 3) Install Dependencies

```bash
pip install -r requirements.txt
```

### 4) Environment Variables

Create a `.env` file in the repo root:

```
GEMINI_API_KEY="your_gemini_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"
```

> `settings.py` reads these variables at runtime. Keep `.env` out of version control.

---

## Running the Engine

The primary interaction point is the `USER_PASSAGE` inside `catalyst/main.py`. Update it with your creative brief (plain English is fine):

```python
# catalyst/main.py (snippet)
USER_PASSAGE = """
Design a capsule collection for AW25 inspired by Brutalist architecture:
monochrome palette, sharp tailoring, and sculptural knitwear for urban professionals.
"""
```

Then run from the project root:

```bash
python -m catalyst.main
```

---

## Outputs

On each run, the engine creates a timestamped folder under `./results/` and updates a `latest` symlink to point to it (on Windows, symlink creation may require elevated permissions).

Inside the run folder you’ll find:

* `itemized_fashion_trends.json` — the validated `FashionTrendReport`
* `generated_prompts.json` — structured narrative prompts
* `images/` — final `.png` renders from the image client
* `logs/` — optional run logs (if enabled)

Example layout:

```
results/
└── 2025-08-23_12-30-45/
    ├── itemized_fashion_trends.json
    ├── generated_prompts.json
    ├── images/
    │   ├── final_0001.png
    │   └── final_0002.png
    └── logs/
```

---

## Cache Management

The L1 semantic cache accelerates repeat or similar briefs.

* **Purge the cache** (use after major prompt changes or to force a fresh synthesis):

```bash
python clear_cache.py
```

* **Cache behavior**
  The `CacheManager` generates a deterministic key from stable, user-driven parts of the deconstructed brief. On a cache hit, the pipeline skips research/synthesis and goes straight to reporting & imaging.

---

## Configuration

Core configuration lives in `catalyst/settings.py`. Common knobs:

* **Model/API**: model names, temperature, and tool-use flags for the research step.
* **I/O**: paths for results, logs, and cache.
* **Imaging**: image size, number of variations, and concurrency.

> Tip: Prefer environment variables for secrets and environment-specific overrides.

---

## Troubleshooting

* **No output / empty research**
  Ensure your model key allows tool-use/search. If web synthesis returns little content, the orchestrator will fall back automatically; you can also refine the `USER_PASSAGE` to be more specific.

* **Rate limits / timeouts**
  Reduce per-step concurrency in `settings.py` or re-run. The pipeline is resilient to intermittent failures.

* **`latest` symlink not created (Windows)**
  Run the shell as Administrator or navigate directly to the timestamped folder under `results/`.

* **Cache didn’t update after prompt change**
  Purge via `python clear_cache.py`. The deterministic key is based on the deconstructed brief; small wording changes may still produce a cache hit.

* **Image generation fails**
  Verify `OPENAI_API_KEY` is valid and your account has access to the specified image model. Check any size/variations limits in `settings.py`.

---

## Contributing

Issues and PRs are welcome! Please:

1. Open an issue describing the improvement or bug.
2. Follow existing module boundaries (one responsibility per processor).
3. Add or update docstrings and type hints.
4. Include minimal, reproducible examples or tests where possible.

---

## License

This project is released under the [MIT License](LICENSE).

---

### Acknowledgments

* Modern prompt-engineering and structured-generation techniques inspired the divide-and-conquer synthesis approach.
* Thanks to the open-source community for libraries that power the cache, models, and orchestration layers.
