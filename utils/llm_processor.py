"""
LLM Processor Module
Handles Claude AI-based extraction of structured data from OCR text
"""

import json
import logging
from typing import Dict, Tuple, Optional
from anthropic import Anthropic
from config import Config

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    Processes OCR text using Claude LLM to extract structured bill data
    Tracks token usage for all API calls
    """
    
    def __init__(self):
        """Initialize LLM processor with Claude client"""
        self.client = Anthropic()
        self.model = Config.CLAUDE_MODEL
        
        # Token tracking
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        
        logger.info(f"🤖 Initialized LLM Processor with model: {self.model}")
    
    
    def extract_bill_items(
        self,
        ocr_text: str,
        page_number: str = "1"
    ) -> Tuple[Dict, int, int]:
        """
        Extract bill items from OCR text using Claude
        
        Args:
            ocr_text: Text extracted from OCR
            page_number: Page number for reference
            
        Returns:
            Tuple of (extracted_data_dict, input_tokens, output_tokens)
        """
        try:
            logger.info(f"📋 Extracting bill items from page {page_number}...")
            
            # Create extraction prompt with guard rails
            prompt = self._create_extraction_prompt(ocr_text, page_number)
            
            # Call Claude API
            logger.debug("📤 Sending request to Claude API...")
            message = self.client.messages.create(
                model=self.model,
                max_tokens=Config.MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Track tokens
            input_tok = message.usage.input_tokens
            output_tok = message.usage.output_tokens
            
            self.input_tokens += input_tok
            self.output_tokens += output_tok
            self.total_tokens += (input_tok + output_tok)
            
            logger.debug(f"📊 Tokens used - Input: {input_tok}, Output: {output_tok}")
            
            # Parse response
            response_text = message.content[0].text
            extracted_data = self._parse_json_response(response_text)
            
            if extracted_data and "line_items" in extracted_data:
                item_count = len(extracted_data.get("line_items", []))
                logger.info(f"✅ Extracted {item_count} items from page {page_number}")
            else:
                logger.warning(f"⚠️  No line items found in extraction")
            
            return extracted_data, input_tok, output_tok
            
        except Exception as e:
            logger.error(f"❌ LLM extraction error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {"line_items": [], "error": str(e)}, 0, 0
    
    
    def validate_extraction(self, extracted_data: Dict) -> Tuple[Dict, int, int]:
        """
        Validate extracted data using Claude
        
        Args:
            extracted_data: Data extracted from OCR/LLM
            
        Returns:
            Tuple of (validation_result, input_tokens, output_tokens)
        """
        try:
            logger.info("🔍 Validating extraction quality...")
            
            prompt = self._create_validation_prompt(extracted_data)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            input_tok = message.usage.input_tokens
            output_tok = message.usage.output_tokens
            
            self.input_tokens += input_tok
            self.output_tokens += output_tok
            self.total_tokens += (input_tok + output_tok)
            
            response_text = message.content[0].text
            validation_result = self._parse_json_response(response_text)
            
            logger.info(f"✅ Validation complete")
            return validation_result, input_tok, output_tok
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return {"is_valid": False, "error": str(e)}, 0, 0
    
    
    def reconcile_totals(
        self,
        line_items: list,
        claimed_total: float
    ) -> Tuple[Dict, int, int]:
        """
        Reconcile extracted totals with claimed totals
        
        Args:
            line_items: List of extracted line items
            claimed_total: Total amount claimed in bill
            
        Returns:
            Tuple of (reconciliation_result, input_tokens, output_tokens)
        """
        try:
            logger.info("📊 Reconciling totals...")
            
            prompt = self._create_reconciliation_prompt(line_items, claimed_total)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            input_tok = message.usage.input_tokens
            output_tok = message.usage.output_tokens
            
            self.input_tokens += input_tok
            self.output_tokens += output_tok
            self.total_tokens += (input_tok + output_tok)
            
            response_text = message.content[0].text
            reconciliation_result = self._parse_json_response(response_text)
            
            logger.info(f"✅ Reconciliation complete")
            return reconciliation_result, input_tok, output_tok
            
        except Exception as e:
            logger.error(f"❌ Reconciliation error: {e}")
            return {"matches": False, "error": str(e)}, 0, 0
    
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse JSON from LLM response, handling markdown formatting
        
        Args:
            response_text: Raw response from Claude
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            response_text = response_text.strip()
            parsed = json.loads(response_text)
            
            logger.debug(f"✅ JSON parsed successfully")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {}
    
    
    def _create_extraction_prompt(self, ocr_text: str, page_number: str) -> str:
        """
        Create extraction prompt with explicit guard rails
        
        Args:
            ocr_text: OCR extracted text
            page_number: Page number
            
        Returns:
            Prompt string for Claude
        """
        return f"""You are a precise bill data extraction specialist. Extract ONLY line items that represent products/services sold.

