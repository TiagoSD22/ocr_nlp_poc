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
- nome_participante: Full name of the certificate recipient (NOT the instructor/presenter)
- evento: Name of the event/course/workshop/training
- local: Location, city, or institution where event took place. If no physical location is found and there are digital validation indicators (URLs, online platform names), use "online"
- data: Date when event occurred (keep original format)
- carga_horaria: Duration or workload hours

PARTICIPANT IDENTIFICATION RULES:
- Look for INSTRUCTOR/PRESENTER keywords: "Instrutores", "Instrutor", "Professor", "Palestrante", "Ministrado por", "Apresentado por"
- Names that appear AFTER these keywords are instructors/presenters, NOT participants
- The participant is usually the certificate recipient, often implied or mentioned before instructor information
- For digital certificates without explicit participant naming, the participant name may need to be inferred from context
- If multiple names appear and some are clearly marked as instructors, exclude instructor names from participant field
- When in doubt about participant identity, use null rather than including instructor names

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

1. DIGITAL PLATFORM RECOGNITION - PRIORITY CHECK:
   - Look for DIGITAL VALIDATION indicators: "URL do certificado", "Número de referência", certificate URLs (ude.my, udemy, coursera, etc.)
   - Check for ONLINE PLATFORM names: "Udemy", "Coursera", "edX", "Khan Academy", "Alura", "Rocketseat", etc.
   - When digital validation is present: participant is ALWAYS a STUDENT/LEARNER, not an instructor
   - Instructor names listed are the COURSE CREATORS, not the certificate recipient
   - For online courses: if no physical location is mentioned, set location as "online"

2. SUBJECT AREA CLASSIFICATION - COMPUTER ENGINEERING RELEVANCE:
   - WITHIN Computer Engineering area: Programming languages (Python, Java, C++, Rust, JavaScript, etc.), Software Development, Web Development, Mobile Development, Database Management, Distributed Systems, Cloud Computing, DevOps, Software Architecture, Data Structures, Algorithms, Machine Learning, Artificial Intelligence, Cybersecurity, Networks, Operating Systems, System Administration, Software Testing, API Development, Microservices, Docker, Kubernetes, Git/Version Control
   - OUTSIDE Computer Engineering area: Business Management, Marketing, Design (unless UI/UX), Languages (unless programming), Finance, Law, Medicine, Arts, Sports, etc.
   - When in doubt about technical topics, classify as WITHIN the area - Computer Engineering is broad and interdisciplinary

3. ACTIVITY TYPE KEYWORDS - Pay attention to these specific terms (KEYWORDS OVERRIDE DURATION):
   - PARTICIPATION/LEARNING activities: "curso", "minicurso", "workshop", "treinamento", "capacitação", "participou", "participação", "certificação", "conclusão"
   - PRESENTATION/SPEAKING activities: "palestra", "palestrante", "apresentação", "apresentou", "ministrou", "ministrando" (BUT check for digital validation first!)
   - ORGANIZATION activities: "organizou", "organizador", "coordenou", "coordenador", "organizaçào"
   - COMPETITION activities: "competição", "concurso", "hackathon", "maratona", "olimpíada", "campeonato", "capture the flag", "CTF"
   - RESEARCH/EXTENSION projects: "projeto de pesquisa", "projeto de extensão", "iniciação científica", "bolsista", "pesquisador", "orientador"
   
4. DURATION ANALYSIS - CRITICAL MATCHING RULES:
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
   
5. CONTEXT CLUES:
   - "participou de" = participant, not presenter
   - "ministrou", "apresentou" = presenter/speaker (UNLESS it's a digital platform course where this refers to instructors)
   - "CAMPEONATO", "CAPTURE THE FLAG" = competition event (4h is NORMAL duration)
   - Academic institutions (IFCE, universidades) host both competitions AND research projects
   - Student centers ("centro acadêmico") organize competitions, courses, and events
   - Being president of academic center does NOT make every activity a research project!
   - DIGITAL PLATFORMS: Certificate recipients are always participants/students, never instructors
   - When certificate shows instructor names, they are course creators, not the person receiving the certificate

6. CERTIFICATE LANGUAGE PATTERNS:
   - "Certificamos que [nome] participou" = participation activity
   - "Certificamos que [nome] ministrou/apresentou" = presentation activity (check for digital validation first!)
   - "CERTIFICADO DE CONCLUSÃO" + URL/digital validation = online course completion (participant role)
   - Check WHO is certifying and WHAT role the person had
   - Digital platforms always certify COMPLETION/PARTICIPATION, not instruction

INSTRUCTIONS:
1. FIRST check for DIGITAL VALIDATION indicators (URLs, certificate numbers, platform names)
2. If digital validation is present, treat as online course participation regardless of instructor names mentioned
3. Read the complete OCR text carefully
4. ANALYZE the structured extracted data (participant, event, location, date, hours) as key reference points
5. DETERMINE subject area relevance: Is this activity related to Computer Engineering topics? (programming, software, databases, etc.)
6. Identify the EXACT activity type using the keywords above from BOTH OCR text and extracted event name
7. CRITICALLY VALIDATE duration: Does the extracted hours match the expected duration for this activity type?
   - "CAMPEONATO/COMPETIÇÃO" with 4h = PERFECT for competition (competitions are short!)
   - "CURSO/CAPACITAÇÃO/TREINAMENTO" with ANY duration (even 200h+) = Learning activity
   - "PROJETO DE PESQUISA" needs both research keywords AND 80h+ duration
   - KEYWORDS are MORE IMPORTANT than duration - use keywords first, then validate with duration!
8. Look for ROLE indicators (participant vs presenter) in both OCR text and context
   - For digital platforms: certificate recipient is ALWAYS a participant/student
   - Instructor names are course creators, not the certificate recipient
9. Cross-reference the extracted event type and location with available categories
10. For location: if online course with no physical location mentioned, use "online"
11. Choose the category that matches BOTH the activity type, subject area relevance, AND realistic duration expectations
12. Use the structured data to confirm and validate your analysis of the raw OCR text

RESPONSE FORMAT (JSON):
{{
    "category_id": <ID of the chosen category>,
    "reasoning": "<Detailed explanation in Portuguese BR: mention the specific keywords found in OCR text, reference the extracted structured data (especially event name and hours), explain the role of the person (participant/presenter), analyze the subject area relevance to Computer Engineering, and why this matches the chosen category>"
}}

Respond ONLY with valid JSON, no additional text."""