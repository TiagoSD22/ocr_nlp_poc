"""
Dependency injection configuration using Flask-Injector.
"""
from injector import Module, provider, singleton
from services.ocr_service import OCRService
from services.llm_service import LLMService
from services.certificate_service import CertificateService
from services.prompt_service import PromptService
from services.activity_categorization_service import ActivityCategorizationService


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
    def provide_activity_categorization_service(
        self, 
        llm_service: LLMService, 
        prompt_service: PromptService
    ) -> ActivityCategorizationService:
        """Provide activity categorization service instance with dependencies injected."""
        return ActivityCategorizationService(llm_service, prompt_service)
    
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