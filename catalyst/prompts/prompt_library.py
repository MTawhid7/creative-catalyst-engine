"""
A library of master prompt templates for the Creative Catalyst Engine.
This is the definitive, cleaned-up version for the final architecture.
"""

# --- Stage 1: Brief Deconstruction & Enrichment Prompts ---

INTELLIGENT_DECONSTRUCTION_PROMPT = """
You are an expert fashion strategist. Your task is to analyze the user's natural language request and transform it into a complete, structured, and contextually-aware JSON creative brief.

**CRITICAL RULES:**
1.  **Extract Explicit Values:** First, analyze the user's text and extract any explicit values for the variables provided below.
2.  **Infer Missing Values:** Second, for any creative variable that is still missing (null), you MUST use your expert reasoning and deep knowledge of fashion to infer a logical and contextually appropriate value based on the core `theme_hint`. Do NOT use generic defaults.
3.  **Strict JSON Output:** Your response MUST be ONLY the valid JSON object.
---
**VARIABLES TO POPULATE:**
- theme_hint: The core creative idea or aesthetic. (Required)
- garment_type: The type of clothing.
- brand_category: The market tier (e.g., 'Streetwear', 'Contemporary', 'Luxury').
- target_audience: The intended wearer.
- region: The geographical or cultural context.
- key_attributes: A list of 2-3 core descriptive attributes.
- season: The fashion season (Default: auto).
- year: The target year (Default: auto).
---
--- EXAMPLE ---
USER REQUEST:
Generate a report on Streetwear Influence.

AI'S THOUGHT PROCESS (for inference):
- theme_hint: "Streetwear Influence" is clear.
- garment_type: Not specified, so null.
- brand_category: Streetwear's influence is strongest in the 'Contemporary' and 'Streetwear' categories, not typically 'Luxury' by default. 'Contemporary' is a good fit.
- target_audience: The core audience is young and urban. "Young, urban consumers" is appropriate.
- key_attributes: What defines streetwear? 'Comfort', 'Authenticity', 'Self-Expression'.

JSON OUTPUT:
{{
  "theme_hint": "Streetwear Influence",
  "garment_type": null,
  "brand_category": "Contemporary",
  "target_audience": "Young, urban consumers",
  "region": null,
  "key_attributes": ["Comfort", "Authenticity", "Self-Expression"],
  "season": "auto",
  "year": "auto"
}}
--- END EXAMPLE ---

USER REQUEST:
---
{user_passage}
---
JSON OUTPUT:
"""

# A new prompt to analyze the user's underlying philosophy.
# catalyst/prompts/prompt_library.py

# A new prompt to analyze the user's underlying philosophy.
ETHOS_ANALYSIS_PROMPT = """
You are an expert brand strategist and fashion critic. Your task is to analyze the user's request to find the unspoken, underlying design philosophy or brand ethos. Look beyond the specific garments and themes to understand the core values being expressed.

**CRITICAL RULES:**
1.  Read the user's passage carefully.
2.  Identify key principles related to craftsmanship, quality, target client's mindset, and overall aesthetic philosophy.
3.  Synthesize these principles into a single, concise paragraph.
4.  If the passage is purely functional and contains no discernible ethos, you MUST return null for the ethos value.
5.  Your response MUST be ONLY a valid JSON object with a single key: "ethos".

--- EXAMPLE 1 ---
USER PASSAGE:
"I prefer timeless, bespoke tailoring made from rare fabrics, with attention to every stitch. Exclusivity and craftsmanship are non-negotiable."

JSON RESPONSE:
{{
  "ethos": "The core ethos is one of ultimate luxury and uncompromising quality. The focus is on artisanal, bespoke craftsmanship over fleeting trends. Key values are timelessness, material rarity, meticulous attention to detail, and a sense of exclusivity for a discerning clientele."
}}
--- END EXAMPLE 1 ---

--- EXAMPLE 2 ---
USER PASSAGE:
"T-shirt for teenagers"

JSON RESPONSE:
{{
  "ethos": null
}}
--- END EXAMPLE 2 ---

USER PASSAGE:
---
{user_passage}
---
JSON RESPONSE:
"""

