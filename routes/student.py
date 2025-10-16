"""
Student management routes.
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

from services.student_service import StudentService
from database.connection import get_db_session

logger = logging.getLogger(__name__)

student_bp = Blueprint('student', __name__, url_prefix='/api/v1/student')


@student_bp.route('/register', methods=['POST'])
def register_student():
    """
    Register a new student in the system.
    
    Required fields:
    - enrollment_number: Student enrollment number (unique)
    - name: Student full name
    - email: Student email address (optional)
    
    Returns:
        JSON with student information and success status
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        enrollment_number = data.get('enrollment_number', '').strip()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip() if data.get('email') else None
        
        if not enrollment_number:
            return jsonify({'error': 'enrollment_number is required'}), 400
        
        if not name:
            return jsonify({'error': 'name is required'}), 400
        
        if email and '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        logger.info(f"Registering student: {enrollment_number} - {name}")
        
        with get_db_session() as session:
            student_service = StudentService()
            
            try:
                result = student_service.register_student(
                    session, enrollment_number, name, email
                )
                session.commit()
                return jsonify(result), 201
                
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
        
    except Exception as e:
        logger.error(f"Error registering student: {e}")
        return jsonify({
            'error': f'Failed to register student: {str(e)}'
        }), 500


@student_bp.route('/<enrollment_number>', methods=['GET'])
def get_student(enrollment_number: str):
    """
    Get student information by enrollment number.
    
    Args:
        enrollment_number: Student enrollment number
        
    Returns:
        JSON with student information
    """
    try:
        with get_db_session() as session:
            student_service = StudentService()
            student = student_service.get_student_by_enrollment(session, enrollment_number)
            
            if not student:
                return jsonify({
                    'error': 'Student not found',
                    'enrollment_number': enrollment_number
                }), 404
            
            return jsonify({
                'success': True,
                'student': student.to_dict()
            })
        
    except Exception as e:
        logger.error(f"Error getting student {enrollment_number}: {e}")
        return jsonify({
            'error': f'Failed to get student: {str(e)}'
        }), 500


@student_bp.route('/<enrollment_number>', methods=['PUT'])
def update_student(enrollment_number: str):
    """
    Update student information.
    
    Args:
        enrollment_number: Student enrollment number
        
    Returns:
        JSON with updated student information
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        with get_db_session() as session:
            student_service = StudentService()
            
            try:
                result = student_service.update_student(
                    session, enrollment_number, **data
                )
                session.commit()
                return jsonify(result)
                
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
        
    except Exception as e:
        logger.error(f"Error updating student {enrollment_number}: {e}")
        return jsonify({
            'error': f'Failed to update student: {str(e)}'
        }), 500