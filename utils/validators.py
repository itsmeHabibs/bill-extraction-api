"""
Validators - Data validation utilities
Guards against common extraction errors
"""

import logging
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BillValidator:
    """
    Validation utilities for bill extraction
    """
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Validate document URL
        
        Args:
            url: URL string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "Document URL is required"
        
        if not isinstance(url, str):
            return False, "Document URL must be a string"
        
        # Basic URL validation
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format"
            
            if result.scheme not in ['http', 'https']:
                return False, "URL must use HTTP or HTTPS protocol"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid URL: {str(e)}"
    
    @staticmethod
    def validate_line_item(item: Dict) -> Tuple[bool, str]:
        """
        Validate a single line item
        
        Args:
            item: Line item dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["item_name", "item_amount", "item_rate", "item_quantity"]
        
        # Check required fields
        for field in required_fields:
            if field not in item:
                return False, f"Missing required field: {field}"
        
        # Validate item_name
        if not item["item_name"] or not isinstance(item["item_name"], str):
            return False, "item_name must be a non-empty string"
        
        # Validate numeric fields
        numeric_fields = ["item_amount", "item_rate", "item_quantity"]
        for field in numeric_fields:
            try:
                value = float(item[field])
                if value < 0:
                    return False, f"{field} cannot be negative"
            except (ValueError, TypeError):
                return False, f"{field} must be a valid number"
        
        # Guard against date/ID misinterpretation
        if BillValidator._looks_like_date_or_id(item["item_name"]):
            logger.warning(f"⚠️  Item name looks like date/ID: {item['item_name']}")
        
        return True, ""
    
    @staticmethod
    def _looks_like_date_or_id(text: str) -> bool:
        """
        Check if text looks like a date or ID number
        
        Args:
            text: Text to check
            
        Returns:
            True if looks like date/ID
        """
        text_lower = text.lower()
        
        # Check for date keywords
        date_keywords = ["date", "time", "invoice", "bill no", "receipt", "patient id"]
        if any(keyword in text_lower for keyword in date_keywords):
            return True
        
        # Check if mostly numbers (likely an ID)
        digits = sum(c.isdigit() for c in text)
        if len(text) > 0 and digits / len(text) > 0.8:
            return True
        
        return False
    
    @staticmethod
    def check_duplicates(line_items: List[Dict]) -> Tuple[int, List[Dict]]:
        """
        Check for duplicate line items
        
        Args:
            line_items: List of line item dictionaries
            
        Returns:
            Tuple of (duplicate_count, list_of_duplicates)
        """
        seen = {}
        duplicates = []
        
        for item in line_items:
            # Create a key from name, amount, and quantity
            key = (
                item.get("item_name", "").lower().strip(),
                float(item.get("item_amount", 0)),
                float(item.get("item_quantity", 0))
            )
            
            if key in seen:
                duplicates.append({
                    "item": item,
                    "first_occurrence": seen[key]
                })
            else:
                seen[key] = item
        
        return len(duplicates), duplicates
    
    @staticmethod
    def validate_extraction_quality(line_items: List[Dict]) -> Dict[str, any]:
        """
        Validate overall extraction quality
        
        Args:
            line_items: List of extracted line items
            
        Returns:
            Dictionary with quality metrics
        """
        total_items = len(line_items)
        valid_items = 0
        warnings = []
        
        for item in line_items:
            is_valid, error = BillValidator.validate_line_item(item)
            if is_valid:
                valid_items += 1
            else:
                warnings.append(f"Invalid item: {error}")
        
        # Check for suspicious patterns
        if total_items == 0:
            warnings.append("No line items extracted")
        
        # Calculate quality score
        quality_score = (valid_items / total_items * 100) if total_items > 0 else 0
        
        report = {
            "total_items": total_items,
            "valid_items": valid_items,
            "quality_score": round(quality_score, 2),
            "warnings": warnings
        }
        
        logger.info(f"📊 Quality Score: {quality_score:.2f}% ({valid_items}/{total_items} valid)")
        
        return report
    
    @staticmethod
    def reconcile_totals(
        extracted_items: List[Dict],
        claimed_total: float
    ) -> Dict[str, any]:
        """
        Reconcile extracted totals with claimed bill total
        
        Args:
            extracted_items: List of extracted line items
            claimed_total: Total amount claimed in bill
            
        Returns:
            Dictionary with reconciliation details
        """
        # Calculate sum of extracted amounts
        extracted_total = sum(float(item.get("item_amount", 0)) for item in extracted_items)
        
        # Calculate variance
        variance = abs(extracted_total - claimed_total)
        variance_percentage = (variance / claimed_total * 100) if claimed_total > 0 else 0
        
        # Determine status
        if variance == 0:
            status = "perfect_match"
        elif variance_percentage < 1:
            status = "acceptable"
        elif variance_percentage < 5:
            status = "needs_review"
        else:
            status = "significant_discrepancy"
        
        reconciliation = {
            "extracted_total": round(extracted_total, 2),
            "claimed_total": round(claimed_total, 2),
            "variance": round(variance, 2),
            "variance_percentage": round(variance_percentage, 2),
            "status": status
        }
        
        logger.info(f"💰 Total Reconciliation: {status} "
                   f"(Extracted: {extracted_total:.2f}, Claimed: {claimed_total:.2f})")
        
        return reconciliation