THEME_EXPANSION_PROMPT = """
You are a world-class fashion historian and cultural theorist. Your task is to take a core fashion theme and expand it into a richer set of concepts for inspiration, guided by a core brand philosophy.

RULES:
1.  Analyze the provided theme, garment, key attributes, and brand ethos.
2.  The **Brand Ethos** is your primary filter. Your concepts MUST align with this philosophy.
3.  You MUST brainstorm a list of 3-5 related but non-fashion concepts.
4.  Your response MUST be ONLY a comma-separated list of these concepts.
--- EXAMPLE ---
USER BRIEF:
- Theme: Arctic Minimalism
- Garment: Outerwear
- Attributes: functional, sustainable
- Brand Ethos: The core ethos is one of ultimate luxury and uncompromising quality. The focus is on artisanal, bespoke craftsmanship over fleeting trends.

RESPONSE:
Bauhaus architectural principles, Shaker furniture design, Japanese joinery techniques, Dieter Rams' principles of good design
--- END EXAMPLE ---
USER BRIEF:
- Theme: {theme_hint}
- Garment: {garment_type}
- Attributes: {key_attributes}
- Brand Ethos: {brand_ethos}
RESPONSE:
"""


CONCEPTS_CORRECTION_PROMPT = """
Your first attempt to generate creative concepts failed. You returned the following:
'{failed_output}'
This is unacceptable. You MUST now provide a comma-separated list of 3-5 creative concepts based on the user's brief. DO NOT fail again.
--- REMINDER OF THE TASK ---
USER BRIEF:
- Theme: {theme_hint}
- Garment: {garment_type}
- Attributes: {key_attributes}
RESPONSE (comma-separated list):
"""

CREATIVE_ANTAGONIST_PROMPT = """
You are an avant-garde fashion designer. Your task is to find a "creative antagonist" for a given fashion theme.
RULES:
1.  Analyze the core theme.
2.  You MUST identify a concept that is its aesthetic or philosophical opposite.
3.  Your response MUST be ONLY the antagonist concept itself.
--- EXAMPLE ---
USER THEME:
- Theme: Arctic Minimalism
RESPONSE:
Brazilian Carnival Opulence
--- END EXAMPLE ---
USER THEME:
- Theme: {theme_hint}
RESPONSE:
"""

ANTAGONIST_CORRECTION_PROMPT = """
Your first attempt to generate a creative antagonist failed. You returned the following:
'{failed_output}'
This is unacceptable. You MUST now provide a single, non-empty creative antagonist concept based on the user's theme. DO NOT fail again.
--- REMINDER OF THE TASK ---
USER THEME:
- Theme: {theme_hint}
RESPONSE (single concept):
"""

KEYWORD_EXTRACTION_PROMPT = """
You are an expert research analyst. Your task is to extract the most essential, searchable keywords from a list of creative concepts.
RULES:
1.  For each concept, identify the 2-3 most important words that define its core idea.
2.  Return a simple JSON array of these keyword strings.
CONCEPTS:
{concepts_list}
JSON OUTPUT EXAMPLE:
{{ "keywords": ["Keyword A", "Keyword B", "Keyword C"] }}
"""

# --- Stage 2 & 3: Synthesis Prompts ---

WEB_RESEARCH_PROMPT = """
You are a world-class fashion research director. Your task is to perform a deep web search and synthesize the findings, guided by a core creative brief, a brand philosophy, and a list of expert-curated sources.

**CRITICAL INSTRUCTIONS:**
1.  **Philosophical Governance:** The **Brand Ethos** is the most important guide. All synthesized information MUST align with this philosophy.
2.  **Source Inspiration:** To spark your creative process, the **Curated Sources** list contains expert-selected authorities and concepts. Treat this list as a **starting point for inspiration, not a restrictive set of instructions.** Your primary goal is to find the most creative and relevant information, so you are encouraged to go beyond this list and discover novel, high-quality sources through your own dynamic research.
3.  **Creative Governance:** The **Core Theme** and **Key Attributes** are the primary focus of the research.
4.  **Synthesize, Do Not List:** Synthesize all information into a cohesive, well-organized summary.

---
**GUIDING PHILOSOPHY:**
- **Brand Ethos:** {brand_ethos}
---
**CURATED SOURCES (For Inspiration):**
{curated_sources}
---
**CREATIVE BRIEF TO RESEARCH:**
- **Core Theme:** {theme_hint}
- **Garment Type:** {garment_type}
- **Target Audience:** {target_audience}
- **Region:** {region}
- **Key Attributes:** {key_attributes}
- **Creative Antagonist (for inspiration):** {creative_antagonist}
- **Key Search Concepts:** {search_keywords}
---

**SYNTHESIZED RESEARCH SUMMARY:**
"""

