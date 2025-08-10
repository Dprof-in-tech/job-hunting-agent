"""
Cloudinary Storage Module for Serverless Deployment
Provides file storage using Cloudinary for Vercel compatibility
"""

import os
import io
import logging
from typing import Optional, Dict, Any
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url

logger = logging.getLogger(__name__)

class CloudinaryStorage:
    """Cloudinary storage provider for serverless deployment"""
    
    def __init__(self):
        # Configure Cloudinary from environment variables
        self.configured = self._configure_cloudinary()
    
    def _configure_cloudinary(self) -> bool:
        """Configure Cloudinary from environment variables"""
        try:
            cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
            api_key = os.environ.get('CLOUDINARY_API_KEY')
            api_secret = os.environ.get('CLOUDINARY_API_SECRET')
            
            if not all([cloud_name, api_key, api_secret]):
                logger.warning("Cloudinary credentials not found in environment variables")
                return False
            
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            
            logger.info("Cloudinary configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure Cloudinary: {e}")
            return False
    
    def upload_file(self, file_content: bytes, filename: str, resource_type: str = "auto") -> Optional[Dict[str, Any]]:
        """Upload file to Cloudinary"""
        if not self.configured:
            logger.error("Cloudinary not configured")
            return None
        
        try:
            # Create file-like object from bytes
            file_obj = io.BytesIO(file_content)
            
            # Generate unique public_id
            import time
            timestamp = int(time.time())
            public_id = f"{timestamp}_{filename.replace('.', '_')}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_obj,
                public_id=public_id,
                resource_type=resource_type,
                folder="job-hunting-agent"  # Organize files in folder
            )
            
            logger.info(f"Successfully uploaded {filename} to Cloudinary")
            return {
                'public_id': result['public_id'],
                'secure_url': result['secure_url'],
                'url': result['url'],
                'format': result['format'],
                'resource_type': result['resource_type']
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file to Cloudinary: {e}")
            return None
    
    def get_file_url(self, public_id: str, **options) -> str:
        """Get Cloudinary URL for a file"""
        if not self.configured:
            return ""
        
        try:
            url, _ = cloudinary_url(public_id, **options)
            return url
        except Exception as e:
            logger.error(f"Failed to generate Cloudinary URL: {e}")
            return ""
    
    def delete_file(self, public_id: str) -> bool:
        """Delete file from Cloudinary"""
        if not self.configured:
            return False
        
        try:
            result = cloudinary.uploader.destroy(public_id)
            success = result.get('result') == 'ok'
            
            if success:
                logger.info(f"Successfully deleted {public_id} from Cloudinary")
            else:
                logger.warning(f"Failed to delete {public_id}: {result}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting file from Cloudinary: {e}")
            return False
    
    def upload_cv(self, cv_content: bytes, filename: str) -> Optional[str]:
        """Upload CV file and return secure URL"""
        result = self.upload_file(cv_content, filename, resource_type="auto")
        return result['secure_url'] if result else None
    
    def upload_resume(self, resume_content: bytes, filename: str) -> Optional[str]:
        """Upload resume file and return secure URL"""
        result = self.upload_file(resume_content, filename, resource_type="auto")
        return result['secure_url'] if result else None

# Fallback storage for when Cloudinary is not available
class FallbackStorage:
    """Fallback storage using base64 encoding"""
    
    def upload_file(self, file_content: bytes, filename: str, resource_type: str = "auto") -> Optional[Dict[str, Any]]:
        """Store file as base64 data URL"""
        try:
            import base64
            
            # Determine MIME type based on file extension
            mime_types = {
                '.pdf': 'application/pdf',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.txt': 'text/plain'
            }
            
            ext = os.path.splitext(filename)[1].lower()
            mime_type = mime_types.get(ext, 'application/octet-stream')
            
            encoded = base64.b64encode(file_content).decode('utf-8')
            data_url = f"data:{mime_type};base64,{encoded}"
            
            logger.warning(f"Using fallback base64 storage for {filename}")
            return {
                'public_id': filename,
                'secure_url': data_url,
                'url': data_url,
                'format': ext.replace('.', ''),
                'resource_type': 'auto'
            }
            
        except Exception as e:
            logger.error(f"Failed to create fallback storage: {e}")
            return None
    
    def upload_cv(self, cv_content: bytes, filename: str) -> Optional[str]:
        """Upload CV using fallback storage"""
        result = self.upload_file(cv_content, filename)
        return result['secure_url'] if result else None
    
    def upload_resume(self, resume_content: bytes, filename: str) -> Optional[str]:
        """Upload resume using fallback storage"""
        result = self.upload_file(resume_content, filename)
        return result['secure_url'] if result else None

def get_storage_provider():
    """Get storage provider based on environment configuration"""
    storage = CloudinaryStorage()
    if storage.configured:
        return storage
    else:
        logger.warning("Falling back to base64 storage - files will be large!")
        return FallbackStorage()

# Global storage instance
storage = get_storage_provider()

def upload_cv_file(cv_content: bytes, filename: str) -> Optional[str]:
    """Upload CV file and return URL"""
    return storage.upload_cv(cv_content, filename)

def upload_resume_file(resume_content: bytes, filename: str) -> Optional[str]:
    """Upload resume file and return URL"""
    return storage.upload_resume(resume_content, filename)