**CRITICAL RULES - FOLLOW EXACTLY:**

1. EXTRACT ONLY real line items (products/services with prices)
2. NEVER include as line items:
   - Invoice dates, times, or IDs (e.g., "2024-01-15", "INV-001", "REF-123")
   - Customer information or identifiers
   - Page numbers, timestamps
   - Subtotals, taxes, or fees that aren't separate line items
   - Non-monetary identifiers

3. VALIDATION CHECKS:
   - item_name: Must be product/service name, NOT a date or ID
   - item_quantity: Must be a positive number
   - item_rate: Must be a positive number (price per unit)
   - item_amount: Must equal (quantity × rate), approximately

4. GUARD AGAINST ERRORS:
   - ❌ "2024-01-15" is a DATE, NOT an amount
   - ❌ "INV-001" is an ID, NOT an amount
   - ✅ "Aspirin 500mg" with amount 250.50 is correct
   - ✅ "Quantity: 5, Rate: 50.10, Amount: 250.50" is correct

**EXTRACTION TASK:**

From this bill text (Page {page_number}), extract ALL real line items:

---
{ocr_text}
---

**RETURN ONLY THIS EXACT JSON (no markdown, no extra text):**

{{
  "page_type": "Bill Detail",
  "line_items": [
    {{
      "item_name": "exact product/service name",
      "item_quantity": 1,
      "item_rate": 100.00,
      "item_amount": 100.00
    }}
  ],
  "extraction_notes": "any issues found"
}}

**MANDATORY VALIDATION BEFORE RETURNING:**
- ✓ All item_names are NOT dates/IDs/timestamps
- ✓ All amounts are positive numbers
- ✓ Each item_amount ≈ item_quantity × item_rate
- ✓ No duplicate entries
- ✓ No metadata values in amount fields

NOW EXTRACT:"""
    
    
    def _create_validation_prompt(self, extracted_data: Dict) -> str:
        """
        Create validation prompt
        
        Args:
            extracted_data: Extracted data to validate
            
        Returns:
            Prompt string for Claude
        """
        return f"""Validate this bill extraction. Check for:
1. Are all item_names products/services (NOT dates like 2024-01-15 or IDs)?
2. Are quantities and rates positive numbers?
3. Does item_amount ≈ quantity × rate for each item?
4. Are there duplicate entries?
5. Is the data structure valid?

Extracted Data:
{json.dumps(extracted_data, indent=2)}

Return ONLY JSON:
{{
  "is_valid": true/false,
  "issues": ["list of issues"],
  "confidence": 0.0_to_1.0
}}"""
    
    
    def _create_reconciliation_prompt(self, line_items: list, claimed_total: float) -> str:
        """
        Create reconciliation prompt
        
        Args:
            line_items: Extracted line items
            claimed_total: Claimed bill total
            
        Returns:
            Prompt string for Claude
        """
        return f"""Reconcile these bill items with claimed total:

Items:
{json.dumps(line_items, indent=2)}

Claimed Total: {claimed_total}

Calculate:
1. Sum of all item_amounts
2. Variance from claimed total
3. Reconciliation status

Return ONLY JSON:
{{
  "calculated_total": 0.0,
  "claimed_total": {claimed_total},
  "matches": true/false,
  "variance": 0.0,
  "variance_percentage": 0.0,
  "status": "perfect|acceptable|needs_review"
}}"""
    
    
    def get_token_usage(self) -> Dict:
        """
        Get cumulative token usage
        
        Returns:
            Dictionary with token counts
        """
        return {
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens
        }
    
    
    def reset_token_usage(self):
        """Reset token counters for new extraction"""
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        logger.info("🔄 Token usage reset")