"""
LLM Processor Module - Grok API Integration
Handles bill line item extraction using Grok API with advanced features:
- Multi-page support with deduplication
- Total reconciliation and validation
- Token usage tracking
- Retry logic with exponential backoff
"""

import json
import logging
import time
from typing import Dict, Tuple, Any, List
import requests
from config import Config
from prompts.extraction_prompts import ExtractionPrompts

logger = logging.getLogger(__name__)


class LineItem:
    """Represents a single line item from a bill"""
    
    def __init__(self, item_name: str, item_amount: float, 
                 item_rate: float, item_quantity: float):
        self.item_name = item_name
        self.item_amount = round(item_amount, 2)
        self.item_rate = round(item_rate, 2)
        self.item_quantity = round(item_quantity, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "item_name": self.item_name,
            "item_amount": self.item_amount,
            "item_rate": self.item_rate,
            "item_quantity": self.item_quantity
        }
    
    def get_hash_key(self) -> Tuple:
        """Get hashable key for duplicate detection"""
        return (
            self.item_name.lower().strip(),
            self.item_amount,
            self.item_quantity
        )
    
    def is_valid(self) -> bool:
        """Check if item has valid data"""
        return (
            self.item_name and 
            self.item_amount > 0 and 
            self.item_rate > 0 and 
            self.item_quantity > 0
        )


