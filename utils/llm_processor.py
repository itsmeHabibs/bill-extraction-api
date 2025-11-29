"""
LLM Processor Module - Using Hugging Face API
Handles Hugging Face-based extraction of structured data from OCR text
"""

import json
import logging
from typing import Dict, Tuple, Any
import requests
from config import Config
from prompts.extraction_prompts import ExtractionPrompts

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    Handles LLM-based extraction using Hugging Face Inference API
    """
    
    def __init__(self):
        """Initialize LLM processor with Hugging Face configuration"""
        self.api_key = Config.HF_API_KEY
        # Using new HF router endpoint (api-inference is deprecated)
        self.base_url = "https://router.huggingface.co/v1"
        # Using Mistral model - faster and better than Llama 2
        self.model = "mistralai/Mistral-7B-Instruct-v0.1"
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        
        if not self.api_key:
            raise ValueError("❌ HF_API_KEY not set in environment variables")
        
        logger.info(f"✅ LLM Processor initialized with Hugging Face model: {self.model}")
    
    def reset_token_usage(self):
        """Reset token usage counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        logger.debug("🔄 Token usage counters reset")
    
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
    
    def extract_bill_items(
        self, 
        ocr_text: str, 
        page_number: str = "1"
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Extract bill line items from OCR text using Hugging Face
        
        Args:
            ocr_text: Text extracted from bill via OCR
            page_number: Page number being processed
            
        Returns:
            Tuple of (extracted_data_dict, input_tokens, output_tokens)
        """
        logger.info(f"🤖 Starting LLM extraction for page {page_number}")
        
        try:
            # Get extraction prompt
            system_prompt = ExtractionPrompts.get_system_prompt()
            user_prompt = ExtractionPrompts.get_user_prompt(ocr_text)
            
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            logger.debug("📤 Sending request to Hugging Face API...")
            
            # Call Hugging Face API with retry logic
            response = self._call_hf_with_retry(full_prompt)
            
            if response is None:
                logger.error("❌ Hugging Face API call failed after retries")
                return {
                    "line_items": [],
                    "page_type": "Bill Detail",
                    "total_amount": 0.0,
                    "error": "API call failed"
                }, 0, 0
            
            # Extract response text
            response_text = response
            
            # Estimate tokens (rough estimate: 4 chars ≈ 1 token)
            input_tokens = len(full_prompt) // 4
            output_tokens = len(response_text) // 4
            
            # Update cumulative counters
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_tokens += (input_tokens + output_tokens)
            
            logger.info(f"✅ Hugging Face API call successful. Est. Tokens: {input_tokens + output_tokens}")
            logger.debug(f"Response text length: {len(response_text)} chars")
            
            # Parse JSON response
            extracted_data = self._parse_json_response(response_text)
            
            if not extracted_data:
                logger.warning("⚠️  Failed to parse JSON, returning empty structure")
                extracted_data = {
                    "line_items": [],
                    "page_type": "Bill Detail",
                    "total_amount": 0.0
                }
            
            item_count = len(extracted_data.get('line_items', []))
            logger.info(f"✅ Extracted {item_count} items from page {page_number}")
            
            return extracted_data, input_tokens, output_tokens
            
        except Exception as e:
            logger.error(f"❌ LLM extraction error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            # Return empty structure on error
            return {
                "line_items": [],
                "page_type": "Bill Detail",
                "total_amount": 0.0,
                "error": str(e)
            }, 0, 0
    
    def _call_hf_with_retry(self, prompt: str, retries: int = 3):
        """
        Call Hugging Face API with retry logic
        
        Args:
            prompt: Full prompt to send
            retries: Number of retries
            
        Returns:
            Response text or None
        """
        for attempt in range(retries + 1):
            try:
                logger.debug(f"🔄 Hugging Face API call (attempt {attempt + 1}/{retries + 1})")
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.1,
                    },
                    timeout=120
                )
                
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                
                # Handle OpenAI-compatible format from router
                if isinstance(result, dict):
                    if 'choices' in result and len(result['choices']) > 0:
                        # OpenAI format
                        response_text = result['choices'][0]['message']['content']
                    elif 'error' in result:
                        logger.error(f"❌ HF API error: {result['error']}")
                        if attempt < retries:
                            logger.info(f"🔄 Retrying...")
                            import time
                            time.sleep(3 * (attempt + 1))
                            continue
                        return None
                    else:
                        response_text = str(result)
                else:
                    response_text = str(result)
                
                logger.debug(f"✅ Hugging Face API request successful")
                return response_text
                
            except requests.exceptions.Timeout:
                logger.error(f"❌ Request timeout (attempt {attempt + 1})")
                if attempt < retries:
                    logger.info(f"🔄 Retrying...")
                    import time
                    time.sleep(3 * (attempt + 1))
                else:
                    return None
                    
            except requests.exceptions.HTTPError as e:
                error_msg = str(e.response.text) if hasattr(e, 'response') else str(e)
                logger.error(f"❌ HTTP error (attempt {attempt + 1}): {error_msg}")
                
                if attempt < retries:
                    logger.info(f"🔄 Retrying...")
                    import time
                    time.sleep(3 * (attempt + 1))
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Error (attempt {attempt + 1}): {e}")
                if attempt < retries:
                    logger.info(f"🔄 Retrying...")
                    import time
                    time.sleep(3 * (attempt + 1))
                else:
                    return None
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from Hugging Face response, handling markdown formatting
        
        Args:
            response_text: Raw response from Hugging Face
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Remove the original prompt if it's included in response
            if response_text.count('{') > 1:
                # Find the last occurrence of JSON
                last_brace = response_text.rfind('{')
                response_text = response_text[last_brace:]
            
            # Remove markdown code blocks if present
            clean_response = response_text.strip()
            
            # Handle various markdown formats
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            elif clean_response.startswith("```"):
                clean_response = clean_response[3:]
            
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            clean_response = clean_response.strip()
            
            logger.debug(f"🔍 Parsing JSON response...")
            parsed = json.loads(clean_response)
            
            logger.debug(f"✅ JSON parsed successfully")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected parsing error: {e}")
            return {}
    
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
        if any(word in text_lower for word in ["pharmacy", "medicine", "drug", "tablet", "capsule", "syrup"]):
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
        logger.debug("✔️  Validating extraction structure...")
        
        try:
            # Check required keys
            if "line_items" not in extracted_data:
                logger.warning("⚠️  Missing 'line_items' key")
                return False
            
            line_items = extracted_data.get("line_items", [])
            
            if not isinstance(line_items, list):
                logger.warning("⚠️  'line_items' is not a list")
                return False
            
            # Validate each line item
            for idx, item in enumerate(line_items):
                required_keys = ["item_name", "item_amount", "item_rate", "item_quantity"]
                
                if not all(key in item for key in required_keys):
                    logger.warning(f"⚠️  Item {idx} missing required keys: {list(item.keys())}")
                    return False
                
                # Validate data types
                try:
                    float(item["item_amount"])
                    float(item["item_rate"])
                    float(item["item_quantity"])
                except (ValueError, TypeError):
                    logger.warning(f"⚠️  Item {idx} has invalid numeric values")
                    return False
            
            logger.debug(f"✅ Validation passed for {len(line_items)} items")
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return False