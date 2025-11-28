"""
Bill Validators Module
Validates bill data for accuracy, consistency, and quality
"""

import logging
import re
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)


class BillValidator:
    """
    Comprehensive validation for bill extraction data
    Includes URL validation, amount validation, and reconciliation
    """
    
    # ========== URL Validation ==========
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Validate document URL format and accessibility
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not url:
            return False, "Document URL is required"
        
        if not isinstance(url, str):
            return False, "Document URL must be a string"
        
        if not url.startswith(("http://", "https://")):
            return False, "Document URL must start with http:// or https://"
        
        if len(url) > 2000:
            return False, "Document URL is too long (max 2000 characters)"
        
        return True, ""
    
    # ========== Amount Validation ==========
    
    @staticmethod
    def validate_amount(amount) -> bool:
        """
        Check if value is a valid monetary amount
        
        Args:
            amount: Value to validate
            
        Returns:
            True if valid positive number, False otherwise
        """
        try:
            num = float(amount)
            return num >= 0
        except (ValueError, TypeError):
            return False
    
    # ========== Line Item Validation ==========
    
    @staticmethod
    def validate_line_item(item: dict) -> Tuple[bool, str]:
        """
        Validate a single line item with comprehensive checks
        
        Args:
            item: Line item dictionary
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        required_fields = ["item_name", "item_amount", "item_rate", "item_quantity"]
        
        # Check all required fields exist
        for field in required_fields:
            if field not in item:
                return False, f"Missing required field: {field}"
        
        # ===== Validate Item Name =====
        item_name = str(item["item_name"]).strip()
        if not item_name:
            return False, "item_name cannot be empty"
        
        # Guard: Check if name looks like metadata
        if BillValidator._is_metadata_value(item_name):
            return False, f"item_name appears to be metadata, not a product: '{item_name}'"
        
        # ===== Validate Amounts =====
        if not BillValidator.validate_amount(item["item_amount"]):
            return False, "item_amount must be a positive number"
        
        if not BillValidator.validate_amount(item["item_rate"]):
            return False, "item_rate must be a positive number"
        
        if not BillValidator.validate_amount(item["item_quantity"]):
            return False, "item_quantity must be a positive number"
        
        # ===== Validate Amount Consistency =====
        quantity = float(item["item_quantity"])
        rate = float(item["item_rate"])
        amount = float(item["item_amount"])
        
        # Check if amount = quantity × rate (with tolerance)
        calculated = quantity * rate
        tolerance = max(0.01, calculated * 0.05)  # 5% tolerance
        
        if abs(calculated - amount) > tolerance:
            logger.warning(
                f"⚠️  Amount mismatch for '{item_name}': "
                f"{quantity} × {rate} = {calculated}, but amount = {amount}"
            )
        
        return True, ""
    
    # ========== Metadata Detection ==========
    
    @staticmethod
    def _is_metadata_value(text: str) -> bool:
        """
        Check if text appears to be metadata rather than item name
        
        Args:
            text: Text to check
            
        Returns:
            True if appears to be metadata, False if appears to be item name
        """
        text_lower = text.lower().strip()
        
        # Pattern matching for common metadata
        metadata_patterns = [
            r"^\d{4}-\d{2}-\d{2}",           # Dates: YYYY-MM-DD
            r"^\d{2}/\d{2}/\d{4}",           # Dates: MM/DD/YYYY
            r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # Various date formats
            r"^inv[^a-z]*\d+",               # Invoice numbers
            r"^ref[^a-z]*\d+",               # Reference numbers
            r"^bill[^a-z]*\d+",              # Bill numbers
            r"^id[^a-z]*\d+",                # IDs
            r"^\d{2}:\d{2}",                 # Times: HH:MM
            r"^page\s*\d+",                  # Page numbers
            r"^\d+\s*[-/]\s*\d+$",           # Ranges like "1-5"
            r"^[a-z]+-\d{6}",                # Invoice-like: PREFIX-XXXXXX
            r"^\d{10,}$",                    # Long numbers (IDs)
        ]
        
        for pattern in metadata_patterns:
            if re.match(pattern, text_lower):
                logger.debug(f"🚫 Detected metadata pattern in: '{text}'")
                return True
        
        # Check if text is ONLY numbers/special chars (no product name)
        if re.match(r"^[\d\-/:.]+$", text):
            logger.debug(f"🚫 Text contains only numbers/special chars: '{text}'")
            return True
        
        return False
    
    # ========== Duplicate Detection ==========
    
    @staticmethod
    def check_duplicates(items: List[dict]) -> Tuple[int, List[str]]:
        """
        Check for duplicate items across pages or within same page
        
        Args:
            items: List of line items from all pages
            
        Returns:
            Tuple of (duplicate_count, list_of_duplicate_details)
        """
        seen = {}
        duplicates = []
        
        for idx, item in enumerate(items):
            # Create hashable key from item details
            key = (
                item.get("item_name", "").lower().strip(),
                round(float(item.get("item_amount", 0)), 2),
                round(float(item.get("item_quantity", 0)), 2)
            )
            
            if key in seen:
                duplicate_info = (
                    f"Item: {item.get('item_name')} | "
                    f"Amount: {item.get('item_amount')} | "
                    f"Qty: {item.get('item_quantity')}"
                )
                duplicates.append(duplicate_info)
                logger.warning(f"⚠️  Potential duplicate found: {duplicate_info}")
                seen[key] += 1
            else:
                seen[key] = 1
        
        duplicate_count = len([v for v in seen.values() if v > 1])
        return duplicate_count, duplicates
    
    # ========== Total Reconciliation ==========
    
    @staticmethod
    def reconcile_totals(items: List[dict], claimed_total: float) -> dict:
        """
        Reconcile extracted items with claimed total
        
        Args:
            items: List of extracted items
            claimed_total: Total amount claimed in bill
            
        Returns:
            Dictionary with reconciliation report
        """
        # Calculate total from items
        calculated_total = sum(
            float(item.get("item_amount", 0)) for item in items
        )
        
        variance = abs(claimed_total - calculated_total)
        variance_percentage = (
            (variance / claimed_total * 100) if claimed_total > 0 else 0
        )
        
        # Determine reconciliation status
        if variance < 0.01:
            status = "perfect"
            logger.info("✅ Totals match perfectly")
        elif variance_percentage < 1:
            status = "acceptable"
            logger.info(f"✅ Totals match within acceptable range (<1%)")
        else:
            status = "needs_review"
            logger.warning(
                f"⚠️  Total variance: ₹{variance:.2f} ({variance_percentage:.2f}%)"
            )
        
        return {
            "calculated_total": round(calculated_total, 2),
            "claimed_total": claimed_total,
            "matches": variance < 0.01,
            "variance": round(variance, 2),
            "variance_percentage": round(variance_percentage, 2),
            "reconciliation_status": status
        }
    
    # ========== Extraction Quality Assessment ==========
    
    @staticmethod
    def validate_extraction_quality(
        items: List[dict],
        claimed_total: float = None
    ) -> dict:
        """
        Comprehensive quality validation of extraction
        
        Args:
            items: Extracted items
            claimed_total: Bill total for reconciliation (optional)
            
        Returns:
            Quality report dictionary
        """
        report = {
            "total_items": len(items),
            "valid_items": 0,
            "invalid_items": 0,
            "issues": [],
            "quality_score": 0.0
        }
        
        # ===== Validate Each Item =====
        for idx, item in enumerate(items):
            is_valid, error_msg = BillValidator.validate_line_item(item)
            if is_valid:
                report["valid_items"] += 1
            else:
                report["invalid_items"] += 1
                report["issues"].append(
                    f"Item {idx + 1}: {error_msg}"
                )
        
        # ===== Check for Duplicates =====
        dup_count, dup_details = BillValidator.check_duplicates(items)
        if dup_count > 0:
            report["issues"].append(f"Found {dup_count} potential duplicate items")
            # Include first 3 duplicates
            report["issues"].extend(dup_details[:3])
        
        # ===== Calculate Quality Score =====
        if report["total_items"] > 0:
            validity_score = report["valid_items"] / report["total_items"]
        else:
            validity_score = 0
        
        # Penalize for duplicates
        if dup_count > 0:
            validity_score *= (1 - (dup_count * 0.1))
        
        report["quality_score"] = round(max(0, validity_score) * 100, 2)
        
        # ===== Log Summary =====
        logger.info(
            f"📊 Quality Assessment: {report['valid_items']}/{report['total_items']} "
            f"valid items | Score: {report['quality_score']}%"
        )
        
        return report
    
    # ========== Utility Methods ==========
    
    @staticmethod
    def sanitize_item_name(name: str) -> str:
        """
        Sanitize item name for consistency
        
        Args:
            name: Item name to sanitize
            
        Returns:
            Sanitized item name
        """
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove special characters but keep alphanumeric and common symbols
        name = re.sub(r'[^a-zA-Z0-9\s\.\-/]', '', name)
        
        return name.strip()
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """
        Format amount as currency
        
        Args:
            amount: Numeric amount
            
        Returns:
            Formatted currency string
        """
        return f"₹{amount:,.2f}"