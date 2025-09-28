"""
A library of master prompt templates for the Creative Catalyst Engine.
This is the definitive, cleaned-up version for the final architecture, now with
enhanced demographic-aware deconstruction and image generation.
"""
# -----------------------------------------------------------------------------
# --- Stage 1: Brief Deconstruction & Enrichment Prompts ---

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


# A new prompt to analyze the user's underlying philosophy.
ETHOS_ANALYSIS_PROMPT = """
You are an expert Brand Strategist and fashion critic. Your primary task is to analyze a user's request and distill their unspoken design philosophy (the "ethos"). Your analysis must be decisive, insightful, and serve as a "Creative Compass" for a design team.

**CRITICAL DIRECTIVES:**
1.  **MAKE A STRATEGIC CHOICE:** Your most important task is to determine where the user's intent falls on the key creative spectrums that define a collection. You must analyze their language to infer their position on these core dichotomies:
    *   **Philosophy:** Artisanal Craft vs. Mass-Market Appeal
    *   **Aesthetic:** Minimalism vs. Maximalism
    *   **Attitude:** Traditional Elegance vs. Subversive Rebellion
    *   **Temporal Focus:** Historical Nostalgia vs. Speculative Futurism
2.  **DISTILL THE CORE "WHY":** Synthesize your choices into a single, powerful paragraph. This ethos must explain the emotional goal or the problem this fashion choice solves for the wearer.
3.  **BE INSIGHTFUL (NEGATIVE CONSTRAINT):** You are FORBIDDEN from using generic platitudes. Avoid vapid phrases like "looking good" or "feeling confident." Your analysis must have a unique point of view.
4.  **INFER FROM FUNCTIONAL BRIEFS:** If a request is purely functional (e.g., "dresses for a festival"), you must infer the ethos of the event or subculture itself.
5.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object with a single key: "ethos".

---
--- GOLD STANDARD EXAMPLE 1: PHILOSOPHICAL REQUEST ---
USER REQUEST:
"I prefer timeless, bespoke tailoring made from rare fabrics, with attention to every stitch. Exclusivity and craftsmanship are non-negotiable."

JSON RESPONSE:
{{
  "ethos": "A pursuit of ultimate, understated luxury defined by unparalleled artisanal craft and traditional elegance. This reflects a discerning client who values intrinsic worth and a timeless aesthetic over fleeting trends, seeking the pinnacle of textile excellence."
}}
--- END EXAMPLE 1 ---
--- GOLD STANDARD EXAMPLE 2: FUNCTIONAL REQUEST ---
USER REQUEST:
"Suggest some dresses for the upcoming Coachella."

JSON RESPONSE:
{{
  "ethos": "A celebration of creative self-expression and unconstrained freedom, rooted in a subversive, rebellious attitude. The aesthetic is maximalist, tailored for a vibrant festival environment to create a visually impactful, photogenic statement that aligns with a bohemian subculture."
}}
--- END EXAMPLE 2 ---

--- YOUR TASK ---
USER REQUEST:
---
{user_passage}
---
JSON RESPONSE:
"""


# A new prompt to enrich the brief with inferred details.
THEME_EXPANSION_PROMPT = """
You are a polymath creative director. Your task is to find 3-5 high-level, tangential concepts that illuminate a core fashion theme, using the provided Brand Ethos as your primary filter.

**CRITICAL DIRECTIVES:**
1.  **USE THE ETHOS AS A FILTER:** The concepts you choose MUST be a direct extension or metaphor for the values expressed in the Brand Ethos. Your most important task is to identify and DISCARD concepts that are thematically related but philosophically incorrect.
2.  **PRIORITIZE ACTIONABLE CONCEPTS:** The concepts MUST be concrete and tangible. Favor ideas with strong visual, structural, material, or procedural qualities. For example, 'Japanese joinery techniques' is better than 'the concept of Zen'.
3.  **ENSURE DIVERSITY OF FIELDS:** The final list MUST be drawn from at least three different domains (e.g., architecture, science, art history, industrial design).
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object with a single key: "concepts".

---
--- GOLD STANDARD EXAMPLE ---
USER BRIEF:
- Theme: Arctic Minimalism
- Garment: Outerwear
- Attributes: functional, sustainable
- Brand Ethos: The core ethos is one of ultimate luxury and uncompromising quality, focusing on artisanal, bespoke craftsmanship over fleeting trends.

AI'S REASONING PROCESS (EMULATE THIS):
- The theme is "Arctic Minimalism," but the ethos is about "artisanal craft" and "uncompromising quality."
- A related but INCORRECT path would be "survivalist gear" or "mass-produced technical fabrics," as these lack the "artisanal luxury" component of the ethos. I will discard these.
- I will find concepts from diverse fields that value minimalism, function, AND extreme craftsmanship.
    - Architecture: Bauhaus architectural principles ("form follows function").
    - Furniture Design: Shaker furniture (minimalist beauty, incredible craft).
    - Industrial Design: Dieter Rams' principles of good design.
- This list is diverse, actionable, and aligns perfectly with the ethos.

FINAL JSON RESPONSE:
{{
  "concepts": [
    "Bauhaus architectural principles",
    "Shaker furniture design",
    "Dieter Rams' principles of good design"
  ]
}}
--- END GOLD STANDARD EXAMPLE ---

--- YOUR TASK ---
USER BRIEF:
- Theme: {theme_hint}
- Garment: {garment_type}
- Attributes: {key_attributes}
- Brand Ethos: {brand_ethos}

JSON RESPONSE:
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

# A new prompt to generate a rich keyword list from the concepts.
KEYWORD_EXTRACTION_PROMPT = """
You are an expert Fashion SEO Strategist and Cultural Research Analyst. Your task is to analyze a list of abstract concepts and generate a potent, diverse list of 10-15 searchable keywords to fuel a fashion design research engine.

