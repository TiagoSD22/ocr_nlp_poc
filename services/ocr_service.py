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
    def extract_text(self, submission):
        """Download file from S3 and extract text for the given submission."""
        # TODO: Implement S3 download and OCR extraction logic
        # Example:
        # file_bytes = S3Service().download_file(submission.s3_key)
        # text = self.process_file(file_bytes, submission.original_filename.split('.')[-1])
        # return text
        pass

    def extract_metadata(self, submission):
        """Extract metadata from the given submission's file."""
        # TODO: Implement metadata extraction logic
        pass
    """Service for handling OCR operations."""
    
    def __init__(self):
        self.tesseract_config = settings.TESSERACT_CONFIG
    
    def extract_text_from_image(self, image: Image.Image) -> tuple[str, float]:
        """Extract text from PIL Image using Tesseract OCR with confidence score."""
        try:
            # Use image_to_data to get confidence information
            data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate confidence
            text_parts = []
            confidences = []
            
            for i, word in enumerate(data['text']):
                if word.strip():  # Only process non-empty words
                    text_parts.append(word)
                    confidence = data['conf'][i]
                    if confidence > 0:  # Valid confidence score
                        confidences.append(confidence)
            
            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            logger.info(f"Extracted {len(text)} characters from image with {avg_confidence:.2f}% confidence")
            return text, avg_confidence
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
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> tuple[str, float]:
        """Extract text from PDF by converting to images first."""
        try:
            images = self.convert_pdf_to_images(pdf_bytes)
            texts = []
            confidences = []
            
            for i, image in enumerate(images):
                text, confidence = self.extract_text_from_image(image)
                texts.append(text)
                confidences.append(confidence)
                logger.info(f"Extracted text from page {i+1}: {len(text)} characters with {confidence:.2f}% confidence")
            
            extracted_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            logger.info(f"Total extracted text: {len(extracted_text)} characters with {avg_confidence:.2f}% confidence")
            return extracted_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def process_file(self, file_content: bytes, file_extension: str) -> tuple[str, float]:
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