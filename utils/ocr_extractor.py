"""
OCR Extractor - Extracts text from document images
Supports Tesseract OCR
"""

import logging
import requests
from io import BytesIO
from PIL import Image
import pytesseract
from config import Config

logger = logging.getLogger(__name__)


class OCRExtractor:
    """
    Handles OCR text extraction from document images
    """
    
    def __init__(self):
        """Initialize OCR extractor"""
        self.ocr_service = Config.OCR_SERVICE
        
        # Set Tesseract command path if specified
        if Config.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
        
        logger.info(f"✅ OCR Extractor initialized with service: {self.ocr_service}")
    
    def extract_text_from_url(self, image_url: str) -> str:
        """
        Extract text from image URL using OCR
        
        Args:
            image_url: URL of the document image
            
        Returns:
            Extracted text string
        """
        logger.info(f"🔍 Starting OCR extraction from URL")
        
        try:
            # Download image
            logger.debug(f"📥 Downloading image from URL...")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Open image
            image = Image.open(BytesIO(response.content))
            logger.info(f"✅ Image loaded successfully. Size: {image.size}")
            
            # Preprocess image
            image = self._preprocess_image(image)
            
            # Extract text using Tesseract
            text = self._extract_with_tesseract(image)
            
            logger.info(f"✅ OCR extraction complete. Text length: {len(text)} chars")
            return text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to download image: {e}")
            raise Exception(f"Failed to download image from URL: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            raise Exception(f"Failed to extract text from image: {str(e)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        logger.debug("🔧 Preprocessing image...")
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (max 4000px on longest side)
        max_size = 4000
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.debug(f"📏 Resized image to {new_size}")
        
        return image
    
    def _extract_with_tesseract(self, image: Image.Image) -> str:
        """
        Extract text using Tesseract OCR
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text
        """
        logger.debug("🔤 Running Tesseract OCR...")
        
        try:
            # Configure Tesseract
            custom_config = r'--oem 3 --psm 6'
            
            # Extract text
            text = pytesseract.image_to_string(
                image,
                config=custom_config,
                lang='eng'
            )
            
            # Clean text
            text = self._clean_text(text)
            
            return text
            
        except pytesseract.TesseractNotFoundError:
            logger.error("❌ Tesseract not found. Please install Tesseract OCR.")
            raise Exception(
                "Tesseract OCR not found. Please install: "
                "https://github.com/tesseract-ocr/tesseract"
            )
        
        except Exception as e:
            logger.error(f"❌ Tesseract extraction failed: {e}")
            raise Exception(f"Tesseract OCR failed: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        
        cleaned_text = '\n'.join(lines)
        return cleaned_text