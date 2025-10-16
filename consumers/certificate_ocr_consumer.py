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
                # Extract metadata using LLM
                metadata_result = self.llm_service.extract_fields(raw_text)
                
                # Save metadata to database (map Portuguese LLM response to English DB fields)
                metadata = self.metadata_repository.create_metadata(
                    session=session,
                    submission_id=submission_id,
                    participant_name=metadata_result.get('nome_participante'),  # nome_participante -> participant_name
                    event_name=metadata_result.get('evento'),  # evento -> event_name
                    location=metadata_result.get('local'),  # local -> location
                    event_date=metadata_result.get('data'),  # data -> event_date
                    original_hours=metadata_result.get('carga_horaria'),  # carga_horaria -> original_hours
                    numeric_hours=self._extract_numeric_hours(metadata_result.get('carga_horaria')),  # extract numeric value
                    extraction_method='llm'
                )
                
                # Publish to metadata topic
                self.kafka_service.publish_certificate_metadata(
                    submission_id=submission_id,
                    metadata_id=metadata.id,
                    extracted_data=metadata_result
                )
                
                logger.info(f"Metadata extraction completed for submission {submission_id}")
                
            except Exception as e:
                logger.error(f"Error extracting metadata for submission {submission_id}: {e}")
                self.submission_repository.update_status(
                    session, submission_id, 'failed', str(e)
                )