class GrokAPIClient:
    """Grok API client with retry logic and token tracking"""
    
    def __init__(self, api_key: str):
        """
        Initialize Grok API client
        
        Args:
            api_key: Grok API key
        """
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama-3.1-8b-instant"
        self.max_retries = 3
        self.initial_retry_delay = 2
        
        logger.info(f"✅ Grok API client initialized with model: {self.model}")
    
    def call(self, messages: List[Dict[str, str]], 
             max_tokens: int = 4000) -> Tuple[str, int, int]:
        """
        Call Grok API with retry logic
        
        Args:
            messages: List of message dictionaries (role, content)
            max_tokens: Maximum tokens in response
            
        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
            
        Raises:
            Exception: If all retries fail
        """
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"🔄 Grok API call attempt {attempt + 1}/{self.max_retries + 1}")
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.1
                    },
                    timeout=60
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract response and tokens
                response_text = result['choices'][0]['message']['content']
                input_tokens = result.get('usage', {}).get('prompt_tokens', 0)
                output_tokens = result.get('usage', {}).get('completion_tokens', 0)
                
                logger.info(f"✅ Grok API call successful. Tokens: {input_tokens + output_tokens}")
                return response_text, input_tokens, output_tokens
                
            except requests.exceptions.HTTPError as e:
                error_msg = str(e.response.text if hasattr(e, 'response') else e)
                logger.error(f"❌ HTTP Error (attempt {attempt + 1}): {error_msg}")
                
                if attempt < self.max_retries:
                    delay = self.initial_retry_delay * (2 ** attempt)
                    logger.info(f"🔄 Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise Exception(f"Grok API failed after {self.max_retries + 1} attempts: {error_msg}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"❌ Request timeout (attempt {attempt + 1})")
                if attempt < self.max_retries:
                    delay = self.initial_retry_delay * (2 ** attempt)
                    logger.info(f"🔄 Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise Exception("Grok API timeout after all retries")
                    
            except Exception as e:
                logger.error(f"❌ Error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries:
                    delay = self.initial_retry_delay * (2 ** attempt)
                    logger.info(f"🔄 Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise


class LLMProcessor:
    """
    Main LLM processor for bill extraction
    Handles multi-page bills, deduplication, and total reconciliation
    """
    
    def __init__(self):
        """Initialize LLM processor with Grok API client"""
        try:
            self.api_client = GrokAPIClient(Config.GROK_API_KEY)
            
            # Token tracking
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_tokens = 0
            
            # Item tracking for deduplication
            self.seen_items: Dict[Tuple, LineItem] = {}
            self.all_items: List[LineItem] = []
            
            logger.info("✅ LLM Processor initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM Processor: {e}")
            raise
    
    def reset_token_usage(self) -> None:
        """Reset token usage counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        logger.debug("🔄 Token usage counters reset")
    
    def reset_items(self) -> None:
        """Reset item tracking for new extraction"""
        self.seen_items.clear()
        self.all_items.clear()
        logger.debug("🔄 Item tracking reset")
    
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
        Extract bill line items from OCR text using Grok
        
        Args:
            ocr_text: Clean OCR-extracted text from bill
            page_number: Current page number
            
        Returns:
            Tuple of (extracted_data_dict, input_tokens, output_tokens)
        """
        logger.info(f"🤖 Starting extraction for page {page_number}")
        
        try:
            # Identify page type
            page_type = self._identify_page_type(ocr_text)
            logger.info(f"📄 Page type identified: {page_type}")
            
            # Create extraction prompt
            prompt = ExtractionPrompts.get_extraction_prompt(ocr_text, page_number)
            
            # Call Grok API
            messages = [{"role": "user", "content": prompt}]
            response_text, input_tok, output_tok = self.api_client.call(messages)
            
            # Update token counters
            self.total_input_tokens += input_tok
            self.total_output_tokens += output_tok
            self.total_tokens += (input_tok + output_tok)
            
            logger.debug(f"📊 Token usage: input={input_tok}, output={output_tok}")
            
            # Parse JSON response
            extracted_data = self._parse_json_response(response_text)
            
            if not extracted_data:
                logger.warning("⚠️  Failed to parse JSON response")
                return {
                    "page_type": page_type,
                    "line_items": [],
                    "subtotal": None
                }, input_tok, output_tok
            
            # Extract and validate line items
            line_items = self._process_line_items(
                extracted_data.get("line_items", []),
                page_number
            )
            
            logger.info(f"✅ Extracted {len(line_items)} valid items from page {page_number}")
            
            return {
                "page_type": page_type,
                "line_items": [item.to_dict() for item in line_items],
                "subtotal": extracted_data.get("subtotal"),
                "page_total": extracted_data.get("page_total")
            }, input_tok, output_tok
            
        except Exception as e:
            logger.error(f"❌ Extraction error on page {page_number}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "page_type": "Bill Detail",
                "line_items": [],
                "error": str(e)
            }, 0, 0
    
    def _identify_page_type(self, ocr_text: str) -> str:
        """
        Identify page type from OCR text
        
        Args:
            ocr_text: OCR text to analyze
            
        Returns:
            Page type: "Bill Detail", "Final Bill", or "Pharmacy"
        """
        text_lower = ocr_text.lower()
        
        # Check for pharmacy indicators
        if any(word in text_lower for word in [
            "pharmacy", "medicine", "drug", "tablet", "capsule", 
            "syrup", "injection", "pharmaceutical", "rx"
        ]):
            return "Pharmacy"
        
        # Check for final bill indicators
        if any(phrase in text_lower for phrase in [
            "final bill", "final total", "amount due", "total due", "grand total"
        ]):
            return "Final Bill"
        
        return "Bill Detail"
    
    def _process_line_items(
        self,
        items_data: List[Dict],
        page_number: str
    ) -> List[LineItem]:
        """
        Process and deduplicate line items
        
        Args:
            items_data: Raw line item data from LLM
            page_number: Page number for logging
            
        Returns:
            List of validated LineItem objects
        """
        processed_items = []
        
        for idx, item_data in enumerate(items_data):
            try:
                # Extract fields
                item_name = str(item_data.get("item_name", "")).strip()
                item_amount = float(item_data.get("item_amount", 0))
                item_rate = float(item_data.get("item_rate", 0))
                item_quantity = float(item_data.get("item_quantity", 0))
                
                # Create LineItem
                item = LineItem(item_name, item_amount, item_rate, item_quantity)
                
                # Validate
                if not item.is_valid():
                    logger.warning(
                        f"⚠️  Invalid item on page {page_number}, index {idx}: "
                        f"name={item_name}, amount={item_amount}"
                    )
                    continue
                
                # Check for duplicates
                hash_key = item.get_hash_key()
                if hash_key in self.seen_items:
                    logger.info(
                        f"🚫 Duplicate detected on page {page_number}: {item_name}"
                    )
                    continue
                
                # Add to tracking
                self.seen_items[hash_key] = item
                self.all_items.append(item)
                processed_items.append(item)
                
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"⚠️  Failed to process item on page {page_number}, index {idx}: {e}"
                )
                continue
        
        return processed_items
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from Grok response
        
        Args:
            response_text: Raw response from Grok
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Remove markdown if present
            clean_text = response_text.strip()
            
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            parsed = json.loads(clean_text)
            logger.debug("✅ JSON parsed successfully")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            logger.debug(f"Response preview: {response_text[:300]}")
            return {}
        except Exception as e:
            logger.error(f"❌ Parsing error: {e}")
            return {}
    
    def get_deduplication_report(self) -> Dict[str, Any]:
        """
        Get deduplication statistics
        
        Returns:
            Report with duplicate counts
        """
        return {
            "total_unique_items": len(self.all_items),
            "total_seen_hashes": len(self.seen_items),
            "duplicates_prevented": len(self.seen_items) - len(self.all_items)
        }
    
    def get_reconciliation_report(self, claimed_total: float) -> Dict[str, Any]:
        """
        Generate reconciliation report
        
        Args:
            claimed_total: Total claimed on bill
            
        Returns:
            Reconciliation report with variance analysis
        """
        calculated_total = sum(item.item_amount for item in self.all_items)
        variance = abs(calculated_total - claimed_total)
        variance_pct = (variance / claimed_total * 100) if claimed_total > 0 else 0
        
        status = "perfect" if variance < 0.01 else \
                 "acceptable" if variance_pct < 1 else \
                 "needs_review"
        
        return {
            "calculated_total": round(calculated_total, 2),
            "claimed_total": round(claimed_total, 2),
            "variance": round(variance, 2),
            "variance_percentage": round(variance_pct, 2),
            "status": status,
            "item_count": len(self.all_items)
        }