**CRITICAL DIRECTIVES:**
1.  **CATEGORIZE YOUR THINKING:** For each input concept, you must generate keywords that fall into these three categories:
    *   **Core Concepts:** The primary nouns and proper nouns (e.g., "Bauhaus," "Shaker furniture").
    *   **Influential Figures/Brands:** Specific people, brands, or movements that are strongly associated with the concept (e.g., "Walter Gropius," "Mies van der Rohe").
    *   **Aesthetic/Technical Terms:** Keywords describing the visual, structural, or material qualities of the concept (e.g., "minimalist craft," "kintsugi," "geometric forms").
2.  **MAINTAIN FASHION RELEVANCE:** Every keyword MUST have relevance to aesthetics, materials, structure, or mood. Filter out any purely academic or technical terms that do not provide visual inspiration.
3.  **AVOID REDUNDANCY:** Do not include simple synonyms. Each keyword should offer a unique search angle.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object with a single key: "keywords", containing the final, flat list of strings.

---
--- GOLD STANDARD EXAMPLE ---
INPUT CONCEPTS:
[
  "Bauhaus architectural principles",
  "Shaker furniture design",
  "Japanese joinery techniques"
]

AI'S REASONING PROCESS (EMULATE THIS):
- **Bauhaus:** Core Concept: "Bauhaus". Influential Figures: "Walter Gropius", "Mies van der Rohe". Aesthetic Terms: "geometric forms", "primary colors".
- **Shaker furniture:** Core Concept: "Shaker furniture". Aesthetic Terms: "minimalist craft", "functionalism".
- **Japanese joinery:** Core Concept: "Japanese joinery". Aesthetic Terms: "kintsugi", "woodworking aesthetics".
- I will combine these into a single, de-duplicated, and potent list.

FINAL JSON RESPONSE:
{{
  "keywords": [
    "Bauhaus",
    "Walter Gropius",
    "Mies van der Rohe",
    "geometric forms",
    "primary colors",
    "Shaker furniture",
    "minimalist craft",
    "functionalism",
    "Japanese joinery",
    "kintsugi",
    "woodworking aesthetics"
  ]
}}
--- END GOLD STANDARD EXAMPLE ---

--- YOUR TASK ---
INPUT CONCEPTS:
{concepts_list}

JSON RESPONSE:
"""

# -----------------------------------------------------------------------------
# ---- Resilience Layer ----


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
# This prompt generates the foundational ResearchDossier.
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

CULTURAL_DRIVERS_PROMPT = """
You are a Cultural Strategist and Trend Analyst. Your task is to analyze the provided Research Dossier and synthesize the 3-4 most important cultural drivers shaping the trend.

**CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE, DON'T JUST EXTRACT:** Analyze the *entire* dossier to identify the core drivers.
2.  **STRUCTURE AS A LIST OF OBJECTS:** Your output must be a JSON object containing a list for `cultural_drivers`. Each item in the list must be an object with two string properties: `name` (the concise name of the cultural driver) and `description` (an insightful paragraph explaining its impact).
3.  **RESILIENCE PROTOCOL:** If the dossier is sparse, use your expert internal knowledge, guided by the original `ENRICHED BRIEF`, to produce a complete, high-quality output.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `CulturalDriversModel` schema.

**SCHEMA DEFINITION for `CulturalDriversModel`:**
{cultural_drivers_schema}

**ENRICHED BRIEF (For Original User Intent):**
{enriched_brief}

