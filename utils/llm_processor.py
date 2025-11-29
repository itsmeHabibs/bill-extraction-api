"""
LLM Processor - Handles interaction with Grok API
Extracts structured data from OCR text
"""

import json
import logging
import requests
from typing import Dict, List, Tuple, Any
from config import Config
from prompts.extraction_prompts import ExtractionPrompts

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    Handles LLM-based extraction using Grok API
    """
    
    def __init__(self):
        """Initialize LLM processor with Grok configuration"""
        self.api_key = Config.GROK_API_KEY
        self.base_url = Config.GROK_API_BASE_URL
        self.model = Config.GROK_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        
        logger.info(f"✅ LLM Processor initialized with model: {self.model}")
    
    def reset_token_usage(self):
        """Reset token usage counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
    
    def get_token_usage(self) -> Dict[str, int]:
        """
        Get cumulative token usage
        
        Returns:
            Dictionary with token counts
        """
        return {
            "total_tokens": self.total_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens
        }
    
    def _call_grok_api(self, messages: List[Dict[str, str]]) -> Tuple[str, int, int]:
        """
        Make API call to Grok
        
        Args:
            messages: List of message dictionaries with role and content
            
        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            logger.debug(f"🔄 Calling Grok API...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract response text
            response_text = result['choices'][0]['message']['content']
            
            # Extract token usage
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            # Update cumulative counters
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_tokens += (input_tokens + output_tokens)
            
            logger.info(f"✅ Grok API call successful. Tokens: {input_tokens + output_tokens}")
            
            return response_text, input_tokens, output_tokens
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Grok API call failed: {e}")
            raise Exception(f"Failed to call Grok API: {str(e)}")
    
    def extract_bill_items(
        self, 
        ocr_text: str, 
        page_number: str = "1"
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Extract bill line items from OCR text using Grok
        
        Args:
            ocr_text: Text extracted from bill via OCR
            page_number: Page number being processed
            
        Returns:
            Tuple of (extracted_data_dict, input_tokens, output_tokens)
        """
        logger.info(f"🤖 Starting LLM extraction for page {page_number}")
        
        # Get extraction prompt
        system_prompt = ExtractionPrompts.get_system_prompt()
        user_prompt = ExtractionPrompts.get_user_prompt(ocr_text)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call Grok API
        response_text, input_tokens, output_tokens = self._call_grok_api(messages)
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            clean_response = response_text.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            extracted_data = json.loads(clean_response)
            
            logger.info(f"✅ Successfully parsed {len(extracted_data.get('line_items', []))} items")
            
            return extracted_data, input_tokens, output_tokens
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            
            # Return empty structure if parsing fails
            return {
                "line_items": [],
                "page_type": "Bill Detail",
                "total_amount": 0.0
            }, input_tokens, output_tokens
    
    def identify_page_type(self, ocr_text: str) -> str:
        """
        Identify the type of bill page
        
        Args:
            ocr_text: Text extracted from page
            
        Returns:
            Page type: "Bill Detail", "Final Bill", or "Pharmacy"
        """
        text_lower = ocr_text.lower()
        
        # Simple keyword-based classification
        if "pharmacy" in text_lower or "medicine" in text_lower or "drug" in text_lower:
            return "Pharmacy"
        elif "final" in text_lower and "bill" in text_lower:
            return "Final Bill"
        else:
            return "Bill Detail"
    
    def validate_extraction(self, extracted_data: Dict[str, Any]) -> bool:
        """
        Validate extracted data structure
        
        Args:
            extracted_data: Dictionary with extracted line items
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ["line_items"]
        
        if not all(key in extracted_data for key in required_keys):
            logger.warning("⚠️  Missing required keys in extraction")
            return False
        
        line_items = extracted_data.get("line_items", [])
        
        if not isinstance(line_items, list):
            logger.warning("⚠️  line_items is not a list")
            return False
        
        # Validate each line item
        for item in line_items:
            required_item_keys = ["item_name", "item_amount", "item_rate", "item_quantity"]
            if not all(key in item for key in required_item_keys):
                logger.warning(f"⚠️  Line item missing required keys: {item}")
                return False
        
        return True