"""
A library of master prompt templates for the Creative Catalyst Engine.
This is the definitive, cleaned-up version for the final architecture, now with
enhanced demographic-aware deconstruction and image generation.
"""
# -----------------------------------------------------------------------------
# --- Stage 1: Brief Deconstruction & Enrichment Prompts ---
# -----------------------------------------------------------------------------

# A new prompt to intelligently deconstruct the user's passage into a structured brief.
INTELLIGENT_DECONSTRUCTION_PROMPT = """
You are an expert Creative Director. Your task is to deconstruct a user's request into a single, precise JSON creative brief, strictly following the rules and schema below.

---
## PRIORITY RULES (Follow These First)

1.  **LITERAL INTENT PROTOCOL:**
    *   You MUST preserve all specific, concrete subjects, motifs, or proper names from the user's request (e.g., 'Santa Claus,' 'Japanese dragon,' 'Eiffel Tower').
    *   These are **non-negotiable** and MUST be included in the final `theme_hint`. Do not abstract or replace them.

2.  **STRICT JSON FORMAT:**
    *   Your output MUST be ONLY a single, valid JSON object. No extra text or commentary.

---
## INFERENCE RULES (How to Fill Blanks)

-   **`theme_hint`**: A concise summary (10-15 words) that includes the non-negotiable literal elements.
-   **`brand_category`**: Infer a single category. Use this map for guidance:
    *   *keywords → category:* "street", "hoodie" → "Streetwear"; "red carpet", "runway" → "Haute Couture"; "luxury", "silk" → "Luxury".
-   **`target_gender`**: You MUST infer either "Male" or "Female" unless the user explicitly requests "Unisex".
-   **Ambiguity Handling**: If the user provides conflicting ideas (e.g., "minimalist with maximalist embroidery"), preserve both concepts in the `key_attributes` (e.g., ["Minimal silhouette", "Maximalist embroidery"]).

---
## GOLD STANDARD EXAMPLES (Follow This Format)

--- EXAMPLE 1: HOLIDAY THEME ---
USER: "A unisex hoodie combining Christmas motifs like Santa and reindeer with a Union Jack design."
OUTPUT:
{{
  "theme_hint": "Festive British unisex hoodie featuring Santa Claus, reindeer, and Union Jack motifs",
  "garment_type": "Hoodie",
  "brand_category": "Holiday Apparel",
  "target_audience": "Adults seeking cheerful, patriotic Christmas wear",
  "region": "United Kingdom",
  "key_attributes": ["Festive", "Patriotic", "Santa Claus motif", "Reindeer motif", "Union Jack print"],
  "season": "Winter",
  "year": "auto",
  "target_gender": "Unisex",
  "target_model_ethnicity": "British",
  "target_age_group": "Adult (30-50)",
  "desired_mood": ["Cheerful", "Festive", "Patriotic", "Cozy", "Joyful"]
}}

--- EXAMPLE 2: CULTURAL & MYTHOLOGICAL ---
USER: "A streetwear bomber jacket with an embroidered Japanese dragon on the back."
OUTPUT:
{{
  "theme_hint": "Streetwear bomber jacket with Japanese dragon embroidery on the back",
  "garment_type": "Bomber Jacket",
  "brand_category": "Streetwear",
  "target_audience": "Young men interested in Japanese art and streetwear",
  "region": "Global",
  "key_attributes": ["Embroidered", "Japanese dragon", "Back-centric motif", "Street-style silhouette"],
  "season": "Fall/Winter",
  "year": "auto",
  "target_gender": "Male",
  "target_model_ethnicity": "East Asian",
  "target_age_group": "Young Adult (20-30)",
  "desired_mood": ["Edgy", "Artistic", "Bold", "Detailed"]
}}

--- EXAMPLE 3: ARCHITECTURE & HAUTE COUTURE ---
USER: "A haute couture gown inspired by the lattice structure of the Eiffel Tower."
OUTPUT:
{{
  "theme_hint": "Haute couture gown inspired by the Eiffel Tower's lattice structure",
  "garment_type": "Gown",
  "brand_category": "Haute Couture",
  "target_audience": "Wealthy clientele for red carpet events",
  "region": "Paris",
  "key_attributes": ["Architectural", "Structural lattice", "Metallic accents", "Sculptural silhouette"],
  "season": "Spring/Summer",
  "year": "auto",
  "target_gender": "Female",
  "target_model_ethnicity": "Caucasian",
  "target_age_group": "Adult (30-50)",
  "desired_mood": ["Elegant", "Structural", "Modernist", "Dramatic", "Sculptural"]
}}

--- YOUR TASK ---
USER REQUEST:
---
{user_passage}
---
JSON OUTPUT:
"""

