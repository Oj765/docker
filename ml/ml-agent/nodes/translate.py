import asyncio
import logging
from typing import Dict, Any
from langdetect import detect, DetectorFactory

from agent.state import AgentState

DetectorFactory.seed = 42
logger = logging.getLogger(__name__)

_tokenizer = None
_model = None


def _get_translator():
    global _tokenizer, _model
    if _model is None:
        logger.info("Lazy-loading NLLB-200 model into memory...")
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            model_name = "facebook/nllb-200-distilled-600M"
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            import torch
            if torch.cuda.is_available():
                _model = _model.to("cuda")
                logger.info("NLLB-200 loaded on CUDA.")
        except Exception as e:
            logger.warning(f"Failed to load NLLB-200 translation model: {e}. Translation will be skipped.")
            return None, None
    return _tokenizer, _model


async def translate_node(state: AgentState) -> Dict[str, Any]:
    text = state.get("original_text", "")
    if not text.strip():
        return {"language": "unknown", "translated_text": text}

    try:
        lang = detect(text)
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        lang = "en"

    reasoning = list(state.get("reasoning_chain", []))

    if lang == "en":
        logger.info("Language is English, skipping translation.")
        reasoning.append("Translate: Detected English. No translation needed.")
        return {"language": "en", "translated_text": text, "reasoning_chain": reasoning}

    logger.info(f"Detected non-English language: {lang}. Attempting translation...")

    try:
        tokenizer, model = await asyncio.to_thread(_get_translator)
        if tokenizer is None or model is None:
            reasoning.append(f"Translate: Detected '{lang}' but translation model unavailable. Proceeding with original text.")
            return {"language": lang, "translated_text": text, "reasoning_chain": reasoning}

        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

        inputs = tokenizer(text, return_tensors="pt").to(device)
        translated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.lang_code_to_id["eng_Latn"],
            max_length=512
        )
        translated_text = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]

        logger.info("Translation complete.")
        reasoning.append(f"Translate: Detected '{lang}' and translated to English via NLLB-200.")

        return {
            "language": lang,
            "translated_text": translated_text,
            "reasoning_chain": reasoning,
        }
    except Exception as e:
        logger.error(f"Translation failed: {e}. Using original text.")
        reasoning.append(f"Translate: Translation failed ({e}). Proceeding with original text.")
        return {"language": lang, "translated_text": text, "reasoning_chain": reasoning}
