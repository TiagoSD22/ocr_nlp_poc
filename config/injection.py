"""
Dependency injection configuration using Flask-Injector.
"""
from injector import Module, provider, singleton
from services.ocr_service import OCRService
from services.llm_service import LLMService
from services.certificate_service import CertificateService
from services.prompt_service import PromptService
from services.activity_categorization_service import ActivityCategorizationService
from services.s3_service import S3Service
from services.kafka_service import KafkaService
from services.certificate_submission_service import CertificateSubmissionService
from services.student_service import StudentService
from repositories.student_repository import StudentRepository
from repositories.certificate_submission_repository import CertificateSubmissionRepository
from repositories.certificate_ocr_text_repository import CertificateOcrTextRepository
from repositories.certificate_metadata_repository import CertificateMetadataRepository
from repositories.extracted_activity_repository import ExtractedActivityRepository
from repositories.activity_category_repository import ActivityCategoryRepository


class ServiceModule(Module):
    """Module that configures dependency injection bindings."""
    
    @singleton
    @provider
    def provide_prompt_service(self) -> PromptService:
        """Provide prompt service instance."""
        return PromptService()
    
    @singleton
    @provider
    def provide_ocr_service(self) -> OCRService:
        """Provide OCR service instance."""
        return OCRService()
    
    @singleton
    @provider
    def provide_s3_service(self) -> S3Service:
        """Provide S3 service instance."""
        return S3Service()
    
    @singleton
    @provider
    def provide_kafka_service(self) -> KafkaService:
        """Provide Kafka service instance."""
        return KafkaService()
    
    @singleton
    @provider
    def provide_student_service(self) -> StudentService:
        """Provide student service instance."""
        return StudentService()
    
    @singleton
    @provider
    def provide_certificate_submission_service(
        self,
        s3_service: S3Service,
        kafka_service: KafkaService,
        student_service: StudentService,
        submission_repository: CertificateSubmissionRepository
    ) -> CertificateSubmissionService:
        """Provide certificate submission service instance."""
        return CertificateSubmissionService(
            s3_service, 
            kafka_service, 
            student_service, 
            submission_repository
        )
    
    @singleton
    @provider
    def provide_activity_categorization_service(
        self, 
        llm_service: LLMService, 
        prompt_service: PromptService,
        activity_repository: ExtractedActivityRepository,
        category_repository: ActivityCategoryRepository
    ) -> ActivityCategorizationService:
        """Provide activity categorization service instance with dependencies injected."""
        return ActivityCategorizationService(llm_service, prompt_service, activity_repository, category_repository)
    
    @singleton
    @provider
    def provide_llm_service(self, prompt_service: PromptService) -> LLMService:
        """Provide LLM service instance with prompt service injected."""
        return LLMService(prompt_service)
    
    @singleton
    @provider
    def provide_certificate_service(
        self, 
        llm_service: LLMService,
        activity_categorization_service: ActivityCategorizationService
    ) -> CertificateService:
        """Provide certificate service instance with dependencies injected."""
        return CertificateService(llm_service, activity_categorization_service)
    
    # Repository Providers
    @singleton
    @provider
    def provide_student_repository(self) -> StudentRepository:
        """Provide student repository instance."""
        return StudentRepository()
    
    @singleton
    @provider
    def provide_certificate_submission_repository(self) -> CertificateSubmissionRepository:
        """Provide certificate submission repository instance."""
        return CertificateSubmissionRepository()
    
    @singleton
    @provider
    def provide_certificate_ocr_text_repository(self) -> CertificateOcrTextRepository:
        """Provide certificate OCR text repository instance."""
        return CertificateOcrTextRepository()
    
    @singleton
    @provider
    def provide_certificate_metadata_repository(self) -> CertificateMetadataRepository:
        """Provide certificate metadata repository instance."""
        return CertificateMetadataRepository()
    
    @singleton
    @provider
    def provide_extracted_activity_repository(self) -> ExtractedActivityRepository:
        """Provide extracted activity repository instance."""
        return ExtractedActivityRepository()
    
    @singleton
    @provider
    def provide_activity_category_repository(self) -> ActivityCategoryRepository:
        """Provide activity category repository instance."""
        return ActivityCategoryRepository()