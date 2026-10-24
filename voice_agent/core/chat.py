"""
General conversation fallback: when nothing matches a specific command
(UNKNOWN intent), send the text to Groq's free LLM instead of just saying
"samajh nahi aaya" — so casual talk ("hello", "kaise ho") gets a real reply.
"""
import logging

import config

logger = logging.getLogger("voice_agent.chat")


def get_reply(text: str) -> str:
    if not config.GROQ_API_KEY:
        return "Maaf kijiye, main samjha nahi. (Normal baat-cheet ke liye Groq key chahiye)"

    try:
        from groq import Groq

        client = Groq(api_key=config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=config.GROQ_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tum ek friendly voice assistant ho. Hindi/Hinglish/English mix me "
                        "chhote, natural jawab do — 1-2 sentence, bilkul casual conversation jaisa."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=150,
        )
        reply = response.choices[0].message.content.strip()
        logger.info("Chat fallback reply: %s", reply[:80])
        return reply
    except Exception as exc:  # noqa: BLE001
        logger.error("chat fallback failed: %s", exc)
        return "Maaf kijiye, abhi reply nahi de paa raha."