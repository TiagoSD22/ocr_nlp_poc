# Certificate Document Processing API

A Flask-based REST API that processes certificate documents using OCR (Optical Character Recognition) and LLM (Large Language Model) analysis to extract structured information.

## 🎯 What It Does

The application processes certificate documents (PDF, PNG, JPEG, etc.) through a complete pipeline:

1. **OCR Text Extraction** - Uses Tesseract to extract raw text from documents
2. **Text Preprocessing** - Cleans and enhances OCR output 
3. **LLM Analysis** - Uses Ollama with local language models for intelligent field extraction
4. **Structured Output** - Returns organized JSON data with extracted fields

**Extracted Fields:**
- `nome_participante` - Participant's full name
- `evento` - Event/course name
- `local` - Location/institution
- `data` - Event date
- `carga_horaria` - Duration/workload hours

## 🏗️ Architecture

- **Framework**: Flask with dependency injection (Flask-Injector)
- **OCR Engine**: Tesseract with Portuguese + English support
- **LLM Integration**: Ollama for local language model processing
- **Deployment**: Docker Compose with multi-container setup
- **API Design**: RESTful with versioned endpoints (`/api/v1/`)

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM (for LLM models)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd ocr
```

### 2. Configure Model (Optional)
```bash
# Edit .env file to choose your preferred model
echo "OLLAMA_MODEL=llama3.2:1b" > .env

# Available models:
# - llama3.2:1b  (~1.3GB, fastest)
# - phi3:mini    (~2.3GB, good accuracy)
# - llama3.2:3b  (~2.0GB, balanced)
```

### 3. Start Services
```bash
# Start all services (Flask + Ollama)
docker-compose up -d

# Monitor model download (first run only)
docker-compose logs -f ollama
```

### 4. Test the API
```bash
# Health check
curl http://localhost:5000/api/v1/health

# Process a certificate
curl -X POST \
  -F "file=@certificate.pdf" \
  http://localhost:5000/api/v1/certificate/process
```

## 📚 API Reference

### Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "api_version": "v1",
  "ollama_available": true,
  "ollama_model": "llama3.2:1b",
  "model_downloaded": true,
  "tesseract_available": true
}
```

### Process Certificate Document
```http
POST /api/v1/certificate/process
Content-Type: multipart/form-data
```

**Parameters:**
- `file` - Certificate file (PDF, PNG, JPEG, TIFF, BMP)

**Success Response:**
```json
{
  "success": true,
  "filename": "certificate.pdf",
  "extracted_fields": {
    "nome_participante": "João Silva",
    "evento": "Python Advanced Course",
    "local": "São Paulo, SP",
    "data": "March 15, 2024",
    "carga_horaria": "40 hours"
  },
  "raw_text": "Complete extracted text...",
  "text_length": 1250
}
```

## 🔧 Development

### Local Development (Without Docker)

1. **Install Ollama**
   ```bash
   # Download from https://ollama.ai/
   # Pull a model
   ollama pull llama3.2:1b
   ollama serve
   ```

2. **Setup Python Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate   # Windows
   
   pip install -r requirements.txt
   ```

3. **Install System Dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-por poppler-utils
   
   # macOS
   brew install tesseract tesseract-lang poppler
   ```

4. **Run Application**
   ```bash
   python main.py
   ```

### Project Structure
```
├── main.py                 # Application entry point
├── config/
│   ├── settings.py        # Configuration variables
│   ├── injection.py       # Dependency injection setup
│   └── prompts.py         # LLM prompt templates
├── services/
│   ├── ocr_service.py     # OCR text extraction
│   ├── llm_service.py     # Ollama LLM integration
│   ├── certificate_service.py  # Certificate processing logic
│   └── prompt_service.py  # Prompt template management
├── routes/
│   ├── health.py          # Health check endpoints
│   └── certificate.py     # Certificate processing endpoints
├── docker-compose.yml     # Multi-container setup
├── Dockerfile             # Flask application container
└── requirements.txt       # Python dependencies
```

## 🐳 Docker Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Flask App     │◄──►│     Ollama      │
│   (port 5000)   │    │   (port 11434)  │
│                 │    │                 │
│ OCR + API       │    │ LLM Processing  │
│ Certificate     │    │ Model Storage   │
│ Processing      │    │                 │
└─────────────────┘    └─────────────────┘
         │                        │
         └──────── Internal Network ────────┘
```

**Containers:**
- `ocr-flask-app` - Flask API with Tesseract OCR
- `ocr-ollama` - Ollama LLM server with model storage

## 🛠️ Technology Stack

- **Backend**: Python 3.11 + Flask
- **Dependency Injection**: Flask-Injector
- **OCR**: Tesseract with image preprocessing (PIL/Pillow)
- **PDF Processing**: pdf2image + poppler-utils
- **LLM**: Ollama (local inference)
- **Containerization**: Docker + Docker Compose
- **HTTP Client**: requests library
- **Logging**: Python logging module

## 📝 Configuration

Environment variables (optional):
```bash
# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_TIMEOUT=90
OLLAMA_CONNECTION_TIMEOUT=5

# Flask settings  
DEBUG=false
HOST=0.0.0.0
PORT=5000

# Image processing
CONTRAST_FACTOR=1.5
SHARPNESS_FACTOR=2.0
```

## 🧪 Testing

Use the included Bruno API collection in `API/OCR Service/` for testing endpoints, or use curl/Postman with the examples above.

## 📋 Requirements

- **RAM**: 8GB+ (for LLM models)
- **Storage**: 5GB+ (for models and dependencies)
- **CPU**: Multi-core recommended for better performance
- **OS**: Linux, macOS, or Windows with WSL2