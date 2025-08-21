# Creative Catalyst Engine

The Creative Catalyst Engine is a professional-grade, AI-powered system that transforms a simple, natural language creative request into a revolutionary and actionable fashion trend report. It uses a multi-stage architecture to enrich creative briefs, perform deep web research, and synthesize findings into a structured, validated report.

## Key Features

- **Intelligent Briefing:** Expands simple user requests into rich creative briefs with expanded concepts and a "creative antagonist."
- **Multi-Vector Discovery:** Generates and executes a wide range of search queries across a configurable set of authoritative sources.
- **Throttled, Concurrent Research:** Processes dozens of URLs in parallel while respecting API rate limits.
- **Three-Stage Synthesis:** A robust "Extract, Organize, Structure" pipeline that uses Gemini 2.5 Flash and Pro models to create a final, validated report.
- **Semantic Caching:** Utilizes a multi-layer ChromaDB cache to dramatically speed up subsequent runs on similar topics.

## Architecture

The project follows a modular, service-oriented architecture. See the file structure diagram for a detailed overview of each component's role.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/creative-catalyst-engine.git
    cd creative-catalyst-engine
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the `.env` File:**
    Create a file named `.env` in the root of the project and add your secret API keys. Use the following template:
    ```    GEMINI_API_KEY="your_gemini_api_key_here"
    GOOGLE_API_KEY="your_google_api_key_here"
    SEARCH_ENGINE_ID="your_custom_search_engine_id_here"
    ```

## How to Run

Execute the main application from the project root directory:

```bash
python -m catalyst.main