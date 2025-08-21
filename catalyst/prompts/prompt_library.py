"""
A library of master prompt templates for the Creative Catalyst Engine.
(Final version with consistent prompt formats and a pre-structuring step)
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

# Asks for a simple comma-separated list for higher reliability.
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

# Asks for a single concept string for higher reliability.
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

# --- Stage 3 & 4 Prompts ---

URL_INSIGHTS_EXTRACTION_PROMPT = """
You are a world-class fashion research assistant. Your task is to analyze the content of the provided URLs and synthesize a comprehensive, unstructured summary of all key findings related to the creative brief.
**CREATIVE BRIEF:**
- Core Theme: {theme_hint}
- Garment Type: {garment_type}
**YOUR PROCESS:**
1.  Using your browsing tool, visit and deeply analyze every URL provided.
2.  Extract all relevant information, including trends, themes, concepts, colors, fabrics, silhouettes, and designers.
3.  Synthesize these findings into a single, detailed, and well-organized text block. Do not use JSON.
**CURATED URLS FOR ANALYSIS:**
{urls_list}
**SYNTHESIZED RESEARCH SUMMARY:**
"""

# --- START OF CORRECTION ---
# Changed from f""" to """ to prevent KeyError
TOP_LEVEL_SYNTHESIS_PROMPT = """
You are a fashion analyst. Your task is to extract the main, high-level themes from the provided research text and structure them as a JSON object.

**CRITICAL RULES:**
- You MUST extract the 'overarching_theme', 'cultural_drivers', and 'influential_models'.
- The output MUST be ONLY the valid JSON object.
- Use the provided JSON example for the exact field names.

--- ORGANIZED RESEARCH ---
{research_context}
---

--- JSON OUTPUT EXAMPLE ---
{{
  "overarching_theme": "Example: Arctic Minimalism",
  "cultural_drivers": ["Example: Sustainability", "Example: Functionalism"],
  "influential_models": ["Example: Tilda Swinton", "Example: Rei Kawakubo"]
}}
---

Now, generate the JSON object based on the research.
"""

ACCESSORIES_SYNTHESIS_PROMPT = """
You are a fashion analyst. Your task is to extract all mentions of accessories from the provided research text and structure them as a JSON object.

**CRITICAL RULES:**
- You MUST group accessories by the categories: "Bags", "Footwear", "Jewelry", and "Other".
- The output MUST be ONLY the valid JSON object.
- Use the provided JSON example for the exact structure.

--- ORGANIZED RESEARCH ---
{research_context}
---

--- JSON OUTPUT EXAMPLE ---
{{
  "accessories": {{
    "Bags": ["Utilitarian cross-body bags", "Recycled material totes"],
    "Footwear": ["Insulated technical boots"],
    "Jewelry": ["Minimalist silver pieces"],
    "Other": ["Smart gloves"]
  }}
}}
---

Now, generate the JSON object based on the research.
"""

KEY_PIECE_SYNTHESIS_PROMPT = """
You are a fashion data analyst. Your task is to extract the details for a single fashion garment from the provided text and structure it as a valid JSON object.

**CRITICAL RULES:**
- You MUST use the exact field names and data types from the JSON OUTPUT EXAMPLE.
- The output MUST be ONLY the single, valid JSON object for this one key piece.

--- KEY PIECE CONTEXT ---
{key_piece_context}
---

--- JSON OUTPUT EXAMPLE ---
{{
  "key_piece_name": "The Sculpted Parka",
  "description": "An oversized parka with clean lines.",
  "inspired_by_designers": ["Jil Sander", "Helmut Lang"],
  "wearer_profile": "The urban creative.",
  "cultural_patterns": [],
  "fabrics": [{{"material": "Recycled Nylon", "texture": "Matte", "sustainable": true, "sustainability_comment": "Made from reclaimed ocean plastics."}}],
  "colors": [{{"name": "Glacial Blue", "pantone_code": "14-4122 TCX", "hex_value": "#A2C4D1"}}],
  "silhouettes": ["Oversized", "A-Line"],
  "details_trims": ["Magnetic closures", "Waterproof zippers"],
  "suggested_pairings": ["Technical knit leggings", "Chunky sole boots"]
}}
---

