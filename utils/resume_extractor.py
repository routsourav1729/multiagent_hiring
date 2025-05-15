#!/usr/bin/env python3
"""
Usage:
    python resume_extractor.py --input /path/to/pdf/folder --output /path/to/output/folder
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional

# Third-party imports
try:
    import pdf2image
    import pytesseract
    from PIL import Image, ImageEnhance
    from tqdm import tqdm
except ImportError:
    print("Required packages not found. Installing dependencies...")
    import subprocess
    packages = ["pdf2image", "pytesseract", "pillow", "tqdm"]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
    print("Dependencies installed successfully.")
    import pdf2image
    import pytesseract
    from PIL import Image, ImageEnhance
    from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("resume_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Common resume section headers for structure detection
RESUME_SECTIONS = [
    "education", "experience", "work experience", "employment", "skills", "technical skills",
    "projects", "certifications", "achievements", "publications", "languages", "interests",
    "professional experience", "work history", "academic background", "qualifications",
    "personal details", "contact information", "summary", "objective", "profile", "about me",
    "internships", "volunteer", "references", "awards", "honors", "coursework", "training"
]

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR quality.
    
    Args:
        image: PIL Image object
        
    Returns:
        Preprocessed PIL Image
    """
    # Convert to grayscale
    image = image.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    # Increase brightness
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.5)
    
    return image

def extract_text_from_pdf(pdf_path: str, dpi: int = 400) -> str:
    """
    Extract text from PDF using OCR.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for image conversion (higher means better quality but slower)
        
    Returns:
        Extracted text
    """
    logger.info(f"Converting PDF to images: {pdf_path}")
    try:
        # Convert PDF to images
        images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
        
        # Extract text from each page
        full_text = ""
        logger.info(f"Performing OCR on {len(images)} pages")
        
        for i, img in enumerate(images):
            # Preprocess image
            processed_img = preprocess_image(img)
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_img)
            
            # Add page separator if not the first page
            if i > 0:
                full_text += "\n\n--- Page Break ---\n\n"
                
            full_text += text
        
        return full_text
    
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
        return f"ERROR: Could not extract text: {str(e)}"

def identify_sections(text: str) -> Dict[str, List[str]]:
    """
    Identify resume sections in the extracted text.
    
    Args:
        text: Extracted text from resume
        
    Returns:
        Dictionary with section names as keys and content lines as values
    """
    lines = text.split('\n')
    sections = {}
    current_section = "header"
    sections[current_section] = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line might be a section header
        line_lower = line.lower()
        
        # Look for potential section headers
        is_header = False
        
        # Check for common section names
        for section in RESUME_SECTIONS:
            if section in line_lower and len(line) < 50:  # Headers are usually short
                current_section = section
                if current_section not in sections:
                    sections[current_section] = []
                is_header = True
                break
                
        # Check for formatting characteristics of headers
        if not is_header and (line.isupper() or line.endswith(':')) and len(line) < 50:
            potential_header = line.rstrip(':').lower()
            current_section = potential_header
            if current_section not in sections:
                sections[current_section] = []
            is_header = True
        
        if not is_header:
            sections[current_section].append(line)
    
    return sections

def generate_markdown(sections: Dict[str, List[str]], name: str = "Unknown") -> str:
    """
    Generate markdown format from identified sections.
    
    Args:
        sections: Dictionary with section names as keys and content lines as values
        name: Name of the candidate (if identified)
        
    Returns:
        Markdown formatted text
    """
    markdown = []
    
    # Extract name from header section if present
    if "header" in sections and sections["header"]:
        for line in sections["header"][:3]:  # Check first few lines for a name
            if len(line.split()) <= 5 and not any(char in line for char in "/@:,"):
                name = line
                break
    
    # Add title
    markdown.append(f"# {name}\n")
    
    # Add personal info from header
    if "header" in sections:
        markdown.append("## Contact Information\n")
        for line in sections["header"]:
            if '@' in line or any(word in line.lower() for word in ["phone", "tel", "email"]):
                markdown.append(f"* {line}")
        markdown.append("\n")
    
    # Process each section
    for section_name, content in sections.items():
        if section_name == "header" or not content:
            continue
            
        # Format section name for markdown
        section_title = section_name.title().replace('_', ' ')
        markdown.append(f"## {section_title}\n")
        
        # Format content with bullets
        for line in content:
            line = line.strip()
            if not line:
                continue
                
            # Check if line seems like a bullet point already
            if line.startswith(('-', '*', '•', '○', '►', '■')):
                markdown.append(f"{line}")
            else:
                markdown.append(f"* {line}")
        
        markdown.append("\n")
    
    return "\n".join(markdown)

def process_pdf(pdf_path: str, output_folder: str) -> Tuple[str, bool]:
    """
    Process a single PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        output_folder: Folder to save the extracted text
        
    Returns:
        Tuple of (file_name, success_status)
    """
    try:
        file_name = os.path.basename(pdf_path)
        file_base = os.path.splitext(file_name)[0]
        output_path = os.path.join(output_folder, f"{file_base}.md")
        
        logger.info(f"Processing: {file_name}")
        
        # Extract text using OCR
        extracted_text = extract_text_from_pdf(pdf_path)
        
        if extracted_text.startswith("ERROR:"):
            logger.error(f"OCR failed for {file_name}: {extracted_text}")
            return file_name, False
        
        # Identify sections
        sections = identify_sections(extracted_text)
        
        # Generate markdown
        markdown_text = generate_markdown(sections, name=file_base)
        
        # Save to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
            
        # Also save raw text for backup/comparison
        raw_output_path = os.path.join(output_folder, f"{file_base}_raw.txt")
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        logger.info(f"Successfully processed: {file_name}")
        return file_name, True
    
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return os.path.basename(pdf_path), False

def main():
    """Main function to process PDFs."""
    parser = argparse.ArgumentParser(description='Extract text from PDF resumes using OCR.')
    parser.add_argument('--input', '-i', required=True, help='Input folder containing PDF resumes')
    parser.add_argument('--output', '-o', required=True, help='Output folder for extracted text')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of worker processes')
    parser.add_argument('--dpi', '-d', type=int, default=400, help='DPI for image conversion')
    
    args = parser.parse_args()
    
    input_folder = args.input
    output_folder = args.output
    workers = args.workers
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all PDF files
    pdf_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) 
                if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        logger.error(f"No PDF files found in {input_folder}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process files in parallel
    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_pdf, pdf_file, output_folder): pdf_file for pdf_file in pdf_files}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing PDFs"):
            file_name, success = future.result()
            results.append((file_name, success))
    
    # Report results
    successful = sum(1 for _, success in results if success)
    logger.info(f"Processing complete. {successful}/{len(pdf_files)} files successfully processed.")
    
    # List failed files
    failed = [(name, ) for name, success in results if not success]
    if failed:
        logger.warning("The following files failed to process:")
        for name in failed:
            logger.warning(f"- {name}")

if __name__ == "__main__":
    main()