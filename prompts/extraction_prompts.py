"""
Extraction Prompts for Grok API
Optimized for accurate bill line item extraction with guardrails
"""


from typing import List


class ExtractionPrompts:
    """Centralized prompt management for bill extraction"""
    
    @staticmethod
    def get_extraction_prompt(ocr_text: str, page_number: str = "1") -> str:
        """
        Generate extraction prompt for Grok API
        
        Args:
            ocr_text: OCR-extracted text from bill
            page_number: Current page number
            
        Returns:
            Extraction prompt string
        """
        return f"""You are an expert bill data extraction AI. Extract line items from bills with 100% accuracy.

CRITICAL RULES - MUST FOLLOW:
1. EXTRACT ONLY monetary line items (products/services with amounts)
2. NEVER extract as line items:
   - Invoice dates, times (e.g., "2024-01-15", "14:30")
   - Invoice/reference numbers (e.g., "INV-001", "REF-123", "BILL-456")
   - Customer IDs or patient IDs (e.g., "CUST-789", "PAT-001")
   - Page numbers, amounts due labels
   - Subtotal rows or grand total rows (extract separately if present)
3. Each line item MUST have all 4 fields:
   - item_name: Product/service name (string)
   - item_quantity: Number of units (float, positive)
   - item_rate: Price per unit (float, positive)
   - item_amount: Total amount for item (float, positive)
4. Validate: item_amount should approximately equal item_quantity × item_rate

GUARDRAILS - PREVENT ERRORS:
✓ "Paracetamol 500mg Tab" → Valid product name
✗ "2024-01-15" → Date, not product
✗ "INV-12345" → Invoice number, not product
✗ "Total" → Metadata, not product
✓ amount_fields must be > 0

PAGE CONTEXT:
This is page {page_number} of the bill. Extract all line items visible.

RESPONSE FORMAT - Return ONLY valid JSON:
{{
  "page_type": "Bill Detail|Final Bill|Pharmacy",
  "line_items": [
    {{
      "item_name": "Product name",
      "item_quantity": 10.0,
      "item_rate": 50.25,
      "item_amount": 502.50
    }}
  ],
  "subtotal": null,
  "page_total": null,
  "notes": "Any extraction notes"
}}

VALIDATION CHECKLIST BEFORE OUTPUT:
□ All item_names are products/services (NOT dates, IDs, metadata)
□ All item_names are unique within this response
□ All quantities, rates, amounts are positive numbers
□ Amount ≈ Quantity × Rate for each item
□ No duplicate items in response
□ Valid JSON format

BILL TEXT (PAGE {page_number}):
{ocr_text}

Extract now. Return ONLY the JSON, no preamble or explanation:"""

    @staticmethod
    def get_validation_prompt(extracted_items: List[dict], ocr_text: str) -> str:
        """
        Generate validation prompt to verify extraction quality
        
        Args:
            extracted_items: List of extracted items
            ocr_text: Original OCR text
            
        Returns:
            Validation prompt string
        """
        return f"""Validate this bill extraction for accuracy.

ORIGINAL BILL TEXT:
{ocr_text}

EXTRACTED LINE ITEMS:
{extracted_items}

VALIDATION CHECKS:
1. Are all item_names actual products/services?
2. Are any item_names dates, IDs, or metadata?
3. Do all amounts seem reasonable?
4. Is there any obvious double-counting?
5. Are there missing items from the original bill?

Return ONLY JSON:
{{
  "is_valid": true|false,
  "issues": ["list of issues if any"],
  "confidence": 0.0-1.0,
  "corrections_needed": false|true
}}"""

    @staticmethod
    def get_reconciliation_prompt(
        all_items: List[dict],
        claimed_total: float
    ) -> str:
        """
        Generate reconciliation prompt to verify totals
        
        Args:
            all_items: All extracted items
            claimed_total: Total claimed on bill
            
        Returns:
            Reconciliation prompt string
        """
        return f"""Reconcile extracted items with bill total.

EXTRACTED ITEMS:
{all_items}

CLAIMED BILL TOTAL: {claimed_total}

RECONCILIATION TASK:
1. Calculate sum of all item_amounts
2. Compare with claimed total
3. Calculate variance and percentage
4. Determine if match is acceptable

Return ONLY JSON:
{{
  "calculated_total": 0.0,
  "claimed_total": {claimed_total},
  "variance": 0.0,
  "variance_percentage": 0.0,
  "status": "perfect|acceptable|needs_review",
  "notes": "explanation"
}}

Status guidelines:
- perfect: variance < ₹0.01
- acceptable: variance < 1%
- needs_review: variance >= 1%
"""
    
    @staticmethod
    def get_deduplication_check_prompt(items_page1: List[dict], items_page2: List[dict]) -> str:
        """
        Generate prompt to check for duplicates across pages
        
        Args:
            items_page1: Items from page 1
            items_page2: Items from page 2
            
        Returns:
            Deduplication prompt string
        """
        return f"""Check for duplicate items across pages.

PAGE 1 ITEMS:
{items_page1}

PAGE 2 ITEMS:
{items_page2}

DUPLICATE CHECK:
1. Compare by: item_name, item_amount, item_quantity
2. Identify exact duplicates (same values)
3. Flag similar items (same name, different amounts)
4. Determine if duplicates are legitimate (e.g., multiple purchases)

Return ONLY JSON:
{{
  "exact_duplicates": [
    {{"page1_item": {{}}, "page2_item": {{}}, "reason": "exact match"}}
  ],
  "similar_items": [
    {{"page1_item": {{}}, "page2_item": {{}}, "reason": "same name, different amount"}}
  ],
  "duplicates_to_remove": ["item names to deduplicate"],
  "recommendation": "keep all|remove page2|review manually"
}}"""