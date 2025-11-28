"""
Comprehensive Test Suite for Bill Extraction API
Tests for validators, response formatters, and API endpoints
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import app
from utils.validators import BillValidator
from utils.response_formatter import ResponseFormatter


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """Create test client for API testing"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_line_item():
    """Sample valid line item"""
    return {
        "item_name": "Aspirin 500mg",
        "item_amount": 100.0,
        "item_rate": 25.0,
        "item_quantity": 4.0
    }


@pytest.fixture
def sample_items():
    """Sample list of line items"""
    return [
        {
            "item_name": "Medicine A",
            "item_amount": 250.0,
            "item_rate": 50.0,
            "item_quantity": 5.0
        },
        {
            "item_name": "Medicine B",
            "item_amount": 300.0,
            "item_rate": 100.0,
            "item_quantity": 3.0
        }
    ]


@pytest.fixture
def sample_response():
    """Sample valid API response"""
    return {
        "is_success": True,
        "token_usage": {
            "total_tokens": 1000,
            "input_tokens": 700,
            "output_tokens": 300
        },
        "data": {
            "pagewise_line_items": [
                {
                    "page_no": "1",
                    "page_type": "Bill Detail",
                    "bill_items": [
                        {
                            "item_name": "Medicine A",
                            "item_amount": 250.0,
                            "item_rate": 50.0,
                            "item_quantity": 5.0
                        }
                    ]
                }
            ],
            "total_item_count": 1
        }
    }


# ============================================================================
# TESTS: URL VALIDATION
# ============================================================================

class TestURLValidation:
    """Tests for URL validation"""
    
    def test_validate_url_valid_https(self):
        """Test URL validation with valid HTTPS URL"""
        is_valid, msg = BillValidator.validate_url("https://example.com/bill.png")
        assert is_valid is True
        assert msg == ""
    
    def test_validate_url_valid_http(self):
        """Test URL validation with valid HTTP URL"""
        is_valid, msg = BillValidator.validate_url("http://example.com/bill.png")
        assert is_valid is True
        assert msg == ""
    
    def test_validate_url_empty(self):
        """Test URL validation with empty string"""
        is_valid, msg = BillValidator.validate_url("")
        assert is_valid is False
        assert "required" in msg.lower()
    
    def test_validate_url_none(self):
        """Test URL validation with None"""
        is_valid, msg = BillValidator.validate_url(None)
        assert is_valid is False
    
    def test_validate_url_no_protocol(self):
        """Test URL validation without protocol"""
        is_valid, msg = BillValidator.validate_url("example.com/bill.png")
        assert is_valid is False
        assert "http" in msg.lower()
    
    def test_validate_url_invalid_type(self):
        """Test URL validation with non-string type"""
        is_valid, msg = BillValidator.validate_url(12345)
        assert is_valid is False
    
    def test_validate_url_too_long(self):
        """Test URL validation with excessively long URL"""
        long_url = "https://example.com/" + "a" * 2000
        is_valid, msg = BillValidator.validate_url(long_url)
        assert is_valid is False


# ============================================================================
# TESTS: AMOUNT VALIDATION
# ============================================================================

class TestAmountValidation:
    """Tests for amount validation"""
    
    def test_validate_amount_float(self):
        """Test amount validation with float"""
        assert BillValidator.validate_amount(100.50) is True
    
    def test_validate_amount_int(self):
        """Test amount validation with integer"""
        assert BillValidator.validate_amount(100) is True
    
    def test_validate_amount_string_valid(self):
        """Test amount validation with valid string"""
        assert BillValidator.validate_amount("100.50") is True
    
    def test_validate_amount_negative(self):
        """Test amount validation with negative number"""
        assert BillValidator.validate_amount(-50) is False
    
    def test_validate_amount_zero(self):
        """Test amount validation with zero"""
        assert BillValidator.validate_amount(0) is True
    
    def test_validate_amount_invalid_string(self):
        """Test amount validation with invalid string"""
        assert BillValidator.validate_amount("invalid") is False
    
    def test_validate_amount_none(self):
        """Test amount validation with None"""
        assert BillValidator.validate_amount(None) is False


