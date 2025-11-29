"""
Response Formatter - Formats API responses
Ensures compliance with required schema
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Handles formatting of API responses
    """
    
    @staticmethod
    def success_response(
        pagewise_items: List[Dict],
        token_usage: Dict[str, int],
        total_item_count: int
    ) -> Dict[str, Any]:
        """
        Format successful extraction response
        
        Args:
            pagewise_items: List of page-wise line items
            token_usage: Token usage dictionary
            total_item_count: Total count of items across all pages
            
        Returns:
            Formatted response dictionary
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
        
        logger.debug(f"✅ Success response formatted with {total_item_count} items")
        return response
    
    @staticmethod
    def error_response(message: str) -> Dict[str, Any]:
        """
        Format error response
        
        Args:
            message: Error message
            
        Returns:
            Formatted error response dictionary
        """
        response = {
            "is_success": False,
            "message": message
        }
        
        logger.debug(f"❌ Error response formatted: {message}")
        return response
    
    @staticmethod
    def format_page_items(
        page_number: str,
        page_type: str,
        line_items: List[Dict]
    ) -> Dict[str, Any]:
        """
        Format items for a single page
        
        Args:
            page_number: Page number as string
            page_type: Type of page (Bill Detail, Final Bill, Pharmacy)
            line_items: List of line item dictionaries
            
        Returns:
            Formatted page dictionary
        """
        # Format each line item
        formatted_items = []
        
        for item in line_items:
            formatted_item = {
                "item_name": str(item.get("item_name", "")),
                "item_amount": float(item.get("item_amount", 0.0)),
                "item_rate": float(item.get("item_rate", 0.0)),
                "item_quantity": float(item.get("item_quantity", 0.0))
            }
            formatted_items.append(formatted_item)
        
        page_data = {
            "page_no": str(page_number),
            "page_type": page_type,
            "bill_items": formatted_items
        }
        
        logger.debug(f"✅ Formatted page {page_number} with {len(formatted_items)} items")
        return page_data
    
    @staticmethod
    def validate_response_schema(response: Dict[str, Any]) -> bool:
        """
        Validate response matches required schema
        
        Args:
            response: Response dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check top-level keys
            if "is_success" not in response:
                logger.warning("⚠️  Missing 'is_success' in response")
                return False
            
            if response["is_success"]:
                # Success response validation
                required_keys = ["token_usage", "data"]
                if not all(key in response for key in required_keys):
                    logger.warning(f"⚠️  Missing required keys in success response")
                    return False
                
                # Validate token_usage
                token_keys = ["total_tokens", "input_tokens", "output_tokens"]
                if not all(key in response["token_usage"] for key in token_keys):
                    logger.warning("⚠️  Missing token usage keys")
                    return False
                
                # Validate data structure
                data = response["data"]
                if "pagewise_line_items" not in data or "total_item_count" not in data:
                    logger.warning("⚠️  Missing data keys")
                    return False
                
                # Validate pagewise_line_items
                for page in data["pagewise_line_items"]:
                    page_keys = ["page_no", "page_type", "bill_items"]
                    if not all(key in page for key in page_keys):
                        logger.warning(f"⚠️  Missing page keys: {page}")
                        return False
                    
                    # Validate bill_items
                    for item in page["bill_items"]:
                        item_keys = ["item_name", "item_amount", "item_rate", "item_quantity"]
                        if not all(key in item for key in item_keys):
                            logger.warning(f"⚠️  Missing item keys: {item}")
                            return False
            
            else:
                # Error response validation
                if "message" not in response:
                    logger.warning("⚠️  Missing 'message' in error response")
                    return False
            
            logger.debug("✅ Response schema validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema validation error: {e}")
            return False
    
    @staticmethod
    def calculate_total_amount(line_items: List[Dict]) -> float:
        """
        Calculate total amount from line items
        
        Args:
            line_items: List of line item dictionaries
            
        Returns:
            Total amount as float
        """
        total = sum(float(item.get("item_amount", 0.0)) for item in line_items)
        return round(total, 2)