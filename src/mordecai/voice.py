from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import subprocess
from datetime import UTC, datetime
from uuid import uuid4
import re
from typing import Any

from mordecai.config import Settings


@dataclass(frozen=True)
class VoiceProfile:
    wake_words: list[str]
    startup_phrase: str
    nicknames: dict[str, str]


@dataclass(frozen=True)
class VoiceRepo:
    slug: str
    name: str
    repo_url: str
    categories: tuple[str, ...]
    tags: tuple[str, ...]
    runtime_fit: str
    integration_tier: str
    notes: str
    supported_by_runtime: bool = False
    managed_asset_ids: tuple[str, ...] = ()
    requires_operator_approval: bool = False


def _voice_repo(
    slug: str,
    name: str,
    repo_url: str,
    *categories: str,
    tags: tuple[str, ...] = (),
    runtime_fit: str = "research",
    integration_tier: str = "reference",
    notes: str = "",
    supported_by_runtime: bool = False,
    managed_asset_ids: tuple[str, ...] = (),
    requires_operator_approval: bool = False,
) -> VoiceRepo:
    return VoiceRepo(
        slug=slug,
        name=name,
        repo_url=repo_url,
        categories=categories,
        tags=tags,
        runtime_fit=runtime_fit,
        integration_tier=integration_tier,
        notes=notes,
        supported_by_runtime=supported_by_runtime,
        managed_asset_ids=managed_asset_ids,
        requires_operator_approval=requires_operator_approval,
    )