Now, generate the JSON object for the key piece described in the context.
"""

STRUCTURING_PREP_PROMPT = """
You are a data structuring analyst. Your task is to take a creative brief and a large, unstructured block of research text and organize the key findings into a clean, bulleted list. The headings for the list MUST match the sections of the final report.
**YOUR PROCESS:**
1.  Read the Creative Brief to understand the core goals.
2.  Read the Synthesized Research Context to identify all key details.
3.  Organize the extracted details under the following specific headings.
4.  For each "Key Piece", create a separate section (e.g., Key Piece 1, Key Piece 2).
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
(Continue for all identified key pieces)
"""

_JSON_EXAMPLE_STRUCTURE = """
{{
  "season": "Fall/Winter", "year": 2026, "region": "Global", "target_model_ethnicity": "Diverse",
  "overarching_theme": "Example: Arctic Minimalism", "cultural_drivers": ["Example: Sustainability", "Example: Functionalism"],
  "influential_models": ["Example: Tilda Swinton", "Example: Rei Kawakubo"],
  "accessories": {{"Bags": ["Utilitarian cross-body bags"], "Footwear": ["Insulated technical boots"], "Jewelry": ["Minimalist silver pieces"], "Other": ["Smart gloves"]}},
  "detailed_key_pieces": [
    {{
      "key_piece_name": "The Sculpted Parka", "description": "An oversized parka with clean lines.",
      "inspired_by_designers": ["Jil Sander", "Helmut Lang"], "wearer_profile": "The urban creative.",
      "cultural_patterns": [],
      "fabrics": ["Recycled Nylon", "Matte Cotton", "Technical Wool"],
      "colors": ["Glacial Blue", "Charcoal Gray", "Off-White"],
      "silhouettes": ["Oversized", "A-Line"], "details_trims": ["Magnetic closures", "Waterproof zippers"],
      "suggested_pairings": ["Technical knit leggings", "Chunky sole boots"]
    }}
  ],
  "visual_analysis": []
}}
"""

# Changed from f""" to """ to prevent KeyError
DIRECT_SYNTHESIS_PROMPT = (
    """
You are the Director of Strategy for 'The Future of Fashion'. Your task is to structure the provided **ORGANIZED RESEARCH** into a final, comprehensive report in the specified JSON format.
**CRITICAL RULES:**
- You MUST use the exact field names and data types as defined in the `response_schema`.
- You MUST follow the structure of the JSON example.
- You MUST provide a value for every required field.
---
**CREATIVE BRIEF:**
- **Theme:** {theme_hint}
- **Garment Type:** {garment_type}
- **Target Audience:** {target_audience}
- **Region:** {region}
- **Creative Antagonist:** {creative_antagonist}
---
**ORGANIZED RESEARCH:**
{research_context}
---
--- JSON OUTPUT EXAMPLE (Structure to Follow) ---
"""
    + _JSON_EXAMPLE_STRUCTURE
    + """
---
Based on the **CREATIVE BRIEF** and **ORGANIZED RESEARCH**, generate a single, valid JSON object for the {season} {year} season.
"""
)

# Changed from f""" to """ to prevent KeyError
JSON_CORRECTION_PROMPT = (
    """
You are a JSON correction expert. Your previous attempt failed validation. You MUST fix it.
**RULES:**
1.  Analyze the "VALIDATION ERRORS" and the "BROKEN JSON".
2.  Fix all errors, such as correcting field names (e.g., "name" to "key_piece_name") and data types (e.g., a dictionary for "accessories").
3.  Refer to the "CORRECT JSON STRUCTURE EXAMPLE" for the correct format.
4.  The output MUST be ONLY the valid JSON object.
--- BROKEN JSON ---
{broken_json}
---
--- VALIDATION ERRORS ---
{validation_errors}
---
--- CORRECT JSON STRUCTURE EXAMPLE ---
"""
    + _JSON_EXAMPLE_STRUCTURE
    + """
---
Now, provide only the corrected, valid JSON object.
"""
)

# --- Phase 4: Image Prompt Generation Templates (UPGRADED) ---
INSPIRATION_BOARD_PROMPT_TEMPLATE = """
Create a hyper-detailed, atmospheric flat lay of a professional fashion designer's physical inspiration board. The board must be a sophisticated blend of historical research and contemporary market awareness.

**Core Concept:**
- Theme: '{theme}'
- Aesthetic Focus: The conceptual idea of a '{key_piece_name}'
- Muse: The style of {model_style}

