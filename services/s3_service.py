"""
S3 Service for handling file uploads to LocalStack S3.
"""
import boto3
import hashlib
import logging
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
import config.settings as settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 operations with LocalStack."""
    
    def __init__(self):
        """Initialize S3 service with LocalStack configuration."""
        self.bucket_name = settings.S3_BUCKET_NAME
        
        # Internal S3 client for operations (within Docker network)
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.AWS_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )
        
        # External S3 client for presigned URLs (accessible from host)
        external_endpoint = getattr(settings, 'S3_EXTERNAL_ENDPOINT_URL', settings.AWS_ENDPOINT_URL)
        self.s3_client_external = boto3.client(
            's3',
            endpoint_url=external_endpoint,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )
        
        logger.info(f"S3 Service initialized - Internal: {settings.AWS_ENDPOINT_URL}, External: {external_endpoint}")
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the S3 bucket exists, create if not."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create S3 bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking S3 bucket: {e}")
                raise
    
    def calculate_checksum(self, file_content: bytes) -> str:
        """Calculate SHA-256 checksum of file content."""
        return hashlib.sha256(file_content).hexdigest()
    
    def upload_file(
        self, 
        file_content: bytes, 
        enrollment_number: str, 
        filename: str,
        checksum: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to S3 with enrollment-based path structure.
        
        Args:
            file_content: File content as bytes
            enrollment_number: Student enrollment number
            filename: Original filename
            checksum: Pre-calculated checksum (optional)
            
        Returns:
            Dict with upload details
        """
        if checksum is None:
            checksum = self.calculate_checksum(file_content)
        
        # Create S3 key with enrollment-based path
        file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
        s3_key = f"certificates/{enrollment_number}/{checksum}.{file_extension}"
        
        try:
            # Upload file to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=self._get_content_type(file_extension),
                Metadata={
                    'enrollment_number': enrollment_number,
                    'original_filename': filename,
                    'checksum': checksum
                }
            )
            
            logger.info(f"Uploaded file to S3: {s3_key}")
            
            return {
                'success': True,
                's3_key': s3_key,
                'checksum': checksum,
                'file_size': len(file_content),
                'bucket': self.bucket_name
            }
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Download file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            File content as bytes or None if failed
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return None
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def get_file_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from S3."""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {}),
                'content_type': response.get('ContentType', '')
            }
        except ClientError as e:
            logger.error(f"Failed to get file metadata: {e}")
            return None
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for file download.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string or None if failed
        """
        try:
            # Use external client for presigned URLs to ensure they're accessible from host
            presigned_url = self.s3_client_external.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.debug(f"Generated presigned URL for {s3_key}")
            return presigned_url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            return None
    
    def _get_content_type(self, file_extension: str) -> str:
        """Get content type based on file extension."""
        content_types = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'tiff': 'image/tiff',
            'bmp': 'image/bmp'
        }
        return content_types.get(file_extension.lower(), 'application/octet-stream')