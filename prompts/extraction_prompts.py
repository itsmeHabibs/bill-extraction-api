"""
Extraction Prompts Module
Contains all LLM prompts with careful guard rails against common errors
"""


def get_main_extraction_prompt(ocr_text: str, page_number: str = "1") -> str:
    """
    Generate main extraction prompt with explicit guards against interpretation errors.
    
    This prompt is designed to:
    1. Extract ONLY actual line items (not metadata)
    2. Identify monetary values correctly
    3. Differentiate between identifiers and amounts
    4. Prevent double-counting
    5. Return valid JSON
    
    Args:
        ocr_text: Clean OCR-extracted text from bill
        page_number: Page number for reference
        
    Returns:
        Prompt string for Claude
    """
    
    return f"""You are an expert bill data extraction specialist. Your task: extract line items from bill text.

═══════════════════════════════════════════════════════════════════════════════
🚨 CRITICAL RULES - MUST FOLLOW EXACTLY
═══════════════════════════════════════════════════════════════════════════════

✅ EXTRACT - These ARE line items:
  • "Aspirin 500mg - Qty: 2, Rate: 50, Amount: 100" → Line item
  • "Paracetamol Syrup - 250ml - 150.00" → Line item
  • "Consultation Fee - 500.00" → Line item

❌ NEVER EXTRACT - These are NOT line items:
  • "Invoice Date: 2024-01-15" → Date (NOT an amount)
  • "Invoice No: INV-2024-001" → Invoice ID (NOT an amount)
  • "Bill Total: 5000" → Use this for reconciliation, not as line item
  • "Page 1 of 2" → Page number (NOT an amount)
  • "Reference: REF-123456" → Reference ID (NOT an amount)
  • "Customer ID: CUST-789" → Customer ID (NOT an amount)

🛡️ GUARD AGAINST THESE ERRORS:
  Error Type 1: Treating dates as amounts
    ❌ WRONG: "2024-01-15" as item_amount
    ✅ RIGHT: Ignore this line, it's metadata
  
  Error Type 2: Treating IDs as amounts
    ❌ WRONG: "INV-001" as item_amount
    ✅ RIGHT: Ignore this line, it's metadata
  
  Error Type 3: Treating totals as line items
    ❌ WRONG: Including "Subtotal: 1000" as a line item
    ✅ RIGHT: Extract subtotal separately, NOT as line item
  
  Error Type 4: Double-counting items
    ❌ WRONG: Same item listed on multiple pages
    ✅ RIGHT: Extract once per occurrence (if legitimately repeated)

═══════════════════════════════════════════════════════════════════════════════
📋 EXTRACTION RULES
═══════════════════════════════════════════════════════════════════════════════

Rule 1: Each line item MUST have:
  • item_name: Product/service name (NOT a date, ID, or number)
  • item_quantity: Positive number representing quantity
  • item_rate: Positive number representing unit price
  • item_amount: Must approximately equal (quantity × rate)

Rule 2: Validate item_name:
  Check: Is it a product/service name?
  Check: Does it look like a date? (YYYY-MM-DD, MM/DD/YYYY) → Skip
  Check: Does it look like an ID? (INV-, REF-, CUST-) → Skip
  Check: Does it look like a number only? → Skip
  ✓ Only extract actual product/service names

Rule 3: Validate amounts:
  • All amounts must be positive numbers
  • item_amount ≈ item_quantity × item_rate (within 5%)
  • If they don't match, verify before extracting

Rule 4: No double-counting:
  • Extract each item once (even if table repeats across pages)
  • Don't count the same item multiple times

═══════════════════════════════════════════════════════════════════════════════
📝 BILL TEXT TO EXTRACT (Page {page_number}):
═══════════════════════════════════════════════════════════════════════════════

{ocr_text}

═══════════════════════════════════════════════════════════════════════════════
🔍 EXTRACTION STEPS:
═══════════════════════════════════════════════════════════════════════════════

Step 1: Identify all potential line items in the text
Step 2: For each item, check if it's metadata or a real item
Step 3: Validate each item follows the rules above
Step 4: Extract item_name, item_quantity, item_rate, item_amount
Step 5: Double-check no dates/IDs are included
Step 6: Generate JSON output

═══════════════════════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT (ONLY RETURN THIS JSON, NO MARKDOWN):
═══════════════════════════════════════════════════════════════════════════════

{{
  "page_type": "Bill Detail",
  "line_items": [
    {{
      "item_name": "exact product or service name",
      "item_quantity": 1,
      "item_rate": 100.00,
      "item_amount": 100.00
    }},
    {{
      "item_name": "another product",
      "item_quantity": 5,
      "item_rate": 50.00,
      "item_amount": 250.00
    }}
  ],
  "page_extracted": "{page_number}",
  "extraction_notes": "any issues found"
}}

═══════════════════════════════════════════════════════════════════════════════
✅ FINAL CHECKLIST BEFORE OUTPUT:
═══════════════════════════════════════════════════════════════════════════════

□ All item_names are actual products/services (NOT dates, IDs, or numbers)
□ All item_names are unique (no exact duplicates)
□ All quantities are positive numbers
□ All rates are positive numbers
□ All amounts are positive numbers
□ For each item: amount ≈ quantity × rate
□ No dates like "2024-01-15" in items
□ No invoice/reference IDs in items
□ JSON is valid and complete

START EXTRACTION NOW:"""