STRUCTURING_PREP_PROMPT = """
You are a data structuring analyst and fashion expert. Your task is to take a creative brief and a large, unstructured block of research text and organize the key findings into a clean, bulleted list.

**YOUR PROCESS:**
1.  Read the Creative Brief to understand the core goals.
2.  Read the Synthesized Research Context to identify all key details.
3.  Organize the extracted details under the specific headings provided below.
4.  **Garment Generation Rule:** You must follow this primary instruction:
    *   **Instruction:** `{garment_generation_instruction}`
    *   **CRITICAL FALLBACK:** If the research context is highly focused on a single item and does not contain clearly distinct, named variations, **you MUST use your fashion expertise to synthesize 2-3 conceptual variations based on the text.** For example, instead of specific product names, you could create descriptive titles like "The Classic Ribbed Turtleneck," "The Oversized Weekend Turtleneck," or "The Fine-Gauge Office Turtleneck" and then fill in their details from the context. **Do NOT fail to produce at least two key pieces.**

---
**CREATIVE BRIEF:**
- **Theme:** `{theme_hint}`
- **Garment Type:** `{garment_type}`
---
**SYNTHESIZED RESEARCH CONTEXT:**
{research_context}
---
**ORGANIZED OUTPUT:**
**Overarching Theme:**
- [Main theme synthesized from research]
**Cultural Drivers:**
- [Driver 1]
- [Driver 2]
**Influential Models / Muses:**
- [CRITICAL: Identify a PERSON, ARCHETYPE, or SUBCULTURE, not a company or a concept. For example: "90s Raver," "Digital Nomad," or "Bella Hadid."]
- [Archetype 1]
- [Archetype 2]
**Accessories:**
- **Bags:** [Description]
- **Footwear:** [Description]
- **Jewelry:** [Description]
- **Other:** [Description]
**Key Piece 1 Name:** [Name of the first key garment]
- **Description:** [Detailed description]
- **Inspired By Designers:** [List of designers]
- **Wearer Profile:** [Description of the wearer]
- **Fabrics:** [List of fabrics, textures, sustainability notes]
- **Colors:** [List of key colors]
- **Silhouettes:** [List of silhouettes]
- **Details & Trims:** [List of details]
- **Suggested Pairings:** [List of pairings]
(Continue for all identified key pieces based on the Garment Generation Rule and the Critical Fallback.)
"""

TOP_LEVEL_SYNTHESIS_PROMPT = """
You are a fashion analyst. Your task is to extract the main, high-level themes from the provided research text and structure them as a JSON object.
**CRITICAL RULES:**
- You MUST extract the 'overarching_theme', 'cultural_drivers', and 'influential_models'.
- For 'influential_models', you MUST extract people, archetypes, or subcultures (e.g., "90s Raver," "Digital Nomad"). Do NOT extract companies or abstract concepts.
- The output MUST be ONLY the valid JSON object.
--- ORGANIZED RESEARCH ---
{research_context}
---
"""

ACCESSORIES_SYNTHESIS_PROMPT = """
You are an expert fashion stylist and data analyst. Your task is to extract all mentions of accessories from the provided research text and structure them as a JSON object.

**CRITICAL RULES:**
1.  **Define "Accessory":** Your primary task is to identify items that *adorn* or *complement* an outfit, not core articles of clothing.
2.  **Negative Constraint:** You MUST EXCLUDE items like **jackets, kimonos, coats, cardigans, and shirts.** These are layering garments, not accessories.
3.  **Strict Categorization:** You MUST focus on extracting items for the specific categories: "Bags", "Footwear", "Jewelry", and "Other" (for items like hats, belts, scarves, sunglasses, etc.).
4.  **Intelligent Enrichment:** If the research text is sparse or missing specific examples for these categories, you MUST use your own expert fashion knowledge of the theme to suggest at least 2-3 relevant and creative items for each primary category ("Bags", "Footwear", "Jewelry"). Do NOT leave them empty if the theme strongly implies their presence (e.g., a festival theme).
5.  **Valid JSON Output:** The output MUST be ONLY the valid JSON object.

--- ORGANIZED RESEARCH ---
{research_context}
---
--- JSON OUTPUT EXAMPLE (Structure to Follow) ---
{{
  "accessories": {{
    "Bags": ["Fringed crossbody bags", "Woven straw totes"],
    "Footwear": ["Suede ankle boots", "Gladiator sandals"],
    "Jewelry": ["Layered turquoise necklaces", "Statement silver rings"],
    "Other": ["Wide-brimmed fedora hats", "Embroidered belts"]
  }}
}}
---
"""

