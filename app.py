"""
Bill Data Extraction API - Main Application
Handles bill data extraction from document images
"""

import logging
import json
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config

# ============================================================================
# Configure Logging
# ============================================================================

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ============================================================================
# Initialize Flask Application
# ============================================================================

app = Flask(__name__)
CORS(app)

# Configure Flask app settings
app.config['JSON_SORT_KEYS'] = Config.JSON_SORT_KEYS
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = Config.JSONIFY_PRETTYPRINT_REGULAR


# ============================================================================
# Validate Configuration on Startup
# ============================================================================

try:
    logger.info("🚀 Initializing Bill Extraction API...")
    Config.validate_config()
    logger.info("✅ Configuration validated successfully")
    logger.info(f"📊 Configuration: {Config.get_config_summary()}")
except ValueError as e:
    logger.error(f"❌ Configuration error: {e}")
    raise


# ============================================================================
# Import Utility Modules (after config validation)
# ============================================================================

from utils.ocr_extractor import OCRExtractor
from utils.llm_processor import LLMProcessor
from utils.response_formatter import ResponseFormatter
from utils.validators import BillValidator


# ============================================================================
# API Routes
# ============================================================================

@app.route('/extract-bill-data', methods=['POST'])
def extract_bill_data():
    """
    Main API endpoint for bill data extraction
    
    Request JSON:
        {
            "document": "https://url-to-document-image.png"
        }
    
    Response JSON (Success):
        {
            "is_success": true,
            "token_usage": {
                "total_tokens": 1523,
                "input_tokens": 1245,
                "output_tokens": 278
            },
            "data": {
                "pagewise_line_items": [...],
                "total_item_count": 4
            }
        }
    
    Response JSON (Error):
        {
            "is_success": false,
            "message": "Error description"
        }
    """
    
    request_start_time = __import__('time').time()
    
    try:
        # ====== Step 1: Parse and Validate Request ======
        logger.info("📨 Received extraction request")
        
        request_data = request.get_json()
        
        if not request_data:
            logger.warning("❌ Request body is not valid JSON")
            return jsonify(ResponseFormatter.error_response(
                "Request body must be valid JSON"
            )), 400
        
        document_url = request_data.get("document")
        
        # Validate URL format
        is_valid, error_msg = BillValidator.validate_url(document_url)
        if not is_valid:
            logger.warning(f"❌ Invalid URL: {error_msg}")
            return jsonify(ResponseFormatter.error_response(error_msg)), 400
        
        logger.info(f"📄 Processing document: {document_url[:80]}...")
        
        
        # ====== Step 2: OCR Text Extraction (Step A) ======
        logger.info("🔍 Step A: Starting OCR extraction...")
        ocr_extractor = OCRExtractor()
        ocr_text = ocr_extractor.extract_text_from_url(document_url)
        
        if not ocr_text or len(ocr_text.strip()) == 0:
            logger.error("❌ OCR extraction failed or returned empty text")
            return jsonify(ResponseFormatter.error_response(
                "Failed to extract text from document. Ensure document is accessible "
                "and contains readable text."
            )), 422
        
        logger.info(f"✅ OCR extraction successful. Text length: {len(ocr_text)} characters")
        
        
        # ====== Step 3: LLM Information Extraction (Step B) ======
        logger.info("🤖 Step B: Starting LLM extraction...")
        llm_processor = LLMProcessor()
        llm_processor.reset_token_usage()
        
        # Extract line items using Claude
        extracted_data, input_tok, output_tok = llm_processor.extract_bill_items(
            ocr_text, 
            page_number="1"
        )
        
        if not extracted_data or "line_items" not in extracted_data:
            logger.error("❌ LLM extraction failed - no data returned")
            return jsonify(ResponseFormatter.error_response(
                "Failed to extract structured data from document"
            )), 500
        
        line_items = extracted_data.get("line_items", [])
        logger.info(f"✅ LLM extraction successful. Found {len(line_items)} line items")
        
        if not line_items:
            logger.warning("⚠️  No line items found in extraction")
            return jsonify(ResponseFormatter.error_response(
                "No bill line items found in the document. Please verify the document contains line items."
            )), 422
        
        
        # ====== Step 4: Data Validation ======
        logger.info("✔️  Step 3: Starting data validation...")
        
        # Validate quality
        validation_report = BillValidator.validate_extraction_quality(line_items)
        logger.info(f"📊 Validation report: {validation_report}")
        
        if validation_report["quality_score"] < 50:
            logger.error(f"❌ Extraction quality too low: {validation_report['quality_score']}%")
            return jsonify(ResponseFormatter.error_response(
                f"Extraction quality below threshold. Quality score: {validation_report['quality_score']}%"
            )), 422
        
        # Check for duplicates
        dup_count, dup_details = BillValidator.check_duplicates(line_items)
        if dup_count > 0:
            logger.warning(f"⚠️  Found {dup_count} potential duplicate items")
            logger.debug(f"Duplicate details: {dup_details}")
        
        
        # ====== Step 5: Format Response ======
        logger.info("📝 Formatting response...")
        
        page_type = extracted_data.get("page_type", "Bill Detail")
        pagewise_items = [
            ResponseFormatter.format_page_items(
                page_number="1",
                page_type=page_type,
                line_items=line_items
            )
        ]
        
        # Count total items
        total_item_count = sum(len(page.get("bill_items", [])) for page in pagewise_items)
        
        # Prepare final response
        response = ResponseFormatter.success_response(
            pagewise_items=pagewise_items,
            token_usage=llm_processor.get_token_usage(),
            total_item_count=total_item_count
        )
        
        
        # ====== Step 6: Validate Response Schema ======
        if not ResponseFormatter.validate_response_schema(response):
            logger.error("❌ Response schema validation failed")
            return jsonify(ResponseFormatter.error_response(
                "Internal error: Response schema validation failed"
            )), 500
        
        
        # ====== Step 7: Log and Return ======
        elapsed_time = __import__('time').time() - request_start_time
        logger.info(f"✅ Successfully processed document in {elapsed_time:.2f}s")
        logger.info(f"📊 Total items: {total_item_count}, Tokens used: {response['token_usage']['total_tokens']}")
        
        return jsonify(response), 200
    
    
    # ========== Error Handling ==========
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in request body")
        return jsonify(ResponseFormatter.error_response(
            "Request body must be valid JSON"
        )), 400
    
    except Exception as e:
        logger.exception(f"❌ Unexpected error during extraction: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return jsonify(ResponseFormatter.error_response(
            "Internal server error during document processing"
        )), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    
    Returns:
        JSON with service status
    """
    return jsonify({
        "status": "healthy",
        "service": "Bill Data Extraction API",
        "version": "1.0.0",
        "environment": Config.ENVIRONMENT
    }), 200


@app.route('/', methods=['GET'])
def home():
    """
    Home endpoint with API information
    
    Returns:
        JSON with API documentation
    """
    return jsonify({
        "message": "Bill Data Extraction API - HackRx Datathon",
        "status": "🟢 Operational",
        "endpoints": {
            "extract": "/extract-bill-data (POST)",
            "health": "/health (GET)"
        },
        "documentation": "See README.md for detailed documentation",
        "version": "1.0.0"
    }), 200


# ========== Error Handlers ==========

@app.errorhandler(404)
def not_found(error):
    """Handle 404 - Not Found errors"""
    logger.warning(f"404 - Endpoint not found")
    return jsonify(ResponseFormatter.error_response(
        "Endpoint not found. See / for available endpoints."
    )), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 - Method Not Allowed errors"""
    logger.warning(f"405 - Method not allowed")
    return jsonify(ResponseFormatter.error_response(
        "Method not allowed for this endpoint"
    )), 405


@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 - Internal Server Error"""
    logger.error(f"500 - Internal server error: {error}")
    return jsonify(ResponseFormatter.error_response(
        "Internal server error. Please try again later."
    )), 500


# ========== Context Processors ==========

@app.before_request
def log_request():
    """Log incoming requests"""
    if request.path != '/health':  # Don't log health checks
        logger.debug(f"→ {request.method} {request.path}")


@app.after_request
def log_response(response):
    """Log outgoing responses"""
    if request.path != '/health':  # Don't log health checks
        logger.debug(f"← {response.status_code} {request.method} {request.path}")
    return response


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 Bill Data Extraction API Starting...")
    logger.info("=" * 70)
    logger.info(f"🌐 Server: 0.0.0.0:{Config.PORT}")
    logger.info(f"🔧 Debug: {Config.DEBUG}")
    logger.info(f"📌 Environment: {Config.ENVIRONMENT}")
    logger.info("=" * 70)
    logger.info("✅ Ready to accept requests!")
    logger.info("=" * 70)
    
    app.run(
        host='0.0.0.0',
        port=Config.PORT,
        debug=Config.DEBUG
    )