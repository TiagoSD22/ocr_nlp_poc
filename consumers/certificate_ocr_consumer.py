"""
Certificate OCR Consumer for processing OCR results and extracting metadata.
"""
import json
import logging
from typing import Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from injector import inject

from database.connection import get_db_session
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from repositories.certificate_metadata_repository import CertificateMetadataRepository
from services.llm_service import LLMService
from services.kafka_service import KafkaService
import config.settings as settings

logger = logging.getLogger(__name__)


class CertificateOCRConsumer:
    """Consumer for certificate.ocr topic - processes OCR results."""
    
    @inject
    def __init__(
        self, 
        llm_service: LLMService,
        kafka_service: KafkaService,
        submission_repository: CertificateSubmissionRepository,
        metadata_repository: CertificateMetadataRepository
    ):
        """Initialize OCR consumer."""
        self.llm_service = llm_service
        self.kafka_service = kafka_service
        self.submission_repository = submission_repository
        self.metadata_repository = metadata_repository
        self.consumer = None
        
        self._init_consumer()
    
    def _init_consumer(self) -> None:
        """Initialize Kafka consumer."""
        try:
            self.consumer = KafkaConsumer(
                'certificate.ocr',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                group_id='certificate-ocr-group',
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info("Certificate OCR consumer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OCR consumer: {e}")
            self.consumer = None
    
    def process_messages(self) -> None:
        """Process messages from certificate.ocr topic."""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
        
        logger.info("Starting certificate OCR message processing...")
        
        try:
            for message in self.consumer:
                try:
                    self._process_ocr_message(message.value)
                except Exception as e:
                    logger.error(f"Error processing OCR message: {e}")
        except KeyboardInterrupt:
            logger.info("Stopping OCR consumer...")
        except Exception as e:
            logger.error(f"Error in OCR consumer: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
    
    def _extract_numeric_hours(self, hours_text: str) -> int:
        """Extract numeric hours from text like '40 horas' or '40h'."""
        if not hours_text:
            return None
        
        import re
        # Look for numbers in the text
        numbers = re.findall(r'\d+', str(hours_text))
        if numbers:
            return int(numbers[0])
        return None
    
    def _validate_participant_name(self, extracted_participant: str, student_name: str) -> bool:
        """
        Validate that the extracted participant name matches the student who submitted the document.
        
        Args:
            extracted_participant: Name extracted from certificate by LLM
            student_name: Name of student who submitted the document
            
        Returns:
            True if names match (with fuzzy matching), False otherwise
        """
        if not extracted_participant or not student_name:
            logger.warning("Missing participant name or student name for validation")
            return False
        
        # Normalize names for comparison
        def normalize_name(name):
            import re
            # Convert to lowercase, remove extra spaces, and common name variations
            normalized = re.sub(r'[^\w\s]', '', name.lower())  # Remove punctuation
            normalized = re.sub(r'\s+', ' ', normalized).strip()  # Normalize spaces
            return normalized
        
        extracted_normalized = normalize_name(extracted_participant)
        student_normalized = normalize_name(student_name)
        
        # Exact match after normalization
        if extracted_normalized == student_normalized:
            return True
        
        # Check if one name is contained within the other (handles full name vs. partial name)
        # For example: "João Silva" vs "João da Silva Santos"
        extracted_parts = set(extracted_normalized.split())
        student_parts = set(student_normalized.split())
        
        # Calculate intersection of name parts
        common_parts = extracted_parts.intersection(student_parts)
        
        # Require at least 2 matching parts for common Brazilian names (first + last name)
        if len(common_parts) >= 2:
            return True
        
        # If only one part matches, check if it's substantial (more than 3 characters)
        if len(common_parts) == 1:
            matching_part = list(common_parts)[0]
            if len(matching_part) > 3:  # Substantial name part
                return True
        
        # Log the validation failure for debugging
        logger.info(f"Name validation failed: extracted='{extracted_participant}' vs student='{student_name}'")
        return False
    
    def _process_ocr_message(self, message: Dict[str, Any]) -> None:
        """Process a single OCR message."""
        submission_id = message['submission_id']
        ocr_text_id = message['ocr_text_id']
        raw_text = message['raw_text']
        
        logger.info(f"Processing metadata extraction for submission {submission_id}")
        
        with get_db_session() as session:
            # Update submission status
            submission = self.submission_repository.get_by_id(
                session, submission_id
            )
            
            if not submission:
                logger.error(f"Submission {submission_id} not found")
                return
            
            self.submission_repository.update_status(
                session, submission_id, 'metadata_processing'
            )
            
            try:
                # Extract metadata using LLM with timing
                import time
                start_time = time.time()
                metadata_result = self.llm_service.extract_fields(raw_text)
                end_time = time.time()
                processing_time_ms = int((end_time - start_time) * 1000)
                
                # Always save metadata to database for audit purposes (map Portuguese LLM response to English DB fields)
                metadata = self.metadata_repository.create_metadata(
                    session=session,
                    submission_id=submission_id,
                    participant_name=metadata_result.get('nome_participante'),  # nome_participante -> participant_name
                    event_name=metadata_result.get('evento'),  # evento -> event_name
                    location=metadata_result.get('local'),  # local -> location
                    event_date=metadata_result.get('data'),  # data -> event_date
                    original_hours=metadata_result.get('carga_horaria'),  # carga_horaria -> original_hours
                    numeric_hours=self._extract_numeric_hours(metadata_result.get('carga_horaria')),  # extract numeric value
                    processing_time_ms=processing_time_ms
                )
                
                # Validate participant name matches student who submitted the document
                extracted_participant = metadata_result.get('nome_participante', '').strip()
                student_name = submission.student.name.strip() if submission.student else ''
                
                if not self._validate_participant_name(extracted_participant, student_name):
                    error_msg = f"Certificate participant '{extracted_participant}' does not match student '{student_name}' who submitted the file"
                    logger.warning(f"Validation failed for submission {submission_id}: {error_msg}")
                    logger.info(f"Metadata saved for audit (ID: {metadata.id}) despite validation failure")
                    self.submission_repository.update_status(
                        session, submission_id, 'failed', error_msg, update_processing_completed=True
                    )
                    return
                
                # Validation passed - publish to metadata topic for further processing
                self.kafka_service.publish_certificate_metadata(
                    submission_id=submission_id,
                    metadata_id=metadata.id,
                    extracted_data=metadata_result
                )
                
                logger.info(f"Metadata extraction and validation completed for submission {submission_id}")
                
            except Exception as e:
                logger.error(f"Error extracting metadata for submission {submission_id}: {e}")
                self.submission_repository.update_status(
                    session, submission_id, 'failed', str(e), update_processing_completed=True
                )