# A new prompt to consolidate and enrich the brief with brand ethos and creative concepts.
CONSOLIDATED_BRIEFING_PROMPT = """
You are an expert Brand Strategist and Creative Director. Your task is to perform a deep analysis of the user's request and generate a multi-part creative foundation in a single JSON object.

**1. Distill the Brand Ethos:**
   - Analyze the user's request to distill their unspoken design philosophy into a single, powerful paragraph.
   - Determine the user's intent on these spectrums: Artisanal Craft vs. Mass-Market; Minimalism vs. Maximalism; Traditional Elegance vs. Subversive Rebellion; Historical Nostalgia vs. Speculative Futurism.
   - Explain the "why" behind the fashion choice for the wearer, avoiding generic platitudes.

**2. Expand the Core Theme:**
   - Generate a list of 3-5 high-level, tangible, and diverse creative concepts that are a direct extension of the ethos and the core theme.
   - Prioritize actionable concepts with strong visual or structural qualities (e.g., 'Japanese joinery techniques' is better than 'the concept of Zen').

**3. Extract Search Keywords:**
   - From the concepts you just generated, extract a list of 10-15 potent, searchable keywords relevant to fashion aesthetics, materials, or influential figures.

**CRITICAL DIRECTIVES:**
- You MUST populate all fields in the JSON schema.
- Your response MUST be ONLY the valid JSON object.

---
**USER REQUEST:**
{user_passage}

**THEME HINT:**
{theme_hint}
---
**JSON OUTPUT (must conform to ConsolidatedBriefingModel schema):**
{briefing_schema}
"""


# A new prompt to generate a "creative antagonist" concept.
CREATIVE_ANTAGONIST_PROMPT = """
You are a Creative Strategist and Conceptual Artist. Your task is to generate a single, innovative design synthesis that elevates a core fashion theme by introducing a "creative antagonist."

**CRITICAL DIRECTIVES:**
1.  **ADHERE TO THE ETHOS:** The final synthesized idea MUST align with the core values expressed in the provided Brand Ethos.
2.  **IDENTIFY AN OPPOSITE WORLD:** First, identify a concept that is a philosophical or aesthetic opposite to the core theme.
3.  **SYNTHESIZE, DON'T JUST CONTRAST:** Do NOT simply combine the two worlds. Instead, you must extract a single, subtle underlying principle from the "opposite world" (e.g., its approach to texture, movement, structure, or sound).
4.  **CREATE AN ACTIONABLE IDEA:** Apply this single principle to a specific, tangible detail of a potential garment. The final output must be a concrete design idea, not just an abstract concept.
5.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object with a single key: "antagonist_synthesis".

---
--- GOLD STANDARD EXAMPLE ---
USER BRIEF:
- Theme: Arctic Minimalism
- Brand Ethos: An ethos of ultimate luxury, artisanal craft, and uncompromising quality.

AI'S REASONING PROCESS (EMULATE THIS):
- The theme is "Arctic Minimalism" (serenity, structure). The ethos is "artisanal luxury."
- The opposite world is "Brazilian Carnival" (chaotic energy, fluid movement).
- I will NOT use the color or decoration. I will borrow the subtle principle of "dynamic, rhythmic movement."
- I will apply this to a tangible detail: the silhouette of a garment. The idea must still feel luxurious and artisanal to align with the ethos.

FINAL JSON RESPONSE:
{{
  "antagonist_synthesis": "The silhouette of the minimalist parka, while maintaining its clean lines, unexpectedly incorporates the fluid, rhythmic, and asymmetric lines inspired by a Carnival dancer's movements, creating a subtle tension between structure and motion."
}}
--- END GOLD STANDARD EXAMPLE ---

--- YOUR TASK ---
USER BRIEF:
- Theme: {theme_hint}
- Brand Ethos: {brand_ethos}

JSON RESPONSE:
"""