# ============================================================================
# TESTS: LINE ITEM VALIDATION
# ============================================================================

class TestLineItemValidation:
    """Tests for line item validation"""
    
    def test_validate_line_item_valid(self, sample_line_item):
        """Test valid line item"""
        is_valid, msg = BillValidator.validate_line_item(sample_line_item)
        assert is_valid is True
        assert msg == ""
    
    def test_validate_line_item_missing_field(self):
        """Test line item with missing required field"""
        item = {
            "item_name": "Medicine",
            "item_amount": 100.0,
            "item_rate": 25.0
        }
        is_valid, msg = BillValidator.validate_line_item(item)
        assert is_valid is False
        assert "item_quantity" in msg
    
    def test_validate_line_item_empty_name(self):
        """Test line item with empty name"""
        item = {
            "item_name": "",
            "item_amount": 100.0,
            "item_rate": 25.0,
            "item_quantity": 4.0
        }
        is_valid, msg = BillValidator.validate_line_item(item)
        assert is_valid is False
    
    def test_validate_line_item_metadata_date(self):
        """Test that dates are rejected as item names"""
        item = {
            "item_name": "2024-01-15",
            "item_amount": 100.0,
            "item_rate": 25.0,
            "item_quantity": 4.0
        }
        is_valid, msg = BillValidator.validate_line_item(item)
        assert is_valid is False
        assert "metadata" in msg.lower()
    
    def test_validate_line_item_metadata_invoice_id(self):
        """Test that invoice IDs are rejected as item names"""
        item = {
            "item_name": "INV-001",
            "item_amount": 100.0,
            "item_rate": 25.0,
            "item_quantity": 4.0
        }
        is_valid, msg = BillValidator.validate_line_item(item)
        assert is_valid is False
    
    def test_validate_line_item_negative_amount(self):
        """Test line item with negative amount"""
        item = {
            "item_name": "Medicine",
            "item_amount": -100.0,
            "item_rate": 25.0,
            "item_quantity": 4.0
        }
        is_valid, msg = BillValidator.validate_line_item(item)
        assert is_valid is False
    
    def test_validate_line_item_amount_mismatch(self):
        """Test line item with amount not matching quantity × rate"""
        item = {
            "item_name": "Medicine",
            "item_amount": 999.0,  # Doesn't match 5 * 50 = 250
            "item_rate": 50.0,
            "item_quantity": 5.0
        }
        is_valid, msg = BillValidator.validate_line_item(item)
        # Should still be valid (logs warning but doesn't fail)
        # This allows for discounts, taxes, etc.
        assert is_valid is True


# ============================================================================
# TESTS: METADATA DETECTION
# ============================================================================

class TestMetadataDetection:
    """Tests for metadata value detection"""
    
    def test_detect_date_format_1(self):
        """Test date detection: YYYY-MM-DD"""
        assert BillValidator._is_metadata_value("2024-01-15") is True
    
    def test_detect_date_format_2(self):
        """Test date detection: MM/DD/YYYY"""
        assert BillValidator._is_metadata_value("01/15/2024") is True
    
    def test_detect_invoice_id(self):
        """Test invoice ID detection"""
        assert BillValidator._is_metadata_value("INV-001") is True
        assert BillValidator._is_metadata_value("INV001") is True
    
    def test_detect_reference_id(self):
        """Test reference ID detection"""
        assert BillValidator._is_metadata_value("REF-123456") is True
    
    def test_detect_time(self):
        """Test time detection"""
        assert BillValidator._is_metadata_value("14:30") is True
    
    def test_not_metadata_product_name(self):
        """Test product names are not detected as metadata"""
        assert BillValidator._is_metadata_value("Aspirin 500mg") is False
        assert BillValidator._is_metadata_value("Paracetamol Syrup") is False


# ============================================================================
# TESTS: DUPLICATE DETECTION
# ============================================================================

