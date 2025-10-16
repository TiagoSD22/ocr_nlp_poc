"""
Configuration settings for the OCR application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# File upload settings
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

# OCR settings
TESSERACT_CONFIG = r'--oem 3 --psm 6 -l por+eng'

# Ollama LLM settings
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', 300))  # Increased to 5 minutes
OLLAMA_CONNECTION_TIMEOUT = int(os.getenv('OLLAMA_CONNECTION_TIMEOUT', 10))  # Increased connection timeout
MODEL_DOWNLOAD_TIMEOUT = int(os.getenv('MODEL_DOWNLOAD_TIMEOUT', 600))  # Increased to 10 minutes

# Image processing settings
CONTRAST_FACTOR = float(os.getenv('CONTRAST_FACTOR', 1.5))
SHARPNESS_FACTOR = float(os.getenv('SHARPNESS_FACTOR', 2.0))

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://complementa_user:complementa_pass@localhost:5434/complementa_db')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'complementa_db')
DB_USER = os.getenv('DB_USER', 'complementa_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'complementa_pass')

# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')

# S3 settings (LocalStack)
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', 'http://localhost:4566')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'certificate-documents')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', 'localstack')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', 'localstack')
S3_REGION = os.getenv('S3_REGION', 'us-east-1')

# AWS credentials for LocalStack/Kafka consumers
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
