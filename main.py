"""
Main application entry point for OCR Certificate Extraction service.
"""
from flask import Flask
import logging
from flask_injector import FlaskInjector

from config.injection import ServiceModule
from routes.health import health_bp
from routes.certificate import certificate_bp
import config.settings as settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure Flask settings
    app.config['MAX_CONTENT_LENGTH'] = settings.MAX_CONTENT_LENGTH
    app.config['DEBUG'] = settings.DEBUG
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(certificate_bp)
    
    # Configure dependency injection
    FlaskInjector(app=app, modules=[ServiceModule])
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    )