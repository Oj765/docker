import os
import logging

logger = logging.getLogger(__name__)

# ---- Groq (preferred) ----
groq_client = None
if os.getenv("GROQ_API_KEY"):
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    except ImportError:
        pass

# ---- Gemini (fallback) ----
gemini_client = None
if not groq_client and os.getenv("GEMINI_API_KEY"):
    try:
        from google import genai
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except ImportError:
        pass

try:
    with open(os.path.join(os.path.dirname(__file__), "..", "prompts", "red_team_system.txt"), "r", encoding="utf-8") as f:
        RED_TEAM_PROMPT = f.read()
except FileNotFoundError:
    RED_TEAM_PROMPT = (
        "You are an adversarial red team agent. Your goal is to rephrase "
        "the given factually incorrect claim to bypass detection. Use "
        "euphemisms, loaded language, and slight factual mutations."
    )


def generate_adversarial_variants(original_claim: str, num_variants: int = 3) -> list:
    """Generate subtle variations of a claim using Groq or Gemini."""

    user_prompt = (
        f"Original Claim: {original_claim}\n\n"
        f"Generate {num_variants} subtle adversarial variations separated by |||."
    )

    # Groq path
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": RED_TEAM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
            )
            variants = [v.strip() for v in response.choices[0].message.content.split("|||") if v.strip()]
            return variants
        except Exception as e:
            logger.error("Groq red team generation failed: %s", e)

    # Gemini fallback
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=RED_TEAM_PROMPT,
                    temperature=0.8,
                ),
            )
            variants = [v.strip() for v in response.text.split("|||") if v.strip()]
            return variants
        except Exception as e:
            logger.error("Gemini red team generation failed: %s", e)

    # No LLM available
    logger.warning("No LLM API key found. Returning mock variants.")
    return [f"Variant {i} of: {original_claim}" for i in range(num_variants)]
