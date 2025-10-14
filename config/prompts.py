"""
Prompt templates for LLM operations.
"""

# Certificate extraction prompt template
CERTIFICATE_EXTRACTION_PROMPT = """You are an intelligent document parser specialized in Brazilian Portuguese certificates. 

Your task:
1. First, clean the OCR text by removing artifacts and special characters
2. Then extract the required fields from the cleaned text

CLEANING RULES:
- Remove OCR artifacts like (68), ®, ©, @, symbols in parentheses, etc.
- Fix broken words and incorrect spacing
- Remove unnecessary line breaks that split words
- Keep all meaningful information (names, dates, places, course details)
- Make text coherent in Portuguese BR

EXTRACTION RULES:
Extract these exact fields in JSON format:
- nome_participante: Full name of the certificate recipient
- evento: Name of the event/course/workshop/training
- local: Location, city, or institution where event took place  
- data: Date when event occurred (keep original format)
- carga_horaria: Duration or workload hours

CRITICAL FORMAT REQUIREMENTS:
- Return ONLY a valid JSON object with these exact field names
- Use null for missing/unclear fields
- Do not include explanations or code blocks
- Each field should appear ONLY ONCE in the JSON
- Field names must be exactly as specified (no extra spaces)
- Process the text considering Portuguese BR language patterns

Example format:
{{
  "nome_participante": "Full Name Here",
  "evento": "Event Name Here",
  "local": "Location Here",
  "data": "Date Here",
  "carga_horaria": "Hours Here"
}}

OCR Text:
{text}

JSON:"""

# Activity categorization prompt template
ACTIVITY_CATEGORIZATION_PROMPT = """You are an expert in classifying complementary activities for Computer Engineering students.

TASK: Analyze the extracted certificate and identify the most appropriate category among the available options.

COMPLETE CERTIFICATE TEXT (OCR):
{raw_text}

STRUCTURED EXTRACTED DATA:
- Participant: {nome_participante}
- Event: {evento}
- Location: {local}
- Date: {data}
- Hours: {carga_horaria}

AVAILABLE CATEGORIES:
{categories_text}

INSTRUCTIONS:
1. FIRST analyze the complete certificate text (OCR) to fully understand the context
2. Use the structured data as additional reference
3. Carefully compare with all available categories
4. Consider keywords, activity type, institution, knowledge area
5. Choose the category that best fits the complete context
6. Explain your decision clearly and in detail

RESPONSE FORMAT (JSON):
{{
    "category_id": <ID of the chosen category>,
    "reasoning": "<Detailed explanation of the choice, mentioning specific elements from the OCR text that led to this decision>The reasoning should be in Portuguese BR"
}}

Respond ONLY with valid JSON, no additional text."""