**Regional & Cultural Elements (CRITICAL):**
- This collection is for the '{region}' market. The board MUST include specific, authentic visual references to this region, such as: {regional_context}

**Core Color Story:**
- The board features a clear and intentional color palette, represented by neatly pinned Pantone-style color chips for: {color_names}.

**Composition & Included Items:**
The board is an artfully arranged collage that juxtaposes historical and modern elements. It MUST include a mix of the following:
1.  **Archival & Textural Layer:** Torn pages from vintage art books, faded historical photographs, rough charcoal sketches of garment details (collars, seams), and handwritten notes on aged paper.
2.  **Modern Context Layer:** High-quality, candid street style photos from '{region}', glossy tear sheets from contemporary fashion magazines (like Vogue Korea or Ginza Magazine if relevant), and screenshots of modern digital art that reflect the theme.
3.  **Material Layer:** Physical, tactile swatches of key fabrics like {fabric_names} with frayed edges, alongside close-up photos of specific hardware, trims, or embroidery techniques.

**Overall Mood:**
A dynamic synthesis of old and new. Tactile, authentic, intellectual, culturally-aware, contemporary, and cinematic.

**Style:**
Ultra-realistic photograph, top-down perspective, shot on a Hasselblad camera, soft but dramatic lighting with deep shadows, extreme detail, 8k.
"""

MOOD_BOARD_PROMPT_TEMPLATE = """
Create a professional fashion designer's mood board, meticulously organized on a raw concrete or linen surface. The board must be a sophisticated and focused tool for defining a specific garment.

**Focus:** Defining the materials, details, and styling for a '{key_piece_name}' for the '{region}' market.

**1. Material & Color Story:**
- **Fabric Swatches:** The board features hyper-realistic, neatly cut physical fabric swatches of: {fabric_names}. The texture and drape must be clearly visible. MUST include a prominent swatch of '{culturally_specific_fabric}' to anchor the regional identity.
- **Color Palette:** A focused color story is arranged with official Pantone-style color chips for: {color_names}.

**2. Detail & Craftsmanship:**
- **Detail Shots:** A dedicated section with macro-photography close-ups of key design details, such as: {details_trims}. This should showcase specific techniques like embroidery, stitching, or hardware.

**3. Styling & Accessories:**
- **Key Accessories:** The board MUST feature 2-3 key physical accessories or high-quality photos of them, such as: {key_accessories}. This provides essential styling context.

**4. Cultural & Demographic Context:**
- **Contextual Images:** To ground the design in its target market, the board MUST include 2-3 smaller, high-quality photographs: a candid street style photo of a young, stylish woman in '{region}', and a close-up of a relevant cultural motif like '{regional_context}'.

**Style:**
Professional studio photography, top-down view (flat lay), soft and diffused lighting, extreme detail, macro photography, 8k.
"""

FINAL_GARMENT_PROMPT_TEMPLATE = """
Full-body editorial fashion photograph for a Vogue Arabia or a high-end Indonesian fashion magazine lookbook.

**Model:**
- A young, professional {model_ethnicity} runway model with the confident, elegant, and stylish presence of {model_style}.

**Garment & Cultural Integration:**
- The model is wearing a stunning '{main_color} {key_piece_name}' crafted from hyper-realistic {main_fabric}.
- **CRITICAL:** Key parts of the garment, such as the sleeves, bodice, or trim, MUST be adorned with a subtle, elegant, tone-on-tone '{cultural_pattern}' pattern, reflecting the design heritage of the region.
- **CRITICAL:** The design strictly adheres to modern modest fashion principles, featuring a high, elegant neckline (no plunging V-necks or shoulder cutouts) and full-length, non-transparent sleeves.

**Silhouette & Details:**
- The silhouette is a modern '{silhouette}', subtly influenced by traditional '{region}' garments.
- Macro details are visible, showcasing the exquisite craftsmanship, such as: {details_trims}.

**Pose & Setting:**
- The model has a confident, poised, and powerful pose.
- Setting: Shot in a minimalist, contemporary architectural setting with dramatic natural light and soft shadows.

**Style:**
- Cinematic fashion photography, shot on a 50mm lens, hyper-detailed, professional color grading, 8k.

**Negative Prompt:**
- -nsfw, -deformed, -bad anatomy, -blurry, -low quality, -generic
"""
