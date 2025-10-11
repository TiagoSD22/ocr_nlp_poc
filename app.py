from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import numpy as np
import requests
import json
import os
import tempfile
import logging
from typing import Dict, List, Tuple, Optional
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

# Ollama configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:1b')  # Default to small model

# Test Ollama connectivity
def test_ollama_connection():
    """Test if Ollama is available."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}")
        return False

def ensure_model_available():
    """Ensure the required model is available, download if not."""
    try:
        # Check if model is already available
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model.get('name', '') for model in models]
            
            if OLLAMA_MODEL in model_names:
                logger.info(f"Model {OLLAMA_MODEL} is already available")
                return True
            
            # Model not found, try to pull it
            logger.info(f"Model {OLLAMA_MODEL} not found, attempting to pull...")
            pull_response = requests.post(
                f"{OLLAMA_BASE_URL}/api/pull",
                json={"name": OLLAMA_MODEL},
                timeout=300  # 5 minutes timeout for model download
            )
            
            if pull_response.status_code == 200:
                logger.info(f"Successfully pulled model {OLLAMA_MODEL}")
                return True
            else:
                logger.error(f"Failed to pull model {OLLAMA_MODEL}: {pull_response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error ensuring model availability: {e}")
        return False


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    """Convert PDF bytes to list of PIL Images."""
    try:
        images = convert_from_bytes(pdf_bytes)
        logger.info(f"Converted PDF to {len(images)} images")
        return images
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        raise


def extract_text_from_image(image: Image.Image) -> str:
    """Extract text from PIL Image using Tesseract OCR."""
    try:
        # Configure Tesseract for better accuracy
        custom_config = r'--oem 3 --psm 6 -l por+eng'
        text = pytesseract.image_to_string(image, config=custom_config)
        logger.info(f"Extracted {len(text)} characters from image")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}")
        raise


def extract_fields_with_llm(text: str) -> Dict[str, any]:
    prompt = f"""You are an intelligent document parser specialized in Brazilian Portuguese certificates. 

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

    try:
        if not test_ollama_connection():
            logger.error("Ollama not available - cannot extract fields")
            return {
                'nome_participante': None,
                'evento': None,
                'local': None,
                'data': None,
                'carga_horaria': None
            }
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.9
            }
        }
        
        logger.info(f"Sending request to Ollama with model: {OLLAMA_MODEL}")
        logger.info(f"Prompt full text: {prompt}")
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=90
        )
        
        logger.info(f"Ollama response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            llm_response = result.get('response', '').strip()
            
            logger.info(f"LLM raw response: {llm_response[:200]}...")
            
            # Try to parse JSON response
            try:
                # First, try to parse as JSON
                if '{' in llm_response and '}' in llm_response:
                    start = llm_response.find('{')
                    end = llm_response.rfind('}') + 1
                    json_str = llm_response[start:end]
                    
                    logger.info(f"Extracted JSON string: {json_str}")
                    
                    extracted_data = json.loads(json_str)
                    
                    # Validate required fields exist
                    required_fields = ['nome_participante', 'evento', 'local', 'data', 'carga_horaria']
                    for field in required_fields:
                        if field not in extracted_data:
                            extracted_data[field] = None
                    
                    logger.info("Successfully extracted fields using LLM (JSON format)")
                    return extracted_data
                
                else:
                    logger.error("No valid JSON found in LLM response")
                    logger.error(f"Full LLM response: {llm_response}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.error(f"LLM response was: {llm_response}")
            except Exception as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"LLM response was: {llm_response}")
        else:
            logger.error(f"Ollama API error: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            
        # Return empty structure on any error
        return {
            'nome_participante': None,
            'evento': None,
            'local': None,
            'data': None,
            'carga_horaria': None
        }
            
    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        return {
            'nome_participante': None,
            'evento': None,
            'local': None,
            'data': None,
            'carga_horaria': None
        }


def extract_certificate_info(text: str) -> Dict[str, any]:
    """Extract certificate information from text using LLM."""
    try:
        # Use LLM-based extraction with built-in text cleaning
        extracted_fields = extract_fields_with_llm(text)
        
        # Format the response to match the expected API structure
        results = {}
        extraction_method = "llm"
        
        for field_name, value in extracted_fields.items():
            results[field_name] = {
                "value": value,
                "extraction_method": extraction_method
            }
        
        return results
        
    except Exception as e:
        logger.error(f"Error in certificate extraction: {e}")
        # Return empty structure on error
        return {
            field: {
                "value": None,
                "extraction_method": "error"
            } for field in ['nome_participante', 'evento', 'local', 'data', 'carga_horaria']
        }


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Check Ollama and model availability in real time
    ollama_status = test_ollama_connection()
    model_status = False
    
    if ollama_status:
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name', '') for model in models]
                model_status = OLLAMA_MODEL in model_names
        except:
            pass
    
    return jsonify({
        "status": "healthy",
        "ollama_available": ollama_status,
        "ollama_model": OLLAMA_MODEL,
        "model_downloaded": model_status,
        "tesseract_available": True
    })


@app.route('/extract-certificate', methods=['POST'])
def extract_certificate():
    """
    Extract information from certificate documents.
    Accepts PDF, PNG, JPEG, and other image formats.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed types: {ALLOWED_EXTENSIONS}'
            }), 400
        
        file_content = file.read()
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        logger.info(f"Processing file: {filename} ({len(file_content)} bytes)")
        
        extracted_text = ""
        
        if file_extension == 'pdf':
            images = convert_pdf_to_images(file_content)
            texts = []
            for i, image in enumerate(images):
                text = extract_text_from_image(image)
                texts.append(text)
                logger.info(f"Extracted text from page {i+1}: {len(text)} characters")
            extracted_text = ' '.join(texts)
        
        else:
            image = Image.open(file.stream)
            extracted_text = extract_text_from_image(image)
        
        if not extracted_text.strip():
            return jsonify({'error': 'No text could be extracted from the document'}), 400
        
        logger.info(f"Total extracted text: {len(extracted_text)} characters")
        
        certificate_info = extract_certificate_info(extracted_text)
        
        response = {
            "success": True,
            "filename": filename,
            "extracted_fields": certificate_info,
            "raw_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
            "text_length": len(extracted_text)
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing certificate: {e}")
        return jsonify({
            'error': f'Error processing document: {str(e)}'
        }), 500


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413


@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
