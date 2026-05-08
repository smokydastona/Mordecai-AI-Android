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