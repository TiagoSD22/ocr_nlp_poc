"""
Certificate Metadata Consumer for processing metadata and categorizing activities.
"""
import json
import logging
from typing import Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from injector import inject

from database.connection import get_db_session
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from services.activity_categorization_service import ActivityCategorizationService
import config.settings as settings

logger = logging.getLogger(__name__)


class CertificateMetadataConsumer:
    """Consumer for certificate.metadata topic - processes metadata for categorization."""
    
    @inject
    def __init__(
        self, 
        activity_categorization_service: ActivityCategorizationService,
        submission_repository: CertificateSubmissionRepository
    ):
        """Initialize metadata consumer."""
        self.activity_categorization_service = activity_categorization_service
        self.submission_repository = submission_repository
        self.consumer = None
        
        self._init_consumer()
    
    def _init_consumer(self) -> None:
        """Initialize Kafka consumer."""
        try:
            self.consumer = KafkaConsumer(
                'certificate.metadata',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                group_id='certificate-metadata-group',
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info("Certificate metadata consumer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize metadata consumer: {e}")
            self.consumer = None
    
    def process_messages(self) -> None:
        """Process messages from certificate.metadata topic."""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
        
        logger.info("Starting certificate metadata message processing...")
        
        try:
            for message in self.consumer:
                try:
                    self._process_metadata_message(message.value)
                except Exception as e:
                    logger.error(f"Error processing metadata message: {e}")
        except KeyboardInterrupt:
            logger.info("Stopping metadata consumer...")
        except Exception as e:
            logger.error(f"Error in metadata consumer: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
    
    def _process_metadata_message(self, message: Dict[str, Any]) -> None:
        """Process a single metadata message."""
        submission_id = message['submission_id']
        extracted_data = message['extracted_data']
        
        logger.info(f"Processing categorization for submission {submission_id}")
        
        with get_db_session() as session:
            # Update submission status
            submission = self.submission_repository.get_by_id(
                session, submission_id
            )
            
            if not submission:
                logger.error(f"Submission {submission_id} not found")
                return
            
            self.submission_repository.update_status(
                session, submission_id, 'categorization_processing'
            )
            
            try:
                # Get raw OCR text from submission's OCR text (1:1 relationship)
                raw_text = ""
                if submission.ocr_text:
                    raw_text = submission.ocr_text.raw_text or ""
                
                # Add raw OCR text to extracted data for categorization service
                extracted_data['raw_text'] = raw_text
                
                # Use activity categorization service to categorize and persist
                categorization_result = self.activity_categorization_service.categorize_activity(
                    extracted_data, submission_id
                )
                
                if categorization_result.get('success', False):
                    # Update submission status to pending review (waiting for coordinator approval)
                    self.submission_repository.update_status(
                        session, submission_id, 'pending_review', update_processing_completed=True
                    )
                    logger.info(f"Categorization completed for submission {submission_id}")
                else:
                    # Categorization failed
                    error_message = categorization_result.get('error', 'Unknown categorization error')
                    logger.error(f"Categorization failed for submission {submission_id}: {error_message}")
                    self.submission_repository.update_status(
                        session, submission_id, 'failed', error_message, update_processing_completed=True
                    )
                
            except Exception as e:
                logger.error(f"Error categorizing submission {submission_id}: {e}")
                self.submission_repository.update_status(
                    session, submission_id, 'failed', str(e)
                )