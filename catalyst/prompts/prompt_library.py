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
You are an expert Creative Director. Your task is to deconstruct a user's request into a structured JSON creative brief, inferring all missing details with expert authority.

**CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE THE CORE THEME:** Your most important task. Synthesize the user's core creative request into a clean, concise, and actionable `theme_hint`. This should be a summary, not a direct copy.
2.  **BE BOLDLY SPECIFIC (NEGATIVE CONSTRAINTS):**
    *   **Gender:** You MUST infer either "Male" or "Female". Do NOT use "Unisex" or "Gender-Neutral" unless explicitly requested.
    *   **Ethnicity:** You MUST infer the single, most specific ethnicity that is demonstrably associated with the brief (e.g., via culture, region, or heritage). Do NOT use "Diverse" or other vague terms.
    *   **Brand Category:** Infer a specific market segment. Examples: "Haute Couture," "Streetwear," "Resort Wear," "Avant-Garde Fashion."
3.  **HANDLE MULTIPLE VALUES:** If the user requests multiple garments, regions, etc., you MUST return them as a list.
4.  **INFER DEMOGRAPHICS:** Based on the inferred `target_audience`, you MUST choose the single most appropriate `target_age_group` from this list: "Child (4-12)", "Teen (13-19)", "Young Adult (20-30)", "Adult (30-50)", "Senior (50+)".
5.  **DEFINE THE DESIRED MOOD:** Generate a `desired_mood` as a list of 3-5 evocative adjectives that capture the final atmosphere of the collection.
6.  **STRICT JSON OUTPUT:** Your response MUST be ONLY the valid JSON object and nothing else.

---
--- GOLD STANDARD EXAMPLE 1: INFERENCE & SYNTHESIS ---
USER REQUEST:
"A report on Cuban resort wear from the 1950s."

JSON OUTPUT:
{{
  "theme_hint": "Timeless Cuban resort wear, circa 1950s",
  "garment_type": "Resort Wear",
  "brand_category": "Resort Fashion",
  "target_audience": "Affluent older women seeking classic Cuban style",
  "region": "Cuba",
  "key_attributes": ["Vintage", "Elegant", "Vibrant", "Sun-drenched"],
  "season": "Spring/Summer",
  "year": 1950,
  "target_gender": "Female",
  "target_model_ethnicity": "Cuban",
  "target_age_group": "Senior (50+)",
  "desired_mood": ["Elegant", "Vibrant", "Nostalgic", "Sophisticated", "Timeless"]
}}
--- END GOLD STANDARD EXAMPLE 1 ---
--- GOLD STANDARD EXAMPLE 2: MULTIPLE VALUES ---
USER REQUEST:
"A report on avant-garde trench coats and bomber jackets for the Tokyo and Seoul markets."

JSON OUTPUT:
{{
  "theme_hint": "Avant-garde outerwear for East Asian markets",
  "garment_type": ["trench coat", "bomber jacket"],
  "brand_category": "Avant-Garde Fashion",
  "target_audience": "Fashion-forward individuals in urban centers",
  "region": ["Tokyo", "Seoul"],
  "key_attributes": ["Deconstructed", "Monochromatic", "Architectural", "Street Style"],
  "season": "Fall/Winter",
  "year": 2025,
  "target_gender": "Female",
  "target_model_ethnicity": "East Asian",
  "target_age_group": "Young Adult (20-30)",
  "desired_mood": ["Edgy", "Architectural", "Minimalist", "Urban"]
}}
--- END GOLD STANDARD EXAMPLE 2 ---

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
You are the Head of Design for a world-class fashion intelligence agency. Your task is to use the provided Research Dossier to invent and fully specify **one single, visionary key garment**.

**A. DESIGN PROTOCOL (YOU MUST FOLLOW THIS):**

1.  **ENSURE COHESION:** The garment you design MUST complement the previously designed garments. If none exist, create the foundational piece.
2.  **SYNTHESIZE THE NARRATIVE:** Write a single, powerful `description` that begins with the garment's core concept and then flows into its detailed description.
3.  **POPULATE ALL FIELDS:** You must populate ALL technical fields by creatively interpreting the `visual_language_synthesis` from the dossier.

**B. TECHNICAL FIELD GUIDELINES:**

*   **`inspired_by_designers`**: Provide a list of 2-3 specific, relevant designer names.
*   **`silhouettes`**: Provide a list of 3-5 descriptive keywords for the garment's shape.
*   **`details_trims`**: Provide a list of 4-6 specific, tangible construction details or embellishments.
*   **`suggested_pairings`**: Provide a list of 3 complementary items to create a full look.

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
        "placement": "Full jacquard weave",
        "scale_cm": 15.0
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
A professional and atmospheric fashion designer's mood board, arranged as a top-down flat-lay on a raw concrete surface. The scene is lit by soft, diffused light.

The board's creative direction is guided by the theme **'{overarching_theme}'** and evokes a mood of **{desired_mood_list}**.

The collage features these key narrative elements:
- A central polaroid of the muse: a professional {target_gender} model of {target_model_ethnicity} ethnicity embodying the **'{influential_model_name}'** persona.
- A small, atmospheric photo capturing the narrative setting: **'{narrative_setting}'**.
- An abstract textural image hinting at the core inspiration: **'{core_concept_inspiration}'**.
- A single, unexpected object hinting at the innovative idea: **'{antagonist_synthesis}'**.

Key physical elements for the garment '{key_piece_name}':
- Hyper-realistic, tactile fabric swatches: {formatted_fabric_details}
- A focused palette of official Pantone color chips: {color_names}
- Printed samples or sketches of key patterns: {formatted_pattern_details}
- A small collection of physical hardware and trims: {details_trims}
- Key styling accessories, such as: {key_accessories}

Final image style: editorial, tactile, atmospheric, rich with narrative detail, professional studio photograph.
Negative prompts: avoid text, words, letters, logos, brand names, recognizable public figures.
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
-   **Pattern:** {visual_pattern_description}.
-   **Key Details & Construction:** {visual_details_description}.

**--- Scene & Styling ---**
-   **Setting:** {narrative_setting_description}.
-   **Styling:** The look is completed with {styling_description}, styled to feel authentic and personally curated.
-   **Model:** A professional {target_gender} fashion model of {target_model_ethnicity} ethnicity, posed in a dynamic, candid way that suggests natural movement.

**--- Final Execution Notes ---**
-   **Positive Keywords:** high-detail, authentic, shallow depth of field, clean finish, uniform color.
-   **Stylistic Negative Keywords:** Avoid {negative_style_keywords}.
-   **Quality Control Negative Keywords:** Avoid nsfw, deformed, extra limbs, poor quality, logo, text, mismatched, asymmetrical, inconsistent, blotchy, uneven, unfinished, frayed.
"""