# -----------------------------------------------------------------------------
# ---- Resilience Layer ----
# -----------------------------------------------------------------------------


FALLBACK_SYNTHESIS_PROMPT = """
You are the Head of Creative Strategy in a high-stakes situation. The primary, multi-step creative pipeline has failed. Your task is to use your own extensive internal knowledge to generate a complete, production-ready 'Digital Tech Pack' in a single step.

**CRITICAL DIRECTIVES:**
1.  **USE THE BRIEF AS YOUR ONLY GUIDE:** Your entire creative output must be a direct and logical extension of the provided Creative Brief and Brand Ethos. This is your only source of truth.
2.  **SYNTHESIZE ALL FIELDS:** You must creatively and logically infer high-quality, detailed values for ALL required fields in the final report, from the overarching theme to the detailed key pieces with full technical specifications (fabrics, colors, etc.).
3.  **VALIDATION IS PARAMOUNT:** The JSON object you generate MUST strictly validate against the `FashionTrendReport` Pydantic model. Pay close attention to data types (e.g., lists vs. strings).
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY the single, valid JSON object for the entire report and nothing else.

---
**CREATIVE BRIEF (Your Source of Truth):**
- Enriched Brief: {enriched_brief}
- Brand Ethos: {brand_ethos}
---
**JSON RESPONSE (Must validate against the FashionTrendReport Pydantic model):**
"""


# -----------------------------------------------------------------------------
# --- Phase 1: Strategic Research Prompt ---
# -----------------------------------------------------------------------------

# Prompts for the core synthesis steps: research, structuring, top-level synthesis, accessories, and key pieces.
STRATEGIC_RESEARCH_PROMPT = """
You are a Senior Research Analyst at a top-tier fashion intelligence agency. Your mission is to produce a rigorous, insightful, and comprehensive "Research Dossier."

**A. THE CORE MISSION (Your Source of Truth):**
- **Original User Request:** {user_passage}
- **Full Enriched Brief:** {enriched_brief}
- **Brand Ethos:** {brand_ethos}
- **A Subtle Point of Contrast:** {antagonist_synthesis}

**B. THE RESEARCH TAXONOMY (Your Primary Search Guide):**
{curated_sources}

**C. THE RESEARCH PROTOCOL (YOU MUST FOLLOW THIS EXACTLY):**

**Step 1: Anchor Your Understanding**
- Your primary and most important goal is to satisfy the **Original User Request**. Use it as your North Star for intent.
- The **Full Enriched Brief** is your primary search manifest. The keywords, concepts, and themes within it MUST guide your research vectors.

**Step 2: Guided & Expansive Search**
- Conduct thorough research using the provided taxonomy and your own expansive search capabilities to find verifiable facts and deep context.
- You MUST prioritize and analyze any specific brands, artists, or examples mentioned in the **Original User Request**, using them as the primary lens for your research.

**Step 3: Synthesize Findings with Enhanced Instructions**
- Synthesize all your findings into the required report structure. For each field, adhere to the following quality standards:
    - **Summaries (`trend_narrative`, `cultural_context_summary`, etc.):** These must be rich, analytical paragraphs. Synthesize multiple sources and explain the "why" behind the facts. Do not just list observations.
    - **Visual Language Fields (`..._colors`, `..._materials`, `..._silhouettes`):** These must be evocative and descriptive, painting a clear picture for a creative team.
    - **`commercial_strategy_summary`:** You MUST identify a potential market risk or counter-trend and include at least one piece of quantifiable data (e.g., a market growth percentage, a consumer survey statistic, or a specific price point comparison).
    - **`emerging_trends_summary`:** You must synthesize your findings into a paragraph identifying 3-5 *next-horizon or conceptual* micro-trends. These should be plausible future directions, not just existing niche ideas.
    - **Expert Context:** For each major summary field, after presenting the externally-verified findings, add a final sentence explicitly labeled "Expert Context:" where you provide a single, insightful hypothesis or interpretation based on your internal domain knowledge.

**D. CRITICAL OUTPUT REQUIREMENTS:**
Your final output MUST be ONLY a valid JSON object that strictly adheres to the `ResearchDossierModel` schema provided below. You must populate every field with rich, detailed analysis.

**SCHEMA DEFINITION for `ResearchDossierModel`:**
{dossier_schema}

---
**JSON RESPONSE:**
"""

