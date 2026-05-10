from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from mordecai.models import AgentPlanRequest, RuntimeFailure, RuntimeEvent, VoiceSessionEventRequest, VoiceSessionEventResponse, VoiceSessionRecord, VoiceSessionStartRequest
from mordecai.planner import PlannerService
from mordecai.store import StateStore
from mordecai.voice import VoiceService
from voice.wake_word import WakeWordDetector


class VoiceSessionService:
    def __init__(self, store: StateStore, planner: PlannerService, voice_service: VoiceService, wake_words: list[str]) -> None:
        self.store = store
        self.planner = planner
        self.voice_service = voice_service
        self.detector = WakeWordDetector(wake_words)

    def start_session(self, request: VoiceSessionStartRequest) -> VoiceSessionRecord:
        now = datetime.now(UTC)
        record = VoiceSessionRecord(
            session_id=uuid4().hex[:12],
            label=request.label,
            background=request.background,
            status="awaiting-wake-word",
            created_at=now,
            updated_at=now,
        )
        self.store.save_voice_session(record)
        self.store.append_event(RuntimeEvent(category="voice-session", detail=f"started:{record.session_id}"))
        return record

    def list_sessions(self) -> list[VoiceSessionRecord]:
        return self.store.read_voice_sessions()

    def get_session(self, session_id: str) -> VoiceSessionRecord:
        record = self.store.get_voice_session(session_id)
        if record is None:
            raise KeyError(session_id)
        return record

    def ingest_event(self, session_id: str, request: VoiceSessionEventRequest) -> VoiceSessionEventResponse:
        session = self.get_session(session_id)
        wake_word_detected = False

        if request.playback_finished and session.status == "speaking":
            session.status = "awaiting-wake-word"

        if request.interrupt and session.status in {"thinking", "speaking"}:
            session.status = "interrupted"
            session.interrupted_count += 1
            session.last_error = None

        transcript = request.transcript.strip()
        if transcript:
            session.last_transcript = transcript

        if not transcript:
            session.updated_at = datetime.now(UTC)
            self.store.save_voice_session(session)
            return VoiceSessionEventResponse(session=session, wake_word_detected=False)

        wake = self.detector.detect(transcript)
        wake_word_detected = wake.matched
        if not request.is_final:
            if wake.matched:
                session.last_wake_word = wake.wake_word
                session.pending_command = wake.command or None
                session.status = "listening-command"
            session.updated_at = datetime.now(UTC)
            self.store.save_voice_session(session)
            return VoiceSessionEventResponse(session=session, wake_word_detected=wake_word_detected)

        command = ""
        if wake.matched:
            session.last_wake_word = wake.wake_word
            command = wake.command
        elif session.status in {"listening-command", "interrupted"} and session.last_wake_word:
            command = transcript
        else:
            session.status = "awaiting-wake-word"
            session.updated_at = datetime.now(UTC)
            self.store.save_voice_session(session)
            return VoiceSessionEventResponse(session=session, wake_word_detected=False)

        command = command.strip()
        if not command:
            session.status = "listening-command"
            session.updated_at = datetime.now(UTC)
            self.store.save_voice_session(session)
            return VoiceSessionEventResponse(session=session, wake_word_detected=wake_word_detected)

        session.pending_command = command
        session.last_plan_goal = command
        session.status = "thinking"
        session.updated_at = datetime.now(UTC)
        self.store.save_voice_session(session)

        plan = self.planner.run(
            AgentPlanRequest(
                goal=command,
                auto_execute=request.auto_execute,
                granted_permissions=request.granted_permissions,
                session_id=f"voice-{session_id}",
                safe_mode=request.safe_mode,
            )
        )
        session.last_response = plan.final_response
        session.last_error = None

        if request.synthesize_response:
            try:
                synthesized = self.voice_service.synthesize(plan.final_response)
            except Exception as exc:
                session.status = "error"
                session.last_error = RuntimeFailure(code="VoiceSynthesisFailed", message=str(exc))
                session.updated_at = datetime.now(UTC)
                self.store.save_voice_session(session)
                return VoiceSessionEventResponse(session=session, plan=plan, wake_word_detected=wake_word_detected)
            session.last_audio_path = synthesized["output_path"]

        session.status = "speaking"
        session.updated_at = datetime.now(UTC)
        self.store.save_voice_session(session)
        self.store.append_event(RuntimeEvent(category="voice-session", detail=f"command:{session.session_id}:{command}"))
        return VoiceSessionEventResponse(session=session, plan=plan, wake_word_detected=wake_word_detected)