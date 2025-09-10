# 🚀 Creative Catalyst Engine

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-repo/creative-catalyst-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

The **Creative Catalyst Engine** is an AI-powered, idea-to-image pipeline delivered as a scalable and resilient web service. It transforms a simple creative brief into a multi-format fashion intelligence package: a structured trend report (JSON), an art-directed style guide with a defined mood and photographic style, and a suite of editorial-quality images.

Built on a robust stack of FastAPI, Celery, and Redis, the engine is architected for high performance and long-term maintainability. It features an intelligent, multi-level caching system and a modular, strategy-based design for its core logic. The system uses sophisticated AI-driven techniques like **Conceptual Blending** for innovation, a **Creative Compass** for mood-based guidance, and a "divide and conquer" synthesis process to achieve a level of creative coherence that mimics a world-class design studio.

---

## Table of Contents

- [🚀 Creative Catalyst Engine](#-creative-catalyst-engine)
  - [Table of Contents](#table-of-contents)
  - [Guiding Principles](#guiding-principles)
  - [Key Features](#key-features)
  - [Architecture Overview](#architecture-overview)
  - [Repository Structure](#repository-structure)
  - [Setup and Configuration](#setup-and-configuration)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Environment Variables](#environment-variables)
  - [Running the Engine](#running-the-engine)
    - [Terminal 1: Start Redis](#terminal-1-start-redis)
    - [Terminal 2: Start Celery Worker](#terminal-2-start-celery-worker)
    - [Terminal 3: Start the API Server](#terminal-3-start-the-api-server)
  - [Interacting with the Engine](#interacting-with-the-engine)
  - [API Output Structure](#api-output-structure)
  - [Troubleshooting](#troubleshooting)

---

## Guiding Principles

This engine is built with a few core architectural principles in mind:

*   **Separation of Concerns:** The **Service Layer** (`api/`) is strictly decoupled from the **Core Engine** (`catalyst/`). The API handles web requests and jobs, while the engine focuses purely on generating fashion intelligence. This modularity makes the system easier to maintain and test.
*   **Strategy-Based Logic:** Complex, multi-step operations (like report synthesis) are encapsulated in dedicated "builder" classes. This eliminates monolithic functions, promotes SOLID principles, and makes the core pipeline processors lean, readable controllers.
*   **Resilience by Design:** The pipeline features granular, stage-aware exception handling, and external API clients have built-in retry logic for transient errors. The system is designed to gracefully handle minor creative failures from the AI and proceed to a successful conclusion.
*   **Configuration over Code:** Key behaviors, such as API keys, URLs, and the choice of image generation model, are controlled via environment variables (`.env`), not hardcoded values.

---

## Key Features

*   **True Asynchronous Processing**: A FastAPI front-end accepts jobs and queues them to Celery, ensuring the API is always responsive. The core pipeline logic is fully `async` for maximum I/O throughput.
*   **Intelligent Multi-Level Caching**:
    *   **L0 Intent Cache (High-Speed):** A pre-inference Redis cache that provides instant results for semantically identical requests, even with different wording.
    *   **L1 Consistency Cache (Semantic):** A vector-based ChromaDB cache that ensures different phrasings of the same core idea produce identical, high-quality results without redundant work.
*   **AI-Powered Creative Direction**:
    *   **Conceptual Blending:** Uses a "Creative Antagonist" not for simple opposition, but to find an opposite world, isolate one tangible principle, and synthesize it into the core theme to create a single, surprising, and innovative design detail.
    *   **Creative Compass (`desired_mood`):** The system first infers a set of evocative "mood words" from the user's request. This "compass" then guides all downstream creative choices, from the selection of inspirational designers to the final art direction of the photography.
*   **Modular "Divide and Conquer" Synthesis**: Instead of a single, unreliable prompt, the system uses a sequence of smaller, hyper-focused, and schema-driven AI calls to assemble the final report. This "builder" pattern dramatically increases the reliability and quality of the structured output.
*   **Robust Artifact Handling**: A transaction-like caching mechanism with automatic rollback prevents data corruption and orphaned files, ensuring data integrity between the file system and the vector database.

---

## Architecture Overview

The engine is architected as a modern, decoupled web service. The diagram below illustrates the full request lifecycle.

<details>
<summary>Click to view the Mermaid diagram source code</summary>

```mermaid
graph TD
    subgraph Client
        A[API Client]
    end

    subgraph Service Layer
        B(FastAPI Server)
        D{Celery Worker}
        C[(Redis Broker & Backend)]
    end

    subgraph Caching
        subgraph L0_Cache [L0 Intent Cache]
            L0_AI[(Fast AI Key Gen)]
            L0_Redis[(Redis K/V Store)]
        end
        subgraph L1_Cache [L1 Consistency Cache]
            L1_Chroma[(ChromaDB)]
        end
    end

    subgraph Core_Engine [Catalyst Core Engine]
        E[Briefing Stage]
        F[Synthesis Stage]
        G[Generation Stage]
    end

    A -- 1. POST /v1/creative-jobs --> B
    B -- 2. Enqueue Job --> C
    C -- 3. Dequeue Job --> D

    D -- 4. Check L0 Cache --> L0_AI
    L0_AI -- 5. Generate Intent Key --> D
    D -- 6. GET key --> L0_Redis

    subgraph L0_Decision; L0_Redis -- 7a. L0 HIT --> D_L0_Hit; L0_Redis -- 7b. L0 MISS --> E; end

    E -- 8. Run Briefing (incl. Mood & Synthesis) --> F
    F -- 9. Check L1 Cache --> L1_Chroma

    subgraph L1_Decision; L1_Chroma -- 10a. L1 HIT --> G; L1_Chroma -- 10b. L1 MISS --> F_Run; end

    F_Run[Run Full Synthesis via Builders] -- 11. --> G
    G -- 12. Finalize & Store in L1 --> D_L1_Done

    D_L0_Hit -- 13a. Job Complete --> C
    D_L1_Done -- 13b. Job Complete --> C
    C -- 14. Store Final Result --> C

    A -- 15. Polls GET /v1/jobs/{id} --> B
    B -- 16. Fetch Result --> C
    C -- 17. Return Result --> B
    B -- 18. Send Final Report --> A
```
</details>

---

## Repository Structure

```
creative-catalyst-engine/
├── .env                  # Environment variables (API keys, URLs). NOT committed to Git.
├── .gitignore            # Specifies files for Git to ignore.
├── README.md             # The high-level project documentation you are reading.
├── requirements.txt      # Python package dependencies.
├── clear_cache.py        # A utility script to wipe all caches (Redis, Chroma, files).
│
├── api/                  # The Service Layer: Handles web requests, jobs, and L0 caching.
│   ├── __init__.py
│   ├── main.py           # FastAPI application: Defines API endpoints (e.g., /v1/creative-jobs).
│   ├── worker.py         # Main Celery worker entry point (for Linux/WSL).
│   ├── eventlet_worker.py# Special Celery entry point for macOS compatibility.
│   ├── cache.py          # Logic for the L0 (high-speed intent) Redis cache.
│   ├── config.py         # API-layer specific configurations (e.g., Redis cache prefix).
│   └── prompts.py        # Prompts used exclusively by the API layer (e.g., for L0 key generation).
│
├── api_client/           # A standalone Python client for interacting with the API.
│   ├── __init__.py
│   ├── client.py         # The `CreativeCatalystClient` class for submitting and polling jobs.
│   ├── exceptions.py     # Custom exceptions for the client (e.g., JobFailedError).
│   └── example.py        # A simple script demonstrating how to use the client.
│
└── catalyst/             # The Core Engine: All business logic for the creative pipeline.
    ├── __init__.py
    ├── main.py           # Core `run_pipeline` function; the main entry point for the engine.
    ├── settings.py       # Central configuration for the engine (file paths, model names).
    ├── context.py        # Defines the `RunContext` class, the data object passed through the pipeline.
    │
    ├── caching/          # L1 Semantic Cache logic.
    │   ├── __init__.py
    │   ├── cache_manager.py # High-level interface for the L1 cache.
    │   └── report_cache.py  # ChromaDB implementation for vector-based semantic caching.
    │
    ├── clients/          # Clients for external services.
    │   └── gemini/
    │       ├── __init__.py         # Public interface for the Gemini client.
    │       ├── client_instance.py  # Initializes the singleton Gemini client object.
    │       ├── core.py             # Core logic for making sync/async API calls.
    │       ├── resilience.py       # Retry logic and backoff delays.
    │       └── schema.py           # Pydantic schema processing for Gemini's structured output.
    │
    ├── models/
    │   └── trend_report.py   # Pydantic models for the final, structured `FashionTrendReport`.
    │
    ├── pipeline/         # The core multi-stage processing pipeline.
    │   ├── __init__.py
    │   ├── orchestrator.py   # The `PipelineOrchestrator` that manages the execution flow.
    │   ├── base_processor.py # The abstract base class that all pipeline steps inherit from.
    │   │
    │   ├── processors/       # The main controllers for each stage of the pipeline.
    │   │   ├── __init__.py
    │   │   ├── briefing.py     # Processors for Stage 1: Deconstruction, Ethos, Enrichment.
    │   │   ├── synthesis.py    # Processors for Stage 3: Web Research, Structuring, Fallback.
    │   │   ├── reporting.py    # Processor for Stage 4: Saving files, triggering prompt generation.
    │   │   │
    │   │   └── generation/     # Image generation strategies.
    │   │       ├── __init__.py             # Factory function `get_image_generator`.
    │   │       ├── base_generator.py       # Abstract base class for image generators.
    │   │       └── nanobanana_generator.py # Specific implementation for the Nano Banana model.
    │   │
    │   ├── prompt_engineering/
    │   │   └── prompt_generator.py # The class that builds the final image prompts from the report.
    │   │
    │   └── synthesis_strategies/ # The modular, "divide and conquer" logic for report assembly.
    │       ├── __init__.py
    │       ├── report_assembler.py   # The orchestrator that manages the specialized builders.
    │       ├── section_builders.py   # NEW: The specialized builder classes for each report section.
    │       └── synthesis_models.py   # Intermediate Pydantic models for the builder outputs.
    │
    ├── prompts/
    │   └── prompt_library.py # The master library of all creative and synthesis prompts.
    │
    └── utilities/            # Shared helper functions.
        ├── __init__.py
        ├── config_loader.py  # Loads and formats `sources.yaml`.
        ├── json_parser.py    # Robustly parses JSON from LLM outputs.
        └── logger.py         # Configures the centralized application logger.
│
├── artifact_cache/       # Permanent storage for L1 cached artifacts (images, reports).
├── chroma_cache/         # Directory for the ChromaDB vector store (L1 cache).
├── logs/                 # Contains the rotating log files (e.g., catalyst_engine.log).
└── results/              # Rotating storage for the N most recent user-facing runs.
```

---

## Setup and Configuration

### Prerequisites

*   Python 3.11+
*   Docker Desktop (for Redis)

### Installation

```bash
git clone https://github.com/MTawhid7/creative-catalyst-engine.git
cd creative-catalyst-engine

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root. This file is ignored by Git.

```ini
# .env

# --- API Keys & Secrets ---
GEMINI_API_KEY="your_gemini_api_key_here"

# --- Feature Flags & Model Selection ---
ENABLE_IMAGE_GENERATION=True
IMAGE_GENERATION_MODEL="nano-banana"  # Options: "dall-e-3", "nano-banana"

# --- Infrastructure & Networking ---
REDIS_URL="redis://localhost:6379/0"

# CRITICAL: This MUST be the public-facing base URL of your server.
# It is used to construct the absolute URLs for images in the final report.
# For local testing, http://127.0.0.1:9500 is correct.
ASSET_BASE_URL="http://127.0.0.1:9500"
```

---

## Running the Engine

You will run three processes in separate terminals.

### Terminal 1: Start Redis

```bash
docker run -d -p 6379:6379 --name creative-catalyst-redis redis
```

### Terminal 2: Start Celery Worker

**For Linux / WSL:**
```bash
source venv/bin/activate
celery -A api.worker.celery_app worker --loglevel=info
```
**For macOS (requires `eventlet`):**
```bash
source venv/bin/activate
celery -A api.eventlet_worker.celery_app worker --loglevel=info -P eventlet
```

### Terminal 3: Start the API Server

```bash
source venv/bin/activate
uvicorn api.main:app --reload --port 9500 --host 0.0.0.0
```

---

## Interacting with the Engine

*   **Recommended:** Use the API Client via `python -m api_client.example`.
*   **Direct API (curl):** First, `POST` to `/v1/creative-jobs`, then `GET` the `/v1/creative-jobs/{job_id}` endpoint.
*   **Local Debugging:** Edit `catalyst/main.py` and run `python -m catalyst.main`.

---

## API Output Structure

A completed job response contains the final report with image URLs embedded directly within each key piece.

**Example `GET /v1/creative-jobs/{id}` Response:**
```json
{
  "job_id": "your-job-id",
  "status": "complete",
  "result": {
    "final_report": {
      "overarching_theme": "The concept of 'Bio-Luminescent Leisure'...",
      "desired_mood": ["Sophisticated", "Effortless", "Radiant"],
      "detailed_key_pieces": [
        {
          "key_piece_name": "The 'Hydro-Lumina Sculpted Maillot'",
          "description": "This one-piece swimsuit serves as the primary canvas...",
          "final_garment_image_url": "http://127.0.0.1:9500/results/run-folder/garment.png",
          "mood_board_image_url": "http://127.0.0.1:9500/results/run-folder/moodboard.png"
        }
      ]
    },
    "artifacts_path": "/path/to/project/results/run-folder"
  }
}
```

---

## Troubleshooting

| Symptom                                | Probable Cause & Solution                                                                                                                                                                                                                                                       |
| :------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **500 Internal Server Error**          | A background job failed. **Check the logs in your Celery worker terminal.** The full Python traceback, which shows the exact error, will be printed there. This is the most important step for debugging any pipeline failure.                                                  |
| **Images not loading (404 Not Found)** | The `ASSET_BASE_URL` in your `.env` file is incorrect. It must be the public-facing address of your server that the client machine can reach (e.g., `http://<your_server_lan_ip>:9500` if testing on a local network). Also ensure the `uvicorn` server is running.             |
| **Empty `accessories` field**          | This is not a bug, but a known variance. The system is designed to gracefully handle cases where the AI's creative enrichment for a secondary field (like accessories) fails. The pipeline will complete successfully with a rich report, but this specific field may be empty. |
| **`asyncio` or `eventlet` errors**     | A conflict between `asyncio` and `eventlet` is occurring. The worker is designed to handle this by running the `async` pipeline in a dedicated, isolated event loop. Ensure your `api/worker.py` uses the `asyncio.new_event_loop()` pattern.                                   |
| **Getting old/cached results**         | The L0 (Redis) or L1 (Chroma) caches are still active. Run the master cache clearing utility: `python clear_cache.py`. This script now clears all file-based caches, results folders, and the Redis database for a completely fresh start.                                      |