#!/usr/bin/env python3
"""
PDF to CSV Converter

This script combines PDF to text conversion and text to CSV extraction in a single workflow.
It first converts a PDF file to a text file, then processes that text file to extract
structured data and save it to a CSV file.
"""

import os
import re
import csv
import sys
import logging
import argparse
from pathlib import Path

# Suppress PDF warnings
logging.basicConfig(level=logging.ERROR)

# Redirect stderr to suppress specific warnings
class StderrFilter:
    def __init__(self):
        self.original_stderr = sys.stderr
        self.filtered_text = "CropBox missing from /Page, defaulting to MediaBox"
    
    def write(self, text):
        if self.filtered_text not in text:
            self.original_stderr.write(text)
    
    def flush(self):
        self.original_stderr.flush()

# Try to import pdfplumber, install if not available
try:
    import pdfplumber
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["pip", "install", "pdfplumber"])
    import pdfplumber

# PDF to Text Conversion Functions
def extract_text_from_pdf(pdf_path):
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    all_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                all_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
    
    return "\n".join(all_text)

def clean_text(text):
    """
    Clean the extracted text by removing headers and unwanted patterns.
    
    Args:
        text (str): Raw text extracted from PDF
        
    Returns:
        str: Cleaned text
    """
    lines = text.split('\n')
    cleaned_lines = []
    skip_until_next_person = False
    
    for line in lines:
        # Skip page markers
        if line.startswith('--- Page'):
            continue
            
        # Skip headers and separators
        if any(header in line for header in ['Relação Anual', 'COOPERATIVA', 'Rubrica', 'TRABALHADOR', 'Página']):
            continue
            
        # Skip separator lines
        if line.startswith('_') or line.strip() == '':
            continue
            
        # Skip month headers (JAN FEV MAR...)
        if 'JAN FEV MAR ABR MAI JUN JUL AGO SET OUT NOV DEZ TOTAL' in line:
            continue
            
        # Skip lines with only dashes
        if line.strip().replace('-', '').strip() == '':
            continue
            
        # Skip totalização and everything after it in a section
        if 'TOTALIZA' in line:
            skip_until_next_person = True
            continue
            
        # Reset skip flag when we find a person (contains 6-digit code)
        if re.search(r'\d{6}', line) and not line.startswith('239'):
            skip_until_next_person = False
            
        # Skip lines until we find the next person
        if skip_until_next_person:
            continue
            
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def save_to_txt(text, output_path):
    """
    Save extracted text to a text file.
    
    Args:
        text (str): Text to save
        output_path (str): Path to save the text file
    """
    with open(output_path, 'w', encoding='utf-8') as txtfile:
        txtfile.write(text)
    
    print(f"Text saved to {output_path}")

