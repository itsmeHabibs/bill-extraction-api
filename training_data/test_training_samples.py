"""
Test script to process all training samples and analyze accuracy
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingSampleTester:
    """Test all training samples and generate accuracy report"""
    
    def __init__(self, api_base_url="http://localhost:3000", samples_dir="training_data/TRAINING_SAMPLES"):
        self.api_base_url = api_base_url
        self.samples_dir = Path(samples_dir)
        self.results_dir = Path("training_data/test_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
        self.summary = {
            "total_documents": 0,
            "successful": 0,
            "failed": 0,
            "total_items_extracted": 0,
            "total_tokens_used": 0,
            "avg_processing_time": 0,
            "documents": []
        }
    
    def upload_file_to_temp_server(self, file_path):
        """
        Upload file to a temporary server and get URL
        For local testing, we'll read the file directly
        """
        # For now, return the local path
        # In production, you'd upload to a cloud storage and get URL
        return str(file_path.absolute())
    
    def process_document(self, file_path):
        """Process a single document"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {file_path.name}")
        logger.info(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            # For local testing, we need to convert file to URL
            # Option 1: Read file and send as base64
            # Option 2: Host locally with a simple server
            # Option 3: Use the API's direct file processing (if available)
            
            # For this example, let's assume we have a way to get the file URL
            # In reality, you'd need to upload to cloud storage first
            
            # Since we're testing locally, let's modify the API call
            # to accept local file paths in development mode
            
            response = self._call_api_with_local_file(file_path)
            
            processing_time = time.time() - start_time
            
            if response.get("is_success"):
                result = {
                    "document_name": file_path.name,
                    "status": "success",
                    "processing_time": round(processing_time, 2),
                    "items_extracted": response["data"]["total_item_count"],
                    "token_usage": response["token_usage"],
                    "pagewise_items": response["data"]["pagewise_line_items"]
                }
                
                self.summary["successful"] += 1
                self.summary["total_items_extracted"] += result["items_extracted"]
                self.summary["total_tokens_used"] += response["token_usage"]["total_tokens"]
                
                logger.info(f"✅ SUCCESS - Extracted {result['items_extracted']} items in {processing_time:.2f}s")
            else:
                result = {
                    "document_name": file_path.name,
                    "status": "failed",
                    "processing_time": round(processing_time, 2),
                    "error": response.get("message", "Unknown error")
                }
                
                self.summary["failed"] += 1
                logger.error(f"❌ FAILED - {result['error']}")
            
            self.results.append(result)
            self.summary["documents"].append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Exception processing {file_path.name}: {e}")
            result = {
                "document_name": file_path.name,
                "status": "error",
                "error": str(e)
            }
            self.results.append(result)
            self.summary["failed"] += 1
            return result
    
    def _call_api_with_local_file(self, file_path):
        """
        Call API with local file
        This is a workaround for testing. In production, files would be hosted online.
        """
        # Read file and convert to base64 or use direct file upload
        # For now, let's use a placeholder URL structure
        
        # If your API endpoint is running locally, you can modify it to accept file paths
        # Or upload the file to a temporary hosting service
        
        # Placeholder implementation:
        # In real scenario, you'd upload file to cloud storage and get URL
        
        logger.warning("⚠️  Local file testing requires modification to handle file uploads")
        logger.info("💡 Recommended: Upload training samples to cloud storage and use URLs")
        
        # Return mock response for now
        return {
            "is_success": False,
            "message": "Local file testing not implemented. Upload files to cloud storage and use URLs."
        }
    
    def run_all_tests(self):
        """Run tests on all training samples"""
        logger.info("🚀 Starting Training Sample Tests...")
        logger.info(f"📁 Samples directory: {self.samples_dir}")
        
        # Find all PDF/PNG files in training samples
        file_patterns = ["*.pdf", "*.png", "*.jpg", "*.jpeg"]
        all_files = []
        
        for pattern in file_patterns:
            all_files.extend(self.samples_dir.glob(pattern))
        
        if not all_files:
            logger.error(f"❌ No files found in {self.samples_dir}")
            return
        
        logger.info(f"📊 Found {len(all_files)} files to process")
        
        self.summary["total_documents"] = len(all_files)
        
        # Process each file
        for i, file_path in enumerate(all_files, 1):
            logger.info(f"\n[{i}/{len(all_files)}] Processing {file_path.name}...")
            self.process_document(file_path)
            
            # Add delay to avoid rate limiting
            time.sleep(2)
        
        # Calculate averages
        if self.summary["successful"] > 0:
            total_time = sum(r.get("processing_time", 0) for r in self.results if "processing_time" in r)
            self.summary["avg_processing_time"] = round(total_time / self.summary["successful"], 2)
        
        # Save results
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.summary, f, indent=2)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*70)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*70)
        logger.info(f"Total Documents: {self.summary['total_documents']}")
        logger.info(f"✅ Successful: {self.summary['successful']}")
        logger.info(f"❌ Failed: {self.summary['failed']}")
        logger.info(f"📦 Total Items Extracted: {self.summary['total_items_extracted']}")
        logger.info(f"🎫 Total Tokens Used: {self.summary['total_tokens_used']}")
        logger.info(f"⏱️  Avg Processing Time: {self.summary['avg_processing_time']}s")
        
        if self.summary['successful'] > 0:
            success_rate = (self.summary['successful'] / self.summary['total_documents']) * 100
            logger.info(f"📈 Success Rate: {success_rate:.2f}%")
        
        logger.info("="*70)


def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║       Training Sample Tester - Bill Extraction API          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Configuration
    API_URL = "http://localhost:3000"
    SAMPLES_DIR = "training_data/TRAINING_SAMPLES"
    
    # Check if samples directory exists
    if not Path(SAMPLES_DIR).exists():
        logger.error(f"❌ Samples directory not found: {SAMPLES_DIR}")
        logger.info("📥 Please download and extract TRAINING_SAMPLES.zip to training_data/")
        return
    
    # Create tester instance
    tester = TrainingSampleTester(api_base_url=API_URL, samples_dir=SAMPLES_DIR)
    
    # Run tests
    tester.run_all_tests()


if __name__ == "__main__":
    main()