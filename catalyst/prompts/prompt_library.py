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
You are a data structuring analyst. Your task is to take a creative brief and a large, unstructured block of research text and organize the key findings into a clean, bulleted list.

**YOUR PROCESS:**
1.  Read the Creative Brief to understand the core goals.
2.  Read the Synthesized Research Context to identify all key details.
3.  Organize the extracted details under the specific headings provided below.
4.  **Garment Generation Rule:** {garment_generation_instruction}

---
**CREATIVE BRIEF:**
- **Theme:** {theme_hint}
- **Garment Type:** {garment_type}
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
(Continue for all identified key pieces based on the Garment Generation Rule)
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


# --- Stage 4: Image Prompt Generation Templates ---

INSPIRATION_BOARD_PROMPT_TEMPLATE = """
Create a hyper-detailed, atmospheric flat lay of a professional fashion designer's physical inspiration board. The board must feel like an authentic, working document, not a static, perfect presentation.

**Core Concept:**
- Theme: '{theme}'
- Aesthetic Focus: The conceptual idea of a '{key_piece_name}' that embodies the idea of '{description_snippet}'
- Muse / Archetype: The style of {model_style}

**Core Color Story:**
- The board features a clear and intentional color palette, represented by neatly pinned Pantone-style color chips for: {color_names}.

**Non-Fashion Inspiration:**
- To ground the theme in the real world, the board MUST include at least two non-fashion items for texture and color reference, such as a piece of weathered driftwood, a close-up photo of peeling paint on concrete, or a vintage map.

**Composition & The Designer's Process:**
The board must look like a dynamic, work-in-progress document. The arrangement is an artfully layered collage, not a clean grid.
- **Interaction & Annotation:** Elements MUST be layered and interact. Fabric swatches are pinned directly on top of photographs to test relationships. There are **handwritten notes in pencil or ink in the margins, arrows drawn in charcoal connecting elements, and visible pinholes and tape marks** from previous arrangements.
- The board MUST include a mix of the following:
    1.  **Archival & Textural Layer:** Torn pages from vintage art books, faded historical photographs, and rough, gestural charcoal sketches of garment details (collars, seams, pockets).
    2.  **Modern Context Layer:** High-quality, candid street style photos and glossy tear sheets from contemporary fashion magazines.
    3.  **Material Layer:** Physical, three-dimensional, and tactile swatches of key fabrics like {fabric_names}. The swatches MUST be **messy, frayed, and show signs of handling.** The board must also include **actual, physical metal hardware** like buttons, zippers, or clasps, not just photos of them.

**Overall Mood:**
Tactile, authentic, intellectual, cinematic, and a **dynamic work-in-progress**.

**Style:**
Ultra-realistic photograph, top-down perspective, shot on a Hasselblad camera, soft but dramatic lighting that creates deep shadows, extreme detail, 8k.
"""

MOOD_BOARD_PROMPT_TEMPLATE = """
Create a professional and atmospheric fashion designer's mood board on a raw concrete or linen surface. The board's primary goal is to evoke the mood, story, and world of a single garment.

**Focus:** Defining the materials, details, and styling for a '{key_piece_name}'.

**Central Anchor Image:**
- The composition MUST be built around a large, central, candid street style photograph of a person who embodies the spirit of the garment. This image sets the mood for the entire board.

**Composition:**
- The layout must be a dynamic, overlapping collage, not a rigid grid or a tidy "knolling" arrangement. Elements should be layered to create texture and depth, showing the designer's thought process.

**Environmental Textures:**
- The board MUST include at least two smaller, secondary photos of urban textures that match the collection's narrative, such as peeling paint, graffiti-covered brick, or worn concrete.

**1. Material & Color Story:**
- **Fabric Swatches:** Hyper-realistic, physical fabric swatches of: {fabric_names}. They should appear handled, with some neat stacks and some messy, draped pieces.
- **Color Palette:** A focused color story arranged with official Pantone-style color chips for: {color_names}.

**2. Detail & Craftsmanship:**
- **Detail Shots:** A dedicated section with macro-photography close-ups of key design details, such as: {details_trims}.

**3. Styling & Accessories:**
- **Integrated Styling:** The board must show key physical accessories like {key_accessories} interacting with other elements, such as a leather belt placed over a stack of fabric swatches, or a beanie next to the central anchor photograph.

**Style:**
Professional studio photography, top-down view (flat lay), soft and diffused lighting that creates an **atmospheric, narrative, and emotional** mood. Extreme detail, macro photography, 8k.
"""

FINAL_GARMENT_PROMPT_TEMPLATE = """
Full-body editorial fashion photograph for a high-end fashion magazine lookbook.

**Guiding Philosophy (Ethos):**
- {brand_ethos}

**Model & Garment:**
- A professional runway model with the confident, elegant, and stylish presence of {model_style}.
- The model is wearing the '{key_piece_name}', a stunning garment that embodies the concept of '{description_snippet}'. It is crafted from hyper-realistic {main_fabric} in a rich '{main_color}'. The craftsmanship MUST reflect the Guiding Philosophy.

**Styling:**
- {styling_description} The overall look must feel authentic and personally styled, not like a mannequin.

**Silhouette & Details:**
- The silhouette is a modern '{silhouette}'.
- Macro details are visible, showcasing the exquisite craftsmanship, such as: {details_trims}.

**Pose & Setting:**
- The model has a **dynamic, candid pose that suggests movement**—walking, leaning, or interacting with the environment.
- **Setting:** {narrative_setting}

**Style:**
- The photographic style MUST align with the **Guiding Philosophy**. If the ethos is raw and unpolished, shoot on 35mm film like Juergen Teller. If the ethos is timeless and elegant, shoot with the polished, romantic style of a top fashion magazine. The image should feel authentic to the brand. 8k.

**Negative Prompt:**
- -nsfw, -deformed, -bad anatomy, -blurry, -low quality, -generic
"""