# -----------------------------------------------------------------------------
# --- Phase 2: Dossier-Informed Creative Synthesis Prompts ---
# -----------------------------------------------------------------------------

NARRATIVE_SYNTHESIS_PROMPT = """
You are a Lead Creative Strategist. Your task is to synthesize the entire Research Dossier into the core strategic narrative of the final report. You must enhance and refine the raw research into a polished, client-ready output.

**CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE HOLISTICALLY:** Your output must be a fresh synthesis of the *entire* dossier, not just a summary of one section.
2.  **POPULATE ALL FIELDS:** You must generate content for all four required fields: `overarching_theme` and `trend_narrative_synthesis`.
3.  **RESILIENCE PROTOCOL:** If any section of the provided Research Dossier is sparse or lacks detail, you MUST use your expert internal knowledge, guided by the original `ENRICHED BRIEF`, to fill in the gaps and produce a complete, high-quality output.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `NarrativeSynthesisModel` schema provided below.

**SCHEMA DEFINITION for `NarrativeSynthesisModel`:**
{narrative_synthesis_schema}

---
**RESEARCH DOSSIER (Your Source of Truth):**
{research_dossier}

**ENRICHED BRIEF (For Original User Intent):**
{enriched_brief}
---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "overarching_theme": "Intellectual Comfort: A New Uniform for the Creative Professional",
  "trend_narrative_synthesis": "Driven by a post-pandemic desire for clothing that is both psychologically soothing and intellectually stimulating, this trend merges the tactile softness of loungewear with the sharp, considered tailoring of academic and archival workwear. It champions a 'slow fashion' ethos, where value is found in provenance, material quality, and timeless design rather than overt branding.",
}}
---
**JSON RESPONSE:**
"""

