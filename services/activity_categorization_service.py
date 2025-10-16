"""
Activity categorization service using LLM for intelligent category matching.
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional
from models.activity_category import ActivityCategory
from models.extracted_activity import ExtractedActivity
from repositories.extracted_activity_repository import ExtractedActivityRepository
from repositories.activity_category_repository import ActivityCategoryRepository
from database.connection import get_db_session
from services.llm_service import LLMService
from services.prompt_service import PromptService

logger = logging.getLogger(__name__)


class ActivityCategorizationService:
    """Service for categorizing extracted activities using LLM and calculating valid hours."""
    
    def __init__(
        self, 
        llm_service: LLMService, 
        prompt_service: PromptService,
        activity_repository: ExtractedActivityRepository,
        category_repository: ActivityCategoryRepository
    ):
        """Initialize the service with LLM, prompt service and repository dependencies."""
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.activity_repository = activity_repository
        self.category_repository = category_repository
    
    def categorize_activity(self, extracted_data: Dict[str, Any], submission_id: int = None) -> Dict[str, Any]:
        """
        Categorize an extracted activity using LLM and calculate valid hours.
        
        Args:
            extracted_data: Dictionary with extracted certificate data
            submission_id: ID of the certificate submission (for database persistence)
            
        Returns:
            Dictionary with categorization results
        """
        evento = extracted_data.get('evento', '')
        carga_horaria = extracted_data.get('carga_horaria', '')
        
        if not evento:
            return self._create_error_result("Missing evento information")
        
        # Extract numeric hours from carga_horaria
        numeric_hours = self._extract_numeric_hours(carga_horaria)
        if numeric_hours is None:
            return self._create_error_result("Could not extract numeric hours")
        
        # Use LLM to identify category
        category_data, llm_reasoning = self._categorize_with_llm(extracted_data)
        if not category_data:
            return self._create_error_result("No matching category found by LLM")
        
        # Calculate valid hours based on category rules
        calculated_hours = self._calculate_hours(category_data, numeric_hours, extracted_data)
        
        # Save to database
        extracted_activity_id = self._save_extracted_activity(
            extracted_data, category_data, numeric_hours, calculated_hours, llm_reasoning, submission_id
        )
        
        return {
            'success': True,
            'category_id': category_data['id'],
            'category_name': category_data['name'],
            'original_hours': numeric_hours,
            'calculated_hours': calculated_hours,
            'calculation_type': category_data['calculation_type'],
            'input_unit': category_data['input_unit'],
            'max_total_hours': category_data['max_total_hours'],
            'llm_reasoning': llm_reasoning,
            'extracted_activity_id': extracted_activity_id
        }
    
    def _categorize_with_llm(self, extracted_data: Dict[str, Any]) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Use LLM to categorize the activity.
        
        Args:
            extracted_data: Extracted certificate data
            
        Returns:
            Tuple of (category_data_dict, reasoning)
        """
        try:
            # Get all available categories (both formatted text and category data dict)
            categories_text, categories_dict = self._get_categories_text()
            
            # Get raw OCR text
            raw_text = extracted_data.get('raw_text', '')
            
            # Get LLM response using proper prompt service
            response = self.llm_service.categorize_activity(
                raw_text=raw_text,
                extracted_data=extracted_data,
                categories_text=categories_text
            )
            logger.info(f"LLM categorization response: {response}")
            
            # Parse response to extract category ID and reasoning
            category_id = response.get('category_id')
            reasoning = response.get('reasoning', 'No reasoning provided')
            
            if category_id and category_id in categories_dict:
                # Return pre-loaded category data from the dictionary
                category_data = categories_dict[category_id]
                return category_data, reasoning
            elif category_id:
                return None, f"Category ID {category_id} not found"
            
            return None, reasoning
            
        except Exception as e:
            logger.error(f"Error in LLM categorization: {e}")
            return None, f"LLM error: {str(e)}"
    
    def _build_categorization_prompt(self, extracted_data: Dict[str, Any], categories: List[ActivityCategory]) -> str:
        """Build prompt for LLM categorization using prompt service."""
        
        # Format categories for the prompt
        categories_text = ""
        for cat in categories:
            categories_text += f"ID: {cat.id}\n"
            categories_text += f"Nome: {cat.name}\n"
            categories_text += f"Descrição: {cat.description}\n"
            categories_text += f"Tipo de Cálculo: {cat.calculation_type}\n"
            if cat.calculation_type.startswith('fixed_'):
                categories_text += f"Horas Concedidas: {cat.hours_awarded}h por {cat.input_unit}\n"
            else:
                categories_text += f"Cálculo: {cat.output_hours}h para cada {cat.input_quantity} {cat.input_unit}\n"
            categories_text += f"Máximo Total: {cat.max_total_hours}h\n\n"
        
        # Use prompt service to get the template and format it
        return self.prompt_service.get_activity_categorization_prompt(
            raw_text=extracted_data.get('raw_text', 'N/A'),
            nome_participante=extracted_data.get('nome_participante', 'N/A'),
            evento=extracted_data.get('evento', 'N/A'),
            local=extracted_data.get('local', 'N/A'),
            data=extracted_data.get('data', 'N/A'),
            carga_horaria=extracted_data.get('carga_horaria', 'N/A'),
            categories_text=categories_text
        )
    
    def _parse_llm_response(self, response: str) -> tuple[Optional[int], str]:
        """Parse LLM response to extract category ID and reasoning."""
        try:
            # Try to find JSON in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                category_id = parsed.get('category_id')
                reasoning = parsed.get('reasoning', 'No reasoning provided')
                
                return category_id, reasoning
            
            return None, f"Could not parse JSON from response: {response}"
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None, f"JSON parsing error: {response}"
    
    def _calculate_hours(self, category_data: Dict[str, Any], numeric_hours: int, extracted_data: Dict[str, Any]) -> int:
        """
        Calculate valid hours based on category calculation rules.
        
        Args:
            category_data: Category data dictionary with calculation rules
            numeric_hours: Original hours from certificate
            extracted_data: Additional extracted data for calculation
            
        Returns:
            Calculated valid hours
        """
        calculation_type = category_data['calculation_type']
        
        if calculation_type == 'fixed_per_semester':
            # Fixed hours per semester
            return category_data['hours_awarded']
        
        elif calculation_type == 'fixed_per_activity':
            # Fixed hours per activity/event
            return category_data['hours_awarded']
        
        elif calculation_type == 'ratio_hours':
            # Hours-based ratio calculation
            ratio = category_data['output_hours'] / category_data['input_quantity']
            calculated = int(numeric_hours * ratio)
            return min(calculated, category_data['max_total_hours'])
        
        elif calculation_type == 'ratio_days':
            # Days-based calculation - need to extract days from data
            days = self._extract_days_from_data(extracted_data)
            if days:
                calculated = days * category_data['output_hours']
                return min(calculated, category_data['max_total_hours'])
            else:
                # Fallback: assume 1 day
                return min(category_data['output_hours'], category_data['max_total_hours'])
        
        elif calculation_type == 'ratio_pages':
            # Pages-based calculation - need to extract pages from data
            pages = self._extract_pages_from_data(extracted_data)
            if pages:
                ratio = category_data['output_hours'] / category_data['input_quantity']
                calculated = int(pages * ratio)
                return min(calculated, category_data['max_total_hours'])
            else:
                # Fallback: assume minimum pages
                return min(category_data['output_hours'], category_data['max_total_hours'])
        
        else:
            logger.warning(f"Unknown calculation type: {calculation_type}")
            return 0
    
    def _extract_days_from_data(self, extracted_data: Dict[str, Any]) -> Optional[int]:
        """Extract number of days from extracted data."""
        # Try to find days in event description or other fields
        text_fields = [
            extracted_data.get('evento', ''),
            extracted_data.get('data', ''),
            extracted_data.get('carga_horaria', '')
        ]
        
        for text in text_fields:
            if text:
                # Look for patterns like "3 dias", "2 days", etc.
                patterns = [
                    r'(\d+)\s*dias?',
                    r'(\d+)\s*days?'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text.lower())
                    if match:
                        return int(match.group(1))
        
        return None
    
    def _extract_pages_from_data(self, extracted_data: Dict[str, Any]) -> Optional[int]:
        """Extract number of pages from extracted data."""
        # Try to find pages in event description or other fields
        text_fields = [
            extracted_data.get('evento', ''),
            extracted_data.get('carga_horaria', '')
        ]
        
        for text in text_fields:
            if text:
                # Look for patterns like "10 páginas", "15 pages", etc.
                patterns = [
                    r'(\d+)\s*páginas?',
                    r'(\d+)\s*pages?',
                    r'(\d+)\s*p\.',
                    r'(\d+)\s*pgs?'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text.lower())
                    if match:
                        return int(match.group(1))
        
        return None
    
    def _extract_numeric_hours(self, carga_horaria: str) -> Optional[int]:
        """
        Extract numeric hours from carga_horaria string.
        
        Args:
            carga_horaria: String containing hour information
            
        Returns:
            Numeric hours or None if not found
        """
        if not carga_horaria:
            return None
        
        # Common patterns for hours
        patterns = [
            r'(\d+)\s*h',  # "40h", "20 h"
            r'(\d+)\s*hora',  # "40 horas", "20 hora"
            r'(\d+)\s*hr',  # "40hr", "20 hrs"
            r'(\d+)(?:\s*|$)',  # Just numbers at end or followed by space
        ]
        
        carga_lower = carga_horaria.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, carga_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _save_extracted_activity(
        self, 
        extracted_data: Dict[str, Any], 
        category_data: Dict[str, Any],
        numeric_hours: int,
        calculated_hours: int,
        llm_reasoning: str,
        submission_id: int = None
    ) -> int:
        """
        Save extracted activity to database using repository pattern.
        
        Args:
            extracted_data: Original extracted data
            category_data: Category data dictionary
            numeric_hours: Extracted numeric hours
            calculated_hours: Calculated valid hours
            llm_reasoning: LLM's reasoning for category selection
            submission_id: ID of the certificate submission
            
        Returns:
            ID of the saved ExtractedActivity instance
        """
        with get_db_session() as session:
            activity = self.activity_repository.create_activity(
                session=session,
                submission_id=submission_id,
                participant_name=extracted_data.get('nome_participante'),
                event_name=extracted_data.get('evento'),
                location=extracted_data.get('local'),
                event_date=extracted_data.get('data'),
                original_hours=extracted_data.get('carga_horaria'),
                numeric_hours=numeric_hours,
                category_id=category_data['id'],
                calculated_hours=calculated_hours,
                llm_reasoning=llm_reasoning if llm_reasoning else None,
                raw_text=extracted_data.get('raw_text', '') if extracted_data.get('raw_text') else None,
                review_status='pending_review'
            )
            
            # Extract the ID while the session is still active
            activity_id = activity.id
            
            logger.info(f"Saved activity: {extracted_data.get('evento')} -> {category_data['name']} ({calculated_hours}h)")
            
            return activity_id
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create error result dictionary.
        
        Args:
            error_message: Error description
            
        Returns:
            Error result dictionary
        """
        logger.warning(f"Activity categorization error: {error_message}")
        return {
            'success': False,
            'error': error_message,
            'category_id': None,
            'category_name': None,
            'original_hours': None,
            'calculated_hours': 0,
            'llm_reasoning': None
        }
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        Get all available activity categories.
        
        Returns:
            List of category dictionaries
        """
        categories = ActivityCategory.query.all()
        result = []
        
        for cat in categories:
            # Build calculation description
            if cat.calculation_type == 'fixed_per_semester':
                calc_desc = f"{cat.hours_awarded}h por semestre"
            elif cat.calculation_type == 'fixed_per_activity':
                calc_desc = f"{cat.hours_awarded}h por atividade"
            elif cat.calculation_type.startswith('ratio_'):
                calc_desc = f"{cat.output_hours}h para cada {cat.input_quantity} {cat.input_unit}"
            else:
                calc_desc = "Cálculo personalizado"
            
            result.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'calculation_type': cat.calculation_type,
                'calculation_description': calc_desc,
                'max_total_hours': cat.max_total_hours,
                'input_unit': cat.input_unit
            })
        
        return result
    
    def get_activity_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent activity processing history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of processed activity dictionaries
        """
        activities = ExtractedActivity.query\
            .order_by(ExtractedActivity.processed_at.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'id': act.id,
                'filename': act.filename,
                'nome_participante': act.nome_participante,
                'evento': act.evento,
                'original_hours': act.carga_horaria_numeric,
                'calculated_hours': act.calculated_hours,
                'category_name': act.category.name if act.category else None,
                'llm_reasoning': act.llm_reasoning,
                'processed_at': act.processed_at.isoformat() if act.processed_at else None
            }
            for act in activities
        ]
    
    def _get_categories_text(self) -> tuple[str, Dict[int, Dict[str, Any]]]:
        """
        Get formatted text of available activity categories and return category data.
        
        Returns:
            Tuple of (formatted_categories_text, categories_data_dict)
        """
        try:
            with get_db_session() as session:
                # Use repository to get formatted text and data dict
                categories_text = self.category_repository.get_categories_formatted_text(session)
                categories_dict = self.category_repository.get_categories_dict(session)
                
                return categories_text, categories_dict
                
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return "Error retrieving categories", {}