class TestDuplicateDetection:
    """Tests for duplicate item detection"""
    
    def test_check_duplicates_none(self):
        """Test with no duplicates"""
        items = [
            {"item_name": "Item A", "item_amount": 100.0, "item_quantity": 1.0},
            {"item_name": "Item B", "item_amount": 50.0, "item_quantity": 1.0}
        ]
        dup_count, dup_details = BillValidator.check_duplicates(items)
        assert dup_count == 0
        assert len(dup_details) == 0
    
    def test_check_duplicates_exact(self):
        """Test with exact duplicate"""
        items = [
            {"item_name": "Item A", "item_amount": 100.0, "item_quantity": 1.0},
            {"item_name": "Item A", "item_amount": 100.0, "item_quantity": 1.0}
        ]
        dup_count, dup_details = BillValidator.check_duplicates(items)
        assert dup_count == 1
        assert len(dup_details) > 0
    
    def test_check_duplicates_case_insensitive(self):
        """Test duplicate detection is case-insensitive"""
        items = [
            {"item_name": "Item A", "item_amount": 100.0, "item_quantity": 1.0},
            {"item_name": "item a", "item_amount": 100.0, "item_quantity": 1.0}
        ]
        dup_count, dup_details = BillValidator.check_duplicates(items)
        assert dup_count == 1


# ============================================================================
# TESTS: TOTAL RECONCILIATION
# ============================================================================

class TestTotalReconciliation:
    """Tests for total reconciliation"""
    
    def test_reconcile_totals_perfect_match(self, sample_items):
        """Test reconciliation with perfect match"""
        result = BillValidator.reconcile_totals(sample_items, 550.0)
        assert result["matches"] is True
        assert result["reconciliation_status"] == "perfect"
        assert result["variance"] < 0.01
    
    def test_reconcile_totals_acceptable_variance(self, sample_items):
        """Test reconciliation with acceptable variance (<1%)"""
        result = BillValidator.reconcile_totals(sample_items, 556.0)  # ~1% variance
        assert result["reconciliation_status"] in ["acceptable", "perfect"]
    
    def test_reconcile_totals_needs_review(self, sample_items):
        """Test reconciliation with large variance"""
        result = BillValidator.reconcile_totals(sample_items, 1000.0)
        assert result["reconciliation_status"] == "needs_review"
        assert result["variance"] > 0
    
    def test_reconcile_totals_zero_claimed(self):
        """Test reconciliation with zero claimed total"""
        items = [{"item_amount": 100.0}]
        result = BillValidator.reconcile_totals(items, 0)
        assert result["calculated_total"] == 100.0


# ============================================================================
# TESTS: EXTRACTION QUALITY
# ============================================================================

class TestExtractionQuality:
    """Tests for extraction quality assessment"""
    
    def test_validate_extraction_quality_all_valid(self, sample_items):
        """Test quality with all valid items"""
        report = BillValidator.validate_extraction_quality(sample_items)
        assert report["valid_items"] == 2
        assert report["invalid_items"] == 0
        assert report["quality_score"] >= 90
    
    def test_validate_extraction_quality_with_invalid(self):
        """Test quality with some invalid items"""
        items = [
            {"item_name": "Valid Item", "item_amount": 100.0, "item_rate": 25.0, "item_quantity": 4.0},
            {"item_name": "2024-01-15", "item_amount": 100.0, "item_rate": 25.0, "item_quantity": 4.0}
        ]
        report = BillValidator.validate_extraction_quality(items)
        assert report["invalid_items"] >= 1
        assert report["quality_score"] < 100
    
    def test_validate_extraction_quality_empty(self):
        """Test quality with empty item list"""
        report = BillValidator.validate_extraction_quality([])
        assert report["total_items"] == 0
        assert report["quality_score"] == 0


# ============================================================================
# TESTS: RESPONSE FORMATTING
# ============================================================================