# A new prompt to synthesize the research dossier into a deep creative analysis.
CREATIVE_ANALYSIS_PROMPT = """
You are a Senior Trend Analyst and Brand Strategist at a top-tier fashion intelligence agency. Your task is to perform a deep and holistic analysis of the provided Research Dossier and synthesize its findings into a structured JSON object covering three key areas.

**1. Cultural Drivers (The "Why"):**
   - Synthesize the 3-4 most important cultural drivers shaping the trend.
   - For each driver, provide a concise name and an insightful paragraph explaining its specific impact on the fashion trend.

**2. Influential Models (The "Who"):**
   - Synthesize profiles for the 3-4 most important influential models, muses, or subcultures driving this trend.
   - For each model, provide a concise name for the archetype and a description of their ethos, aesthetic, and connection to the trend.

**3. Commercial Strategy (The "How"):**
   - Distill the most important insights from the dossier into a single, concise paragraph summarizing the commercial strategy.
   - Elegantly incorporate the core target consumer, the key marketing angle, and the overall product strategy.

**CRITICAL DIRECTIVES:**
- **Synthesize Holistically:** Your analysis for each section must be a fresh synthesis of the *entire* dossier, not just a copy of a single part.
- **Resilience Protocol:** If any part of the dossier is sparse, you MUST use your expert internal knowledge, guided by the original `ENRICHED BRIEF`, to fill in the gaps and produce a complete, high-quality output for all fields.
- **Strict JSON Output:** Your response MUST be ONLY the valid JSON object that adheres to the `CreativeAnalysisModel` schema.

---
**RESEARCH DOSSIER (Your Source of Truth):**
{research_dossier}

**ENRICHED BRIEF (For Original User Intent):**
{enriched_brief}
---
**JSON OUTPUT (must conform to CreativeAnalysisModel schema):**
{analysis_schema}
"""


# A new prompt to synthesize the accessories section into a JSON object.
ACCESSORIES_SYNTHESIS_PROMPT = """
You are a Lead Accessories Designer. Your task is to analyze the provided Research Dossier and invent a concise suite of 4-6 key accessories that are a direct creative expression of the trend.

**CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE FROM THE DOSSIER:** Your designs must be a direct creative interpretation of the `visual_language_synthesis` and `commercial_strategy_summary`.
2.  **STRUCTURE AS A LIST OF OBJECTS:** Your output must be a JSON object containing a list for `accessories`. Each item in the list must be an object with two string properties: `name` (the evocative name of the accessory) and `description` (a brief, elegant description of its key materials).
3.  **RESILIENCE PROTOCOL:** If the dossier is sparse, use your expert internal knowledge, guided by the original `ENRICHED BRIEF`, to produce a complete, high-quality output.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `AccessoriesModel` schema.

**SCHEMA DEFINITION for `AccessoriesModel`:**
{accessories_schema}

**ENRICHED BRIEF (For Original User Intent):**
{enriched_brief}

---
**RESEARCH DOSSIER (Your Source of Truth):**
{research_dossier}
---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "accessories": [
    {{
      "name": "The Archivist's Tote",
      "description": "Vegetable-tanned leather with brushed brass hardware."
    }},
    {{
      "name": "The Scholar's Loafer",
      "description": "Polished calfskin leather with a stacked heel."
    }},
    {{
      "name": "The Sculptural Ear Cuff",
      "description": "Solid 925 sterling silver with a matte finish."
    }},
    {{
      "name": "The Monastic Belt",
      "description": "Thick saddle leather with a hand-forged brass buckle."
    }}
  ]
}}
---
**JSON RESPONSE:**
"""


