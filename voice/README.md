# Voice Layer

This directory is the canonical home for wake-word detection, speech-to-text, and text-to-speech integration.

## Current Implementation

The current runtime only ships voice identity metadata:

- `src/mordecai/voice.py`
- `prompts/system_prompt.txt`

## Intended Expansion

- Wake-word detection for `Mordecai`
- STT integration, likely Whisper-class tooling
- TTS integration, likely Piper-class tooling
- Explicit routing between voice input, runtime policy, and spoken output

Voice features must remain subordinate to the same safety and policy constraints as text interactions.

## Open-Source Voice Model Index

This is a curated, high-signal list of open-source projects for TTS, voice cloning, speech synthesis, and audio-generation exploration in Mordecai.

### Curated Index

1. Awesome AI Voice (curated index)
	- https://github.com/wildminder/awesome-ai-voice
2. WhisperSpeech (Whisper-inverted TTS and cloning)
	- https://github.com/collabora/WhisperSpeech
3. AI Video Dubbing Pipeline (transcribe/translate/TTS/alignment)
	- https://github.com/vidailab/ai-video-dubbing-pipeline
4. Kokoro TTS
	- https://github.com/hexgrad/Kokoro-TTS
5. XTTS v2
	- https://github.com/coqui-ai/xtts-v2
6. Bark
	- https://github.com/suno-ai/bark
7. Piper
	- https://github.com/rhasspy/piper
8. Fish Speech
	- https://github.com/fishaudio/fish-speech
9. Dia
	- https://github.com/narilabs/dia
10. F5-TTS
	- https://github.com/SWivid/F5-TTS
11. Parler-TTS
	- https://github.com/huggingface/parler-tts
12. OmniVoice
	- https://github.com/XiaomiAI/OmniVoice

## Practical Guidance For Mordecai

- Recommended default TTS baseline: Piper (CPU-friendly, practical for phone-first setups).
- Recommended expansion path for naturalness and cloning: XTTS v2, F5-TTS, WhisperSpeech.
- Experimental generative audio track: Bark.
- Use model allowlisting and explicit operator opt-in before enabling any cloud or auto-download behavior.

## Integration Notes

- Keep model discovery and install flows explicit and reversible.
- Route all downloads through the existing outbound allowlist and proxy controls.
- Keep voice runtime selection visible in API/dashboard capability surfaces.
- Do not treat cloning-capable models as implicitly safe; require explicit operator approval.