class TestResponseFormatting:
    """Tests for response formatting"""
    
    def test_success_response_structure(self):
        """Test success response has correct structure"""
        response = ResponseFormatter.success_response(
            pagewise_items=[],
            token_usage={"total_tokens": 100, "input_tokens": 70, "output_tokens": 30},
            total_item_count=0
        )
        
        assert response["is_success"] is True
        assert "token_usage" in response
        assert "data" in response
        assert response["token_usage"]["total_tokens"] == 100
    
    def test_error_response_structure(self):
        """Test error response has correct structure"""
        response = ResponseFormatter.error_response("Test error")
        
        assert response["is_success"] is False
        assert response["message"] == "Test error"
    
    def test_format_page_items(self):
        """Test page item formatting"""
        items = [{"item_name": "Medicine", "item_amount": 100.0, "item_rate": 25.0, "item_quantity": 4.0}]
        page = ResponseFormatter.format_page_items("1", "Bill Detail", items)
        
        assert page["page_no"] == "1"
        assert page["page_type"] == "Bill Detail"
        assert len(page["bill_items"]) == 1
    
    def test_clean_line_item_valid(self):
        """Test cleaning valid line item"""
        item = {
            "item_name": "  Medicine A  ",
            "item_amount": "100.50",
            "item_rate": "25.12",
            "item_quantity": "4"
        }
        cleaned = ResponseFormatter._clean_line_item(item)
        
        assert cleaned is not None
        assert cleaned["item_name"] == "Medicine A"
        assert cleaned["item_amount"] == 100.50
    
    def test_to_float_conversion_string(self):
        """Test float conversion from string"""
        assert ResponseFormatter._to_float("100.50") == 100.50
    
    def test_to_float_conversion_currency(self):
        """Test float conversion from currency string"""
        assert ResponseFormatter._to_float("₹100") == 100.0
        assert ResponseFormatter._to_float("$100.50") == 100.50
    
    def test_to_float_conversion_with_comma(self):
        """Test float conversion with comma separator"""
        assert ResponseFormatter._to_float("1,000.50") == 1000.50
    
    def test_to_float_conversion_invalid(self):
        """Test float conversion with invalid input"""
        assert ResponseFormatter._to_float("invalid") is None
    
    def test_validate_page_type_exact(self):
        """Test page type validation with exact match"""
        assert ResponseFormatter._validate_page_type("Bill Detail") == "Bill Detail"
    
    def test_validate_page_type_case_insensitive(self):
        """Test page type validation is case-insensitive"""
        assert ResponseFormatter._validate_page_type("bill detail") == "Bill Detail"
    
    def test_validate_page_type_invalid(self):
        """Test page type validation with invalid type"""
        assert ResponseFormatter._validate_page_type("Invalid") == "Bill Detail"


# ============================================================================
# TESTS: SCHEMA VALIDATION
# ============================================================================

class TestSchemaValidation:
    """Tests for response schema validation"""
    
    def test_validate_schema_valid_success(self, sample_response):
        """Test validation of valid success response"""
        assert ResponseFormatter.validate_response_schema(sample_response) is True
    
    def test_validate_schema_missing_is_success(self):
        """Test validation fails when is_success is missing"""
        response = {"data": {}}
        assert ResponseFormatter.validate_response_schema(response) is False
    
    def test_validate_schema_missing_token_usage(self):
        """Test validation fails when token_usage is missing"""
        response = {
            "is_success": True,
            "data": {"pagewise_line_items": [], "total_item_count": 0}
        }
        assert ResponseFormatter.validate_response_schema(response) is False
    
    def test_validate_schema_valid_error(self):
        """Test validation of valid error response"""
        response = {"is_success": False, "message": "Error message"}
        assert ResponseFormatter.validate_response_schema(response) is True


# ============================================================================
# TESTS: API ENDPOINTS
# ============================================================================

class TestAPIEndpoints:
    """Tests for API endpoints"""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
    
    def test_home_endpoint(self, client):
        """Test home endpoint"""
        response = client.get('/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "endpoints" in data
    
    def test_extract_bill_data_missing_document(self, client):
        """Test extract endpoint with missing document"""
        response = client.post(
            '/extract-bill-data',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["is_success"] is False
    
    def test_extract_bill_data_invalid_json(self, client):
        """Test extract endpoint with invalid JSON"""
        response = client.post(
            '/extract-bill-data',
            data="invalid json",
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_extract_bill_data_invalid_url(self, client):
        """Test extract endpoint with invalid URL"""
        response = client.post(
            '/extract-bill-data',
            json={"document": "not-a-url"},
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_not_found_endpoint(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["is_success"] is False
    
    def test_method_not_allowed(self, client):
        """Test 405 error handling"""
        response = client.get('/extract-bill-data')
        assert response.status_code == 405


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])