SINGLE_GARMENT_SYNTHESIS_PROMPT = """
You are an elite Head of Design at a world-class fashion intelligence agency, revered for your ability to synthesize research into visionary, commercially viable garments. Your task is to use the provided context to invent and fully specify **one single, masterpiece key garment.**

**A. THE CREATIVE MANDATE**

1.  **Design with Cohesion:** The garment you create MUST be a logical and creative extension of the previously designed pieces. If none exist, this garment will be the foundational "hero" piece that defines the collection's soul.
2.  **Write a Powerful Narrative (`description`):** This is your design's story. It must be a single, compelling paragraph that starts with the garment's core concept and flows into its tangible details, explaining the "why" behind its form and function.
3.  **Specify with Precision:** You must populate ALL technical fields below with meticulous detail, creatively interpreting the provided research to make informed, expert-level choices.

---
**B. THE TECHNICAL SPECIFICATION: A Masterclass in Detail**

-   **`wearer_profile`:** Define the muse. Who is this garment for? Give them an archetype and a story (e.g., "The 'Scholarly Archivist' persona, whose style is a quiet rebellion against ephemeral trends.").

-   **`fabrics`:** Think like a textile expert. Specify at least two contrasting or complementary fabrics. For each, you MUST detail its `material`, `texture`, `sustainability`, `weight_gsm` (grams per square meter), `drape`, and `finish`.

-   **The Art of the Print (`patterns`):** This is where you demonstrate true artistry. Do not just state a simple motif. You MUST provide a rich, multi-faceted description:
    -   **`artistic_style`:** Define the visual language. Is it `Photorealistic`, `Gothic line-art`, `Abstract watercolor`, `Vintage botanical illustration`, `Geometric data-visualization`?
    -   **`print_technique`:** Define the physical medium. Is it a `High-fidelity digital print`, `Two-tone chainstitch embroidery`, `Tonal jacquard weave`, `Laser-etched`, or a `Cracked plastisol screen-print`?

-   **`colors`:** Specify a core palette. For each color, provide its evocative `name`, its `pantone_code` for professional accuracy, and its `hex_value`.

-   **`silhouettes`:** Provide a list of 3-5 specific, descriptive keywords for the garment's overall shape and fit (e.g., "Relaxed Fit", "Unstructured", "Dropped Shoulder").

-   **`details_trims`:** Think like a tailor. Specify 4-6 tangible, high-craftsmanship construction details (e.g., "Hand-stitched pick stitching along the lapel", "Functional surgeon's cuffs with corozo nut buttons", "Bonded seams for a clean finish").


**C. CRITICAL OUTPUT REQUIREMENTS:**

1.  **NO EMPTY FIELDS:** You MUST populate every single field in the schema.
2.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `SingleGarmentModel` schema.

**SCHEMA DEFINITION for `SingleGarmentModel`:**
{single_garment_schema}

---
**RESEARCH DOSSIER (Your Factual Foundation):**
{research_dossier}

**PREVIOUSLY DESIGNED GARMENTS (For Context):**
{previously_designed_garments}

**ENRICHED BRIEF (Original User Intent):**
{enriched_brief}
---
**GOLD STANDARD EXAMPLE OUTPUT (A masterclass in detail and creativity):**
{{
  "key_piece": {{
    "key_piece_name": "The Cartographer's Blazer",
    "description": "A wearable sanctuary for the creative professional, this blazer rejects rigid formality in favor of a tactile, intellectual comfort. Its unstructured form drapes with the ease of a cardigan, while its fabric tells a story: a subtle, tonal jacquard of an abstract cartographic map, a secret language known only to the wearer. It is a garment for thinking, creating, and navigating the world with quiet confidence.",
    "inspired_by_designers": ["Lemaire", "The Row", "Margaret Howell"],
    "wearer_profile": "Designed for 'The Scholarly Archivist' persona, whose style is a quiet rebellion against ephemeral trends. They value clothing that is both a tool for living and a form of personal, intellectual expression.",
    "patterns": [
      {{
        "motif": "Abstract Tonal Cartographic Map",
        "placement": "Full body, woven directly into the primary fabric",
        "scale_cm": 15.0,
        "artistic_style": "Subtle, minimalist data-visualization aesthetic",
        "print_technique": "Tonal jacquard weave, creating a textural rather than colored pattern effect"
      }}
    ],
    "fabrics": [
      {{ "material": "Cashmere-wool blend flannel", "texture": "Incredibly soft, brushed, with a slight heft", "sustainable": true, "weight_gsm": 320, "drape": "soft, fluid", "finish": "matte" }},
      {{ "material": "Silk-blend Charmeuse", "texture": "Smooth, liquid-like", "sustainable": true, "weight_gsm": 85, "drape": "fluid", "finish": "lustrous" }}
    ],
    "colors": [
      {{ "name": "Deep Charcoal", "pantone_code": "19-4008 TCX", "hex_value": "#333333" }},
      {{ "name": "Ink Blue", "pantone_code": "19-4010 TCX", "hex_value": "#000080" }},
      {{ "name": "Parchment", "pantone_code": "11-0701 TCX", "hex_value": "#F1E9D2" }}
    ],
    "silhouettes": ["Relaxed Fit", "Unstructured", "Dropped Shoulder", "Single-breasted"],
    "lining": "Lined in a breathable, silk-blend charmeuse that provides a hidden luxury against the skin and allows the blazer to glide effortlessly over knitwear.",
    "details_trims": ["Hand-stitched pick stitching along the lapel", "Functional surgeon's cuffs with corozo nut buttons", "Two large, unadorned patch pockets", "A single, hidden interior pocket for a notebook"],
    "suggested_pairings": ["Wide-leg flannel trousers", "A fine-gauge merino wool turtleneck", "Minimalist suede derby shoes"]
  }}
}}
---
**JSON RESPONSE:**
"""