def get_validation_prompt(extracted_data: dict, original_text: str = "") -> str:
    """
    Generate validation prompt to verify extraction accuracy
    
    Args:
        extracted_data: Data extracted from OCR/LLM
        original_text: Original OCR text for comparison
        
    Returns:
        Validation prompt string
    """
    
    return f"""Validate this bill extraction for accuracy:

Extracted Data:
{extracted_data}

Original Bill Text (snippet):
{original_text[:1000] if original_text else "Not provided"}

VALIDATION CHECKS:
1. Are all item_names actual products/services (NOT dates like 2024-01-15)?
2. Are all item_names unique (no exact duplicates)?
3. Are all amounts positive numbers?
4. Does each item_amount ≈ item_quantity × item_rate?
5. Are there any suspicious patterns (all amounts same, all quantities same)?
6. Are any metadata values mixed in (dates, IDs, invoice numbers)?
7. Does the extraction make business sense?

Return ONLY this JSON structure:
{{
  "is_valid": true or false,
  "validation_issues": ["list of issues found"],
  "confidence_score": 0.0 to 1.0,
  "recommendations": ["corrective actions if any"]
}}"""


def get_reconciliation_prompt(extracted_items: list, claimed_total: float) -> str:
    """
    Generate reconciliation prompt to verify totals match
    
    Args:
        extracted_items: List of extracted line items
        claimed_total: Actual bill total to reconcile against
        
    Returns:
        Reconciliation prompt string
    """
    
    return f"""Reconcile the extracted bill items with the claimed bill total.

Extracted Items:
{extracted_items}

Claimed Bill Total: {claimed_total}

RECONCILIATION TASK:
1. Calculate the sum of all item_amount values
2. Compare with the claimed bill total
3. Calculate variance and variance percentage
4. Determine reconciliation status

Return ONLY this JSON structure:
{{
  "calculated_total": 0.0,
  "claimed_total": {claimed_total},
  "matches": true or false,
  "variance": 0.0,
  "variance_percentage": 0.0,
  "reconciliation_status": "perfect" or "acceptable" or "needs_review",
  "notes": "explanation if variance exists"
}}

Status Guidelines:
- "perfect": variance < ₹0.01 (essentially exact match)
- "acceptable": variance < 1% (minor rounding differences)
- "needs_review": variance >= 1% (significant difference, investigate)
"""


def get_duplicate_detection_prompt(all_items: list) -> str:
    """
    Generate prompt for detecting duplicate items
    
    Args:
        all_items: All extracted items
        
    Returns:
        Duplicate detection prompt
    """
    
    return f"""Check these extracted items for duplicates across pages.

All Items Extracted:
{all_items}

DUPLICATE DETECTION:
1. Look for items with same name but different quantities/amounts
2. Look for items with exactly same name, quantity, and amount (likely duplicates)
3. Note any suspicious patterns
4. Consider if duplicates make business sense (e.g., same medicine ordered twice)

Return ONLY this JSON:
{{
  "has_duplicates": true or false,
  "potential_duplicates": [
    {{
      "item_name": "name",
      "occurrences": 2,
      "note": "explanation"
    }}
  ],
  "confidence": 0.0 to 1.0
}}"""


# ═════════════════════════════════════════════════════════════════════════════
# System Prompt for Claude (optional, for enhanced consistency)
# ═════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_EXTRACTION = """You are an expert in bill and invoice data extraction. Your role is to:

1. Extract structured data from unstructured bill text
2. Identify and prevent common extraction errors
3. Follow strict data validation rules
4. Return only valid JSON
5. Flag ambiguous or missing data

Key strengths you use:
- Identifying metadata vs actual data
- Detecting and preventing duplicate extraction
- Validating numeric consistency
- Ensuring output matches exact requirements

You are very careful about:
- NOT treating dates as monetary amounts
- NOT treating IDs as monetary amounts
- Proper data type conversion
- JSON schema compliance
- Accuracy over completion (better to skip than to guess)"""