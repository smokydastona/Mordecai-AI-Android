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
    emotion_scores = {
        "focus": 0,
        "concerned": 0,
        "intrigued": 0,
        "surprised": 0,
        "proud": 0,
        "sleep": 0,
        "unimpressed": 0,
        "thinking": 0,
        "wise-smirk": 0,
        "happy": 0,
        "laughing": 0,
    }
    
    if any(action in {"github-search", "fetch-url", "web-search"} for action in actions):
        emotion_scores["focus"] += 3
    
    focus_tokens = ["focus", "analy", "inspect", "investigat", "scan", "examine", "review", "study"]
    emotion_scores["focus"] += sum(1 for token in focus_tokens if token in lowered)
    
    concerned_tokens = ["warning", "blocked", "cannot", "failed", "denied", "forbidden", "error", "issue", "problem", "unavailable", "invalid"]
    emotion_scores["concerned"] += sum(1 for token in concerned_tokens if token in lowered)
    
    intrigued_tokens = ["intrigued", "curious", "interesting", "noted", "fascinating", "remarkable"]
    emotion_scores["intrigued"] += sum(1 for token in intrigued_tokens if token in lowered)
    
    surprised_tokens = ["surprised", "unexpected", "override acknowledged", "startling", "astonishing"]
    emotion_scores["surprised"] += sum(1 for token in surprised_tokens if token in lowered)
    
    proud_tokens = ["proud", "excellent", "accomplished", "solid work", "well done", "success", "achieved"]
    emotion_scores["proud"] += sum(1 for token in proud_tokens if token in lowered)
    
    sleep_tokens = ["sleep", "idle", "standby", "rest", "pause", "dormant"]
    emotion_scores["sleep"] += sum(1 for token in sleep_tokens if token in lowered)
    
    unimpressed_tokens = ["unimpressed", "predictable", "ordinary", "routine", "mundane", "trivial"]
    emotion_scores["unimpressed"] += sum(1 for token in unimpressed_tokens if token in lowered)
    
    thinking_tokens = ["think", "consider", "plan", "reason", "reflect", "understand", "analyze", "evaluate"]
    emotion_scores["thinking"] += sum(1 for token in thinking_tokens if token in lowered)
    
    wise_tokens = ["wise", "steady", "stable", "calm", "measured", "prudent", "sage"]
    emotion_scores["wise-smirk"] += sum(1 for token in wise_tokens if token in lowered)
    
    happy_tokens = ["glad", "good", "great", "done", "complete", "online", "ready", "happy", "excellent", "running"]
    emotion_scores["happy"] += sum(1 for token in happy_tokens if token in lowered)
    
    laughing_tokens = ["laugh", "humor", "amusing", "funny", "comic", "hilarious"]
    emotion_scores["laughing"] += sum(1 for token in laughing_tokens if token in lowered)
    
    max_score = max(emotion_scores.values())
    if max_score > 0:
        best_emotion = next(emotion for emotion, score in emotion_scores.items() if score == max_score)
        return best_emotion
    
    return DEFAULT_AVATAR_EMOTION