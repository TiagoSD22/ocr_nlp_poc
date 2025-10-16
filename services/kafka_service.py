"""
Kafka Service for handling message publishing to Kafka topics.
"""
import json
import logging
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
import config.settings as settings

logger = logging.getLogger(__name__)


class KafkaService:
    """Service for handling Kafka operations."""
    
    def __init__(self):
        """Initialize Kafka service."""
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.producer = None
        self._init_producer()
    
    def _init_producer(self) -> None:
        """Initialize Kafka producer."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                retry_backoff_ms=1000,
                request_timeout_ms=30000
            )
            logger.info(f"Kafka producer initialized with servers: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def publish_certificate_ingest(
        self, 
        submission_id: int,
        enrollment_number: str,
        s3_key: str,
        checksum: str,
        original_filename: str
    ) -> bool:
        """
        Publish message to certificate.ingest topic.
        
        Args:
            submission_id: Database ID of certificate submission
            enrollment_number: Student enrollment number
            s3_key: S3 object key
            checksum: File checksum
            original_filename: Original filename
            
        Returns:
            True if published successfully, False otherwise
        """
        message = {
            'submission_id': submission_id,
            'enrollment_number': enrollment_number,
            's3_key': s3_key,
            'checksum': checksum,
            'original_filename': original_filename,
            'stage': 'ingest',
            'timestamp': self._get_timestamp()
        }
        
        return self._publish_message(
            topic='certificate.ingest',
            key=str(submission_id),
            value=message
        )
    
    def publish_certificate_ocr(
        self,
        submission_id: int,
        ocr_text_id: int,
        raw_text: str,
        ocr_confidence: Optional[float] = None
    ) -> bool:
        """
        Publish message to certificate.ocr topic.
        
        Args:
            submission_id: Database ID of certificate submission
            ocr_text_id: Database ID of OCR text record
            raw_text: Extracted text from OCR
            ocr_confidence: OCR confidence score
            
        Returns:
            True if published successfully, False otherwise
        """
        message = {
            'submission_id': submission_id,
            'ocr_text_id': ocr_text_id,
            'raw_text': raw_text,
            'ocr_confidence': ocr_confidence,
            'stage': 'ocr_completed',
            'timestamp': self._get_timestamp()
        }
        
        return self._publish_message(
            topic='certificate.ocr',
            key=str(submission_id),
            value=message
        )
    
    def publish_certificate_metadata(
        self,
        submission_id: int,
        metadata_id: int,
        extracted_data: Dict[str, Any]
    ) -> bool:
        """
        Publish message to certificate.metadata topic.
        
        Args:
            submission_id: Database ID of certificate submission
            metadata_id: Database ID of metadata record
            extracted_data: Extracted metadata
            
        Returns:
            True if published successfully, False otherwise
        """
        message = {
            'submission_id': submission_id,
            'metadata_id': metadata_id,
            'extracted_data': extracted_data,
            'stage': 'metadata_extracted',
            'timestamp': self._get_timestamp()
        }
        
        return self._publish_message(
            topic='certificate.metadata',
            key=str(submission_id),
            value=message
        )
    
    def publish_certificate_categorization(
        self,
        submission_id: int,
        activity_id: int,
        category_id: int,
        calculated_hours: int,
        llm_reasoning: str
    ) -> bool:
        """
        Publish message to certificate.categorization topic.
        
        Args:
            submission_id: Database ID of certificate submission
            activity_id: Database ID of extracted activity
            category_id: Identified category ID
            calculated_hours: Calculated hours
            llm_reasoning: LLM reasoning for categorization
            
        Returns:
            True if published successfully, False otherwise
        """
        message = {
            'submission_id': submission_id,
            'activity_id': activity_id,
            'category_id': category_id,
            'calculated_hours': calculated_hours,
            'llm_reasoning': llm_reasoning,
            'stage': 'categorized',
            'timestamp': self._get_timestamp()
        }
        
        return self._publish_message(
            topic='certificate.categorization',
            key=str(submission_id),
            value=message
        )
    
    def _publish_message(self, topic: str, key: str, value: Dict[str, Any]) -> bool:
        """
        Publish message to Kafka topic.
        
        Args:
            topic: Kafka topic name
            key: Message key
            value: Message value
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False
        
        try:
            future = self.producer.send(topic, key=key, value=value)
            # Wait for the message to be sent
            record_metadata = future.get(timeout=10)
            logger.info(
                f"Message published to {topic} - "
                f"partition: {record_metadata.partition}, "
                f"offset: {record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing to {topic}: {e}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def close(self) -> None:
        """Close Kafka producer."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")