#!/usr/bin/env python3
"""
Usage:
    python simple_jd_extractor.py --input /path/to/pdf/folder --output /path/to/output/folder
"""
import sys
import os
import re
import argparse
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jd_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import PyPDF2
    import pytesseract
    import pdf2image
    from PIL import Image
    from tqdm import tqdm
except ImportError:
    import subprocess
    packages = ["pypdf2", "pytesseract", "pdf2image", "pillow", "tqdm"]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
    import PyPDF2
    import pytesseract
    import pdf2image
    from PIL import Image
    from tqdm import tqdm

# Set tesseract path - REPLACE WITH YOUR ACTUAL PATH
pytesseract.pytesseract.tesseract_cmd = '/raid/biplab/souravr/miniconda3/envs/TIHRESUME/bin/tesseract'

# Simple list of JD section headers (no categorization, just direct matching)
JD_SECTIONS = [
    "position details", "job title", "job function", "designation", "role",
    "profile summary", "job purpose", "job summary", "overview", "about the role", "summary",
    "responsibilities", "principal accountabilities", "key responsibilities", "duties", "job description",
    "qualifications", "requirements", "skills", "desired profile", "experience",
    "education", "educational requirements", "academic qualifications",
    "company", "about us", "organization", 
    "department", "team", "unit", "division",
    "salary", "compensation", "benefits", "perks",
    "location", "work location", "reporting", "reporting to"
]

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using the best available method."""
    logger.info(f"Extracting text from PDF: {pdf_path}")
    
    try:
        # First try PyPDF2 for digital PDFs
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        
        # If we got meaningful text, return it
        if len(text.strip()) > 100:  # Arbitrary threshold to determine if text was successfully extracted
            return text
        
        # If PyPDF2 didn't get good text, try OCR
        logger.info(f"Using OCR for better text extraction: {pdf_path}")
        images = pdf2image.convert_from_path(pdf_path, dpi=300)
        
        text = ""
        for i, img in enumerate(images):
            # Convert to grayscale for better OCR
            img = img.convert('L')
            
            # Perform OCR
            page_text = pytesseract.image_to_string(img)
            text += page_text + "\n\n"
        
        return text
    
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
        return f"ERROR: Could not extract text: {str(e)}"

def clean_text(text: str) -> str:
    """Basic text cleaning without fancy replacements."""
    # Remove page breaks and similar markers
    text = re.sub(r'-+\s*Page\s+Break\s*-+', '\n\n', text)
    
    # Remove classification markers
    text = re.sub(r'Classification\s*\|\s*INTERNAL', '', text, flags=re.IGNORECASE)
    
    # Fix line breaks (convert multiple blank lines to two line breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def identify_sections(text: str) -> Dict[str, List[str]]:
    """Identify JD sections using simple pattern matching."""
    # Clean and split the text
    clean_txt = clean_text(text)
    lines = clean_txt.split('\n')
    
    # Initialize with header section
    sections = {"header": []}
    current_section = "header"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a section header
        is_header = False
        line_lower = line.lower()
        
        # Simple section header detection
        if any(section in line_lower for section in JD_SECTIONS) and len(line) < 50:
            # Find which section it is
            for section in JD_SECTIONS:
                if section in line_lower:
                    current_section = section
                    if current_section not in sections:
                        sections[current_section] = []
                    is_header = True
                    break
        
        # Additional section header detection for numbered/formatted headers
        if not is_header and (line.isupper() or line.endswith(':')) and len(line) < 50:
            # Looks like a header
            current_section = line.rstrip(':').lower()
            if current_section not in sections:
                sections[current_section] = []
            is_header = True
            
        # Add line to current section if not a header
        if not is_header:
            sections[current_section].append(line)
    
    return sections

def generate_markdown(sections: Dict[str, List[str]], title: str = "Job Description") -> str:
    """Generate markdown format from identified sections - simple and reliable."""
    markdown = []
    
    # Try to extract title from header
    if "job title" in sections:
        title = " ".join(sections["job title"][:1])
    elif "position" in sections:
        title = " ".join(sections["position"][:1])
    elif "designation" in sections:
        title = " ".join(sections["designation"][:1])
    
    # Add title
    markdown.append(f"# {title}\n")
    
    # Add all sections
    for section_name, content in sections.items():
        if section_name == "header" or not content:
            continue
        
        # Format section name
        section_title = section_name.title().replace('_', ' ')
        markdown.append(f"## {section_title}\n")
        
        # Format content with bullets, including existing bullet markers
        for line in content:
            line = line.strip()
            if not line:
                continue
            
            # Keep existing bullet points
            if line.startswith(('-', '*', '•', '○', '►', '■')):
                markdown.append(f"{line}")
            else:
                markdown.append(f"* {line}")
        
        markdown.append("")
    
    return "\n".join(markdown)

def process_jd(jd_path: str, output_folder: str) -> Tuple[str, bool]:
    """Process a single JD file - simple and effective."""
    try:
        file_name = os.path.basename(jd_path)
        file_base = os.path.splitext(file_name)[0]
        output_path = os.path.join(output_folder, f"{file_base}.md")
        
        logger.info(f"Processing JD: {file_name}")
        
        # Extract text based on file type
        if jd_path.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(jd_path)
        else:
            # For text files
            with open(jd_path, 'r', encoding='utf-8', errors='replace') as f:
                extracted_text = f.read()
        
        if extracted_text.startswith("ERROR:"):
            logger.error(f"Text extraction failed for {file_name}: {extracted_text}")
            return file_name, False
        
        # Save raw text
        raw_output_path = os.path.join(output_folder, f"{file_base}_raw.txt")
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        # Identify sections (simple approach)
        sections = identify_sections(extracted_text)
        
        # Generate markdown (simple approach)
        markdown_text = generate_markdown(sections, title=file_base)
        
        # Save markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        logger.info(f"Successfully processed JD: {file_name}")
        return file_name, True
    
    except Exception as e:
        logger.error(f"Error processing {jd_path}: {str(e)}")
        return os.path.basename(jd_path), False

def main():
    """Main function to process JDs."""
    parser = argparse.ArgumentParser(description='Extract and structure JDs from PDFs and text files.')
    parser.add_argument('--input', '-i', required=True, help='Input folder containing JD files')
    parser.add_argument('--output', '-o', required=True, help='Output folder for extracted text')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of worker processes')
    
    args = parser.parse_args()
    
    input_folder = args.input
    output_folder = args.output
    workers = args.workers
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all PDF and text files
    jd_files = [
        os.path.join(input_folder, f) for f in os.listdir(input_folder) 
        if f.lower().endswith(('.pdf', '.txt'))
    ]
    
    if not jd_files:
        logger.error(f"No JD files (PDF, TXT) found in {input_folder}")
        return
    
    logger.info(f"Found {len(jd_files)} JD files to process")
    
    # Process files in parallel
    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_jd, jd_file, output_folder): jd_file for jd_file in jd_files}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing JDs"):
            file_name, success = future.result()
            results.append((file_name, success))
    
    # Report results
    successful = sum(1 for _, success in results if success)
    logger.info(f"Processing complete. {successful}/{len(jd_files)} files successfully processed.")
    
    # List failed files
    failed = [name for name, success in results if not success]
    if failed:
        logger.warning("The following files failed to process:")
        for name in failed:
            logger.warning(f"- {name}")

if __name__ == "__main__":
    main()