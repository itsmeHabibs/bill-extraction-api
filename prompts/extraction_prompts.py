"""
Extraction Prompts for Bill Data Extraction
Contains carefully crafted prompts with guard rails
Optimized for GPT-OSS model
"""


import json


class ExtractionPrompts:
    """
    Centralized prompt management for bill extraction
    """
    
    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt for bill extraction
        
        Returns:
            System prompt string with instructions and constraints
        """
        return """You are a specialized bill data extraction system. Extract line items from bills/invoices with precision.

CRITICAL RULES:
1. Extract ONLY items with monetary values (products/services with prices)
2. DO NOT extract: dates, invoice numbers, patient IDs, reference codes, subtotals, or grand totals
3. Each line item MUST have: name, amount, rate, and quantity
4. Return ONLY valid JSON - no explanations, no markdown, no extra text

OUTPUT FORMAT (MANDATORY):
{
  "page_type": "Bill Detail" OR "Final Bill" OR "Pharmacy",
  "line_items": [
    {
      "item_name": "product/service name",
      "item_amount": numeric_value,
      "item_rate": numeric_value,
      "item_quantity": numeric_value
    }
  ],
  "total_amount": sum_of_all_amounts
}

If no line items found, return:
{
  "page_type": "Bill Detail",
  "line_items": [],
  "total_amount": 0.0
}"""

    @staticmethod
    def get_user_prompt(ocr_text: str) -> str:
        """
        Get the user prompt with OCR text
        
        Args:
            ocr_text: The OCR extracted text from bill
            
        Returns:
            User prompt string
        """
        # Truncate OCR text if too long to avoid token limits
        max_ocr_length = 3000
        if len(ocr_text) > max_ocr_length:
            ocr_text = ocr_text[:max_ocr_length] + "... (truncated)"
            
        return f"""Extract line items from this bill. Return ONLY JSON.

BILL TEXT:
{ocr_text}

INSTRUCTIONS:
- Find items with name, quantity, rate, and amount
- Ignore dates, IDs, reference numbers
- Return ONLY the JSON structure shown in system prompt
- If no items found, return empty line_items array

JSON OUTPUT:"""

    @staticmethod
    def get_validation_prompt(extracted_items: list, ocr_text: str) -> str:
        """
        Get validation prompt to verify extraction quality
        
        Args:
            extracted_items: List of extracted items
            ocr_text: Original OCR text
            
        Returns:
            Validation prompt string
        """
        return f"""Review this extraction and verify accuracy.

ORIGINAL BILL:
{ocr_text[:1000]}

EXTRACTED ITEMS:
{json.dumps(extracted_items, indent=2)}

VALIDATE:
1. Are all actual line items captured?
2. Any dates/IDs incorrectly included?
3. Do amounts match the bill?
4. Any duplicates?

Return JSON:
{{
  "is_valid": true/false,
  "issues": ["list issues"],
  "corrected_items": [corrected list if needed]
}}"""
    
    @staticmethod
    def get_retry_prompt(ocr_text: str, previous_response: str) -> str:
        """
        Get retry prompt when first extraction fails
        
        Args:
            ocr_text: Original OCR text
            previous_response: Previous failed response
            
        Returns:
            Retry prompt string
        """
        return f"""The previous extraction failed. Try again with this bill.

BILL TEXT:
{ocr_text[:2000]}

PREVIOUS FAILED RESPONSE:
{previous_response[:500]}

REQUIREMENTS:
- You MUST return valid JSON
- Use this exact structure:
{{
  "page_type": "Bill Detail",
  "line_items": [
    {{"item_name": "name", "item_amount": 0.0, "item_rate": 0.0, "item_quantity": 0.0}}
  ],
  "total_amount": 0.0
}}
- If no items found, return empty line_items array
- NO markdown, NO explanations, ONLY JSON

JSON OUTPUT:"""