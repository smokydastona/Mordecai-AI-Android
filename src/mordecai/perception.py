from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
import xml.etree.ElementTree as ET

from mordecai.models import AndroidPerceptionIngestRequest, AndroidPerceptionSnapshot, NotificationActionMetadata, PerceptionElement, RuntimeEvent
from mordecai.store import StateStore


class PerceptionService:
    def __init__(self, store: StateStore) -> None:
        self.store = store

    def ingest(self, request: AndroidPerceptionIngestRequest) -> AndroidPerceptionSnapshot:
        xml_elements = self._parse_ui_xml(request.ui_dump_xml)
        visible_text = self._dedupe([*request.visible_text, *self._extract_visible_text(xml_elements)])
        action_labels = self._dedupe([*request.action_labels, *self._extract_action_labels(xml_elements)])
        app_package = request.app_package or self._infer_package(xml_elements)
        screen_title = request.screen_title or (visible_text[0] if visible_text else None)
        snapshot = AndroidPerceptionSnapshot(
            snapshot_id=uuid4().hex[:12],
            source=request.source,
            app_package=app_package,
            activity=request.activity,
            screen_title=screen_title,
            visible_text=visible_text,
            action_labels=action_labels,
            focused_text=request.focused_text,
            focused_node=request.focused_node,
            clipboard_text=request.clipboard_text,
            notification_summaries=self._dedupe(request.notification_summaries),
            notification_actions=[NotificationActionMetadata.model_validate(item) for item in request.notification_actions],
            ui_elements=xml_elements,
            screenshot_path=self._normalize_path(request.screenshot_path),
            interactive=request.interactive,
            created_at=datetime.now(UTC),
        )
        self.store.save_perception_snapshot(snapshot)
        self.store.append_event(
            RuntimeEvent(
                category="perception",
                detail=f"ingested:{snapshot.snapshot_id}:{snapshot.app_package or 'unknown'}",
            )
        )
        return snapshot

    def latest_snapshot(self) -> AndroidPerceptionSnapshot | None:
        return self.store.latest_perception()

    def history(self) -> list[AndroidPerceptionSnapshot]:
        return self.store.read_perception_history()

    @staticmethod
    def device_state(snapshot: AndroidPerceptionSnapshot | None) -> dict[str, object]:
        if snapshot is None:
            return {}
        return {
            "app_package": snapshot.app_package,
            "activity": snapshot.activity,
            "screen_title": snapshot.screen_title,
            "visible_text": snapshot.visible_text[:20],
            "action_labels": snapshot.action_labels[:20],
            "focused_text": snapshot.focused_text,
            "focused_node": snapshot.focused_node.model_dump(mode="json") if snapshot.focused_node else None,
            "notification_actions": [item.model_dump(mode="json") for item in snapshot.notification_actions[:10]],
            "interactive": snapshot.interactive,
        }

    def _parse_ui_xml(self, ui_dump_xml: str | None) -> list[PerceptionElement]:
        if not ui_dump_xml:
            return []
        root = ET.fromstring(ui_dump_xml)
        elements: list[PerceptionElement] = []
        for node in root.iter("node"):
            elements.append(
                PerceptionElement(
                    text=self._clean(node.attrib.get("text")),
                    content_desc=self._clean(node.attrib.get("content-desc")),
                    resource_id=self._clean(node.attrib.get("resource-id")),
                    class_name=self._clean(node.attrib.get("class")),
                    package=self._clean(node.attrib.get("package")),
                    clickable=node.attrib.get("clickable") == "true",
                    enabled=node.attrib.get("enabled", "true") != "false",
                    bounds=self._clean(node.attrib.get("bounds")),
                )
            )
        return elements

    def _extract_visible_text(self, elements: list[PerceptionElement]) -> list[str]:
        values = []
        for element in elements:
            if element.text:
                values.append(element.text)
            elif element.content_desc:
                values.append(element.content_desc)
        return values

    def _extract_action_labels(self, elements: list[PerceptionElement]) -> list[str]:
        values = []
        for element in elements:
            if not element.clickable:
                continue
            if element.text:
                values.append(element.text)
            elif element.content_desc:
                values.append(element.content_desc)
            elif element.resource_id:
                values.append(element.resource_id.rsplit("/", 1)[-1])
        return values

    def _infer_package(self, elements: list[PerceptionElement]) -> str | None:
        packages = [element.package for element in elements if element.package]
        if not packages:
            return None
        return Counter(packages).most_common(1)[0][0]

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            cleaned = value.strip()
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result

    @staticmethod
    def _normalize_path(path: str | None) -> str | None:
        if not path:
            return None
        return Path(path).expanduser().resolve().as_posix()

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None