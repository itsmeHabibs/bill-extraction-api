"""
Convert PDF files to PNG images for easier processing
Requires: pdf2image library
Install: pip install pdf2image pillow
Also requires: poppler (https://github.com/oschwartz10612/poppler-windows/releases/)
"""

import os
from pathlib import Path
from pdf2image import convert_from_path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_pdf_to_images(pdf_path, output_dir, dpi=300):
    """
    Convert a PDF file to PNG images (one per page)
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save images
        dpi: Resolution for conversion (default 300)
    """
    try:
        logger.info(f"Converting {pdf_path.name}...")
        
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        output_files = []
        for i, image in enumerate(images, 1):
            output_file = output_dir / f"{pdf_path.stem}_page_{i}.png"
            image.save(output_file, 'PNG')
            output_files.append(output_file)
            logger.info(f"  ✅ Saved page {i} to {output_file.name}")
        
        return output_files
        
    except Exception as e:
        logger.error(f"  ❌ Failed to convert {pdf_path.name}: {e}")
        return []


def batch_convert_pdfs(input_dir, output_dir):
    """
    Convert all PDFs in a directory to images
    
    Args:
        input_dir: Directory containing PDFs
        output_dir: Directory to save images
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    logger.info(f"Output directory: {output_path}")
    logger.info("="*70)
    
    total_pages = 0
    for pdf_file in pdf_files:
        output_files = convert_pdf_to_images(pdf_file, output_path)
        total_pages += len(output_files)
    
    logger.info("="*70)
    logger.info(f"✅ Conversion complete!")
    logger.info(f"📄 Processed {len(pdf_files)} PDFs")
    logger.info(f"🖼️  Generated {total_pages} images")


def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           PDF to Image Converter - Training Data            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    INPUT_DIR = "training_data/TRAINING_SAMPLES"
    OUTPUT_DIR = "training_data/TRAINING_IMAGES"
    
    # Check if input directory exists
    if not Path(INPUT_DIR).exists():
        logger.error(f"❌ Input directory not found: {INPUT_DIR}")
        logger.info("📥 Please download and extract TRAINING_SAMPLES.zip")
        return
    
    # Convert PDFs
    batch_convert_pdfs(INPUT_DIR, OUTPUT_DIR)
    
    logger.info(f"\n💡 Next steps:")
    logger.info(f"   1. Upload images from {OUTPUT_DIR} to cloud storage")
    logger.info(f"   2. Get public URLs for each image")
    logger.info(f"   3. Test with your API endpoint")


if __name__ == "__main__":
    main()