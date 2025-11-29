"""
Extraction Prompts for Bill Data Extraction
Contains carefully crafted prompts with guard rails
"""


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
        return """You are an expert bill/invoice data extraction AI. Your task is to extract line item details from bill text with extreme accuracy.

**CRITICAL RULES - MUST FOLLOW:**

1. **Identify ONLY Monetary Line Items:**
   - Extract only items that have a price/amount associated with them
   - DO NOT extract dates, invoice numbers, patient IDs, or reference numbers as line items
   - DO NOT extract subtotals or grand totals as individual line items

2. **Required Fields for Each Line Item:**
   - item_name: The exact name/description of the product or service
   - item_amount: The NET amount (final price after any discounts)
   - item_rate: The price per unit
   - item_quantity: The number of units

3. **Currency Values Only:**
   - item_amount, item_rate must represent money (₹, $, etc.)
   - If a number represents date, ID, or reference - DO NOT include it

4. **Page Type Classification:**
   - Identify if page is "Bill Detail", "Final Bill", or "Pharmacy"

5. **Output Format:**
   - Return ONLY valid JSON
   - No markdown, no explanations, no preamble
   - Use the exact structure specified

**Example of CORRECT extraction:**
```json
{
  "page_type": "Pharmacy",
  "line_items": [
    {
      "item_name": "Paracetamol 500mg",
      "item_amount": 120.50,
      "item_rate": 12.05,
      "item_quantity": 10.0
    }
  ],
  "total_amount": 120.50
}
```

**Example of INCORRECT - DO NOT DO THIS:**
```json
{
  "line_items": [
    {
      "item_name": "Invoice Date",
      "item_amount": 20251129  // WRONG - This is a date!
    },
    {
      "item_name": "Patient ID",
      "item_amount": 12345  // WRONG - This is an ID!
    }
  ]
}
```

Remember: Only extract actual purchasable items with prices. Dates, IDs, and reference numbers are NOT line items."""

    @staticmethod
    def get_user_prompt(ocr_text: str) -> str:
        """
        Get the user prompt with OCR text
        
        Args:
            ocr_text: The OCR extracted text from bill
            
        Returns:
            User prompt string
        """
        return f"""Extract all line items from this bill text. Follow the rules strictly.

**Bill Text:**
{ocr_text}

**Instructions:**
1. Find all items that have a name, quantity, rate, and amount
2. Ignore any dates, invoice numbers, patient IDs, reference numbers
3. Calculate total_amount as sum of all item_amounts
4. Return ONLY the JSON structure, no extra text

**Required JSON Structure:**
{{
  "page_type": "Bill Detail" or "Final Bill" or "Pharmacy",
  "line_items": [
    {{
      "item_name": "exact name from bill",
      "item_amount": numeric_value,
      "item_rate": numeric_value,
      "item_quantity": numeric_value
    }}
  ],
  "total_amount": sum_of_all_item_amounts
}}

Extract now:"""

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
        return f"""Review this extraction and verify it's correct.

**Original Bill Text:**
{ocr_text}

**Extracted Items:**
{extracted_items}

**Validation Questions:**
1. Are all actual line items captured?
2. Are there any dates, IDs, or non-monetary values incorrectly included?
3. Do the amounts match the bill?
4. Is anything double-counted?

Respond with:
{{
  "is_valid": true/false,
  "issues": ["list of any issues found"],
  "corrected_items": [corrected list if needed]
}}"""