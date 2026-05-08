from __future__ import annotations

from pathlib import Path

from mordecai.config import Settings
from mordecai.models import AvatarFrame, AvatarProfile


DEFAULT_AVATAR_EMOTION = "neutral"
AVATAR_STYLE = "warm-old-man-vector"
EMOTION_ORDER = [
    "neutral",
    "happy",
    "thinking",
    "concerned",
    "surprised",
    "laughing",
    "wise-smirk",
]


def build_avatar_profile(settings: Settings, current_emotion: str = DEFAULT_AVATAR_EMOTION) -> AvatarProfile:
    frames = [
        AvatarFrame(
            emotion=emotion,
            label=emotion.replace("-", " ").title(),
            asset_path=(settings.avatar_assets_dir / f"{emotion}.svg").as_posix(),
            svg=(settings.avatar_assets_dir / f"{emotion}.svg").read_text(encoding="utf-8"),
        )
        for emotion in EMOTION_ORDER
    ]
    return AvatarProfile(
        style=AVATAR_STYLE,
        immutable_assets=True,
        immutable_behavior=True,
        immutable_style=True,
        current_emotion=current_emotion if current_emotion in EMOTION_ORDER else DEFAULT_AVATAR_EMOTION,
        frames=frames,
    )


def classify_avatar_emotion(reply: str, actions: list[str]) -> str:
    lowered = reply.lower()
    if any(action in {"github-search", "fetch-url"} for action in actions):
        return "thinking"
    if any(token in lowered for token in ["warning", "blocked", "cannot", "failed", "denied", "forbidden"]):
        return "concerned"
    if any(token in lowered for token in ["surprised", "remarkable", "unexpected", "override acknowledged"]):
        return "surprised"
    if any(token in lowered for token in ["wise", "steady", "stable", "calm", "measured"]):
        return "wise-smirk"
    if any(token in lowered for token in ["glad", "good", "great", "done", "complete", "online"]):
        return "happy"
    if any(token in lowered for token in ["laugh", "humor", "amusing"]):
        return "laughing"
    return DEFAULT_AVATAR_EMOTION