"""
A library of master prompt templates for the Creative Catalyst Engine.
This is the definitive, cleaned-up version for the final architecture.
"""

# --- Stage 1: Brief Deconstruction & Enrichment Prompts ---

SCHEMA_DRIVEN_DECONSTRUCTION_PROMPT = """
You are an expert assistant to a top-tier fashion Creative Director. Your task is to analyze the user's natural language request and deconstruct it into a structured JSON object.
RULES:
1.  Analyze the user's text for hints about the following variables.
2.  For any variable that is not mentioned, its value in the JSON object MUST be null.
3.  Your response MUST be ONLY the valid JSON object.
VARIABLES TO EXTRACT:
---
{variable_rules}
---
--- EXAMPLE ---
USER REQUEST:
I'm thinking about a line of luxury silk scarves for the Indonesian market, maybe for next year. The main idea is 'Archipelago Dreams'.
JSON OUTPUT:
{{
  "theme_hint": "Archipelago Dreams",
  "garment_type": "Silk Scarves",
  "brand_category": "Luxury",
  "target_audience": null,
  "region": "Indonesian",
  "key_attributes": null,
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

THEME_EXPANSION_PROMPT = """
You are a world-class fashion historian and cultural theorist. Your task is to take a core fashion theme and expand it into a richer set of abstract, historical, and artistic concepts for inspiration.
RULES:
1.  Analyze the provided theme, garment, and key attributes.
2.  You MUST brainstorm a list of 3-5 related but non-fashion concepts.
3.  You MUST include a mix of BOTH abstract/artistic concepts AND specific historical fashion references.
4.  Your response MUST be ONLY a comma-separated list of these concepts.
--- EXAMPLE ---
USER BRIEF:
- Theme: Arctic Minimalism
- Garment: Outerwear
- Attributes: functional, sustainable, stark beauty
RESPONSE:
Bauhaus architectural principles, 19th-century polar expedition gear, Japanese wabi-sabi philosophy, Modern Scandinavian interior design
--- END EXAMPLE ---
USER BRIEF:
- Theme: {theme_hint}
- Garment: {garment_type}
- Attributes: {key_attributes}
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
You are a world-class fashion research director. Your primary task is to perform a comprehensive web search based on the provided creative brief and synthesize your findings into a single, detailed, unstructured text block.

**CRITICAL INSTRUCTIONS:**
1.  **Think Like an Expert:** You MUST prioritize information from globally recognized fashion authorities (like Vogue Runway, Business of Fashion), respected trend forecasting services (like WGSN), and major cultural institutions and museums. While also considering blogs, social media, and street style for emerging trends.
2.  **Perform a Deep Web Search:** Use your built-in search tools to find the most current and relevant articles, runway analyses, interviews, and cultural discussions related to all concepts in the brief.
3.  **Synthesize, Do Not List:** Do not simply list URLs or snippets. Synthesize all the information you find into a cohesive, well-organized, and comprehensive summary. Your goal is to provide a rich context for the next step in the creative process.
4.  **Be Comprehensive:** Ensure your summary includes rich details on potential themes, concepts, colors, fabrics, textures, silhouettes, accessories, and relevant cultural patterns that align with the brief.

