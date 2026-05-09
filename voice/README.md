# Voice Layer

This directory is the canonical home for wake-word detection, speech-to-text, and text-to-speech integration.

## Current Implementation

The current runtime ships concrete voice execution and discovery surfaces:

- `src/mordecai/voice.py`
- `GET /api/voice/engines`
- `GET /api/voice/catalog`
- `POST /api/voice/synthesize`
- `POST /api/voice/transcribe`
- `prompts/system_prompt.txt`

Today this means:

- Piper-backed local TTS remains the explicit baseline runtime.
- Whisper CLI remains the explicit baseline ASR runtime.
- whisper.cpp is now an additional explicit ASR runtime path when its binary and managed model bundle are installed.
- sherpa-onnx is now an additional explicit ASR runtime path when its offline binary is installed and the managed archive bundle has been extracted.
- The dashboard now exposes a structured ecosystem catalog of open-source voice repositories for operator-visible evaluation.
- The dashboard catalog supports filtering by query, category, runtime fit, and runtime-supported status.
- Cloning-capable repositories are cataloged, but they are not implicitly safe or auto-enabled.

## Intended Expansion

- Wake-word routing for `Mordecai`
- Additional explicit ASR backends beyond Whisper
- Additional explicit TTS backends beyond Piper
- Explicit routing between voice input, runtime policy, and spoken output

Voice features must remain subordinate to the same safety and policy constraints as text interactions.

## Open-Source Voice Model Index

This is a curated, high-signal list of open-source projects for TTS, voice cloning, speech synthesis, and audio-generation exploration in Mordecai.

The runtime catalog now groups repositories into these categories:

- Text-to-Speech
- Voice Cloning
- Speech Recognition
- Audio / Voice Pipelines
- Training Frameworks
- Audio Enhancement / Restoration
- Multimodal / Experimental Audio
- Curated Master Lists

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
- Treat the catalog as a decision surface, not as permission to silently install or execute upstream model stacks.
- Use explicit install manifests for promoted phone-safe integrations like `whisper.cpp` and `sherpa-onnx`; some bundles require an acknowledgement gate before download.
- Archive-backed bundles now extract into managed setup directories, emit a sherpa manifest, and include helper notes so they can be wired into live runtimes without manual archive inspection.