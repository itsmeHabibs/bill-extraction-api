"""
Test API with actual URLs from training samples
You need to upload training images to cloud storage first and add URLs here
"""

import requests
import json
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class APITester:
    """Test API with sample URLs"""
    
    def __init__(self, api_url="http://localhost:3000"):
        self.api_url = api_url
        self.results = []
    
    def test_document(self, document_url, document_name=""):
        """Test a single document"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing: {document_name or document_url}")
        logger.info(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            # Make API request
            response = requests.post(
                f"{self.api_url}/extract-bill-data",
                json={"document": document_url},
                timeout=120
            )
            
            processing_time = time.time() - start_time
            
            # Parse response
            result = response.json()
            
            if response.status_code == 200 and result.get("is_success"):
                logger.info(f"✅ SUCCESS (HTTP {response.status_code})")
                logger.info(f"⏱️  Processing Time: {processing_time:.2f}s")
                logger.info(f"📦 Items Extracted: {result['data']['total_item_count']}")
                logger.info(f"🎫 Tokens Used: {result['token_usage']['total_tokens']}")
                
                # Show extracted items
                logger.info(f"\n📋 Extracted Items:")
                for page in result['data']['pagewise_line_items']:
                    logger.info(f"  Page {page['page_no']} ({page['page_type']}):")
                    for item in page['bill_items']:
                        logger.info(f"    • {item['item_name']}: ₹{item['item_amount']} "
                                  f"({item['item_quantity']} × ₹{item['item_rate']})")
                
                self.results.append({
                    "document": document_name or document_url,
                    "status": "success",
                    "items": result['data']['total_item_count'],
                    "tokens": result['token_usage']['total_tokens'],
                    "time": processing_time
                })
                
            else:
                logger.error(f"❌ FAILED (HTTP {response.status_code})")
                logger.error(f"Error: {result.get('message', 'Unknown error')}")
                
                self.results.append({
                    "document": document_name or document_url,
                    "status": "failed",
                    "error": result.get('message', 'Unknown error')
                })
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ TIMEOUT - Request took longer than 120s")
            return None
            
        except Exception as e:
            logger.error(f"❌ ERROR - {str(e)}")
            return None
    
    def print_summary(self):
        """Print test summary"""
        logger.info(f"\n{'='*70}")
        logger.info("📊 TEST SUMMARY")
        logger.info(f"{'='*70}")
        
        successful = len([r for r in self.results if r['status'] == 'success'])
        failed = len([r for r in self.results if r['status'] == 'failed'])
        
        logger.info(f"Total Tests: {len(self.results)}")
        logger.info(f"✅ Passed: {successful}")
        logger.info(f"❌ Failed: {failed}")
        
        if successful > 0:
            avg_items = sum(r.get('items', 0) for r in self.results if r['status'] == 'success') / successful
            avg_tokens = sum(r.get('tokens', 0) for r in self.results if r['status'] == 'success') / successful
            avg_time = sum(r.get('time', 0) for r in self.results if r['status'] == 'success') / successful
            
            logger.info(f"\n📈 Averages:")
            logger.info(f"  Items per document: {avg_items:.1f}")
            logger.info(f"  Tokens per document: {avg_tokens:.0f}")
            logger.info(f"  Processing time: {avg_time:.2f}s")
        
        logger.info(f"{'='*70}")


def main():
    """Main testing function"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          API Tester - Bill Extraction with URLs             ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Your API URL (change to deployed URL for production testing)
    API_URL = "http://localhost:3000"
    
    # Test URLs - Add your uploaded training sample URLs here
    test_cases = [
        # {
        #     "name": "Sample 2 - Pharmacy Bill",
        #     "url": "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"
        # },
        # # Add more test cases here after uploading training samples
       {
  "name": "train_sample_1_page-0001",
  "url": "https://i.postimg.cc/yNY7pXhf/train-sample-1-page-0001.jpg"
},
{
  "name": "train_sample_1_page-0002",
  "url": "https://i.postimg.cc/SNNVsnGv/train-sample-1-page-0002.jpg"
}
# {
#   "name": "train_sample_2_page-0001",
#   "url": "https://i.postimg.cc/pXXkTmB1/train-sample-2-page-0001.jpg"
# },
# {
#   "name": "train_sample_2_page-0002",
#   "url": "https://i.postimg.cc/m22VDPSn/train-sample-2-page-0002.jpg"
# },
# {
#   "name": "train_sample_2_page-0003",
#   "url": "https://i.postimg.cc/022ZQzCX/train-sample-2-page-0003.jpg"
# },
# {
#   "name": "train_sample_3_page-0001",
#   "url": "https://i.postimg.cc/c49h8dDp/train-sample-3-page-0001.jpg"
# },
# {
#   "name": "train_sample_4_page-0001",
#   "url": "https://i.postimg.cc/Pr3y8d6c/train-sample-4-page-0001.jpg"
# },
# {
#   "name": "train_sample_4_page-0002",
#   "url": "https://i.postimg.cc/VLGgbz7p/train-sample-4-page-0002.jpg"
# },
# {
#   "name": "train_sample_5_page-0001",
#   "url": "https://i.postimg.cc/c49h8dDP/train-sample-5-page-0001.jpg"
# },
# {
#   "name": "train_sample_5_page-0002",
#   "url": "https://i.postimg.cc/g2xDV1QY/train-sample-5-page-0002.jpg"
# },
# {
#   "name": "train_sample_5_page-0003",
#   "url": "https://i.postimg.cc/52X3BDT9/train-sample-5-page-0003.jpg"
# },
# {
#   "name": "train_sample_6_page-0001",
#   "url": "https://i.postimg.cc/Hkr2wFRj/train-sample-6-page-0001.jpg"
# },
# {
#   "name": "train_sample_6_page-0002",
#   "url": "https://i.postimg.cc/8z7HRx95/train-sample-6-page-0002.jpg"
# },
# {
#   "name": "train_sample_6_page-0003",
#   "url": "https://i.postimg.cc/138HGb2p/train-sample-6-page-0003.jpg"
# },
# {
#   "name": "train_sample_7_page-0001",
#   "url": "https://i.postimg.cc/RZWR72y7/train-sample-7-page-0001.jpg"
# },
# {
#   "name": "train_sample_8_page-0001",
#   "url": "https://i.postimg.cc/pLmZf34C/train-sample-8-page-0001.jpg"
# },
# {
#   "name": "train_sample_9_page-0001",
#   "url": "https://i.postimg.cc/T3BcCCX6/train-sample-9-page-0001.jpg"
# },
# {
#   "name": "train_sample_9_page-0002",
#   "url": "https://i.postimg.cc/xdH37M9B/train-sample-9-page-0002.jpg"
# },
# {
#   "name": "train_sample_9_page-0003",
#   "url": "https://i.postimg.cc/t48z22HX/train-sample-9-page-0003.jpg"
# },
# {
#   "name": "train_sample_10_page-0001",
#   "url": "https://i.postimg.cc/FKcVq3h8/train-sample-10-page-0001.jpg"
# },
# {
#   "name": "train_sample_10_page-0002",
#   "url": "https://i.postimg.cc/zfWFMKJ5/train-sample-10-page-0002.jpg"
# },
# {
#   "name": "train_sample_10_page-0003",
#   "url": "https://i.postimg.cc/jjN49PsD/train-sample-10-page-0003.jpg"
# },
# {
#   "name": "train_sample_11_page-0001",
#   "url": "https://i.postimg.cc/9MhYj0MM/train-sample-11-page-0001.jpg"
# },
# {
#   "name": "train_sample_12_page-0001",
#   "url": "https://i.postimg.cc/cJYBjwsY/train-sample-12-page-0001.jpg"
# },
# {
#   "name": "train_sample_12_page-0002",
#   "url": "https://i.postimg.cc/brvbztjT/train-sample-12-page-0002.jpg"
# },
# {
#   "name": "train_sample_12_page-0003",
#   "url": "https://i.postimg.cc/x8dH0zSP/train-sample-12-page-0003.jpg"
# },
# {
#   "name": "train_sample_12_page-0004",
#   "url": "https://i.postimg.cc/prd82Ftq/train-sample-12-page-0004.jpg"
# },
# {
#   "name": "train_sample_12_page-0005",
#   "url": "https://i.postimg.cc/L5sfH1My/train-sample-12-page-0005.jpg"
# },
# {
#   "name": "train_sample_12_page-0006",
#   "url": "https://i.postimg.cc/Y0yFjCpx/train-sample-12-page-0006.jpg"
# },
# {
#   "name": "train_sample_13_page-0001",
#   "url": "https://i.postimg.cc/0jHSry8Z/train-sample-13-page-0001.jpg"
# },
# {
#   "name": "train_sample_13_page-0002",
#   "url": "https://i.postimg.cc/pr1jyL2C/train-sample-13-page-0002.jpg"
# },
# {
#   "name": "train_sample_13_page-0003",
#   "url": "https://i.postimg.cc/2yXW3Szc/train-sample-13-page-0003.jpg"
# },
# {
#   "name": "train_sample_13_page-0004",
#   "url": "https://i.postimg.cc/6q1ZTp9F/train-sample-13-page-0004.jpg"
# },
# {
#   "name": "train_sample_13_page-0005",
#   "url": "https://i.postimg.cc/d3SCDVsP/train-sample-13-page-0005.jpg"
# },
# {
#   "name": "train_sample_14_page-0001",
#   "url": "https://i.postimg.cc/rsY4zwV2/train-sample-14-page-0001.jpg"
# },
# {
#   "name": "train_sample_14_page-0002",
#   "url": "https://i.postimg.cc/wMbN3jqp/train-sample-14-page-0002.jpg"
# },
# {
#   "name": "train_sample_14_page-0003",
#   "url": "https://i.postimg.cc/3rLmtngk/train-sample-14-page-0003.jpg"
# },
# {
#   "name": "train_sample_14_page-0004",
#   "url": "https://i.postimg.cc/ryhxfQSt/train-sample-14-page-0004.jpg"
# },
# {
#   "name": "train_sample_14_page-0005",
#   "url": "https://i.postimg.cc/9XxZLJG7/train-sample-14-page-0005.jpg"
# },
# {
#   "name": "train_sample_14_page-0006",
#   "url": "https://i.postimg.cc/kMjKTfxR/train-sample-14-page-0006.jpg"
# },
# {
#   "name": "train_sample_15_page-0001",
#   "url": "https://i.postimg.cc/2jHh024v/train-sample-15-page-0001.jpg"
# },
# {
#   "name": "train_sample_15_page-0002",
#   "url": "https://i.postimg.cc/zDdKx0nF/train-sample-15-page-0002.jpg"
# },
# {
#   "name": "train_sample_15_page-0003",
#   "url": "https://i.postimg.cc/jq8PMZzh/train-sample-15-page-0003.jpg"
# },
# {
#   "name": "train_sample_15_page-0004",
#   "url": "https://i.postimg.cc/Kc9B0JnN/train-sample-15-page-0004.jpg"
# },
# {
#   "name": "train_sample_15_page-0005",
#   "url": "https://i.postimg.cc/J7TZpPbK/train-sample-15-page-0005.jpg"
# },
# {
#   "name": "train_sample_15_page-0006",
#   "url": "https://i.postimg.cc/qBmy1j8D/train-sample-15-page-0006.jpg"
# },
# {
#   "name": "train_sample_15_page-0007",
#   "url": "https://i.postimg.cc/59PLsnwk/train-sample-15-page-0007.jpg"
# },
# {
#   "name": "train_sample_15_page-0008",
#   "url": "https://i.postimg.cc/XN2dsQwh/train-sample-15-page-0008.jpg"
# },
# {
#   "name": "train_sample_15_page-0009",
#   "url": "https://i.postimg.cc/Pf6YS2m0/train-sample-15-page-0009.jpg"
# },
# {
#   "name": "train_sample_15_page-0010",
#   "url": "https://i.postimg.cc/8kyMZthq/train-sample-15-page-0010.jpg"
# }


    ]
    
    # Create tester
    tester = APITester(api_url=API_URL)
    
    # Test health endpoint first
    logger.info("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            logger.info("✅ API is healthy and ready")
        else:
            logger.error(f"❌ API health check failed (HTTP {response.status_code})")
            return
    except Exception as e:
        logger.error(f"❌ Cannot connect to API: {e}")
        return
    
    # Run tests
    logger.info(f"\n🚀 Starting tests with {len(test_cases)} documents...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n[{i}/{len(test_cases)}]")
        tester.test_document(test_case['url'], test_case['name'])
        
        # Add delay between requests
        if i < len(test_cases):
            time.sleep(2)
    
    # Print summary
    tester.print_summary()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"training_data/test_results/api_test_{timestamp}.json"
    
    import os
    os.makedirs("training_data/test_results", exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(tester.results, f, indent=2)
    
    logger.info(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    main()