VOICE_REPOS: tuple[VoiceRepo, ...] = (
    _voice_repo(
        "awesome-ai-voice",
        "Awesome AI Voice",
        "https://github.com/wildminder/awesome-ai-voice",
        "master-index",
        tags=("index", "curated", "tts", "asr", "audio"),
        runtime_fit="reference",
        integration_tier="reference",
        notes="Primary curated index for open-source speech and audio repos.",
    ),
    _voice_repo(
        "asr-tts-paper-daily",
        "ASR-TTS-paper-daily",
        "https://github.com/ASR-TTS-paper-daily/ASR-TTS-paper-daily",
        "master-index",
        "speech-recognition",
        tags=("papers", "index", "asr", "tts"),
        runtime_fit="reference",
        integration_tier="reference",
        notes="Paper-linked research index across ASR and TTS projects.",
    ),
    _voice_repo(
        "longcat-audiodit",
        "LongCat-AudioDiT",
        "https://github.com/meituan-longcat/LongCat-AudioDiT",
        "text-to-speech",
        tags=("diffusion", "zero-shot", "zh", "en"),
        runtime_fit="server",
        integration_tier="research",
        notes="Waveform-latent diffusion TTS with strong quality focus.",
    ),
    _voice_repo(
        "longcat-next",
        "LongCat-Next",
        "https://github.com/meituan-longcat/LongCat-Next",
        "text-to-speech",
        "voice-cloning",
        "multimodal-experimental",
        tags=("tts", "asr", "multimodal", "streaming"),
        runtime_fit="server",
        integration_tier="research",
        notes="Unified text, vision, and audio foundation model.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "step-audio",
        "Step-Audio",
        "https://github.com/stepfun-ai/Step-Audio",
        "text-to-speech",
        "voice-cloning",
        "audio-pipeline",
        "multimodal-experimental",
        tags=("tts", "asr", "speech-to-speech", "streaming"),
        runtime_fit="server",
        integration_tier="research",
        notes="Unified speech comprehension and generation stack.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "step-audio-editx",
        "Step-Audio-EditX",
        "https://github.com/stepfun-ai/Step-Audio-EditX",
        "text-to-speech",
        "voice-cloning",
        "audio-pipeline",
        tags=("editing", "expressive", "multilingual"),
        runtime_fit="server",
        integration_tier="research",
        notes="Iterative audio editing model for expressive speech work.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "qwen3-tts",
        "Qwen3-TTS",
        "https://github.com/QwenLM/Qwen3-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("llm-tts", "streaming", "voice-design", "multilingual"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Strong open LLM-TTS option with streaming and voice design.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "glm-tts",
        "GLM-TTS",
        "https://github.com/zai-org/GLM-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("llm-tts", "phoneme-control", "zh", "en"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="LLM-based TTS with reinforcement learning alignment.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "megatts3",
        "MegaTTS3",
        "https://github.com/bytedance/MegaTTS3",
        "text-to-speech",
        "voice-cloning",
        tags=("diffusion", "zero-shot", "zh", "en"),
        runtime_fit="server",
        integration_tier="research",
        notes="Latent diffusion zero-shot speech synthesis.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "spark-tts",
        "Spark-TTS",
        "https://github.com/SparkAudio/Spark-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("llm-tts", "streaming", "zh", "en"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Efficient single-stream speech token TTS.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "neutts",
        "NeuTTS",
        "https://github.com/neuphonic/neutts",
        "text-to-speech",
        "voice-cloning",
        tags=("on-device", "gguf", "instant-cloning"),
        runtime_fit="phone",
        integration_tier="expansion",
        notes="On-device TTS family with quantized deployment story.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "tinytts",
        "TinyTTS",
        "https://github.com/tronghieuit/tiny-tts",
        "text-to-speech",
        tags=("lightweight", "cpu", "onnx"),
        runtime_fit="phone",
        integration_tier="expansion",
        notes="Very small CPU-friendly TTS for edge deployment.",
    ),
    _voice_repo(
        "piper",
        "Piper",
        "https://github.com/rhasspy/piper",
        "text-to-speech",
        tags=("baseline", "cpu", "onnx", "offline"),
        runtime_fit="phone",
        integration_tier="managed",
        notes="Current Mordecai default TTS executor and managed voice asset path.",
        supported_by_runtime=True,
        managed_asset_ids=("piper-en-us-lessac-medium-onnx", "piper-en-us-lessac-medium-config"),
    ),
    _voice_repo(
        "vibevoice",
        "VibeVoice",
        "https://github.com/microsoft/VibeVoice",
        "text-to-speech",
        "voice-cloning",
        "speech-recognition",
        tags=("realtime", "streaming", "asr", "multilingual"),
        runtime_fit="server",
        integration_tier="research",
        notes="Microsoft speech stack spanning low-latency TTS and long-form ASR.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "omnivoice",
        "OmniVoice",
        "https://github.com/XiaomiAI/OmniVoice",
        "text-to-speech",
        "voice-cloning",
        tags=("multilingual", "600-languages", "voice-design"),
        runtime_fit="server",
        integration_tier="research",
        notes="Large multilingual TTS for very broad language coverage.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "fish-speech",
        "Fish Speech",
        "https://github.com/fishaudio/fish-speech",
        "text-to-speech",
        "voice-cloning",
        tags=("expressive", "multilingual", "streaming"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Strong expressive TTS and cloning model family.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "fireredtts2",
        "FireRedTTS2",
        "https://github.com/FireRedTeam/FireRedTTS2",
        "text-to-speech",
        "voice-cloning",
        tags=("dialogue", "multi-speaker", "streaming"),
        runtime_fit="server",
        integration_tier="research",
        notes="Long-form streaming TTS for dialogue generation.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "voxcpm",
        "VoxCPM",
        "https://github.com/OpenBMB/VoxCPM",
        "text-to-speech",
        "voice-cloning",
        tags=("tokenizer-free", "streaming", "zh", "en"),
        runtime_fit="server",
        integration_tier="research",
        notes="Context-aware tokenizer-free TTS and cloning model.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "irodori-tts",
        "Irodori-TTS",
        "https://github.com/Aratako/Irodori-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("japanese", "emoji-style-control"),
        runtime_fit="server",
        integration_tier="research",
        notes="Japanese diffusion TTS with emoji-conditioned style control.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "vieneu-tts",
        "VieNeu-TTS",
        "https://github.com/pnnbao97/VieNeu-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("vietnamese", "on-device"),
        runtime_fit="phone",
        integration_tier="research",
        notes="Vietnamese on-device TTS with short-reference cloning.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "soulx-singer",
        "SoulX-Singer",
        "https://github.com/Soul-AILab/SoulX-Singer",
        "text-to-speech",
        "voice-cloning",
        "multimodal-experimental",
        tags=("singing", "midi", "f0-control"),
        runtime_fit="server",
        integration_tier="research",
        notes="Zero-shot singing synthesis rather than general assistant speech.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "soulx-podcast",
        "SoulX-Podcast",
        "https://github.com/Soul-AILab/SoulX-Podcast",
        "text-to-speech",
        "voice-cloning",
        tags=("podcast", "multi-speaker", "long-form"),
        runtime_fit="server",
        integration_tier="research",
        notes="Long-form multi-speaker dialogue and podcast generation.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "bark",
        "Bark",
        "https://github.com/suno-ai/bark",
        "text-to-speech",
        "multimodal-experimental",
        tags=("generative-audio", "expressive", "classic"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Generative audio model with non-deterministic expressive output.",
    ),
    _voice_repo(
        "kokoro",
        "Kokoro-82M",
        "https://github.com/hexgrad/kokoro",
        "text-to-speech",
        "voice-cloning",
        tags=("lightweight", "streaming", "multilingual"),
        runtime_fit="phone",
        integration_tier="expansion",
        notes="High-value lightweight open TTS option for edge use.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "orpheus-tts",
        "Orpheus-TTS",
        "https://github.com/canopyai/Orpheus-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("llm-tts", "streaming", "multilingual"),
        runtime_fit="server",
        integration_tier="research",
        notes="Llama-backed TTS with strong expressive performance.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "cosyvoice",
        "CosyVoice",
        "https://github.com/FunAudioLLM/CosyVoice",
        "text-to-speech",
        "voice-cloning",
        tags=("multilingual", "dialects", "streaming"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Multilingual and dialect-aware TTS stack.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "whisperspeech",
        "WhisperSpeech",
        "https://github.com/collabora/WhisperSpeech",
        "text-to-speech",
        "voice-cloning",
        tags=("tts", "whisper-derived", "few-shot"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Whisper-inverted TTS and cloning oriented stack.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "kokoclone",
        "KokoClone",
        "https://github.com/Ashish-Patnaik/kokoclone",
        "voice-cloning",
        tags=("kokoro", "realtime", "cpu"),
        runtime_fit="phone",
        integration_tier="experimental",
        notes="Kokoro-based multilingual cloning workflow.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "kimi-audio",
        "Kimi-Audio",
        "https://github.com/MoonshotAI/Kimi-Audio",
        "voice-cloning",
        "multimodal-experimental",
        tags=("audio-llm", "tts", "asr", "conversation"),
        runtime_fit="server",
        integration_tier="research",
        notes="Audio foundation model for conversation and generation.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "parler-tts",
        "Parler-TTS",
        "https://github.com/huggingface/parler-tts",
        "text-to-speech",
        "voice-cloning",
        tags=("voice-design", "prompt-conditioned"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Prompt-based voice design and controllable speech synthesis.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "lfm2-audio",
        "LFM2-Audio-1.5B",
        "https://github.com/LiquidAI/LFM2-Audio-1.5B",
        "voice-cloning",
        "multimodal-experimental",
        tags=("audio-foundation", "asr", "low-latency"),
        runtime_fit="server",
        integration_tier="research",
        notes="Low-latency audio foundation model with integrated ASR.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "mimo-audio",
        "MiMo-Audio",
        "https://github.com/XiaomiMiMo/MiMo-Audio",
        "voice-cloning",
        "multimodal-experimental",
        tags=("audio-language-model", "tts", "asr"),
        runtime_fit="server",
        integration_tier="research",
        notes="Few-shot audio language model spanning synthesis and understanding.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "xtts",
        "XTTS-v2",
        "https://github.com/coqui-ai/TTS",
        "voice-cloning",
        "training-framework",
        tags=("coqui", "few-shot", "multilingual"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Coqui TTS framework includes XTTS-style multilingual cloning flows.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "f5-tts",
        "F5-TTS",
        "https://github.com/SWivid/F5-TTS",
        "voice-cloning",
        "text-to-speech",
        tags=("few-shot", "flow-matching"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Modern few-shot cloning-capable TTS model.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "whisper",
        "Whisper",
        "https://github.com/openai/whisper",
        "speech-recognition",
        tags=("baseline", "offline", "transcription"),
        runtime_fit="phone",
        integration_tier="managed",
        notes="Current Mordecai ASR executor via CLI integration.",
        supported_by_runtime=True,
    ),
    _voice_repo(
        "whisper-cpp",
        "whisper.cpp",
        "https://github.com/ggml-org/whisper.cpp",
        "speech-recognition",
        "audio-pipeline",
        tags=("edge", "cpp", "offline", "vad"),
        runtime_fit="phone",
        integration_tier="managed",
        notes="Explicit phone-safe ASR expansion path with ggml models and optional Silero VAD.",
    ),
    _voice_repo(
        "faster-whisper",
        "faster-whisper",
        "https://github.com/SYSTRAN/faster-whisper",
        "speech-recognition",
        tags=("whisper", "optimized", "ctranslate2"),
        runtime_fit="phone",
        integration_tier="expansion",
        notes="More efficient Whisper inference path worth future runtime support.",
    ),
    _voice_repo(
        "fairseq-wav2vec",
        "fairseq wav2vec",
        "https://github.com/facebookresearch/fairseq",
        "speech-recognition",
        "training-framework",
        tags=("wav2vec", "research", "ssl"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Research foundation for wav2vec 2.0 and speech tasks.",
    ),
    _voice_repo(
        "nemo",
        "NVIDIA NeMo",
        "https://github.com/NVIDIA/NeMo",
        "speech-recognition",
        "training-framework",
        tags=("asr", "tts", "speaker", "toolkit"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Full speech toolkit spanning ASR, TTS, diarization, and training.",
    ),
    _voice_repo(
        "lrs-voxmm",
        "LRS-VoxMM",
        "https://github.com/doyeopkwak/LRS-VoxMM",
        "speech-recognition",
        tags=("avsr", "multimodal", "research"),
        runtime_fit="research",
        integration_tier="reference",
        notes="Audio-visual speech recognition research repo.",
    ),
    _voice_repo(
        "apptek-asr",
        "AppTek-ASR",
        "https://github.com/apptek/AppTek-ASR",
        "speech-recognition",
        tags=("call-center", "asr"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Specialized ASR reference implementation.",
    ),
    _voice_repo(
        "funasr",
        "FunASR",
        "https://github.com/modelscope/FunASR",
        "speech-recognition",
        "audio-pipeline",
        tags=("vad", "diarization", "punctuation"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Broad speech recognition toolkit with production features.",
    ),
    _voice_repo(
        "seamless-communication",
        "Seamless Communication",
        "https://github.com/facebookresearch/seamless_communication",
        "audio-pipeline",
        "speech-recognition",
        "multimodal-experimental",
        tags=("speech-to-speech", "translation", "speech-text-speech"),
        runtime_fit="server",
        integration_tier="research",
        notes="End-to-end speech translation and speech-to-speech pipeline.",
    ),
    _voice_repo(
        "voicecraft",
        "VoiceCraft",
        "https://github.com/jasonppy/VoiceCraft",
        "audio-pipeline",
        "voice-cloning",
        tags=("speech-editing", "speech-to-speech"),
        runtime_fit="server",
        integration_tier="research",
        notes="Speech editing and continuation rather than pure assistant TTS.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "naturalspeech3",
        "NaturalSpeech3",
        "https://github.com/ictnlp/NaturalSpeech3",
        "audio-pipeline",
        "text-to-speech",
        tags=("speech-to-speech", "zero-shot"),
        runtime_fit="server",
        integration_tier="research",
        notes="Speech-to-speech and zero-shot synthesis reference repo.",
    ),
    _voice_repo(
        "ai-video-dubbing-pipeline",
        "AI Video Dubbing Pipeline",
        "https://github.com/vidailab/ai-video-dubbing-pipeline",
        "audio-pipeline",
        tags=("dubbing", "translation", "alignment"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Full dubbing pipeline with alignment and TTS components.",
    ),
    _voice_repo(
        "montreal-forced-aligner",
        "Montreal Forced Aligner",
        "https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner",
        "audio-pipeline",
        tags=("alignment", "phonemes", "corpus"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Alignment tool for phoneme and word timing.",
    ),
    _voice_repo(
        "prosodylab-aligner",
        "Prosodylab-Aligner",
        "https://github.com/prosodylab/Prosodylab-Aligner",
        "audio-pipeline",
        tags=("alignment", "prosody"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Prosody and corpus alignment toolchain.",
    ),
    _voice_repo(
        "espnet",
        "ESPnet",
        "https://github.com/espnet/espnet",
        "training-framework",
        "speech-recognition",
        "text-to-speech",
        tags=("toolkit", "asr", "tts", "training"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Major speech toolkit for research and training.",
    ),
    _voice_repo(
        "speechbrain",
        "SpeechBrain",
        "https://github.com/speechbrain/speechbrain",
        "training-framework",
        "speech-recognition",
        tags=("toolkit", "speech", "training"),
        runtime_fit="server",
        integration_tier="reference",
        notes="General speech research and production toolkit.",
    ),
    _voice_repo(
        "coqui-tts",
        "Coqui TTS",
        "https://github.com/coqui-ai/TTS",
        "training-framework",
        "text-to-speech",
        "voice-cloning",
        tags=("tts", "training", "xtts"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Widely used TTS training and inference framework.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "glow-tts",
        "Glow-TTS",
        "https://github.com/jaywalnut310/glow-tts",
        "training-framework",
        "text-to-speech",
        tags=("flow", "tts", "classic"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Classic flow-based TTS training repo.",
    ),
    _voice_repo(
        "vits",
        "VITS",
        "https://github.com/jaywalnut310/vits",
        "training-framework",
        "text-to-speech",
        tags=("classic", "end-to-end", "tts"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Classic end-to-end TTS baseline.",
    ),
    _voice_repo(
        "fastspeech2",
        "FastSpeech2",
        "https://github.com/ming024/FastSpeech2",
        "training-framework",
        "text-to-speech",
        tags=("fast", "tts", "classic"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Standard FastSpeech2 implementation.",
    ),
    _voice_repo(
        "hifi-gan",
        "HiFi-GAN",
        "https://github.com/jik876/hifi-gan",
        "training-framework",
        tags=("vocoder", "audio", "tts"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Common neural vocoder used across many TTS stacks.",
    ),
    _voice_repo(
        "audioldm",
        "AudioLDM",
        "https://github.com/haoheliu/AudioLDM",
        "training-framework",
        "multimodal-experimental",
        tags=("audio-diffusion", "generation"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Diffusion training and inference for general audio generation.",
    ),
    _voice_repo(
        "diffwave",
        "DiffWave",
        "https://github.com/lmnt-com/diffwave",
        "training-framework",
        tags=("diffusion", "vocoder", "audio"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Diffusion vocoder and waveform generation baseline.",
    ),
    _voice_repo(
        "demucs",
        "Demucs",
        "https://github.com/facebookresearch/demucs",
        "enhancement-restoration",
        tags=("source-separation", "restoration"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Source separation and cleanup tooling for audio assets.",
    ),
    _voice_repo(
        "audiocraft",
        "AudioCraft",
        "https://github.com/facebookresearch/audiocraft",
        "enhancement-restoration",
        "multimodal-experimental",
        tags=("musicgen", "audiogen", "generation"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Meta audio generation stack including MusicGen and AudioGen.",
    ),
    _voice_repo(
        "rnnoise",
        "RNNoise",
        "https://github.com/xiph/rnnoise",
        "enhancement-restoration",
        tags=("noise-suppression", "realtime", "cpu"),
        runtime_fit="phone",
        integration_tier="reference",
        notes="Very practical realtime noise suppression component.",
    ),
    _voice_repo(
        "deepfilternet",
        "DeepFilterNet",
        "https://github.com/Rikorose/DeepFilterNet",
        "enhancement-restoration",
        tags=("noise-suppression", "enhancement"),
        runtime_fit="phone",
        integration_tier="reference",
        notes="Speech enhancement and denoising.",
    ),
    _voice_repo(
        "segan",
        "SEGAN",
        "https://github.com/santi-pdp/segan",
        "enhancement-restoration",
        tags=("speech-enhancement", "gan"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Classic speech enhancement GAN implementation.",
    ),
    _voice_repo(
        "audiosr",
        "AudioSR",
        "https://github.com/Saganaki22/ComfyUI-AudioSR",
        "enhancement-restoration",
        tags=("super-resolution", "upscaling"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Audio super-resolution model packaging.",
    ),
    _voice_repo(
        "novasr",
        "NovaSR",
        "https://github.com/ysharma3501/NovaSR",
        "enhancement-restoration",
        tags=("upscaling", "lightweight"),
        runtime_fit="phone",
        integration_tier="reference",
        notes="Very small and very fast audio upsampler.",
    ),
    _voice_repo(
        "nvidia-a2sb",
        "NVIDIA diffusion-audio-restoration",
        "https://github.com/NVIDIA/diffusion-audio-restoration",
        "enhancement-restoration",
        tags=("restoration", "inpainting", "diffusion"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Audio restoration and inpainting for high-resolution audio.",
    ),
    _voice_repo(
        "musicgen",
        "MusicGen",
        "https://github.com/facebookresearch/audiocraft",
        "multimodal-experimental",
        tags=("music", "generation"),
        runtime_fit="server",
        integration_tier="reference",
        notes="AudioCraft subproject for text-to-music generation.",
    ),
    _voice_repo(
        "audiogen",
        "AudioGen",
        "https://github.com/facebookresearch/audiocraft",
        "multimodal-experimental",
        tags=("general-audio", "generation"),
        runtime_fit="server",
        integration_tier="reference",
        notes="AudioCraft subproject for general audio generation.",
    ),
    _voice_repo(
        "audiox",
        "AudioX",
        "https://github.com/ZeyueT/AudioX",
        "multimodal-experimental",
        tags=("anything-to-audio", "editing", "speech", "music"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Any-to-audio unified generation and editing framework.",
    ),
    _voice_repo(
        "audio-omni",
        "Audio-Omni",
        "https://github.com/ZeyueT/Audio-Omni",
        "multimodal-experimental",
        tags=("anything-to-audio", "omni", "editing"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Unified audio understanding, generation, and editing framework.",
    ),
    _voice_repo(
        "audio-flamingo",
        "Audio Flamingo",
        "https://github.com/NVIDIA/audio-flamingo",
        "multimodal-experimental",
        "speech-recognition",
        tags=("audio-llm", "reasoning", "captioning"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Audio understanding and reasoning model family.",
    ),
    _voice_repo(
        "mmaudio",
        "MMAudio",
        "https://github.com/hkchengrex/MMAudio",
        "multimodal-experimental",
        tags=("video-to-audio", "text-to-audio", "image-to-audio"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Multimodal synchronized audio generation.",
    ),
    _voice_repo(
        "woosh-sfx",
        "Woosh-SFX",
        "https://github.com/SonyResearch/Woosh-SFX",
        "multimodal-experimental",
        tags=("sound-effects", "video-to-audio", "text-to-audio"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Sound-effects-first generation stack.",
    ),
    _voice_repo(
        "thinksound",
        "ThinkSound",
        "https://github.com/FunAudioLLM/ThinkSound",
        "multimodal-experimental",
        tags=("any2audio", "editing", "cot"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Any2audio framework with reasoning-guided generation.",
    ),
    _voice_repo(
        "uni-moe",
        "Uni-MoE",
        "https://github.com/HITsz-TMG/Uni-MoE",
        "multimodal-experimental",
        tags=("omnimodal", "tts", "voice-cloning", "text-to-music"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="MoE omnimodal audio model spanning speech and music.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "ace-step",
        "ACE-Step 1.5",
        "https://github.com/ace-step/ACE-Step-1.5",
        "multimodal-experimental",
        tags=("music", "voice2bgm", "generation"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Local music and accompaniment generation stack.",
    ),
    _voice_repo(
        "songgeneration",
        "SongGeneration",
        "https://github.com/tencent-ailab/songgeneration",
        "multimodal-experimental",
        tags=("music", "lyrics", "generation"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Commercial-grade open music generation reference.",
    ),
    _voice_repo(
        "magenta-realtime",
        "Magenta Realtime",
        "https://github.com/magenta/magenta-realtime",
        "multimodal-experimental",
        tags=("music", "realtime", "audio-conditioned"),
        runtime_fit="server",
        integration_tier="experimental",
        notes="Continuous realtime music generation from prompts or audio.",
    ),
    _voice_repo(
        "resemble-chatterbox",
        "Chatterbox",
        "https://github.com/resemble-ai/chatterbox",
        "text-to-speech",
        "voice-cloning",
        tags=("multilingual", "expressive", "streaming"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Modern multilingual cloning-capable TTS family.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "moss-tts",
        "MOSS-TTS",
        "https://github.com/OpenMOSS/MOSS-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("streaming", "multilingual", "production-grade"),
        runtime_fit="server",
        integration_tier="research",
        notes="Production-oriented multilingual TTS family.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "moss-tts-nano",
        "MOSS-TTS-Nano",
        "https://github.com/OpenMOSS/MOSS-TTS-Nano",
        "text-to-speech",
        "voice-cloning",
        tags=("cpu", "lightweight", "realtime"),
        runtime_fit="phone",
        integration_tier="research",
        notes="Smaller CPU-friendly sibling in the MOSS-TTS family.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "t5gemma-tts",
        "T5Gemma-TTS",
        "https://github.com/Aratako/T5Gemma-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("encoder-decoder", "duration-control"),
        runtime_fit="server",
        integration_tier="research",
        notes="Multilingual TTS on T5Gemma architecture.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "lemas-tts",
        "LEMAS-TTS",
        "https://github.com/LEMAS-Project/LEMAS-TTS",
        "text-to-speech",
        "voice-cloning",
        tags=("multilingual", "editing", "word-level"),
        runtime_fit="server",
        integration_tier="research",
        notes="Large multilingual audio suite with word-level editing.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "fish-audio-s2-pro",
        "Fish Audio S2 Pro",
        "https://github.com/fishaudio/fish-speech",
        "text-to-speech",
        "voice-cloning",
        tags=("prosody-control", "expressive", "streaming"),
        runtime_fit="server",
        integration_tier="research",
        notes="Catalog alias for the newer Fish Speech model family.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "sopro",
        "SoproTTS",
        "https://github.com/samuel-vitorino/sopro",
        "text-to-speech",
        "voice-cloning",
        tags=("cpu", "english", "lightweight"),
        runtime_fit="phone",
        integration_tier="experimental",
        notes="Low-cost English zero-shot TTS path.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "supertonic",
        "Supertonic",
        "https://github.com/supertone-inc/supertonic",
        "text-to-speech",
        tags=("on-device", "onnx", "high-speed"),
        runtime_fit="phone",
        integration_tier="research",
        notes="Fast on-device TTS focused on ONNX deployment.",
    ),
    _voice_repo(
        "kugelaudio-open",
        "KugelAudio",
        "https://github.com/Kugelaudio/kugelaudio-open",
        "text-to-speech",
        "voice-cloning",
        tags=("european-languages", "streaming"),
        runtime_fit="server",
        integration_tier="research",
        notes="European-language-focused open TTS.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "indextts2",
        "IndexTTS2",
        "https://github.com/xuchenxu168/Comfyui-Index-TTS2",
        "text-to-speech",
        "voice-cloning",
        tags=("emotion", "multi-speaker", "zh", "en"),
        runtime_fit="server",
        integration_tier="research",
        notes="Multi-speaker and emotion-capable TTS packaging.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "miotts-inference",
        "MioTTS-Inference",
        "https://github.com/Aratako/MioTTS-Inference",
        "text-to-speech",
        "voice-cloning",
        tags=("high-speed", "en", "jp"),
        runtime_fit="server",
        integration_tier="research",
        notes="Inference repo for the MioTTS model family.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "zipvoice",
        "ZipVoice",
        "https://github.com/k2-fsa/ZipVoice",
        "text-to-speech",
        "voice-cloning",
        tags=("flow-matching", "dialogue", "fast"),
        runtime_fit="server",
        integration_tier="research",
        notes="Fast zero-shot TTS models based on flow matching.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "kittentts",
        "KittenTTS",
        "https://github.com/KittenML/KittenTTS",
        "text-to-speech",
        "voice-cloning",
        tags=("lightweight", "cpu", "realtime"),
        runtime_fit="phone",
        integration_tier="research",
        notes="Lightweight realistic TTS under 25MB.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "openvoice",
        "OpenVoice",
        "https://github.com/myshell-ai/OpenVoice",
        "text-to-speech",
        "voice-cloning",
        tags=("cloning", "style-transfer", "multilingual"),
        runtime_fit="server",
        integration_tier="expansion",
        notes="Widely used voice cloning and style transfer stack.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "melotts",
        "MeloTTS",
        "https://github.com/myshell-ai/MeloTTS",
        "text-to-speech",
        tags=("multilingual", "lightweight", "offline"),
        runtime_fit="phone",
        integration_tier="expansion",
        notes="Practical multilingual TTS project with lighter deployment story.",
    ),
    _voice_repo(
        "gpt-sovits",
        "GPT-SoVITS",
        "https://github.com/RVC-Boss/GPT-SoVITS",
        "text-to-speech",
        "voice-cloning",
        tags=("few-shot", "cloning", "popular"),
        runtime_fit="server",
        integration_tier="research",
        notes="Popular few-shot speech synthesis and cloning stack.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "styletts2",
        "StyleTTS2",
        "https://github.com/yl4579/StyleTTS2",
        "text-to-speech",
        "training-framework",
        tags=("style", "tts", "research"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Modern style-aware TTS training and inference implementation.",
    ),
    _voice_repo(
        "vall-e-x",
        "VALL-E-X",
        "https://github.com/Plachtaa/VALL-E-X",
        "text-to-speech",
        "voice-cloning",
        tags=("zero-shot", "cross-lingual", "speech-prompt"),
        runtime_fit="server",
        integration_tier="research",
        notes="Cross-lingual zero-shot TTS inspired by VALL-E.",
        requires_operator_approval=True,
    ),
    _voice_repo(
        "amphion",
        "Amphion",
        "https://github.com/open-mmlab/Amphion",
        "training-framework",
        "text-to-speech",
        "speech-recognition",
        tags=("speech-toolkit", "tts", "singing", "vc"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Open speech toolkit covering TTS, VC, and singing tasks.",
    ),
    _voice_repo(
        "whisper-cpp",
        "whisper.cpp",
        "https://github.com/ggml-org/whisper.cpp",
        "speech-recognition",
        tags=("whisper", "cpp", "edge", "offline"),
        runtime_fit="phone",
        integration_tier="expansion",
        notes="Edge-friendly C/C++ Whisper inference backend.",
    ),
    _voice_repo(
        "sherpa-onnx",
        "sherpa-onnx",
        "https://github.com/k2-fsa/sherpa-onnx",
        "speech-recognition",
        "audio-pipeline",
        tags=("onnx", "streaming", "keyword-spotting", "tts"),
        runtime_fit="phone",
        integration_tier="managed",
        notes="Managed phone-side expansion path for offline ASR, TTS, and VAD model packages.",
    ),
    _voice_repo(
        "kaldi",
        "Kaldi",
        "https://github.com/kaldi-asr/kaldi",
        "speech-recognition",
        "training-framework",
        tags=("classic", "asr", "toolkit"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Classic ASR toolkit still relevant as a reference baseline.",
    ),
    _voice_repo(
        "wenet",
        "WeNet",
        "https://github.com/wenet-e2e/wenet",
        "speech-recognition",
        "training-framework",
        tags=("end-to-end", "asr", "streaming"),
        runtime_fit="server",
        integration_tier="reference",
        notes="End-to-end ASR toolkit with production-oriented deployment paths.",
    ),
    _voice_repo(
        "icefall",
        "icefall",
        "https://github.com/k2-fsa/icefall",
        "speech-recognition",
        "training-framework",
        tags=("recipes", "asr", "k2"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Speech recipe collection used across k2-based ASR systems.",
    ),
    _voice_repo(
        "pyannote-audio",
        "pyannote-audio",
        "https://github.com/pyannote/pyannote-audio",
        "speech-recognition",
        "audio-pipeline",
        tags=("diarization", "speaker", "segmentation"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Speaker diarization and segmentation toolkit.",
    ),
    _voice_repo(
        "asteroid",
        "Asteroid",
        "https://github.com/asteroid-team/asteroid",
        "enhancement-restoration",
        "training-framework",
        tags=("source-separation", "speech-enhancement"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Audio source separation and enhancement toolkit.",
    ),
    _voice_repo(
        "noisereduce",
        "noisereduce",
        "https://github.com/timsainb/noisereduce",
        "enhancement-restoration",
        tags=("noise-reduction", "python", "preprocessing"),
        runtime_fit="phone",
        integration_tier="reference",
        notes="Simple and practical Python noise reduction utility.",
    ),
    _voice_repo(
        "stable-audio-tools",
        "stable-audio-tools",
        "https://github.com/Stability-AI/stable-audio-tools",
        "multimodal-experimental",
        "training-framework",
        tags=("audio-generation", "training", "diffusion"),
        runtime_fit="server",
        integration_tier="reference",
        notes="Stability AI tooling for training and serving audio generative models.",
    ),
)


VOICE_CATEGORY_ORDER: tuple[str, ...] = (
    "text-to-speech",
    "voice-cloning",
    "speech-recognition",
    "audio-pipeline",
    "training-framework",
    "enhancement-restoration",
    "multimodal-experimental",
    "master-index",
)


VOICE_CATEGORY_LABELS: dict[str, str] = {
    "text-to-speech": "Text-to-Speech",
    "voice-cloning": "Voice Cloning",
    "speech-recognition": "Speech Recognition",
    "audio-pipeline": "Audio / Voice Pipelines",
    "training-framework": "Training Frameworks",
    "enhancement-restoration": "Enhancement / Restoration",
    "multimodal-experimental": "Multimodal / Experimental",
    "master-index": "Curated Master Lists",
}


class VoiceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def engines(self) -> dict[str, Any]:
        piper_model = self._default_piper_model()
        piper_config = Path(f"{piper_model}.json") if piper_model else None
        whisper_binary = shutil.which("whisper")
        whisper_cpp_binary = shutil.which("whisper-cli")
        sherpa_binary = shutil.which("sherpa-onnx-offline")
        piper_binary = shutil.which("piper")
        sherpa_manifest = self._sherpa_manifest_path()
        return {
            "piper": {
                "available": piper_binary is not None,
                "binary": piper_binary,
                "model": piper_model.as_posix() if piper_model else None,
                "model_exists": piper_model.exists() if piper_model else False,
                "config": piper_config.as_posix() if piper_config else None,
                "config_exists": piper_config.exists() if piper_config else False,
            },
            "whisper": {
                "available": whisper_binary is not None,
                "binary": whisper_binary,
            },
            "whisper.cpp": {
                "available": whisper_cpp_binary is not None,
                "binary": whisper_cpp_binary,
                "model": self._whisper_cpp_model_path().as_posix() if self._whisper_cpp_model_path() else None,
                "model_exists": self._whisper_cpp_model_path().exists() if self._whisper_cpp_model_path() else False,
                "vad_model": self._whisper_cpp_vad_model_path().as_posix() if self._whisper_cpp_vad_model_path() else None,
                "vad_model_exists": self._whisper_cpp_vad_model_path().exists() if self._whisper_cpp_vad_model_path() else False,
            },
            "sherpa-onnx": {
                "available": sherpa_binary is not None,
                "binary": sherpa_binary,
                "manifest": sherpa_manifest.as_posix() if sherpa_manifest else None,
                "manifest_exists": sherpa_manifest.exists() if sherpa_manifest else False,
                "vad_model": self._sherpa_vad_model_path().as_posix() if self._sherpa_vad_model_path() else None,
                "vad_model_exists": self._sherpa_vad_model_path().exists() if self._sherpa_vad_model_path() else False,
            },
            "catalog_summary": self.catalog()["summary"],
            "recommended_stack": self.catalog()["recommended_stack"],
        }

    def catalog(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        runtime_fit: str | None = None,
        integration_tier: str | None = None,
        supported_only: bool = False,
        approval_required: bool | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        repos = list(VOICE_REPOS)
        filtered = self._filter_repos(
            repos,
            query=query,
            category=category,
            runtime_fit=runtime_fit,
            integration_tier=integration_tier,
            supported_only=supported_only,
            approval_required=approval_required,
        )
        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be at least 1")
            filtered = filtered[:limit]

        categories: list[dict[str, Any]] = []
        category_counts: dict[str, int] = {}
        for category in VOICE_CATEGORY_ORDER:
            members = [repo for repo in filtered if category in repo.categories]
            category_counts[category] = len(members)
            categories.append(
                {
                    "id": category,
                    "label": VOICE_CATEGORY_LABELS[category],
                    "count": len(members),
                    "repos": [self._repo_snapshot(repo) for repo in members],
                }
            )

        supported = [repo for repo in filtered if repo.supported_by_runtime]
        phone_ready = [repo for repo in filtered if repo.runtime_fit == "phone"]
        approval_gated = [repo for repo in filtered if repo.requires_operator_approval]

        return {
            "summary": {
                "unique_repositories": len(filtered),
                "total_repositories": len(repos),
                "category_counts": category_counts,
                "runtime_supported": len(supported),
                "phone_ready_candidates": len(phone_ready),
                "approval_required": len(approval_gated),
            },
            "filters": {
                "query": query,
                "category": category,
                "runtime_fit": runtime_fit,
                "integration_tier": integration_tier,
                "supported_only": supported_only,
                "approval_required": approval_required,
                "limit": limit,
            },
            "recommended_stack": {
                "baseline_tts": "piper",
                "baseline_asr": "whisper",
                "phone_expansion_candidates": ["tinytts", "kokoro", "neutts", "faster-whisper", "rnnoise", "deepfilternet"],
                "server_expansion_candidates": ["qwen3-tts", "fish-speech", "cosyvoice", "funasr", "seamless-communication", "parler-tts"],
                "policy_notes": [
                    "Cloning-capable models require explicit operator approval before use.",
                    "Managed downloads should continue to flow through the existing SafeHttpClient and allowlist.",
                    "Current runtime support remains explicit: Piper for synthesis plus Whisper CLI, whisper.cpp, and sherpa-onnx offline paths for transcription.",
                ],
            },
            "categories": categories,
            "repos": [self._repo_snapshot(repo) for repo in filtered],
        }

    def synthesize(self, text: str, output_filename: str | None = None) -> dict[str, Any]:
        self._validate_text(text)
        piper_binary = shutil.which("piper")
        if piper_binary is None:
            raise RuntimeError("piper binary is not available on PATH")

        model_path = self._default_piper_model()
        if model_path is None or not model_path.exists():
            raise RuntimeError("Piper voice model is not installed; install the phone-starter bundle first")

        config_path = Path(f"{model_path}.json")
        if not config_path.exists():
            raise RuntimeError("Piper voice config is missing; install the phone-starter bundle first")

        voice_dir = self.settings.data_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_output_name(output_filename)
        output_path = voice_dir / safe_name
        command = [
            piper_binary,
            "--model",
            model_path.as_posix(),
            "--config",
            config_path.as_posix(),
            "--output_file",
            output_path.as_posix(),
        ]
        result = subprocess.run(command, input=text, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "piper synthesis failed")
        if not output_path.exists():
            raise RuntimeError("piper did not produce an output file")

        return {
            "engine": "piper",
            "output_path": output_path.as_posix(),
            "bytes": output_path.stat().st_size,
            "created_at": datetime.now(UTC).isoformat(),
        }

    def transcribe(self, audio_path: str, model: str = "base", provider: str = "whisper") -> dict[str, Any]:
        normalized_provider = provider.strip().lower()
        if normalized_provider == "whisper.cpp":
            return self._transcribe_whisper_cpp(audio_path)
        if normalized_provider == "sherpa-onnx":
            return self._transcribe_sherpa_onnx(audio_path)
        if normalized_provider != "whisper":
            raise ValueError("provider must be one of 'whisper', 'whisper.cpp', or 'sherpa-onnx'")

        whisper_binary = shutil.which("whisper")
        if whisper_binary is None:
            raise RuntimeError("whisper binary is not available on PATH")

        source = Path(audio_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Audio file not found: {source.as_posix()}")

        voice_dir = self.settings.data_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        command = [
            whisper_binary,
            source.as_posix(),
            "--model",
            model,
            "--output_format",
            "txt",
            "--output_dir",
            voice_dir.as_posix(),
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "whisper transcription failed")

        transcript_path = voice_dir / f"{source.stem}.txt"
        if not transcript_path.exists():
            raise RuntimeError("whisper did not produce a transcript file")

        text = transcript_path.read_text(encoding="utf-8").strip()
        return {
            "engine": "whisper",
            "provider": "whisper",
            "model": model,
            "audio_path": source.as_posix(),
            "transcript_path": transcript_path.as_posix(),
            "text": text,
        }

    def _transcribe_whisper_cpp(self, audio_path: str) -> dict[str, Any]:
        whisper_cpp_binary = shutil.which("whisper-cli")
        if whisper_cpp_binary is None:
            raise RuntimeError("whisper-cli binary is not available on PATH")

        source = Path(audio_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Audio file not found: {source.as_posix()}")

        model_path = self._whisper_cpp_model_path()
        if model_path is None or not model_path.exists():
            raise RuntimeError("whisper.cpp model is not installed; install the voice-asr-whispercpp-phone bundle first")

        voice_dir = self.settings.data_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        output_prefix = voice_dir / source.stem
        transcript_path = output_prefix.with_suffix(".txt")
        if transcript_path.exists():
            transcript_path.unlink()

        command = [
            whisper_cpp_binary,
            "-m",
            model_path.as_posix(),
            "-f",
            source.as_posix(),
            "-of",
            output_prefix.as_posix(),
            "-otxt",
        ]
        vad_model = self._whisper_cpp_vad_model_path()
        if vad_model is not None and vad_model.exists():
            command.extend(["--vad", "--vad-model", vad_model.as_posix()])

        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "whisper.cpp transcription failed")
        if not transcript_path.exists():
            raise RuntimeError("whisper.cpp did not produce a transcript file")

        text = transcript_path.read_text(encoding="utf-8").strip()
        return {
            "engine": "whisper.cpp",
            "provider": "whisper.cpp",
            "model": model_path.name,
            "audio_path": source.as_posix(),
            "transcript_path": transcript_path.as_posix(),
            "text": text,
        }

    def _transcribe_sherpa_onnx(self, audio_path: str) -> dict[str, Any]:
        sherpa_binary = shutil.which("sherpa-onnx-offline")
        if sherpa_binary is None:
            raise RuntimeError("sherpa-onnx-offline binary is not available on PATH")

        source = Path(audio_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Audio file not found: {source.as_posix()}")

        manifest = self._load_sherpa_manifest()
        encoder = manifest.get("whisper_encoder")
        decoder = manifest.get("whisper_decoder")
        tokens = manifest.get("tokens")
        if not encoder or not decoder or not tokens:
            raise RuntimeError("sherpa-onnx manifest is incomplete; reinstall the voice-asr-sherpa-phone bundle")

        voice_dir = self.settings.data_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sherpa_binary,
            f"--whisper-encoder={encoder}",
            f"--whisper-decoder={decoder}",
            f"--tokens={tokens}",
            "--num-threads=2",
            "--decoding-method=greedy_search",
            source.as_posix(),
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "sherpa-onnx transcription failed")

        text = self._extract_sherpa_text(result.stdout)
        transcript_path = voice_dir / f"{source.stem}.sherpa-onnx.txt"
        transcript_path.write_text(text, encoding="utf-8")
        return {
            "engine": "sherpa-onnx",
            "provider": "sherpa-onnx",
            "model": Path(encoder).parent.name,
            "audio_path": source.as_posix(),
            "transcript_path": transcript_path.as_posix(),
            "text": text,
        }

    def _default_piper_model(self) -> Path | None:
        models_dir = self.settings.models_dir
        if models_dir is None:
            return None
        return models_dir / "en_US-lessac-medium.onnx"

    def _whisper_cpp_model_path(self) -> Path | None:
        models_dir = self.settings.models_dir
        if models_dir is None:
            return None
        return models_dir / "ggml-base.en.bin"

    def _whisper_cpp_vad_model_path(self) -> Path | None:
        models_dir = self.settings.models_dir
        if models_dir is None:
            return None
        return models_dir / "ggml-silero-v6.2.0.bin"

    def _sherpa_manifest_path(self) -> Path | None:
        models_dir = self.settings.models_dir
        if models_dir is None:
            return None
        return models_dir / "sherpa-onnx-whisper-tiny.en" / "mordecai-sherpa-manifest.json"

    def _sherpa_vad_model_path(self) -> Path | None:
        models_dir = self.settings.models_dir
        if models_dir is None:
            return None
        return models_dir / "silero_vad.onnx"

    def _load_sherpa_manifest(self) -> dict[str, Any]:
        manifest_path = self._sherpa_manifest_path()
        if manifest_path is None or not manifest_path.exists():
            raise RuntimeError("sherpa-onnx manifest is not installed; install the voice-asr-sherpa-phone bundle first")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    @staticmethod
    def _extract_sherpa_text(stdout: str) -> str:
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line.startswith("{") or '"text"' not in line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = str(payload.get("text", "")).strip()
            if text:
                return text
        non_empty_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if non_empty_lines:
            return non_empty_lines[-1]
        raise RuntimeError("sherpa-onnx did not emit transcript text")

    @staticmethod
    def _safe_output_name(output_filename: str | None) -> str:
        if not output_filename:
            return f"tts-{uuid4().hex[:12]}.wav"
        cleaned = output_filename.strip()
        if not cleaned.lower().endswith(".wav"):
            cleaned += ".wav"
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", cleaned):
            raise ValueError("output_filename can only contain letters, numbers, dot, underscore, and dash")
        return cleaned

    @staticmethod
    def _validate_text(text: str) -> None:
        stripped = text.strip()
        if not stripped:
            raise ValueError("Text cannot be empty")
        if len(stripped) > 2000:
            raise ValueError("Text must be 2000 characters or fewer")

    @staticmethod
    def _repo_snapshot(repo: VoiceRepo) -> dict[str, Any]:
        return {
            "slug": repo.slug,
            "name": repo.name,
            "repo_url": repo.repo_url,
            "categories": list(repo.categories),
            "tags": list(repo.tags),
            "runtime_fit": repo.runtime_fit,
            "integration_tier": repo.integration_tier,
            "notes": repo.notes,
            "supported_by_runtime": repo.supported_by_runtime,
            "managed_asset_ids": list(repo.managed_asset_ids),
            "requires_operator_approval": repo.requires_operator_approval,
        }

    @staticmethod
    def _filter_repos(
        repos: list[VoiceRepo],
        *,
        query: str | None,
        category: str | None,
        runtime_fit: str | None,
        integration_tier: str | None,
        supported_only: bool,
        approval_required: bool | None,
    ) -> list[VoiceRepo]:
        normalized_query = query.strip().lower() if query else None
        filtered: list[VoiceRepo] = []
        for repo in repos:
            if category and category not in repo.categories:
                continue
            if runtime_fit and repo.runtime_fit != runtime_fit:
                continue
            if integration_tier and repo.integration_tier != integration_tier:
                continue
            if supported_only and not repo.supported_by_runtime:
                continue
            if approval_required is not None and repo.requires_operator_approval != approval_required:
                continue
            if normalized_query:
                haystack = " ".join((repo.slug, repo.name, repo.notes, *repo.categories, *repo.tags)).lower()
                if normalized_query not in haystack:
                    continue
            filtered.append(repo)
        return filtered


def build_voice_profile(settings: Settings) -> VoiceProfile:
    return VoiceProfile(
        wake_words=settings.wake_words,
        startup_phrase="I am listening.",
        nicknames={
            "Mordecai": "formal",
            "Mori": "soft",
            "Cai": "efficient",
            "Morde": "focused",
            "Mort": "diagnostic",
            "Decai": "analytical",
        },
    )