---
**RESEARCH DOSSIER (Your Source of Truth):**
{research_dossier}
---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "cultural_drivers": [
    {{
      "name": "The Rise of Quiet Luxury",
      "description": "A societal shift away from conspicuous branding towards products whose value is communicated through exceptional materials and craftsmanship. This directly fuels the demand for ultra-luxury denim, as consumers seek the intrinsic value and understated confidence that comes from superior, logo-free garments."
    }},
    {{
      "name": "The Influence of Wabi-Sabi",
      "description": "A Japanese aesthetic centered on the acceptance of imperfection and the beauty of natural aging. In denim, this manifests as an appreciation for the natural patina of aged indigo and the subtle beauty of artisanal, hand-finished details."
    }}
  ]
}}
---
**JSON RESPONSE:**
"""

INFLUENTIAL_MODELS_PROMPT = """
You are a Fashion Anthropologist and Brand Strategist. Your task is to analyze the provided Research Dossier and synthesize profiles for the 3-4 most important influential models, muses, or subcultures driving this trend.

**CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE HOLISTICALLY:** Analyze the *entire* dossier to identify the key personas.
2.  **STRUCTURE AS A LIST OF OBJECTS:** Your output must be a JSON object containing a list for `influential_models`. Each item in the list must be an object with two string properties: `name` (the concise name of the archetype) and `description` (an insightful paragraph explaining their ethos and connection to the trend).
3.  **RESILIENCE PROTOCOL:** If the dossier is sparse, use your expert internal knowledge, guided by the original `ENRICHED BRIEF`, to produce a complete, high-quality output.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `InfluentialModelsModel` schema.

**SCHEMA DEFINITION for `InfluentialModelsModel`:**
{influential_models_schema}

**ENRICHED BRIEF (For Original User Intent):**
{enriched_brief}

---
**RESEARCH DOSSIER (Your Source of Truth):**
{research_dossier}
---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "influential_models": [
    {{
      "name": "The Scholarly Archivist",
      "description": "A persona who prioritizes texture, quality, and intellectual rigor over fleeting trends. Their aesthetic is informed by academic and archival workwear, valuing timeless design and craftsmanship, as seen in brands like The Row and Lemaire."
    }},
    {{
      "name": "The Street Style Intellectual",
      "description": "Seen in the real-world adoption of heritage pieces in urban creative hubs, this persona recontextualizes classic garments with a modern, slightly irreverent sensibility, blending high-end tailoring with everyday items."
    }}
  ]
}}
---
**JSON RESPONSE:**
"""

COMMERCIAL_STRATEGY_PROMPT = """
You are the Head of Commercial Strategy. Your task is to analyze the provided Research Dossier and synthesize its findings into a single, concise, and elegant paragraph summarizing the commercial strategy for the trend.

**CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE, DON'T JUST LIST:** You must distill the most important insights from the `commercial_strategy_summary` and `market_manifestation_summary` in the dossier.
2.  **FOCUS ON THE ESSENTIALS:** Your summary must elegantly incorporate the core target consumer, the key marketing angle, and the overall product strategy (e.g., investment pieces).
3.  **RESILIENCE PROTOCOL:** If the dossier is sparse, use your expert internal knowledge, guided by the original `ENRICHED BRIEF`, to produce a complete, high-quality output.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `CommercialStrategyModel` schema.

**SCHEMA DEFINITION for `CommercialStrategyModel`:**
{commercial_strategy_schema}

**ENRICHED BRIEF (For Original User Intent):**
{enriched_brief}

---
**RESEARCH DOSSIER (Your Source of Truth):**
{research_dossier}
---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "commercial_strategy_summary": "The commercial strategy centers on positioning these garments as long-term investment pieces for a discerning, design-literate consumer. The core marketing message is 'The Luxury of Longevity,' focusing on craftsmanship and material provenance. This approach targets a post-logo consumer who defines luxury through quality and is willing to invest in pieces that offer both comfort and quiet confidence."
}}
---
**JSON RESPONSE:**
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
NARRATIVE_SETTING_PROMPT = """
You are a world-class Art Director and Set Designer. Your primary task is to synthesize all the provided context into a powerful, concise, and atmospheric setting description, optimized for an AI image generation model.

**A. CREATIVE DIRECTION (Your Guiding Principles):**
- **Brand Ethos:** {brand_ethos}
- **Primary Focus:** For this task, you must derive your core inspiration from the `trend_narrative` and `visual_language_synthesis` within the dossier.

**B. THE RESEARCH DOSSIER (Your Factual Foundation):**
{research_dossier}

**C. CRITICAL DIRECTIVES & CREATIVE PROCESS (YOU MUST FOLLOW THIS EXACTLY):**

1.  **CHOOSE THE CORE ENVIRONMENT (Primary Filter):** You MUST first apply this strategic framework to determine the setting's environment. This is your most important decision.
    *   **The Nature-First Principle:** If the theme is tied to nature or organic elements, you MUST choose a **Natural** environment.
    *   **The Context-Is-King Principle:** If the theme is tied to a specific subculture or profession, you MUST choose an authentic **Urban** or **Interior** setting.
    *   **The Abstract-by-Design Principle:** Only choose an **Abstract/Conceptual** environment if the theme is explicitly surreal or avant-garde.

2.  **REFINE WITH THE ETHOS (Secondary Filter):** Once you have chosen the environment, you must then use the **Brand Ethos** to add specific, brand-aligned details.

3.  **SYNTHESIZE A CONCISE, HYPER-DETAILED NARRATIVE:** Your final description must be a single, atmospheric paragraph, strictly **under 50 words**. It must be dense with key visual and sensory details (light, texture, sound) that are unambiguous for an image generation model.

4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `NarrativeSettingModel` schema provided below.

**SCHEMA DEFINITION for `NarrativeSettingModel`:**
{narrative_setting_schema}

---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "narrative_setting_description": "The dusty, forgotten backstage of a dimly lit music club. A single, bare bulb casts long shadows across peeling paint and torn band flyers. Worn velvet and tangled cables complete the raw, authentic scene."
}}
---
**JSON RESPONSE:**
"""


