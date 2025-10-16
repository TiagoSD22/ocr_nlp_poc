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

CRITICAL CLASSIFICATION GUIDELINES:

1. ACTIVITY TYPE KEYWORDS - Pay attention to these specific terms (KEYWORDS OVERRIDE DURATION):
   - PARTICIPATION/LEARNING activities: "curso", "minicurso", "workshop", "treinamento", "capacitação", "participou", "participação", "certificação"
   - PRESENTATION/SPEAKING activities: "palestra", "palestrante", "apresentação", "apresentou", "ministrou", "ministrando"
   - ORGANIZATION activities: "organizou", "organizador", "coordenou", "coordenador", "organizaçào"
   - COMPETITION activities: "competição", "concurso", "hackathon", "maratona", "olimpíada", "campeonato", "capture the flag", "CTF"
   - RESEARCH/EXTENSION projects: "projeto de pesquisa", "projeto de extensão", "iniciação científica", "bolsista", "pesquisador", "orientador"
   
2. DURATION ANALYSIS - CRITICAL MATCHING RULES:
   - COMPETITIONS/CONTESTS (1-24h): CTF, hackathons, programming contests, championships
     * 4h CTF = PERFECT duration for competition
     * 8h hackathon = TYPICAL competition duration
     * Competitions are SHORT, intensive events
   
   - COURSES/TRAINING (8-300h): Mini-courses, workshops, training programs, online courses
     * 20h mini-course = SHORT learning activity
     * 40h course = MEDIUM learning activity
     * 100-200h online course = EXTENDED learning activity
   
   - RESEARCH/EXTENSION PROJECTS (80h+): Semester-long projects, scientific initiation
     * Must have explicit "projeto de pesquisa/extensão" keywords
     * 80h+ research project = MINIMUM for research activities
     * Research projects require MONTHS of work with research methodology
   
   - PRESENTATIONS/LECTURES (1-8h): Single presentations, lectures, seminars
   
   DURATION LOGIC CHECK:
   - If activity = "campeonato/competição" AND duration = 4-8h → DEFINITELY a competition
   - If activity = "curso/capacitação/treinamento" AND duration = ANY → Learning activity (even 200h+)
   - If activity = "projeto de pesquisa" AND has research keywords AND duration 80h+ → Research project
   - Keywords override duration assumptions!
   
3. CONTEXT CLUES:
   - "participou de" = participant, not presenter
   - "ministrou", "apresentou" = presenter/speaker
   - "CAMPEONATO", "CAPTURE THE FLAG" = competition event (4h is NORMAL duration)
   - Academic institutions (IFCE, universidades) host both competitions AND research projects
   - Student centers ("centro acadêmico") organize competitions, courses, and events
   - Being president of academic center does NOT make every activity a research project!

4. CERTIFICATE LANGUAGE PATTERNS:
   - "Certificamos que [nome] participou" = participation activity
   - "Certificamos que [nome] ministrou/apresentou" = presentation activity
   - Check WHO is certifying and WHAT role the person had

INSTRUCTIONS:
1. FIRST read the complete OCR text carefully
2. ANALYZE the structured extracted data (participant, event, location, date, hours) as key reference points
3. Identify the EXACT activity type using the keywords above from BOTH OCR text and extracted event name
4. CRITICALLY VALIDATE duration: Does the extracted hours match the expected duration for this activity type?
   - "CAMPEONATO/COMPETIÇÃO" with 4h = PERFECT for competition (competitions are short!)
   - "CURSO/CAPACITAÇÃO/TREINAMENTO" with ANY duration (even 200h+) = Learning activity
   - "PROJETO DE PESQUISA" needs both research keywords AND 80h+ duration
   - KEYWORDS are MORE IMPORTANT than duration - use keywords first, then validate with duration!
5. Look for ROLE indicators (participant vs presenter) in both OCR text and context
6. Cross-reference the extracted event type and location with available categories
7. Choose the category that matches BOTH the activity type AND realistic duration expectations
8. Use the structured data to confirm and validate your analysis of the raw OCR text

RESPONSE FORMAT (JSON):
{{
    "category_id": <ID of the chosen category>,
    "reasoning": "<Detailed explanation in Portuguese BR: mention the specific keywords found in OCR text, reference the extracted structured data (especially event name and hours), explain the role of the person (participant/presenter), and why this matches the chosen category>"
}}

Respond ONLY with valid JSON, no additional text."""