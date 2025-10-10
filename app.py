from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
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

# Initialize sentence transformer model
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Sentence transformer model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load sentence transformer model: {e}")
    model = None

# Target fields to extract
TARGET_FIELDS = {
    "nome_participante": [
        "nome do participante",
        "participante",
        "nome completo",
        "certificamos que",
        "nome"
    ],
    "evento": [
        "evento",
        "curso",
        "workshop",
        "seminário",
        "palestra",
        "treinamento",
        "capacitação"
    ],
    "local": [
        "local",
        "cidade",
        "endereço",
        "localização",
        "realizado em"
    ],
    "data": [
        "data",
        "período",
        "realizado em",
        "durante",
        "de"
    ],
    "carga_horaria": [
        "carga horária",
        "horas",
        "duração",
        "total de horas",
        "ch"
    ]
}


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


def preprocess_text(text: str) -> str:
    """Clean and preprocess extracted text."""
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    # Remove special characters but keep accents
    text = re.sub(r'[^\w\sÀ-ÿ.,;:()\-]', ' ', text)
    return text.strip()


def find_relevant_text_semantic(text: str, target_phrases: List[str], context_window: int = 50) -> Tuple[str, float]:
    """
    Find the most relevant text segment using semantic similarity.
    Returns the best matching text segment and its similarity score.
    """
    if not model:
        return "", 0.0
    
    try:
        # Split text into smaller chunks for better precision
        words = text.split()
        chunks = []
        
        # Create overlapping windows of text for better context
        window_size = 15  # Smaller window for more precision
        step_size = 5
        
        for i in range(0, len(words), step_size):
            chunk = ' '.join(words[i:i + window_size])
            if len(chunk.strip()) > 10:
                chunks.append(chunk)
        
        # Also try sentence-based splitting
        sentences = re.split(r'[.!?]\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        # Combine both approaches
        all_segments = chunks + sentences
        
        if not all_segments:
            return "", 0.0
        
        # Create embeddings for target phrases
        target_embeddings = model.encode(target_phrases)
        
        # Create embeddings for text segments
        segment_embeddings = model.encode(all_segments)
        
        # Calculate similarities
        similarities = cosine_similarity(segment_embeddings, target_embeddings)
        
        # Find best match
        best_scores = np.max(similarities, axis=1)
        best_segment_idx = np.argmax(best_scores)
        best_score = best_scores[best_segment_idx]
        
        # Get the best matching segment
        best_segment = all_segments[best_segment_idx]
        
        return best_segment, float(best_score)
    
    except Exception as e:
        logger.error(f"Error in semantic text finding: {e}")
        return "", 0.0


def extract_specific_patterns(text: str, field: str) -> Optional[str]:
    """Extract specific patterns based on field type."""
    text_lower = text.lower()
    
    if field == "data":
        # Look for date patterns with more comprehensive regex
        date_patterns = [
            r'\b\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4}\b',  # "10 DE OUTUBRO DE 2019" (uppercase)
            r'\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b',  # "10 de outubro de 2019" (lowercase)
            r'\bDIA\s+\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4}\b',  # "DIA 10 DE OUTUBRO DE 2019"
            r'\bdia\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b',  # "dia 10 de outubro de 2019"
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',             # "10/10/2019"
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',             # "10-10-2019"
            r'\b\d{4}-\d{2}-\d{2}\b',                 # "2019-10-10"
            r'\b\d{1,2}\s+\w+\s+\d{4}\b',            # "10 outubro 2019"
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Clean up the match - remove extra "DIA" if present
                match = matches[0].strip()
                if match.upper().startswith('DIA '):
                    match = match[4:].strip()
                return match
    
    elif field == "carga_horaria":
        # Look for hour patterns with better specificity
        hour_patterns = [
            r'\b(\d+)\s*horas?\s*de\s*carga\s*hor[aá]ria\b',
            r'\bcarga\s*hor[aá]ria[:\s]*(\d+)\s*horas?\b',
            r'\bch[:\s]*(\d+)\s*h?\b',
            r'\b(\d+)\s*h(?:oras?)?\s*$',
            r'\bteve\s+(\d+)\s*horas?\b',
            r'\bduração[:\s]*(\d+)\s*horas?\b',
            r'\btotal[:\s]*(\d+)\s*horas?\b'
        ]
        
        for pattern in hour_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Return the number with "horas"
                return f"{matches[0]} horas"
    
    return None


def extract_field_value(text: str, field: str, target_phrases: List[str]) -> Tuple[str, str, float]:
    """
    Extract specific field value from text using both semantic analysis and patterns.
    Returns: (extracted_value, context_text, confidence_score)
    """
    # First try pattern matching for precise extraction
    pattern_match = extract_specific_patterns(text, field)
    if pattern_match:
        return pattern_match, text, 1.0
    
    # Then use semantic analysis to find relevant context
    context_text, similarity_score = find_relevant_text_semantic(text, target_phrases)
    
    if not context_text:
        return "Não encontrado", "", 0.0
    
    # Try pattern matching on the semantic context
    pattern_match = extract_specific_patterns(context_text, field)
    if pattern_match:
        return pattern_match, context_text, similarity_score
    
    # Field-specific extraction from context
    if field == "nome_participante":
        # Look for name after "certificamos que" or similar phrases
        name_patterns = [
            r'certificamos?\s+que\s+([A-ZÁÊÇÃO\s]+?)(?:\s+participou|\s+concluiu)',
            r'(?:nome|participante)[:\s]+([A-ZÁÊÇÃO\s]+?)(?:\s|$)',
            r'sr\.?\s*([A-ZÁÊÇÃO\s]+?)(?:\s+participou|\s+concluiu)',
            r'sra\.?\s*([A-ZÁÊÇÃO\s]+?)(?:\s+participou|\s+concluiu)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = ' '.join(word.capitalize() for word in name.split())
                return name, context_text, similarity_score
    
    elif field == "evento":
        # Look for event names in context
        event_patterns = [
            r'(?:workshop|curso|seminário|palestra|treinamento|capacitação)[:\s\-]*([^.!?]+?)(?:\s+durante|\s+realizado|\s+no)',
            r'participou\s+do\s+([^.!?]+?)(?:\s+durante|\s+realizado)',
            r'(?:do|da)\s+(workshop|curso|seminário|palestra|treinamento|capacitação)\s+([^.!?]+?)(?:\s+durante|\s+realizado)'
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    event = f"{match.group(1)} {match.group(2)}".strip()
                else:
                    event = match.group(1).strip()
                return event, context_text, similarity_score
    
    elif field == "data":
        # Look for date information with specific patterns
        date_patterns = [
            r'(?:NO\s+DIA|no\s+dia|dia)\s+(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})',
            r'(?:EM|em)\s+(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})',
            r'(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(?:realizado|realizada)\s+(?:em|no\s+dia)\s+([^.!?]+?)(?:\s|$)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Clean up and format the date
                if 'DE' in date_str.upper():
                    return date_str.upper()
                return date_str
    
    elif field == "local":
        # Look for location information
        location_patterns = [
            r'(?:realizado|realizada)\s+(?:no|na|pelo|pela)\s+([^.!?]+?)(?:\s+no\s+dia|\s+em)',
            r'(?:campus|instituto|universidade|faculdade)\s+(?:de|do|da)\s+([^.!?]+?)(?:\s+do|\s+no)',
            r'(?:cidade|local)[:\s]+([^.!?]+?)(?:\s|$)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, context_text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                return location, context_text, similarity_score
    
    # If no specific extraction worked, return the most relevant part of context
    words = context_text.split()
    if len(words) > 15:
        # Return a smaller, more relevant excerpt
        return ' '.join(words[:15]) + "...", context_text, similarity_score
    
def extract_certificate_info(text: str) -> Dict[str, any]:
    """Extract certificate information from text using semantic analysis."""
    results = {}
    
    processed_text = preprocess_text(text)
    
    for field, target_phrases in TARGET_FIELDS.items():
        try:
            # Use the new improved extraction function
            extracted_value, context_text, confidence_score = extract_field_value(
                processed_text, field, target_phrases
            )
            
            # Also try pattern matching on full text for backup
            pattern_match = extract_specific_patterns(processed_text, field)
            
            # Choose the best result
            final_value = pattern_match if pattern_match else extracted_value
            
            results[field] = {
                "extracted_text": context_text if context_text else "Não encontrado",
                "confidence_score": confidence_score,
                "pattern_match": pattern_match,
                "value": final_value
            }
            
        except Exception as e:
            logger.error(f"Error extracting {field}: {e}")
            results[field] = {
                "extracted_text": "Erro na extração",
                "confidence_score": 0.0,
                "pattern_match": None,
                "value": "Erro na extração"
            }
    
    return results


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "tesseract_available": True
    })


@app.route('/extract-certificate', methods=['POST'])
def extract_certificate():
    """
    Extract information from certificate documents.
    Accepts PDF, PNG, JPEG, and other image formats.
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed types: {ALLOWED_EXTENSIONS}'
            }), 400
        
        # Read file content
        file_content = file.read()
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        logger.info(f"Processing file: {filename} ({len(file_content)} bytes)")
        
        # Process based on file type
        extracted_text = ""
        
        if file_extension == 'pdf':
            # Convert PDF to images and extract text from each page
            images = convert_pdf_to_images(file_content)
            texts = []
            for i, image in enumerate(images):
                text = extract_text_from_image(image)
                texts.append(text)
                logger.info(f"Extracted text from page {i+1}: {len(text)} characters")
            extracted_text = ' '.join(texts)
        
        else:
            # Handle image files
            image = Image.open(file.stream)
            extracted_text = extract_text_from_image(image)
        
        if not extracted_text.strip():
            return jsonify({'error': 'No text could be extracted from the document'}), 400
        
        logger.info(f"Total extracted text: {len(extracted_text)} characters")
        
        # Extract certificate information
        certificate_info = extract_certificate_info(extracted_text)
        
        # Prepare response
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
