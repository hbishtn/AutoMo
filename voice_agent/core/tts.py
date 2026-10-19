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
    import concurrent.futures
    import edge_tts
    import playsound

    def _run():
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)

            async def _synthesize():
                communicate = edge_tts.Communicate(text, config.TTS_EDGE_VOICE)
                await communicate.save(path)

            loop.run_until_complete(_synthesize())
            playsound.playsound(path)
        finally:
            loop.close()
            try:
                os.remove(path)
            except OSError:
                pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run).result()


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