# A new prompt to create a technical and artistic call sheet for a photoshoot.

CREATIVE_STYLE_GUIDE_PROMPT = """
You are a Lead Photographer and Art Director. Your task is to synthesize all the provided context into a hyper-optimized "master prompt" (`art_direction`) and a set of strategic `negative_style_keywords`.

**A. RESEARCH DOSSIER (Your Factual Foundation):**
{research_dossier}

**B. FINAL REPORT SYNTHESIS (Your Creative Focus):**
- **Overarching Theme:** {overarching_theme}
- **Refined Mood:** {refined_mood}
- **Influential Models / Archetypes:** {influential_models}
- **Brand Ethos:** {brand_ethos}

**C. CRITICAL DIRECTIVES:**
1.  **SYNTHESIZE, DON'T COPY:** Your output must be a creative synthesis of the dossier and the final report, not just a summary.
2.  **CONSTRUCT THE MASTER PROMPT (`art_direction`):** Generate a single, dense paragraph (under 50 words) that follows this exact structure:
    *   **Part 1 (Photography Style):** Start with the overall aesthetic, informed by the dossier's findings.
    *   **Part 2 (Model Persona):** Describe the model's persona, directly inspired by the `Influential Models / Archetypes`.
    *   **Part 3 (Lighting & Mood):** Describe the lighting in a technical and atmospheric way that evokes the `Refined Mood`.
3.  **GENERATE STRATEGIC NEGATIVE KEYWORDS:** The `negative_style_keywords` must be a concise, comma-separated list of the 5-7 most critical visual styles to AVOID.
4.  **STRICT JSON OUTPUT:** Your response MUST be ONLY a valid JSON object that adheres to the `CreativeStyleGuideModel` schema provided below.

**SCHEMA DEFINITION for `CreativeStyleGuideModel`:**
{style_guide_schema}

---
**GOLD STANDARD EXAMPLE OUTPUT:**
{{
  "art_direction": "An editorial fashion photograph, sharp focus, high detail. The model embodies the quiet strength of a 'Scholarly Archivist,' with a grounded and powerful presence. Lighting is stark and directional, like that of a library reading room, creating deep, sculptural shadows that evoke a 'Considered' and 'Scholarly' mood.",
  "negative_style_keywords": "ornate, frivolous, superficial, delicate, whimsical, soft-focus, romantic, chaotic"
}}
---
**JSON RESPONSE:**
"""

# -----------------------------------------------------------------------------
# --- Stage 4: Image Prompt Generation Templates ---

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

**Art Direction:** {art_direction}

**--- GARMENT BRIEF ---**
-   **Garment Name:** {key_piece_name}.
-   **Core Concept & Description:** {garment_description_with_synthesis}.
-   **Color Palette:** {visual_color_palette}.
-   **Material & Texture:** {visual_fabric_description}.
-   **Pattern:** {visual_pattern_description}.
-   **Key Details & Construction:** {visual_details_description}.

**--- SCENE & STYLING ---**
-   **Setting:** {narrative_setting}.
-   **Styling:** The look is completed with {styling_description}, styled to feel authentic and personally curated.
-   **Model:** A professional {target_gender} fashion model of {target_model_ethnicity} ethnicity, posed in a dynamic, candid way that suggests natural movement.

**--- FINAL EXECUTION NOTES ---**
-   **Positive Keywords:** high-detail, authentic, shallow depth of field, clean finish, uniform color.
-   **Stylistic Negative Keywords:** Avoid {negative_style_keywords}.
-   **Quality Control Negative Keywords:** Avoid nsfw, deformed, extra limbs, poor quality, logo, text, mismatched, asymmetrical, inconsistent, blotchy, uneven, unfinished, frayed.
"""