KEY_PIECE_SYNTHESIS_PROMPT = """
You are a fashion data analyst and creative consultant. Your task is to extract and enrich the details for a single fashion garment from the provided text and structure it as a valid JSON object.
**CRITICAL RULES:**
1.  **Use Exact Structure:** You MUST use the exact field names and data types from the JSON OUTPUT EXAMPLE.
2.  **Enrich with Expertise:** If the context lacks specific details (e.g., fabric textures, Pantone/HEX codes), you MUST use your internal knowledge of fashion, textile science, and color theory to provide creative, insightful, and relevant suggestions that fit the theme.
3.  **Cultural Patterns Mandate:** For the `cultural_patterns` field, if the source text contains no relevant patterns, you MUST invent 1-2 creative patterns that align with the overarching theme (e.g., 'Art Deco motifs', 'Baroque scrollwork', 'traditional Shibori dyeing techniques'). Do NOT leave this field empty.
4.  **Be Commercially Aware:**
    - For `inspired_by_designers`, include BOTH high-fashion references AND commercially successful, trend-driven brands relevant to the target market (e.g., for fast-fashion, think of brands like Ganni or Self-Portrait).
    - For `sustainable` fabrics, be realistic. For a fast-fashion context, it's more credible to suggest a "hero" sustainable fabric or a blend with recycled content rather than claim everything is sustainable.
5.  The output MUST be ONLY the single, valid JSON object for this one key piece.
--- KEY PIECE CONTEXT ---
{key_piece_context}
---
--- JSON OUTPUT EXAMPLE (Structure to Follow) ---
{{
  "key_piece_name": "The Sculpted Parka",
  "description": "An oversized parka with clean lines that embodies quiet strength.",
  "inspired_by_designers": ["Jil Sander", "Helmut Lang", "COS"],
  "wearer_profile": "The urban creative who values form and function.",
  "cultural_patterns": ["Glitch Art Print", "Datamoshing"],
  "fabrics": [
    {{"material": "Recycled Nylon", "texture": "Matte", "sustainable": true}},
    {{"material": "Technical Wool Blend", "texture": "Brushed", "sustainable": false}}
  ],
  "colors": [
    {{"name": "Glacial Blue", "pantone_code": "14-4122 TCX", "hex_value": "#A2C4D1"}},
    {{"name": "Charcoal Gray", "pantone_code": "18-0601 TCX", "hex_value": "#5B5E5E"}}
  ],
  "silhouettes": ["Oversized", "A-Line"],
  "details_trims": ["Magnetic closures", "Waterproof zippers"],
  "suggested_pairings": ["Technical knit leggings", "Chunky sole boots"]
}}
---
"""

NARRATIVE_SETTING_PROMPT = """
You are a world-class art director and storyteller. Based on the following core concepts, write a single, evocative paragraph describing the ideal setting for a fashion editorial photoshoot. The setting must tell the story of the collection's theme.
- Overarching Theme: {overarching_theme}
- Cultural Drivers: {cultural_drivers}
The response MUST be a single paragraph of text. Do not use JSON.
"""

