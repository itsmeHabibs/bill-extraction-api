"""
OCR Extractor Module
Handles Optical Character Recognition for bill images
"""

import io
import logging
import requests
from typing import Optional
from PIL import Image
from config import Config

logger = logging.getLogger(__name__)


class OCRExtractor:
    """
    Extracts text from bill images using OCR
    Supports multiple OCR services: Google Vision and Tesseract
    """
    
    def __init__(self):
        """Initialize OCR extractor with configured service"""
        self.service = Config.OCR_SERVICE
        logger.info(f"🔧 Initializing OCR with service: {self.service}")
        
        # Configure Tesseract if using local OCR
        if self.service == "tesseract" and Config.TESSERACT_CMD:
            try:
                import pytesseract
                pytesseract.pytesseract.pytesseract_cmd = Config.TESSERACT_CMD
                logger.info(f"✅ Tesseract configured at: {Config.TESSERACT_CMD}")
            except Exception as e:
                logger.warning(f"⚠️  Tesseract configuration failed: {e}")
    
    
    def extract_text_from_url(self, document_url: str) -> Optional[str]:
        """
        Download image from URL and extract text using OCR
        
        Args:
            document_url: URL to the document image
            
        Returns:
            Extracted text string, or None if extraction fails
            
        Raises:
            None - Logs errors and returns None gracefully
        """
        try:
            logger.info(f"📥 Downloading document from URL...")
            
            # Download image from URL
            response = requests.get(
                document_url,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            logger.info(f"✅ Document downloaded successfully ({len(response.content)} bytes)")
            
            # Open image from bytes
            img = Image.open(io.BytesIO(response.content))
            logger.info(f"🖼️  Image loaded: {img.size} {img.format}")
            
            # Convert to RGB if necessary (handle RGBA, grayscale, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                logger.info(f"🔄 Image converted to RGB mode")
            
            # Preprocess image for better OCR
            img = self.preprocess_image(img)
            
            # Extract text based on configured service
            if self.service == "google_vision":
                extracted_text = self._extract_with_google_vision(img)
            else:
                extracted_text = self._extract_with_tesseract(img)
            
            if extracted_text:
                logger.info(f"📝 Extracted {len(extracted_text)} characters of text")
                return extracted_text
            else:
                logger.warning("⚠️  OCR returned empty text")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Request timeout while downloading document")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection error while downloading document")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to download document: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    
    def _extract_with_tesseract(self, image: Image.Image) -> str:
        """
        Extract text using Tesseract OCR (local)
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text string
        """
        try:
            import pytesseract
            logger.info("🔍 Extracting with Tesseract OCR...")
            
            text = pytesseract.image_to_string(image, lang='eng')
            
            logger.info(f"✅ Tesseract extraction successful")
            return text.strip()
            
        except ImportError:
            logger.error("❌ pytesseract not installed")
            return ""
        except Exception as e:
            logger.error(f"❌ Tesseract extraction error: {e}")
            return ""
    
    
    def _extract_with_google_vision(self, image: Image.Image) -> str:
        """
        Extract text using Google Cloud Vision API
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text string
        """
        try:
            from google.cloud import vision
            
            logger.info("🔍 Extracting with Google Cloud Vision...")
            
            client = vision.ImageAnnotatorClient()
            
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            image_content = img_byte_arr.read()
            image_obj = vision.Image(content=image_content)
            
            # Call Google Cloud Vision API
            response = client.document_text_detection(image=image_obj)
            
            # Extract full text
            if response.full_text:
                logger.info(f"✅ Google Vision extraction successful")
                return response.full_text.strip()
            else:
                logger.warning("⚠️  Google Vision returned no text")
                return ""
                
        except ImportError:
            logger.warning("⚠️  google-cloud-vision not installed, falling back to Tesseract")
            return self._extract_with_tesseract(image)
        except Exception as e:
            logger.error(f"❌ Google Vision extraction error: {e}")
            logger.info("🔄 Falling back to Tesseract...")
            return self._extract_with_tesseract(image)
    
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy
        Includes: grayscale conversion, thresholding, denoising
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image object
        """
        try:
            import cv2
            import numpy as np
            
            logger.info("🎨 Preprocessing image...")
            
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            logger.debug("  • Converted to grayscale")
            
            # Apply thresholding to get binary image
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            logger.debug("  • Applied binary threshold")
            
            # Denoise image
            denoised = cv2.fastNlMeansDenoising(thresh)
            logger.debug("  • Applied denoising")
            
            # Convert back to PIL
            result = Image.fromarray(denoised)
            logger.info("✅ Image preprocessing completed")
            return result
            
        except ImportError:
            logger.warning("⚠️  opencv-python not installed, using original image")
            return image
        except Exception as e:
            logger.warning(f"⚠️  Image preprocessing failed: {e}, using original")
            return image
    
    
    @staticmethod
    def validate_image(image: Image.Image) -> bool:
        """
        Validate that image is suitable for OCR
        
        Args:
            image: PIL Image object
            
        Returns:
            True if image is valid, False otherwise
        """
        try:
            # Check image size
            width, height = image.size
            if width < 100 or height < 100:
                logger.warning(f"⚠️  Image too small: {width}x{height}")
                return False
            
            # Check image format
            if image.format not in ['PNG', 'JPEG', 'GIF', 'BMP', 'TIFF']:
                logger.warning(f"⚠️  Unsupported image format: {image.format}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Image validation error: {e}")
            return False