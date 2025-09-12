# 🚀 Creative Catalyst Engine

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-repo/creative-catalyst-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

The **Creative Catalyst Engine** is an AI-powered, idea-to-image pipeline delivered as a scalable and resilient web service. It transforms a simple creative brief into a multi-format fashion intelligence package: a structured trend report (JSON), an art-directed style guide, and a suite of editorial-quality images.

Built on a robust, modern stack of **FastAPI, ARQ, and Redis**, the engine is fully containerized with Docker for perfect reproducibility and ease of use. It features an intelligent, multi-level caching system, integrated error monitoring with Sentry, and a modular, "divide and conquer" synthesis process to achieve a level of creative coherence that mimics a world-class design studio.

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
  - [Interacting with the Engine](#interacting-with-the-engine)
  - [Dependency Management](#dependency-management)
  - [Troubleshooting](#troubleshooting)

---

## Guiding Principles

This engine is built with a few core architectural principles in mind:

*   **Separation of Concerns:** The **Service Layer** (`api/`) is strictly decoupled from the **Core Engine** (`catalyst/`). The API handles web requests and jobs, while the engine focuses purely on generating fashion intelligence.
*   **Strategy-Based Logic:** Complex, multi-step operations are encapsulated in dedicated "builder" classes, promoting SOLID principles and making the core pipeline readable and maintainable.
*   **Resilience by Design:** The pipeline features granular, stage-aware exception handling, a fallback synthesis path, and integrated error tracking with Sentry to ensure high availability.
*   **Production-Ready by Design:** The entire application is containerized, ensuring a consistent and reproducible environment from local development to production. Key behaviors are controlled via environment variables, not hardcoded values.

---

## Key Features

*   **True Asynchronous Processing**: A FastAPI front-end accepts jobs and queues them to **ARQ (Async-Redis-Queue)**, a modern, high-performance `asyncio`-native task queue, ensuring the API is always responsive.
*   **Containerized & Reproducible**: The entire application stack (API, worker, Redis) is defined in Docker and orchestrated with a single `docker-compose` command for a seamless, one-step setup.
*   **Intelligent Multi-Level Caching**:
    *   **L0 Intent Cache (High-Speed):** A pre-inference Redis cache that provides instant results for semantically identical requests.
    *   **L1 Consistency Cache (Semantic):** A vector-based ChromaDB cache that ensures different phrasings of the same core idea produce identical results without redundant work.
*   **Integrated Error Monitoring**: The API and worker are instrumented with **Sentry** to automatically capture, diagnose, and report any errors in real-time.
*   **Human-Readable & Machine-Parsable Logging**: Features a dual-format logging system that outputs beautiful, color-coded logs to the console for developers and structured JSON logs to a file for machine analysis.
*   **AI-Powered Creative Direction**:
    *   **Conceptual Blending:** Uses a "Creative Antagonist" to synthesize a single, surprising, and innovative design detail.
    *   **Creative Compass (`desired_mood`):** Infers a set of "mood words" that guide all downstream creative choices for a coherent final package.

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

    subgraph "Service Layer (Docker Network)"
        B(FastAPI Server)
        D{ARQ Worker}
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
├── .env                    # Local environment variables (API keys, DSN). Ignored by Git.
├── .gitignore              # Specifies files for Git to ignore.
├── .dockerignore           # Specifies files for Docker to ignore during image builds.
├── Dockerfile              # The multi-stage blueprint for building our secure, production-ready container image.
├── docker-compose.yml      # The master orchestrator for running the entire application stack (api, worker, redis).
├── requirements.in         # The high-level, human-managed list of Python dependencies.
├── requirements.txt        # The full, frozen "lock file" of all dependencies, generated by pip-tools.
├── clear_cache.py          # A utility script to wipe all caches (Redis, Chroma, files) for a fresh start.
├── LICENSE                 # The project's software license.
├── README.md               # The high-level project documentation.
└── WORKFLOW_GUIDE.md       # The definitive guide to the team's Git workflow.
│
├── api/                    # The Service Layer: Handles web requests, jobs, and observability.
│   ├── __init__.py
│   ├── main.py             # The FastAPI application, including Sentry initialization and ARQ job submission logic.
│   ├── worker.py           # Contains the main ARQ task function (`create_creative_report`).
│   ├── worker_settings.py  # The configuration file for the ARQ worker, including Sentry initialization.
│   ├── cache.py            # Async-native logic for the L0 (high-speed intent) Redis cache.
│   ├── config.py           # API-layer specific configurations (e.g., Redis cache prefix).
│   └── prompts.py          # Prompts used exclusively by the API layer (e.g., for L0 key generation).
│
├── api_client/             # A standalone Python client for interacting with the API.
│   ├── __init__.py
│   ├── client.py           # The `CreativeCatalystClient` class for submitting and polling jobs.
│   ├── exceptions.py       # Custom exceptions for the client.
│   └── example.py          # A simple script demonstrating how to use the client.
│
└── catalyst/               # The Core Engine: All business logic for the creative pipeline.
    ├── __init__.py
    ├── main.py             # Core `run_pipeline` function; the main entry point for the engine.
    ├── settings.py         # Central configuration for the engine (file paths, model names).
    ├── context.py          # Defines the `RunContext` class, the data object passed through the pipeline.
    │
    ├── caching/            # L1 Semantic Cache logic.
    │   ├── __init__.py
    │   ├── cache_manager.py # High-level interface for the L1 cache.
    │   └── report_cache.py  # ChromaDB implementation for vector-based semantic caching.
    │
    ├── clients/            # Clients for external services.
    │   └── gemini/
    │       ├── __init__.py
    │       ├── client_instance.py
    │       ├── core.py
    │       ├── resilience.py
    │       └── schema.py
    │
    ├── models/
    │   └── trend_report.py   # Pydantic models for the final, structured `FashionTrendReport`.
    │
    ├── pipeline/           # The core multi-stage processing pipeline.
    │   ├── __init__.py
    │   ├── orchestrator.py   # The `PipelineOrchestrator` that manages the execution flow.
    │   ├── base_processor.py
    │   │
    │   ├── processors/       # The main controllers for each stage of the pipeline.
    │   │   ├── __init__.py
    │   │   ├── briefing.py
    │   │   ├── synthesis.py
    │   │   ├── reporting.py
    │   │   └── generation/
    │   │       ├── __init__.py
    │   │       ├── base_generator.py
    │   │       └── nanobanana_generator.py
    │   │
    │   ├── prompt_engineering/
    │   │   └── prompt_generator.py
    │   │
    │   └── synthesis_strategies/ # The modular, "divide and conquer" logic for report assembly.
    │       ├── __init__.py
    │       ├── report_assembler.py
    │       ├── section_builders.py
    │       └── synthesis_models.py
    │
    ├── prompts/
    │   └── prompt_library.py # The master library of all creative and synthesis prompts.
    │
    └── utilities/            # Shared helper functions.
        ├── __init__.py
        ├── config_loader.py
        ├── json_parser.py
        ├── logger.py         # Configures the dual-format (console + JSON) application logger.
        └── log_formatter.py  # The custom class for color-coded console log formatting.
│
├── artifact_cache/         # Permanent storage for L1 cached artifacts (images, reports). Ignored by Git.
├── chroma_cache/           # Directory for the ChromaDB vector store (L1 cache). Ignored by Git.
├── logs/                   # Contains the rotating log files (e.g., catalyst_engine.log). Ignored by Git.
└── results/                # Rotating storage for the N most recent user-facing runs. Ignored by Git.
```

---

## Setup and Configuration

### Prerequisites

*   **Docker Desktop:** The primary requirement for running the application.
*   **Python 3.11+:** Required only for managing dependencies with `pip-tools`.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/MTawhid7/creative-catalyst-engine.git
    cd creative-catalyst-engine
    ```
2.  **Create the Environment File:**
    Copy the provided `.env.example` file to `.env` and fill in your secret keys (at a minimum, `GEMINI_API_KEY` and `SENTRY_DSN`).

### Environment Variables

Your `.env` file controls the application's configuration.

```ini
# .env

# --- API Keys & Secrets ---
GEMINI_API_KEY="your_gemini_api_key_here"
SENTRY_DSN="your_sentry_dsn_here"

# --- Feature Flags & Model Selection ---
ENABLE_IMAGE_GENERATION=True
IMAGE_GENERATION_MODEL="nano-banana"

# --- Infrastructure & Networking ---
# CRITICAL: This MUST be 'redis' to connect to the Docker service.
REDIS_URL="redis://redis:6379/0"

# The public-facing base URL for the server.
# Replace with your computer's IP address on your local network.
ASSET_BASE_URL="http://192.168.10.189:9500"
```

---

## Running the Engine

The entire application stack is orchestrated with a single command.

1.  **Ensure Docker Desktop is running.**
2.  **Open a terminal** in the project's root directory.
3.  **Run the master command:**
    ```bash
    docker-compose up --build
    ```
    *   The `--build` flag is only necessary the first time you run the application or after you've changed dependencies or the `Dockerfile`.
    *   For daily use, you can simply run `docker-compose up`.

You will see the logs from the API server, the ARQ worker, and Redis streaming in your terminal. The application is ready when you see the lines:
`Uvicorn running on http://0.0.0.0:9500` and `ARQ worker started. Ready to process creative jobs.`

To stop the entire application, press `Ctrl+C` in the terminal, then run `docker-compose down`.

---

## Interacting with the Engine

*   **Local:** Run in terminal `python -m catalyst.main`.
*   **Recommended:** Use the API Client via `python -m api_client.example`.
*   **Direct API (curl):** First, `POST` to `/v1/creative-jobs`, then `GET` the `/v1/creative-jobs/{job_id}` endpoint.

---

## Dependency Management

This project uses `pip-tools` for robust, deterministic dependency management.

*   **To add or change a dependency:** Edit the high-level `requirements.in` file.
*   **To update the lock file:** Activate your local virtual environment (`source venv/bin/activate`) and run:
    ```bash
    pip-compile --strip-extras requirements.in
    ```
    Then, commit both the updated `requirements.in` and `requirements.txt` files.

---

## Troubleshooting

| Symptom                                                      | Probable Cause & Solution                                                                                                                                                                                                                                                 |
| :----------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`docker-compose up` fails with a container name conflict** | A container from a previous run was not properly shut down. **Solution:** Run `docker-compose down` to remove the old containers, then run `docker-compose up` again.                                                                                                     |
| **Build fails with `No matching distribution found`**        | A Python dependency is incompatible with the `glibc`-based builder image. This is rare but possible. **Solution:** Research the problematic package for a compatible version or alternative.                                                                              |
| **500 Internal Server Error**                                | A background job in the ARQ worker failed. **Solution:** Check your **Sentry dashboard**. The full Python traceback, request data, and context will be there, allowing for instant debugging. You can also check the container logs with `docker-compose logs -f worker`. |
| **Images not loading (404 Not Found)**                       | The `ASSET_BASE_URL` in your `.env` file is incorrect. It must be the public-facing address of your server that the client machine can reach (e.g., `http://<your_macbook_lan_ip>:9500`).                                                                                 |
| **Getting old/cached results**                               | The L0 (Redis) or L1 (Chroma) caches are still active. **Solution:** Run the master cache clearing utility: `python clear_cache.py`. This script now clears all file-based caches, results folders, and the Redis database for a completely fresh start.                  | ``` |