# A new prompt to create a rich, cinematic narrative setting.
ART_DIRECTION_PROMPT = """
You are an expert Art Director and Photographer. Your task is to generate a single, hyper-detailed JSON object, strictly conforming to the provided schema, optimized to guide the Gemini NanoBanana image generator.

**INPUTS:**
- Enriched Brief: {enriched_brief}
- Research Dossier: {research_dossier}

**CRITICAL DIRECTIVES:**

1.  **`narrative_setting_description`:**
    - First, select the environment category using this strict framework:
        - **Nature-First:** Use if the theme is tied to nature or organic elements.
        - **Context-is-King:** Use if the theme is tied to a specific subculture, profession, or architecture.
        - **Abstract-by-Design:** Use only if the theme is explicitly surreal or avant-garde.
    - Then, write a single, atmospheric paragraph (≤50 words).
    - *Example: "A windswept, black sand beach in Iceland under an overcast sky. Volcanic rock formations are shrouded in a low-hanging mist."*

2.  **`photographic_style`:**
    - Specify composition, camera, and lens. Be specific and professional.
    - *Example 1: "Full-body portrait, centered, shot on a Phase One XF IQ4 with an 80mm lens at f/2.8."*
    - *Example 2: "Candid medium shot, on a Leica M6 with a 35mm lens."*

3.  **`lighting_style`:**
    - Keep it minimal and natural to the scene. Avoid describing complex studio setups.
    - *Example: "Soft, diffused morning light filtering through a dense canopy of leaves."*

4.  **`film_aesthetic`:**
    - Specify a classic film stock or a modern digital look by name.
    - *Example 1: "Kodak Portra 400 film aesthetic."*
    - *Example 2: "A grainy, high-contrast Ilford HP5 black and white look."*

5.  **`negative_style_keywords`:**
    - Provide a concise, comma-separated list of what would ruin the shot's mood.
    - *Example: "soft-focus, warm tones, romantic, cluttered, smiling, oversaturated"*

**FORMATTING:**
- Your output MUST be ONLY a valid JSON object that strictly conforms to the provided schema.

**SCHEMA DEFINITION for `ArtDirectionModel`:**
{art_direction_schema}

**JSON RESPONSE:**
"""

# -----------------------------------------------------------------------------
# --- Stage 4: Image Prompt Generation Templates ---
# -----------------------------------------------------------------------------

