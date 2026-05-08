from __future__ import annotations

from dataclasses import dataclass

from mordecai.config import Settings


@dataclass(frozen=True)
class VoiceProfile:
    wake_words: list[str]
    startup_phrase: str
    nicknames: dict[str, str]


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