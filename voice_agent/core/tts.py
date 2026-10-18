"""
Text-to-speech.

Two backends:
  1. "edge" (default) — Microsoft Edge's free online Neural voices. Far more
     natural-sounding than the robotic default Windows voices, and includes
     a proper Hindi voice that handles Hinglish much better. Needs internet.
  2. "pyttsx3" — fully offline, uses Windows' built-in SAPI5 voices.

Automatically falls back to pyttsx3 if edge-tts fails for any reason.
"""
import logging
import os
import tempfile
import threading

import config

logger = logging.getLogger("voice_agent.tts")

_lock = threading.Lock()

import pyttsx3

_pyttsx3_engine = pyttsx3.init()
_pyttsx3_engine.setProperty("rate", config.TTS_RATE)


def _speak_pyttsx3(text):
    _pyttsx3_engine.say(text)
    _pyttsx3_engine.runAndWait()


def _speak_edge(text):
    import asyncio
    import edge_tts
    import playsound

    async def _synthesize(path):
        communicate = edge_tts.Communicate(text, config.TTS_EDGE_VOICE)
        await communicate.save(path)

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(_synthesize(path))
        playsound.playsound(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def speak(text):
    if not text:
        return
    logger.info("Speaking: %s", text)
    with _lock:
        if config.TTS_ENGINE == "edge":
            try:
                _speak_edge(text)
                return
            except Exception as exc:
                logger.error("Edge TTS failed (%s) — falling back to pyttsx3 for this line.", exc)
        _speak_pyttsx3(text)