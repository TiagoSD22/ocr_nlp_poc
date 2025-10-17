"""
Certificate Ingest Consumer for processing uploaded certificate files.
"""
import json
import logging
from typing import Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from injector import inject

from database.connection import get_db_session
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from repositories.certificate_ocr_text_repository import CertificateOcrTextRepository
from services.ocr_service import OCRService
from services.s3_service import S3Service
from services.kafka_service import KafkaService
import config.settings as settings

logger = logging.getLogger(__name__)


class CertificateIngestConsumer:
    """Consumer for certificate.ingest topic - processes uploaded files."""
    
    @inject
    def __init__(
        self, 
        ocr_service: OCRService,
        s3_service: S3Service,
        kafka_service: KafkaService,
        submission_repository: CertificateSubmissionRepository,
        ocr_text_repository: CertificateOcrTextRepository
    ):
        """Initialize ingest consumer."""
        self.ocr_service = ocr_service
        self.s3_service = s3_service
        self.kafka_service = kafka_service
        self.submission_repository = submission_repository
        self.ocr_text_repository = ocr_text_repository
        self.consumer = None
        self._init_consumer()
    
    def _init_consumer(self) -> None:
        """Initialize Kafka consumer."""
        try:
            self.consumer = KafkaConsumer(
                'certificate.ingest',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                group_id='certificate-ingest-group',
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info("Certificate ingest consumer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ingest consumer: {e}")
            self.consumer = None
    
    def process_messages(self) -> None:
        """Process messages from certificate.ingest topic."""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
        
        logger.info("Starting certificate ingest message processing...")
        
        try:
            for message in self.consumer:
                try:
                    self._process_ingest_message(message.value)
                except Exception as e:
                    logger.error(f"Error processing ingest message: {e}")
                    # Continue processing other messages
        except KeyboardInterrupt:
            logger.info("Stopping ingest consumer...")
        except Exception as e:
            logger.error(f"Error in ingest consumer: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
    
    def _process_ingest_message(self, message: Dict[str, Any]) -> None:
        """Process a single ingest message."""
        submission_id = message['submission_id']
        s3_key = message['s3_key']
        
        logger.info(f"Processing certificate ingest for submission {submission_id}")
        
        with get_db_session() as session:
            # Update submission status to processing
            submission = self.submission_repository.get_by_id(
                session, submission_id
            )
            
            if not submission:
                logger.error(f"Submission {submission_id} not found")
                return
            
            self.submission_repository.update_status(
                session, submission_id, 'ocr_processing'
            )
            
            try:
                # Download file from S3
                file_content = self.s3_service.download_file(s3_key)
                if not file_content:
                    logger.error(f"Failed to download file {s3_key}")
                    self.submission_repository.update_status(
                        session, submission_id, 'failed',
                        f"Failed to download file from S3: {s3_key}"
                    )
                    return
                
                # Get file extension from original filename
                file_extension = submission.original_filename.split('.')[-1] if submission.original_filename else 'pdf'
                
                # Perform OCR with timing
                import time
                start_time = time.time()
                extracted_text, confidence = self.ocr_service.process_file(file_content, file_extension)
                end_time = time.time()
                processing_time_ms = int((end_time - start_time) * 1000)
                
                # Create OCR result structure
                ocr_result = {
                    'text': extracted_text,
                    'confidence': confidence,
                    'processing_time_ms': processing_time_ms
                }
                
                # Save OCR result to database
                ocr_text = self.ocr_text_repository.create_ocr_text(
                    session=session,
                    submission_id=submission_id,
                    raw_text=ocr_result['text'],
                    ocr_confidence=ocr_result['confidence'],
                    processing_time_ms=ocr_result['processing_time_ms']
                )
                
                # Publish to OCR topic
                self.kafka_service.publish_certificate_ocr(
                    submission_id=submission_id,
                    ocr_text_id=ocr_text.id,
                    raw_text=ocr_result['text'],
                    ocr_confidence=ocr_result.get('confidence')
                )
                
                logger.info(f"OCR completed for submission {submission_id}")
                
            except Exception as e:
                logger.error(f"Error processing OCR for submission {submission_id}: {e}")
                self.submission_repository.update_status(
                    session, submission_id, 'failed', str(e)
                )