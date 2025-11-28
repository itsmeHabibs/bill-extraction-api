"""
Response Formatter Module
Formats extraction results into required API response structure
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Formats extraction results into the exact required API response structure
    Ensures all responses match the specified schema
    """
    
    # ========== Success Response ==========
    
    @staticmethod
    def success_response(
        pagewise_items: List[Dict],
        token_usage: Dict,
        total_item_count: int
    ) -> Dict:
        """
        Format successful extraction into required response structure
        
        Args:
            pagewise_items: List of page items with extracted data
            token_usage: Token usage statistics
            total_item_count: Total count of items across all pages
            
        Returns:
            Formatted response dictionary following exact spec
            
        Response Structure:
        {
            "is_success": true,
            "token_usage": {
                "total_tokens": integer,
                "input_tokens": integer,
                "output_tokens": integer
            },
            "data": {
                "pagewise_line_items": [...],
                "total_item_count": integer
            }
        }
        """
        response = {
            "is_success": True,
            "token_usage": {
                "total_tokens": token_usage.get("total_tokens", 0),
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0)
            },
            "data": {
                "pagewise_line_items": pagewise_items,
                "total_item_count": total_item_count
            }
        }
        
        logger.info(f"✅ Success response formatted with {total_item_count} items")
        return response
    
    # ========== Error Response ==========
    
    @staticmethod
    def error_response(error_message: str) -> Dict:
        """
        Format error response
        
        Args:
            error_message: Description of the error
            
        Returns:
            Formatted error response dictionary
            
        Response Structure:
        {
            "is_success": false,
            "message": "error description"
        }
        """
        response = {
            "is_success": False,
            "message": error_message
        }
        
        logger.warning(f"❌ Error response: {error_message}")
        return response
    
    # ========== Page Formatting ==========
    
    @staticmethod
    def format_page_items(
        page_number: str,
        page_type: str,
        line_items: List[Dict]
    ) -> Dict:
        """
        Format items for a single page
        
        Args:
            page_number: Page number (as string)
            page_type: Type of page (Bill Detail, Final Bill, Pharmacy)
            line_items: List of line items
            
        Returns:
            Formatted page item dictionary
            
        Structure:
        {
            "page_no": "1",
            "page_type": "Bill Detail",
            "bill_items": [...]
        }
        """
        # Clean and validate line items
        cleaned_items = []
        for item in line_items:
            cleaned = ResponseFormatter._clean_line_item(item)
            if cleaned:
                cleaned_items.append(cleaned)
        
        page_item = {
            "page_no": str(page_number),
            "page_type": ResponseFormatter._validate_page_type(page_type),
            "bill_items": cleaned_items
        }
        
        logger.info(
            f"📄 Formatted page {page_number} "
            f"({page_item['page_type']}) with {len(cleaned_items)} items"
        )
        return page_item
    
    # ========== Line Item Cleaning ==========
    
    @staticmethod
    def _clean_line_item(item: Dict) -> Optional[Dict]:
        """
        Clean and validate a single line item
        Converts all fields to correct types
        
        Args:
            item: Raw line item dictionary
            
        Returns:
            Cleaned line item or None if invalid
        """
        try:
            cleaned = {
                "item_name": str(item.get("item_name", "")).strip(),
                "item_amount": ResponseFormatter._to_float(item.get("item_amount")),
                "item_rate": ResponseFormatter._to_float(item.get("item_rate")),
                "item_quantity": ResponseFormatter._to_float(item.get("item_quantity"))
            }
            
            # Validate that item has required fields with values
            if not cleaned["item_name"]:
                logger.warning("⚠️  Item missing name, skipping")
                return None
            
            # If any numeric field is None, it's invalid
            if any(v is None for v in [
                cleaned["item_amount"],
                cleaned["item_rate"],
                cleaned["item_quantity"]
            ]):
                logger.warning(
                    f"⚠️  Item '{cleaned['item_name']}' has missing numeric values"
                )
                return None
            
            logger.debug(
                f"✓ Cleaned item: {cleaned['item_name']} "
                f"(Qty: {cleaned['item_quantity']}, Rate: {cleaned['item_rate']}, "
                f"Amount: {cleaned['item_amount']})"
            )
            return cleaned
            
        except Exception as e:
            logger.error(f"❌ Error cleaning line item: {e}")
            return None
    
    # ========== Type Conversion ==========
    
    @staticmethod
    def _to_float(value) -> Optional[float]:
        """
        Safely convert value to float
        Handles currency symbols, commas, etc.
        
        Args:
            value: Value to convert (int, float, string, etc.)
            
        Returns:
            Float value or None if conversion fails
        """
        try:
            if value is None:
                return None
            
            # Already a number
            if isinstance(value, (int, float)):
                return float(value)
            
            # String - need to parse
            if isinstance(value, str):
                # Remove common currency symbols
                cleaned = value.replace("₹", "")
                cleaned = cleaned.replace("$", "")
                cleaned = cleaned.replace("€", "")
                cleaned = cleaned.replace("£", "")
                
                # Remove commas (thousands separator)
                cleaned = cleaned.replace(",", "")
                
                # Strip whitespace
                cleaned = cleaned.strip()
                
                if cleaned:
                    return float(cleaned)
            
            return None
            
        except (ValueError, TypeError):
            logger.debug(f"⚠️  Failed to convert to float: {value}")
            return None
    
    # ========== Page Type Validation ==========
    
    @staticmethod
    def _validate_page_type(page_type: str) -> str:
        """
        Validate and normalize page type
        Ensures only valid page types are returned
        
        Args:
            page_type: Page type string
            
        Returns:
            Valid page type from predefined list
        """
        valid_types = ["Bill Detail", "Final Bill", "Pharmacy"]
        
        page_type = str(page_type).strip()
        
        # Check for exact match
        if page_type in valid_types:
            return page_type
        
        # Try to match partial/case-insensitive
        for valid in valid_types:
            if valid.lower() in page_type.lower():
                logger.debug(f"🔄 Mapped page type '{page_type}' to '{valid}'")
                return valid
        
        # Default to Bill Detail if no match
        logger.warning(
            f"⚠️  Unknown page type '{page_type}', defaulting to 'Bill Detail'"
        )
        return "Bill Detail"
    
    # ========== Schema Validation ==========
    
    @staticmethod
    def validate_response_schema(response: Dict) -> bool:
        """
        Validate that response matches required schema exactly
        
        Args:
            response: Response dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check success response structure
            if response.get("is_success"):
                # ===== Check token_usage =====
                assert "token_usage" in response, "Missing token_usage"
                token_usage = response["token_usage"]
                assert "total_tokens" in token_usage, "Missing total_tokens"
                assert "input_tokens" in token_usage, "Missing input_tokens"
                assert "output_tokens" in token_usage, "Missing output_tokens"
                
                # Validate token values are integers
                assert isinstance(token_usage["total_tokens"], int), \
                    "total_tokens must be integer"
                assert isinstance(token_usage["input_tokens"], int), \
                    "input_tokens must be integer"
                assert isinstance(token_usage["output_tokens"], int), \
                    "output_tokens must be integer"
                
                # ===== Check data =====
                assert "data" in response, "Missing data"
                data = response["data"]
                assert "pagewise_line_items" in data, "Missing pagewise_line_items"
                assert "total_item_count" in data, "Missing total_item_count"
                assert isinstance(data["total_item_count"], int), \
                    "total_item_count must be integer"
                
                # ===== Check pagewise_line_items structure =====
                pagewise_items = data["pagewise_line_items"]
                assert isinstance(pagewise_items, list), \
                    "pagewise_line_items must be list"
                
                for page in pagewise_items:
                    # Required page fields
                    assert "page_no" in page, "Missing page_no in page"
                    assert "page_type" in page, "Missing page_type in page"
                    assert "bill_items" in page, "Missing bill_items in page"
                    
                    # Validate page fields
                    assert isinstance(page["page_no"], str), \
                        "page_no must be string"
                    assert page["page_type"] in ["Bill Detail", "Final Bill", "Pharmacy"], \
                        f"Invalid page_type: {page['page_type']}"
                    assert isinstance(page["bill_items"], list), \
                        "bill_items must be list"
                    
                    # ===== Check bill_items structure =====
                    for item in page["bill_items"]:
                        # Required item fields
                        required = ["item_name", "item_amount", "item_rate", "item_quantity"]
                        for field in required:
                            assert field in item, f"Missing {field} in item"
                        
                        # Validate types
                        assert isinstance(item["item_name"], str), \
                            "item_name must be string"
                        assert isinstance(item["item_amount"], (int, float)), \
                            "item_amount must be number"
                        assert isinstance(item["item_rate"], (int, float)), \
                            "item_rate must be number"
                        assert isinstance(item["item_quantity"], (int, float)), \
                            "item_quantity must be number"
                        
                        # Validate non-negative
                        assert item["item_amount"] >= 0, \
                            "item_amount must be non-negative"
                        assert item["item_rate"] >= 0, \
                            "item_rate must be non-negative"
                        assert item["item_quantity"] >= 0, \
                            "item_quantity must be non-negative"
            
            else:
                # ===== Error response structure =====
                assert "message" in response, "Missing message in error response"
                assert isinstance(response["message"], str), \
                    "message must be string"
            
            logger.info("✅ Response schema validation passed")
            return True
            
        except AssertionError as e:
            logger.error(f"❌ Response validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected validation error: {e}")
            return False
    
    # ========== Debugging ==========
    
    @staticmethod
    def get_response_summary(response: Dict) -> str:
        """
        Get a human-readable summary of response
        
        Args:
            response: Response dictionary
            
        Returns:
            Summary string
        """
        if response.get("is_success"):
            data = response.get("data", {})
            item_count = data.get("total_item_count", 0)
            token_usage = response.get("token_usage", {})
            return (
                f"✅ Success | Items: {item_count} | "
                f"Tokens: {token_usage.get('total_tokens', 0)}"
            )
        else:
            message = response.get("message", "Unknown error")
            return f"❌ Error | {message}"