---
**CREATIVE BRIEF TO RESEARCH:**
- **Core Theme:** {theme_hint}
- **Garment Type:** {garment_type}
- **Target Audience:** {target_audience}
- **Region:** {region}
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
**Influential Models:**
- [Model 1]
- [Model 2]
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
- The output MUST be ONLY the valid JSON object.
--- ORGANIZED RESEARCH ---
{research_context}
---
"""

ACCESSORIES_SYNTHESIS_PROMPT = """
You are a fashion analyst. Your task is to extract all mentions of accessories from the provided research text and structure them as a JSON object.
**CRITICAL RULES:**
- You MUST group accessories by the categories: "Bags", "Footwear", "Jewelry", and "Other".
- The output MUST be ONLY the valid JSON object.
--- ORGANIZED RESEARCH ---
{research_context}
---
"""

KEY_PIECE_SYNTHESIS_PROMPT = """
You are a fashion data analyst and creative consultant. Your task is to extract and enrich the details for a single fashion garment from the provided text and structure it as a valid JSON object.
**CRITICAL RULES:**
1.  You MUST use the exact field names and data types from the JSON OUTPUT EXAMPLE.
2.  **Analyze and Enrich:** If the context lacks specific details (e.g., fabric textures, Pantone/HEX codes), you MUST use your internal knowledge of fashion, textile science, and color theory to provide creative, insightful, and relevant suggestions that fit the theme.
3.  The output MUST be ONLY the single, valid JSON object for this one key piece.
--- KEY PIECE CONTEXT ---
{key_piece_context}
---
--- JSON OUTPUT EXAMPLE (Structure to Follow) ---
{{
  "key_piece_name": "The Sculpted Parka",
  "description": "An oversized parka with clean lines that embodies quiet strength.",
  "inspired_by_designers": ["Jil Sander", "Helmut Lang"],
  "wearer_profile": "The urban creative who values form and function.",
  "cultural_patterns": [],
  "fabrics": [
    {{"material": "Recycled Nylon", "texture": "Matte", "sustainable": true}},
    {{"material": "Technical Wool", "texture": "Brushed", "sustainable": true}}
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

_JSON_EXAMPLE_FOR_DIRECT_KNOWLEDGE = """
{
  "season": "Fall/Winter", "year": 2026, "region": "Global",
  "target_model_ethnicity": "Diverse",
  "narrative_setting_description": "An ancient, misty forest with towering, moss-covered stones. The air is cool and silent, with soft, diffused light filtering through the canopy.",
  "overarching_theme": "Example: Goblincore Mysticism",
  "cultural_drivers": ["Example: Return to Nature", "Example: Anti-Perfectionism"],
  "influential_models": ["Example: Lord of the Rings Elves"],
  "accessories": {"Bags": ["Worn leather pouches"], "Footwear": ["Soft, moss-colored boots"], "Jewelry": ["Silver amulets"]},
  "detailed_key_pieces": [
    {
      "key_piece_name": "The Moss-Stitched Cloak", "description": "A heavy, flowing cloak.",
      "inspired_by_designers": ["Rick Owens", "Yohji Yamamoto"], "wearer_profile": "The modern druid.",
      "cultural_patterns": [],
      "fabrics": [{"material": "Brushed Wool", "texture": "Felted", "sustainable": true}],
      "colors": [{"name": "Forest Floor Brown", "pantone_code": "19-1118 TCX", "hex_value": "#5B4D3D"}],
      "silhouettes": ["Asymmetrical", "Draped"], "details_trims": ["Raw edges", "Antler toggles"],
      "suggested_pairings": ["Linen trousers", "Leather accessories"]
    }
  ]
}
"""

DIRECT_KNOWLEDGE_SYNTHESIS_PROMPT = (
    """
You are the Director of Strategy for 'The Future of Fashion'. Your task is to generate a complete fashion trend report based solely on the provided creative brief and your own extensive internal knowledge.
**CRITICAL RULES:**
- You MUST rely entirely on your pre-trained knowledge of fashion history, cultural trends, textile science, and color theory.
- You MUST use the exact field names and data types as defined in the `response_schema`.
- You MUST follow the structure of the JSON example below.
- You MUST provide a value for every required field, inventing creative and relevant details where necessary.
---
**CREATIVE BRIEF:**
- **Core Theme:** {theme_hint}
- **Garment Type:** {garment_type}
- **Target Audience:** {target_audience}
- **Season:** {season} {year}
- **Creative Antagonist (for inspiration):** {creative_antagonist}
---
--- JSON OUTPUT EXAMPLE (Structure to Follow) ---
"""
    + _JSON_EXAMPLE_FOR_DIRECT_KNOWLEDGE
    + """
---
Based on the **CREATIVE BRIEF** and your internal knowledge, generate a single, valid JSON object.
"""
)


# --- Stage 4: Image Prompt Generation Templates ---

INSPIRATION_BOARD_PROMPT_TEMPLATE = """
Create a hyper-detailed, atmospheric flat lay of a professional fashion designer's physical inspiration board.
**Core Concept:**
- Theme: '{theme}'
- Aesthetic Focus: The conceptual idea of a '{key_piece_name}' that embodies the idea of '{description_snippet}'
- Muse / Archetype: The style of {model_style}
**Core Color Story:**
- The board features a clear and intentional color palette, represented by neatly pinned Pantone-style color chips for: {color_names}.
**Composition & Included Items:**
The board is an artfully arranged collage that MUST include a mix of the following:
1.  **Archival & Textural Layer:** Torn pages from vintage art books, faded historical photographs, rough charcoal sketches of garment details.
2.  **Modern Context Layer:** High-quality, candid street style photos, glossy tear sheets from contemporary fashion magazines.
3.  **Material Layer:** Physical, tactile swatches of key fabrics like {fabric_names} with frayed edges, alongside close-up photos of specific hardware.
**Style:**
Ultra-realistic photograph, top-down perspective, shot on a Hasselblad camera, soft but dramatic lighting, 8k.
"""

MOOD_BOARD_PROMPT_TEMPLATE = """
Create a professional fashion designer's mood board, meticulously organized on a raw concrete or linen surface.
**Focus:** Defining the materials, details, and styling for a '{key_piece_name}'.
**1. Material & Color Story:**
- **Fabric Swatches:** The board features hyper-realistic, neatly cut physical fabric swatches of: {fabric_names}.
- **Color Palette:** A focused color story is arranged with official Pantone-style color chips for: {color_names}.
**2. Detail & Craftsmanship:**
- **Detail Shots:** A dedicated section with macro-photography close-ups of key design details, such as: {details_trims}.
**3. Styling & Accessories:**
- **Key Accessories:** The board MUST feature 2-3 key physical accessories or high-quality photos of them, such as: {key_accessories}.
**Style:**
Professional studio photography, top-down view (flat lay), soft and diffused lighting, extreme detail, macro photography, 8k.
"""

FINAL_GARMENT_PROMPT_TEMPLATE = """
Full-body editorial fashion photograph for a high-end fashion magazine lookbook.
**Model & Garment:**
- A professional runway model with the confident, elegant, and stylish presence of {model_style}.
- The model is wearing the '{key_piece_name}', a stunning garment that embodies the concept of '{description_snippet}'. It is crafted from hyper-realistic {main_fabric} in a rich '{main_color}'.
**Silhouette & Details:**
- The silhouette is a modern '{silhouette}'.
- Macro details are visible, showcasing the exquisite craftsmanship, such as: {details_trims}.
**Pose & Setting:**
- The model has a confident, poised, and powerful pose that complements the environment.
- **Setting:** {narrative_setting}
**Style:**
- Cinematic fashion photography, shot on a 50mm lens, hyper-detailed, professional color grading, 8k.
**Negative Prompt:**
- -nsfw, -deformed, -bad anatomy, -blurry, -low quality, -generic
"""
