"""
Speech-to-text.

Two backends, chosen automatically:
  1. Groq hosted Whisper  -> used only if GROQ_API_KEY is set in .env
  2. SpeechRecognition's free Google Web Speech API -> used otherwise

Both need a working microphone. Neither stores audio permanently.
"""
import io
import logging
import wave

import speech_recognition as sr

import config

logger = logging.getLogger("voice_agent.stt")

_recognizer = sr.Recognizer()
_microphone = sr.Microphone()

# Calibrate once for ambient noise so short commands aren't cut off.
with _microphone as _source:
    _recognizer.adjust_for_ambient_noise(_source, duration=1)


def _record_audio() -> sr.AudioData:
    with _microphone as source:
        logger.info("Listening (%ss)...", config.LISTEN_DURATION_SECONDS)
        audio = _recognizer.listen(
            source,
            timeout=config.LISTEN_DURATION_SECONDS,
            phrase_time_limit=config.LISTEN_DURATION_SECONDS,
        )
    return audio


def _transcribe_with_groq(audio: sr.AudioData) -> str:
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)

    wav_bytes = audio.get_wav_data()
    buf = io.BytesIO(wav_bytes)
    buf.name = "command.wav"  # Groq's client reads the filename from this attribute

    kwargs = {"file": buf, "model": config.GROQ_STT_MODEL}
    if config.AGENT_LANGUAGE_HINT:
        kwargs["language"] = config.AGENT_LANGUAGE_HINT

    result = client.audio.transcriptions.create(**kwargs)
    return (result.text or "").strip()


def _transcribe_with_free_fallback(audio: sr.AudioData) -> str:
    try:
        # language=None lets Google auto-detect; works reasonably for Hinglish.
        kwargs = {}
        if config.AGENT_LANGUAGE_HINT:
            kwargs["language"] = config.AGENT_LANGUAGE_HINT
        return _recognizer.recognize_google(audio, **kwargs).strip()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        logger.error("Free STT backend unreachable: %s", exc)
        return ""


def listen_and_transcribe() -> str:
    """
    Blocks until it has recorded one utterance, returns the transcribed text
    (empty string if nothing understood). Never raises on recognition failure —
    callers should treat "" as "didn't catch that".
    """
    try:
        audio = _record_audio()
    except sr.WaitTimeoutError:
        return ""

    backend = config.stt_backend()
    try:
        if backend == "groq":
            text = _transcribe_with_groq(audio)
        else:
            text = _transcribe_with_free_fallback(audio)
    except Exception as exc:  # noqa: BLE001 - we must never crash the voice loop
        logger.error("STT backend '%s' failed: %s", backend, exc)
        return ""

    logger.info("Heard: %s", text)
    return text