CREATIVE_STYLE_GUIDE_PROMPT = """
You are an expert creative director for a high-fashion magazine. Your task is to translate an abstract fashion brief into a concrete, actionable style guide for a photoshoot.

**CRITICAL RULES:**
1.  **Translate Ethos to Photography:** Analyze the `brand_ethos` and `overarching_theme` to define a specific photographic style. Provide concrete details like lighting, camera lens, and mood.
2.  **Enrich the Model Persona:** Expand the `influential_models` archetype into a single, descriptive sentence that captures the model's attitude, presence, and energy.
3.  **Weaponize the Antagonist:** Use the `creative_antagonist` to create a comma-separated list of visual styles, textures, or concepts that should be explicitly AVOIDED in the final image.
4.  **Strict JSON Output:** Your response MUST be ONLY a valid JSON object with the keys "photographic_style", "model_persona", and "negative_style_keywords".

---
**FASHION BRIEF:**
- **Brand Ethos:** {brand_ethos}
- **Overarching Theme:** {overarching_theme}
- **Influential Models / Archetypes:** {influential_models}
- **Creative Antagonist:** {creative_antagonist}
---
--- EXAMPLE ---
**FASHION BRIEF:**
- **Brand Ethos:** "The core ethos is one of ultimate luxury and uncompromising quality... a sense of exclusivity for a discerning clientele."
- **Overarching Theme:** "Timeless, bespoke tailoring as an artifact of unparalleled craftsmanship."
- **Influential Models / Archetypes:** ["The Modern Connoisseur", "The Legacy Builder"]
- **Creative Antagonist:** "Synthetic, Disposable Ubiquity"

**JSON RESPONSE:**
{{
  "photographic_style": "The lighting should be soft and directional, like natural light from a large window, creating gentle shadows that emphasize texture. Use a prime lens (e.g., 85mm at f/2.0) for a shallow depth of field, giving the image a timeless, painterly quality.",
  "model_persona": "The model embodies the quiet confidence of a modern connoisseur, with a poised, contemplative presence that speaks to an appreciation for heritage and craftsmanship.",
  "negative_style_keywords": "cheap, synthetic, mass-produced, disposable, plastic, overly trendy, flashy, generic"
}}
---

**JSON RESPONSE:**
"""

# --- Stage 4: Image Prompt Generation Templates ---


MOOD_BOARD_PROMPT_TEMPLATE = """
Create a professional, atmospheric fashion mood board laid out on a raw concrete or linen surface. The board's goal is to evoke the mood, story, and world of a single garment: '{key_piece_name}'.

**Composition & Feel:**
- Use a top-down flat-lay composition. The layout should be a dynamic, slightly overlapping collage, not a rigid grid. Layer elements to create a sense of texture and depth.
- The lighting should be soft and diffused, as if from a large studio window, creating a narrative and emotional mood.
- Feature a printed, Polaroid-style portrait of a professional fashion model with artistic features, representing the garment's wearer. This portrait should appear as an object clipped or pinned into the flat-lay.

**Required Elements:**
1.  **Material & Color Story:**
    - Include hyper-realistic, tactile fabric swatches of: {fabric_names}. Arrange some neatly stacked and some casually draped to show their texture.
    - Feature a focused color palette arranged with official, Pantone-like color chips for: {color_names}.

2.  **Details & Craftsmanship:**
    - Include a dedicated section with macro-photography close-ups of key design details and trims, such as: {details_trims}. These should clearly show the stitch, weave, and surface texture.

3.  **Styling & Accessories:**
    - Show key physical accessories, like {key_accessories}, interacting with other elements to create a sense of process and curation.

**Style & Negative Constraints:**
- Style: Professional studio photography, editorial, tactile, atmospheric, high-detail.
- Negative Prompts: Avoid text, watermarks, logos, brand names, and recognizable public figures. The image should be clean and professional.
"""

FINAL_GARMENT_PROMPT_TEMPLATE = """
Full-body editorial fashion photograph for a high-end magazine lookbook, featuring the '{key_piece_name}'.

**Photography Style & Mood:**
- {photographic_style_guide}
- The photograph should have a shallow depth of field, keeping the garment's texture and details in sharp focus while the background is softly blurred.

**Model Persona & Garment:**
- **Model:** {model_persona} The model is a professional fashion model with artistic features.
- **Garment:** The model is wearing the '{key_piece_name}', crafted from {main_fabric} in a rich '{main_color}'. The rendering should showcase the material's texture, weave, and drape with photorealistic detail.
- **Styling:** The garment is styled with {styling_description} to create a look that feels authentic and personally curated.

**Composition & Setting:**
- **Setting:** {narrative_setting}
- **Composition:** The primary shot is a full-body view capturing the garment's modern '{silhouette}'. The model should have a dynamic, candid pose that suggests movement.

**Style & Negative Constraints:**
- **Style:** Editorial, photorealistic, cinematic, tactile, high-detail, authentic.
- **Negative Prompts:** Avoid {negative_style_keywords}, nsfw, deformed anatomy, extra limbs, poor quality, watermarks, logos, text overlays, and any likeness of real public figures or celebrities.
"""
