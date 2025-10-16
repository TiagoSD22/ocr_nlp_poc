"""
Kafka Consumer Manager for running certificate processing pipeline consumers.
"""
import logging
import threading
import signal
import sys
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from consumers import (
    CertificateIngestConsumer,
    CertificateOCRConsumer, 
    CertificateMetadataConsumer
)
from services.ocr_service import OCRService
from services.llm_service import LLMService
from services.s3_service import S3Service
from services.kafka_service import KafkaService
from services.prompt_service import PromptService
from services.activity_categorization_service import ActivityCategorizationService
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from repositories.certificate_ocr_text_repository import CertificateOcrTextRepository
from repositories.certificate_metadata_repository import CertificateMetadataRepository
from repositories.extracted_activity_repository import ExtractedActivityRepository
from repositories.activity_category_repository import ActivityCategoryRepository

logger = logging.getLogger(__name__)


class ConsumerManager:
    """Manager for running multiple Kafka consumers."""
    
    def __init__(self):
        """Initialize consumer manager."""
        self.consumers = []
        self.executor = None
        self.shutdown_event = threading.Event()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down consumers...")
        self.shutdown()
    
    def _create_consumers(self) -> List:
        """Create consumer instances with dependency injection."""
        logger.info("Initializing services and repositories...")
        
        # Create service instances
        prompt_service = PromptService()
        ocr_service = OCRService()
        llm_service = LLMService(prompt_service)
        s3_service = S3Service()
        kafka_service = KafkaService()
        
        # Create repository instances
        submission_repository = CertificateSubmissionRepository()
        ocr_text_repository = CertificateOcrTextRepository()
        metadata_repository = CertificateMetadataRepository()
        activity_repository = ExtractedActivityRepository()
        category_repository = ActivityCategoryRepository()
        
        # Create additional services
        activity_categorization_service = ActivityCategorizationService(
            llm_service, prompt_service, activity_repository, category_repository
        )
        
        logger.info("Creating consumer instances...")
        
        # Create consumers
        consumers = [
            CertificateIngestConsumer(
                ocr_service, 
                s3_service, 
                kafka_service,
                submission_repository,
                ocr_text_repository
            ),
            CertificateOCRConsumer(
                llm_service, 
                kafka_service,
                submission_repository,
                metadata_repository
            ),
            CertificateMetadataConsumer(
                activity_categorization_service,
                submission_repository
            )
        ]
        
        logger.info(f"Created {len(consumers)} consumer instances")
        return consumers
    
    def start(self) -> None:
        """Start all consumers in separate threads."""
        logger.info("Starting Kafka consumer manager...")
        
        try:
            # Create consumer instances
            self.consumers = self._create_consumers()
            
            if not self.consumers:
                logger.error("No consumers were created")
                return
            
            # Start consumers in thread pool
            self.executor = ThreadPoolExecutor(
                max_workers=len(self.consumers),
                thread_name_prefix="kafka-consumer"
            )
            
            # Submit consumer tasks
            futures = []
            for i, consumer in enumerate(self.consumers):
                consumer_name = consumer.__class__.__name__
                logger.info(f"Starting consumer {i+1}/{len(self.consumers)}: {consumer_name}")
                
                future = self.executor.submit(self._run_consumer, consumer, consumer_name)
                futures.append(future)
            
            logger.info(f"Successfully started {len(self.consumers)} consumers")
            
            # Wait for consumers to complete or shutdown signal
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Consumer failed: {e}")
                    # Continue with other consumers
            
        except Exception as e:
            logger.error(f"Error starting consumers: {e}")
            self.shutdown()
            raise
    
    def _run_consumer(self, consumer, consumer_name: str) -> None:
        """Run a single consumer with error handling."""
        try:
            logger.info(f"Consumer {consumer_name} started")
            consumer.process_messages()
        except Exception as e:
            logger.error(f"Consumer {consumer_name} failed: {e}")
            raise
        finally:
            logger.info(f"Consumer {consumer_name} stopped")
    
    def shutdown(self) -> None:
        """Shutdown all consumers gracefully."""
        logger.info("Shutting down consumer manager...")
        
        self.shutdown_event.set()
        
        # Close all consumers
        for consumer in self.consumers:
            try:
                if hasattr(consumer, 'consumer') and consumer.consumer:
                    consumer.consumer.close()
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")
        
        # Shutdown thread pool
        if self.executor:
            logger.info("Shutting down thread pool...")
            self.executor.shutdown(wait=True, timeout=30)
        
        logger.info("Consumer manager shutdown complete")


def main():
    """Main entry point for running consumers."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('kafka_consumers.log')
        ]
    )
    
    logger.info("Starting Kafka consumers for certificate processing pipeline...")
    
    # Note: Database should already be initialized by the main Flask application
    logger.info("Assuming database is already initialized by main application")
    
    # Create and start consumer manager
    manager = ConsumerManager()
    
    try:
        manager.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        manager.shutdown()
        logger.info("Application stopped")


if __name__ == "__main__":
    main()