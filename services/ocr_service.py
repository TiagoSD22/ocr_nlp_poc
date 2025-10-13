"""
OCR Service for text extraction from images and PDFs.
"""
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import logging
from typing import List

import config.settings as settings

logger = logging.getLogger(__name__)


class OCRService:
    """Service for handling OCR operations."""
    
    def __init__(self):
        self.tesseract_config = settings.TESSERACT_CONFIG
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from PIL Image using Tesseract OCR."""
        try:
            text = pytesseract.image_to_string(image, config=self.tesseract_config)
            logger.info(f"Extracted {len(text)} characters from image")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            raise
    
    def convert_pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Convert PDF bytes to list of PIL Images."""
        try:
            images = convert_from_bytes(pdf_bytes)
            logger.info(f"Converted PDF to {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF by converting to images first."""
        try:
            images = self.convert_pdf_to_images(pdf_bytes)
            texts = []
            
            for i, image in enumerate(images):
                text = self.extract_text_from_image(image)
                texts.append(text)
                logger.info(f"Extracted text from page {i+1}: {len(text)} characters")
            
            extracted_text = ' '.join(texts)
            logger.info(f"Total extracted text: {len(extracted_text)} characters")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def process_file(self, file_content: bytes, file_extension: str) -> str:
        """Process file and extract text based on file type."""
        try:
            if file_extension.lower() == 'pdf':
                return self.extract_text_from_pdf(file_content)
            else:
                # Handle image files
                from io import BytesIO
                image = Image.open(BytesIO(file_content))
                return self.extract_text_from_image(image)
                
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            raise