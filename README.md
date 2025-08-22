# Creative Catalyst Engine

The Creative Catalyst Engine is a professional-grade, AI-powered system that transforms a simple, natural language creative request into a revolutionary and actionable fashion trend report. It uses a robust, multi-stage pipeline architecture to enrich creative briefs, perform deep synthesis using Gemini's native web search capabilities, and generate structured, validated reports and art-directed visual prompts.

## Key Features

- **Intelligent Briefing:** Expands a simple user request into a rich creative brief with expanded abstract concepts and a "creative antagonist" for inspiration.
- **Direct Web Synthesis:** Leverages Gemini 1.5 Flash's built-in search tools to perform comprehensive web research and synthesize findings in a single, efficient step.
- **Robust "Divide and Conquer" Structuring:** A multi-step synthesis process that breaks down the research into smaller parts to reliably generate a perfectly structured and validated final JSON report.
- **Intelligent Fallback:** If the primary web-synthesis path fails, the system automatically pivots to a fallback that uses Gemini's vast pre-trained knowledge to generate a high-quality report, ensuring a successful result every time.
- **L1 Report Caching:** Utilizes a ChromaDB semantic cache to store final reports. Running the same or a very similar creative brief a second time is nearly instantaneous.

## Architecture

The project follows a modern, modular, and extensible **Composable Pipeline Architecture**. The entire workflow is a series of discrete "Processor" steps managed by a central Orchestrator. This design makes the system easy to maintain, test, and extend with new features.

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
    Create a file named `.env` in the root of the project and add your Gemini API key. Use the following template:
    ```
    GEMINI_API_KEY="your_gemini_api_key_here"
    ```

## How to Run

Execute the main application from the project root directory. This will run the entire pipeline and save the results in a new folder under `/results`.

```bash
python -m catalyst.main