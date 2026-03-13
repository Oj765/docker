import logging

logger = logging.getLogger(__name__)


async def check_image_provenance(image_url: str) -> dict:
    """Placeholder for reverse image search / image provenance checking.

    In a production build this would call a service like TinEye, Google
    Reverse Image Search, or Sightengine to determine whether an image
    has been manipulated or originates from a known satirical/stock source.

    For the hackathon demo we return a neutral result so the pipeline
    does not crash when media_urls are present.
    """
    logger.info("Image provenance check requested for: %s (returning neutral result)", image_url)
    return {
        "url": image_url,
        "manipulation_score": 0.0,
        "known_source": None,
        "note": "Image provenance checking is not yet implemented.",
    }
