"""PDF text extraction utilities."""

import os
from typing import Optional

import PyPDF2
from tqdm import tqdm


def validate_pdf(file_path: str) -> bool:
    """Validate that the file exists and is a PDF."""
    if not os.path.exists(file_path):
        print(f"Error: File not found at path: {file_path}")
        return False
    if not file_path.lower().endswith(".pdf"):
        print("Error: File is not a PDF")
        return False
    return True


def extract_text_from_pdf(file_path: str, max_chars: int = -1) -> Optional[str]:
    """
    Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file
        max_chars: Maximum characters to extract (-1 for no limit)

    Returns:
        Extracted text or None if extraction fails
    """
    if not validate_pdf(file_path):
        return None

    try:
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            print(f"Processing PDF with {num_pages} pages...")

            extracted_text = []
            total_chars = 0

            for page_num in tqdm(range(num_pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                if max_chars != -1 and total_chars + len(text) > max_chars:
                    remaining_chars = max_chars - total_chars
                    extracted_text.append(text[:remaining_chars])
                    print(f"Reached {max_chars} character limit at page {page_num + 1}")
                    break

                extracted_text.append(text)
                total_chars += len(text)

            final_text = "\n".join(extracted_text)
            print(f"\nExtraction complete! Total characters: {len(final_text)}")
            return final_text

    except PyPDF2.errors.PdfReadError:
        print("Error: Invalid or corrupted PDF file")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None
