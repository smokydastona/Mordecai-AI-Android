# Mordecai Core Models

Model configuration is currently handled by:

- `src/mordecai/config.py` for provider settings and defaults
- `src/mordecai/providers.py` for provider routing
- `src/mordecai/models.py` for runtime request and response schemas

This directory is reserved for future local-model manifests, quantization profiles, and provider-specific configuration bundles.

The current runtime registry seeds a small set of default local model profiles for:

- cloud chat through an OpenAI-compatible provider
- Ollama-managed local chat
- `llama.cpp` GGUF chat models
- `llamafile` single-file local chat models
- Whisper-class speech-to-text
- Piper-class text-to-speech

These profiles describe expected commands and model file locations, but Mordecai does not download the corresponding weights automatically.