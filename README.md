# PDF Data Processing Automation

This script converts PDF files to structured CSV data. It extracts name, code, role, and value information from PDF documents, and can calculate percentages and distribute amounts based on contribution.

## Features

- Convert PDF files to cleaned text format
- Extract structured data from text files in 3-line blocks
- Calculate percentages based on contribution to total value
- Distribute amounts proportionally based on percentages
- Properly format numbers in Brazilian format (comma as decimal separator, dot as thousands separator)
- Suppress unnecessary PDF processing warnings

## Requirements

- Python 3.6+
- pdfplumber

## Usage

### Basic Usage

```bash
python main.py path/to/your/file.pdf
```

### Advanced Options

```bash
python main.py path/to/your/file.pdf --csv-output custom_output.csv --print
```

### Full Command Reference

```bash
python main.py <pdf_path> [options]
```

Options:
- `--txt-output`, `-t`: Custom output path for the text file
- `--csv-output`, `-c`: Custom output path for the CSV file
- `--print`, `-p`: Print extracted data to console
- `--no-clean`: Skip text cleaning (keep headers and other unwanted text)
- `--amount`, `-a`: Total amount to distribute based on percentages (e.g., "9902,53")

### Example with Distribution Amount

```bash
python main.py rel-2.pdf --csv-output custom_output.csv --amount "9902,53"
```

This will process the PDF, extract data, calculate each person's percentage contribution, and distribute the specified amount proportionally.

Then run the script:

```bash
# Process a single PDF file
python pdf_to_csv_extractor.py path/to/your/file.pdf

# Process a single PDF file with custom output path
python pdf_to_csv_extractor.py path/to/your/file.pdf --output custom_output.csv

# Process all PDF files in a directory
python pdf_to_csv_extractor.py path/to/directory/with/pdfs/

# Specify a different proportional total (default is 16700)
python pdf_to_csv_extractor.py path/to/your/file.pdf --proportional-total 10000

# Run with debug information
python pdf_to_csv_extractor.py path/to/your/file.pdf --debug
```

## Output Format

The script generates both CSV and Excel files with the following columns:

- name: The person's name
- code: The numeric code associated with the person
- role: The person's role or position
- value: The numeric value (with comma as decimal separator)
- percent: The percentage this value represents of the total value
- proportional: The proportional value calculated based on the percentage and the specified proportional total

## Example

For a PDF containing a line like:
```
Abadia Pereira da Silva    101559    Tecnico de enfermagem    0001 - COOPERADOS    89,16
```

The CSV output would be:
```
name,code,role,value
Abadia Pereira da Silva,101559,Tecnico de enfermagem,89,16
```