def process_pdf(pdf_path, output_path=None, clean=True, no_page_markers=False):
    """
    Process a single PDF file and convert it to text.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_path (str, optional): Path to save the text file
        clean (bool): Whether to clean the text by removing headers
        no_page_markers (bool): Whether to include page markers in the output
    
    Returns:
        str: Path to the saved text file
    """
    if output_path is None:
        # Create output path with same name but .txt extension
        output_path = str(Path(pdf_path).with_suffix('.txt'))
    
    print(f"Processing {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    
    if clean:
        text = clean_text(text)
    elif no_page_markers:
        # Just remove the page markers but keep everything else
        text = '\n'.join([line for line in text.split('\n') if not line.startswith('--- Page')])
    
    save_to_txt(text, output_path)
    
    return output_path

# Text to CSV Conversion Functions
def extract_data_from_txt(txt_path):
    """
    Extract data from the text file in 3-line blocks.
    
    Args:
        txt_path (str): Path to the text file
        
    Returns:
        list: List of dictionaries containing extracted data
    """
    results = []
    
    with open(txt_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Clean up lines - remove empty lines and headers
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines and separator lines
        if not line or line.startswith('_') or line.startswith('-'):
            continue
            
        # Skip header lines
        if any(header in line for header in ['Relação', 'COOPERATIVA', 'Rubrica', 'TRABALHADOR', 'Página']):
            continue
            
        cleaned_lines.append(line)
    
    # Process lines in 3-line blocks
    i = 0
    while i < len(cleaned_lines) - 2:  # Ensure we have at least 3 lines
        # Get the 3 lines for this block
        person_line = cleaned_lines[i]
        produtividade_line = cleaned_lines[i + 1]
        total_line = cleaned_lines[i + 2]
        
        # Extract name, code, and role from the first line
        # Pattern: Name + 6-digit code + role
        person_pattern = r'([A-Za-zÀ-ÖØ-öø-ÿ\s]+?)\s+(\d{6})\s+(.+)$'
        person_match = re.search(person_pattern, person_line)
        
        if person_match:
            name = person_match.group(1).strip()
            code = person_match.group(2).strip()
            role = person_match.group(3).strip()
            
            # Extract the total value from the second line (PRODUTIVIDADE line)
            # Get the last number in the line
            value_pattern = r'.*\s+([\d\.]+,\d+)$'
            value_match = re.search(value_pattern, produtividade_line)
            
            if value_match:
                value = value_match.group(1).strip()
                
                # Create person record
                person = {
                    'name': name,
                    'code': code,
                    'role': role,
                    'value': value
                }
                
                # Add person to results
                results.append(person)
            
            # Move to the next 3-line block
            i += 3
        else:
            # If not a person line, move to the next line
            i += 1
    
    return results

def calculate_total_value(data):
    """
    Calculate the sum of all values in the data.
    
    Args:
        data (list): List of dictionaries containing extracted data
        
    Returns:
        float: Sum of all values
    """
    total = 0.0
    for item in data:
        if item.get('value'):
            # Convert value string to float (replace comma with dot)
            try:
                value_str = item['value'].replace('.', '').replace(',', '.')
                value_float = float(value_str)
                total += value_float
            except (ValueError, TypeError):
                print(f"Warning: Could not convert value '{item.get('value')}' to float for {item.get('name')}")
    
    return total

def format_brazilian_number(number, decimal_places=2):
    """
    Format a number using Brazilian number format (dot as thousands separator, comma as decimal separator).
    
    Args:
        number (float): Number to format
        decimal_places (int): Number of decimal places
        
    Returns:
        str: Formatted number string
    """
    # Format with specified decimal places
    formatted = f"{number:.{decimal_places}f}"
    
    # Split into integer and decimal parts
    parts = formatted.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ''
    
    # Add thousands separators to integer part
    if len(integer_part) > 3:
        # Insert dots for thousands separators
        result = ''
        for i, char in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                result = '.' + result
            result = char + result
        integer_part = result
    
    # Combine with comma as decimal separator
    if decimal_part:
        return f"{integer_part},{decimal_part}"
    return integer_part

def calculate_percentages_and_distribution(data, distribution_amount=None):
    """
    Calculate percentages and distribution amounts for each person.
    
    Args:
        data (list): List of dictionaries containing extracted data
        distribution_amount (float, optional): Total amount to distribute
        
    Returns:
        list: Updated data with percentage and distribution amounts
    """
    if not data:
        return data
    
    # Calculate total value
    total_value = calculate_total_value(data)
    
    # Calculate percentages and distribution amounts
    for item in data:
        if item.get('value'):
            try:
                # Convert value string to float
                value_str = item['value'].replace('.', '').replace(',', '.')
                value_float = float(value_str)
                
                # Calculate percentage
                percentage = (value_float / total_value) * 100
                # Format percentage with 6 decimal places in Brazilian format (without % symbol)
                item['percentage'] = format_brazilian_number(percentage, 6)
                item['percentage_float'] = percentage
                
                # Calculate distribution amount if provided
                if distribution_amount is not None:
                    distribution = (percentage / 100) * distribution_amount
                    # Format total in Brazilian currency format
                    item['total'] = format_brazilian_number(distribution, 2)
                    item['total_float'] = distribution
            except (ValueError, TypeError, ZeroDivisionError):
                item['percentage'] = "0,000000"
                item['percentage_float'] = 0.0
                if distribution_amount is not None:
                    item['total'] = "0,00"
                    item['total_float'] = 0.0
    
    return data

def save_to_csv(data, output_path, distribution_amount=None):
    """
    Save extracted data to CSV file.
    
    Args:
        data (list): List of dictionaries containing extracted data
        output_path (str): Path to save the CSV file
        distribution_amount (float, optional): Total amount to distribute
    """
    if not data:
        print("No data extracted.")
        return
    
    # Calculate percentages and distribution amounts
    data = calculate_percentages_and_distribution(data, distribution_amount)
    
    # Determine fieldnames based on whether distribution_amount was provided
    if distribution_amount is not None:
        fieldnames = ['name', 'code', 'role', 'value', 'percentage', 'total']
    else:
        fieldnames = ['name', 'code', 'role', 'value', 'percentage']
    
    # Create a copy of the data without the internal calculation fields
    csv_data = []
    for item in data:
        csv_item = {}
        for field in fieldnames:
            if field in item:
                csv_item[field] = item[field]
        csv_data.append(csv_item)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"Data saved to {output_path}")
    print(f"Total records: {len(data)}")
    
    # Calculate total value
    total_value = calculate_total_value(data)
    print(f"Sum of all values: {total_value:.2f}")
    
    # Print distribution information if provided
    if distribution_amount is not None:
        print(f"Distribution amount: {distribution_amount:.2f}")

def print_data(data, distribution_amount=None):
    """
    Print extracted data in a readable format.
    
    Args:
        data (list): List of dictionaries containing extracted data
        distribution_amount (float, optional): Total amount to distribute
    """
    if not data:
        print("No data extracted.")
        return
    
    # Calculate percentages and distribution amounts
    data = calculate_percentages_and_distribution(data, distribution_amount)
    
    # Calculate total value
    total_value = calculate_total_value(data)
        
    print(f"Total records: {len(data)}")
    print(f"Sum of all values: {total_value:.2f}")
    if distribution_amount is not None:
        print(f"Distribution amount: {distribution_amount:.2f}")
    
    for item in data:
        print("\n> data")
        print(f"name: {item['name']}")
        print(f"code: {item['code']}")
        print(f"role: {item['role']}")
        print(f"value: {item['value']}")
        print(f"percentage: {item.get('percentage', '0.000000%')}")
        if distribution_amount is not None:
            print(f"total: {item.get('total', '0.00')}")

def process_pdf_to_csv(pdf_path, txt_output=None, csv_output=None, print_data_flag=False, clean_txt=True, distribution_amount=None):
    """
    Process a PDF file to extract data and save to CSV.
    
    Args:
        pdf_path (str): Path to the PDF file
        txt_output (str, optional): Path to save the text file
        csv_output (str, optional): Path to save the CSV file
        print_data_flag (bool): Whether to print the extracted data
        clean_txt (bool): Whether to clean the text by removing headers
        distribution_amount (float, optional): Total amount to distribute based on percentages
        
    Returns:
        tuple: (txt_path, csv_path) - Paths to the generated files
    """
    # Generate default output paths if not provided
    if txt_output is None:
        txt_output = str(Path(pdf_path).with_suffix('.txt'))
    
    if csv_output is None:
        csv_output = str(Path(pdf_path).with_suffix('.csv'))
    
    # Step 1: Convert PDF to text
    print(f"Step 1: Converting PDF to text...")
    
    # Redirect stderr to filter out CropBox warnings
    stderr_filter = StderrFilter()
    original_stderr = sys.stderr
    sys.stderr = stderr_filter
    
    try:
        txt_path = process_pdf(pdf_path, txt_output, clean=clean_txt)
    finally:
        # Restore stderr
        sys.stderr = original_stderr
    
    # Step 2: Extract data from text and save to CSV
    print(f"\nStep 2: Extracting data from text and saving to CSV...")
    data = extract_data_from_txt(txt_path)
    
    # Print data if requested
    if print_data_flag:
        print_data(data)
    
    # Save to CSV with distribution calculations if amount is provided
    save_to_csv(data, csv_output, distribution_amount)
    
    return txt_path, csv_output

def parse_amount(amount_str):
    """
    Parse amount string with comma as decimal separator to float.
    
    Args:
        amount_str (str): Amount string (e.g., "9902,53")
        
    Returns:
        float: Parsed amount
    """
    if amount_str is None:
        return None
        
    try:
        # Replace comma with dot for decimal separator
        amount_str = amount_str.replace('.', '').replace(',', '.')
        return float(amount_str)
    except (ValueError, AttributeError):
        print(f"Warning: Could not parse amount '{amount_str}'. Using None.")
        return None

def main():
    parser = argparse.ArgumentParser(description='Convert PDF files to CSV with structured data extraction.')
    parser.add_argument('pdf_path', help='Path to the PDF file or directory containing PDF files')
    parser.add_argument('--txt-output', '-t', help='Output text file path (default: same name as PDF with .txt extension)')
    parser.add_argument('--csv-output', '-c', help='Output CSV file path (default: same name as PDF with .csv extension)')
    parser.add_argument('--print', '-p', action='store_true', help='Print extracted data')
    parser.add_argument('--no-clean', action='store_true', help='Do not clean the text (keep headers and other unwanted text)')
    parser.add_argument('--amount', '-a', help='Total amount to distribute based on percentages (e.g., "9902,53")')
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    txt_output = args.txt_output
    csv_output = args.csv_output
    print_data_flag = args.print
    clean_txt = not args.no_clean
    distribution_amount = parse_amount(args.amount)
    
    if pdf_path.is_file() and pdf_path.suffix.lower() == '.pdf':
        # Process single PDF file
        process_pdf_to_csv(str(pdf_path), txt_output, csv_output, print_data_flag, clean_txt, distribution_amount)
    elif pdf_path.is_dir():
        # Process all PDF files in directory
        pdf_files = list(pdf_path.glob('*.pdf'))
        
        if not pdf_files:
            print(f"No PDF files found in {pdf_path}")
            return
        
        for pdf_file in pdf_files:
            # For directories, always use default output naming
            process_pdf_to_csv(str(pdf_file), None, None, print_data_flag, clean_txt, distribution_amount)
    else:
        print("Invalid input. Please provide a PDF file or directory containing PDF files.")

if __name__ == "__main__":
    main()