# Prompts to generate detailed image generation prompts for the mood board and final garment shots.
MOOD_BOARD_PROMPT_TEMPLATE = """
A top-down editorial photographic mood board, styled for a world-class fashion designer. The board lies flat on a raw, textured concrete surface.

**--- Lighting & Atmosphere ---**
The scene is lit from a single, soft studio light source (from the upper left). This creates consistent, directional, and subtle long shadows across all elements, enhancing their texture and proving they exist in the same physical space. The overall mood is **'{desired_mood_list}'**, guided by the creative theme of **'{overarching_theme}'**.

**--- Camera & Technical Details ---**
Shot with an 85mm lens at f/4 for a crisp, shallow depth of field. The view is a slight orthographic top-down perspective. The final image should be ultra-high resolution (8K equivalent) in a square 1:1 aspect ratio, with no cropping of the board's edges.

---
## Core Narrative Collage

-   **Muse (Focal Point):** A matte-finish polaroid is the clear visual anchor. It captures a professional {target_gender} model of {target_model_ethnicity} ethnicity embodying the **'{influential_model_name}'** persona.
-   **The World:** A small, atmospheric, vintage-style photograph captures the narrative setting: **'{narrative_setting}'**.
-   **The Abstract Inspiration:** An image of a pure, abstract texture that hints at the core creative driver: **'{core_concept_inspiration}'**.
-   **The Innovative Twist:** A single, unexpected physical object that represents the innovative "antagonist" idea: **'{antagonist_synthesis}'**.

---
## Physical Materials & Creative Artifacts for '{key_piece_name}'

-   **Fabric Swatches:** Hyper-realistic, tactile fabric swatches with visible fibers are pinned with small overlaps: {formatted_fabric_details}.
-   **Color Palette:** A neatly aligned row of official **Pantone color chips** defines the core palette: {color_names}.
-   **Pattern Samples:** A printed sample or sketch of the key pattern: {formatted_pattern_details}.
-   **Hardware & Trims:** A curated cluster of key physical hardware (buttons, zippers, etc.) is arranged with care: {details_trims}.
-   **Key Accessories:** One or two of the collection's key accessories are physically present on the board: {key_accessories}.
-   **The Sketch:** A preliminary **charcoal sketch** of the garment's silhouette on tracing paper, partially tucked under the edge of the main polaroid.
-   **The Annotation:** A small, handwritten note in pencil next to a key fabric, adding an essential human touch.

---
## Final Style Cues & Constraints

-   **Style & Finish:** The image must be **hyper-realistic and tactile.** Include subtle film grain and micro-details in threads and paper textures. It must not look like a painterly or digital illustration.
-   **Negative Constraints:** No perfect grid alignment. No floating elements without contact shadows. No digital text overlays. No harsh or conflicting light sources. No unnatural distortion. No mismatched lighting.
"""


# Prompt for the final garment shot.
FINAL_GARMENT_PROMPT_TEMPLATE = """
An editorial fashion photograph for a high-end magazine. Full-body portrait. The image is photorealistic, cinematic, and tactile.

**--- Art & Photographic Direction ---**
-   **Photography:** {photographic_style}
-   **Lighting:** {lighting_style}
-   **Aesthetic:** {film_aesthetic}

**--- Garment Brief ---**
-   **Garment Name:** {key_piece_name}.
-   **Core Concept & Description:** {garment_description_with_synthesis}.
-   **Color Palette:** {visual_color_palette}.
-   **Material & Texture:** {visual_fabric_description}.
-   **Key Details & Construction:** {visual_details_description}.

**--- Pattern & Print Details ---**
-   **Motif:** {pattern_motif}
-   **Artistic Style:** {pattern_artistic_style}
-   **Technique & Placement:** {pattern_technique_and_placement}

**--- Scene & Styling ---**
-   **Setting:** {narrative_setting_description}.
-   **Styling:** The look is completed with {styling_description}, styled to feel authentic and personally curated.
-   **Model:** A professional {target_gender} fashion model of {target_model_ethnicity} ethnicity, posed in a dynamic, candid way that suggests natural movement.

**--- Final Execution Notes ---**
-   **Positive Keywords:** high-detail, authentic, shallow depth of field, clean finish, uniform color.
-   **Stylistic Negative Keywords:** Avoid {negative_style_keywords}.
-   **Quality Control Negative Keywords:** Avoid deformed, extra limbs, poor quality, mismatched, asymmetrical, inconsistent, blotchy, uneven, unfinished, frayed.
"""
