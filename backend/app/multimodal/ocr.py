import easyocr
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Initialize reader once at module level — expensive to reload
reader = easyocr.Reader(['en'], gpu=False)

async def extract_text_from_image(image_path: str) -> Optional[str]:
    """
    Run EasyOCR on a local image file.
    Returns extracted text or None if failed.
    """
    try:
        results = reader.readtext(image_path, detail=0, paragraph=True)
        text = " ".join(results).strip()
        logger.info(f"OCR extracted {len(text)} chars from {image_path}")
        return text if text else None
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        return None