import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

class PDFExtractor:
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract raw text from PDF file using PyMuPDF.
        
        Args:
            file_path (str): Path to the PDF file
        
        Returns:
            str: Extracted chapter text
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If PDF is corrupted or empty
        """
        try:
            logger.info("Started Extracting raw chapter text")
            # Check if file exists
            if not file_path:
                raise FileNotFoundError("File path is empty")
            
            # Open PDF
            doc = fitz.open(file_path)
            logger.info(f"Opened PDF: {file_path} with {len(doc)} pages")
            
            # Check if PDF has pages
            if len(doc) == 0:
                raise ValueError("PDF has no pages")
            
            # Extract text from all pages
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
                logger.debug(f"Extracted page {page_num + 1}/{len(doc)}")
            
            # Check if text was extracted
            if not text or not text.strip():
                raise ValueError("PDF contains no extractable text (might be scanned/image-based)")
            
            doc.close()
            
            # Minimal cleaning: remove excessive whitespace
            text = " ".join(text.split())
            
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
        
        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"PDF file not found: {file_path}") from e
        
        except fitz.FileError as e:
            logger.error(f"PDF is corrupted or invalid: {file_path}")
            raise ValueError(f"PDF is corrupted or invalid: {file_path}") from e
        
        except ValueError as e:
            logger.error(f"Extraction error: {str(e)}")
            raise ValueError(f"Text extraction failed: {str(e)}") from e
        
        except Exception as e:
            logger.error(f"Unexpected error during PDF extraction: {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}") from e