from __future__ import annotations

from pathlib import Path

from mordecai.config import Settings
from mordecai.models import AvatarFrame, AvatarProfile


DEFAULT_AVATAR_EMOTION = "neutral"
AVATAR_STYLE = "warm-old-man-vector"
PREFERRED_EMOTION_ORDER = [
    "neutral",
    "happy",
    "thinking",
    "focus",
    "concerned",
    "intrigued",
    "surprised",
    "laughing",
    "proud",
    "sleep",
    "unimpressed",
    "wise-smirk",
]


def list_avatar_emotions(assets_dir: Path) -> list[str]:
    available_emotions = {asset.stem for asset in assets_dir.glob("*.svg") if asset.is_file()}
    ordered_emotions = [emotion for emotion in PREFERRED_EMOTION_ORDER if emotion in available_emotions]
    ordered_emotions.extend(sorted(available_emotions - set(ordered_emotions)))
    return ordered_emotions


def build_avatar_profile(settings: Settings, current_emotion: str = DEFAULT_AVATAR_EMOTION) -> AvatarProfile:
    emotions = list_avatar_emotions(settings.avatar_assets_dir)
    if not emotions:
        raise FileNotFoundError(f"No avatar SVG assets found in {settings.avatar_assets_dir}")

    fallback_emotion = DEFAULT_AVATAR_EMOTION if DEFAULT_AVATAR_EMOTION in emotions else emotions[0]
    frames = [
        AvatarFrame(
            emotion=emotion,
            label=emotion.replace("-", " ").title(),
            asset_path=(settings.avatar_assets_dir / f"{emotion}.svg").as_posix(),
            svg=(settings.avatar_assets_dir / f"{emotion}.svg").read_text(encoding="utf-8"),
        )
        for emotion in emotions
    ]
    return AvatarProfile(
        style=AVATAR_STYLE,
        immutable_assets=True,
        immutable_behavior=True,
        immutable_style=True,
        current_emotion=current_emotion if current_emotion in emotions else fallback_emotion,
        frames=frames,
    )


def classify_avatar_emotion(reply: str, actions: list[str]) -> str:
    lowered = reply.lower()
    if any(action in {"github-search", "fetch-url", "web-search"} for action in actions):
        return "focus"
    if any(token in lowered for token in ["focus", "analy", "inspect", "investigat", "scan"]):
        return "focus"
    if any(token in lowered for token in ["warning", "blocked", "cannot", "failed", "denied", "forbidden"]):
        return "concerned"
    if any(token in lowered for token in ["intrigued", "curious", "interesting", "noted"]):
        return "intrigued"
    if any(token in lowered for token in ["surprised", "remarkable", "unexpected", "override acknowledged"]):
        return "surprised"
    if any(token in lowered for token in ["proud", "excellent", "accomplished", "solid work"]):
        return "proud"
    if any(token in lowered for token in ["sleep", "idle", "standby", "rest"]):
        return "sleep"
    if any(token in lowered for token in ["unimpressed", "predictable", "ordinary", "routine"]):
        return "unimpressed"
    if any(token in lowered for token in ["think", "consider", "plan", "reason"]):
        return "thinking"
    if any(token in lowered for token in ["wise", "steady", "stable", "calm", "measured"]):
        return "wise-smirk"
    if any(token in lowered for token in ["glad", "good", "great", "done", "complete", "online"]):
        return "happy"
    if any(token in lowered for token in ["laugh", "humor", "amusing"]):
        return "laughing"
    return DEFAULT_AVATAR_EMOTION