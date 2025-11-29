"""
Aggressive LLM Processor - Forces the model to extract properly
Uses multiple strategies to get valid JSON
"""

import json
import logging
import time
import re
from typing import Dict, Tuple, Any
import requests
import os
from config import Config
from prompts.extraction_prompts import ExtractionPrompts

logger = logging.getLogger(__name__)


class LLMProcessor:
    """Ultra-aggressive extraction that forces results"""
    
    def __init__(self):
        """Initialize with Groq"""
        self.api_key = Config.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "openai/gpt-oss-20b"
        
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        
        if not self.api_key:
            raise ValueError("❌ GROQ_API_KEY not set")
        
        logger.info(f"✅ LLM Processor initialized: {self.model}")
    
    def reset_token_usage(self):
        """Reset counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get token usage"""
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
        Extract with MAXIMUM aggression - try everything
        """
        logger.info(f"🤖 Aggressive extraction for page {page_number}")
        
        try:
            # Get prompts
            system_prompt = ExtractionPrompts.get_system_prompt()
            user_prompt = ExtractionPrompts.get_user_prompt(ocr_text)
            
            # Try main extraction
            response = self._call_groq_with_retry(system_prompt, user_prompt)
            
            if response is None:
                logger.error("❌ All attempts failed")
                return self._empty_result()
            
            result = response.json()
            response_text = result['choices'][0]['message']['content']
            input_tokens = result.get('usage', {}).get('prompt_tokens', 0)
            output_tokens = result.get('usage', {}).get('completion_tokens', 0)
            
            # Update tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_tokens += (input_tokens + output_tokens)
            
            logger.info(f"✅ Got response. Tokens: {input_tokens + output_tokens}")
            logger.debug(f"Response: {response_text[:300]}")
            
            # Try to parse
            extracted_data = self._aggressive_parse(response_text)
            
            if extracted_data and extracted_data.get('line_items'):
                item_count = len(extracted_data['line_items'])
                logger.info(f"✅ Extracted {item_count} items")
                return extracted_data, input_tokens, output_tokens
            
            # Failed - try retry
            logger.warning("⚠️  No items, trying retry...")
            retry_prompt = ExtractionPrompts.get_retry_prompt(ocr_text, response_text[:500])
            retry_response = self._call_groq_with_retry(system_prompt, retry_prompt, retries=1)
            
            if retry_response:
                retry_result = retry_response.json()
                retry_text = retry_result['choices'][0]['message']['content']
                input_tokens += retry_result.get('usage', {}).get('prompt_tokens', 0)
                output_tokens += retry_result.get('usage', {}).get('completion_tokens', 0)
                
                extracted_data = self._aggressive_parse(retry_text)
                
                if extracted_data and extracted_data.get('line_items'):
                    item_count = len(extracted_data['line_items'])
                    logger.info(f"✅ Retry succeeded! {item_count} items")
                    return extracted_data, input_tokens, output_tokens
            
            # Still failed - return empty but valid
            logger.warning("⚠️  Returning empty result")
            return self._empty_result()[0], input_tokens, output_tokens
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return self._empty_result()
    
    def _empty_result(self) -> Tuple[Dict[str, Any], int, int]:
        """Return valid empty result"""
        return {
            "line_items": [],
            "page_type": "Bill Detail",
            "total_amount": 0.0
        }, 0, 0
    
    def _call_groq_with_retry(self, system_prompt: str, user_prompt: str, retries: int = 2):
        """Call with aggressive retry"""
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.0,  # Zero temperature for consistency
                        "response_format": {"type": "json_object"}  # Force JSON
                    },
                    timeout=60
                )
                
                response.raise_for_status()
                logger.debug(f"✅ Success on attempt {attempt + 1}")
                return response
                
            except requests.exceptions.HTTPError as e:
                error_msg = str(e.response.text) if hasattr(e, 'response') else str(e)
                
                # Rate limit
                if "rate_limit" in error_msg.lower():
                    if attempt < retries:
                        wait = 5 + (attempt * 2)
                        logger.warning(f"⏳ Rate limit - waiting {wait}s...")
                        time.sleep(wait)
                        continue
                
                logger.error(f"❌ HTTP error: {error_msg[:200]}")
                if attempt < retries:
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                if attempt < retries:
                    time.sleep(2)
        
        return None
    
    def _aggressive_parse(self, response_text: str) -> Dict[str, Any]:
        """
        ULTRA-AGGRESSIVE parsing - extract JSON no matter what
        """
        try:
            # Clean the response
            clean = response_text.strip()
            
            if not clean:
                return {}
            
            # Remove markdown
            clean = re.sub(r'```json\s*', '', clean)
            clean = re.sub(r'```\s*', '', clean)
            clean = clean.strip()
            
            # Find JSON object
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
            if json_match:
                clean = json_match.group(0)
            else:
                logger.error("No JSON found in response")
                return {}
            
            # Parse
            parsed = json.loads(clean)
            
            # Validate structure
            if not isinstance(parsed, dict):
                return {}
            
            if 'line_items' not in parsed:
                parsed['line_items'] = []
            
            if 'page_type' not in parsed:
                parsed['page_type'] = "Bill Detail"
            
            if 'total_amount' not in parsed:
                parsed['total_amount'] = 0.0
            
            logger.debug(f"✅ Parsed {len(parsed.get('line_items', []))} items")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON error: {e}")
            logger.error(f"Text: {response_text[:500]}")
            return {}
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return {}
    
    def identify_page_type(self, ocr_text: str) -> str:
        """Identify page type"""
        text_lower = ocr_text.lower()
        
        if any(word in text_lower for word in ["pharmacy", "medicine", "drug"]):
            return "Pharmacy"
        elif "final" in text_lower:
            return "Final Bill"
        else:
            return "Bill Detail"
    
    def validate_extraction(self, extracted_data: Dict[str, Any]) -> bool:
        """Validate"""
        try:
            if "line_items" not in extracted_data:
                return False
            
            line_items = extracted_data.get("line_items", [])
            if not isinstance(line_items, list):
                return False
            
            for item in line_items:
                required = ["item_name", "item_amount", "item_rate", "item_quantity"]
                if not all(key in item for key in required):
                    return False
                
                try:
                    float(item["item_amount"])
                    float(item["item_rate"])
                    float(item["item_quantity"])
                except:
                    return False
            
            return True
        except:
            return False