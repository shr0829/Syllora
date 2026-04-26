from __future__ import annotations

import json
import queue
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .llm_client import LLMClient, build_lesson_markdown, build_plan_markdown, build_research_markdown
from .markdown_tools import extract_goals_from_plan, extract_markdown_links, parse_markdown_document


STAGE_IMAGE_COUNT = 2
MAX_STAGE_GENERATION_WORKERS = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "learning-project"


def build_fallback_plan_markdown(topic: str) -> str:
    return f"""# 学习路径计划

## 学习目标
围绕“{topic}”建立一个从主题边界、核心概念到阶段实践的完整学习闭环。

## 建议节奏
建议按照“理解主题 → 建立结构 → 动手实践 → 复盘沉淀”的节奏推进，每个阶段保留清晰的产出物。

## 阶段概览
### 阶段 1｜定义主题边界
- 摘要：明确这个主题到底学什么、不学什么。
- 完成标志：能用自己的话说明主题边界和最终目标。
- 预计时长：0.5 天
- 前置知识：
  - 无
- 学习动作：
  - 阅读研究材料中的主题定位与核心问题
  - 写出自己的主题说明
- 阶段产出：
  - 一份 200 字以内的主题定位说明

### 阶段 2｜建立概念地图
- 摘要：把核心概念和上下游关系串成结构图。
- 完成标志：能说明各概念之间的关系与先后顺序。
- 预计时长：1 天
- 前置知识：
  - 阶段 1
- 学习动作：
  - 提取关键术语
  - 将概念分为基础、方法、实践三层
- 阶段产出：
  - 一张概念结构图

### 阶段 3｜完成最小实践
- 摘要：围绕主题做一次最小可运行练习。
- 完成标志：跑通一个可验证的小案例。
- 预计时长：1 天
- 前置知识：
  - 阶段 2
- 学习动作：
  - 选择一个最小案例
  - 跑通完整流程并记录结果
- 阶段产出：
  - 一份最小实践记录

### 阶段 4｜复盘与扩展
- 摘要：总结收获、识别盲区，并规划下一阶段。
- 完成标志：形成可复用的复盘文档。
- 预计时长：0.5 天
- 前置知识：
  - 阶段 3
- 学习动作：
  - 回顾研究、计划与实践内容
  - 写出后续深化方向
- 阶段产出：
  - 一份复盘与下一步计划
"""


class ProjectStore:
    def __init__(self, root: Path, llm: LLMClient) -> None:
        self.root = root
        self.data_root = self.root / "data" / "plans"
        self.index_path = self.data_root / "index.json"
        self.llm = llm
        self._subscriber_lock = threading.Lock()
        self._project_subscribers: dict[str, set[queue.Queue[dict[str, Any]]]] = {}
        self._project_lock_guard = threading.Lock()
        self._project_locks: dict[str, threading.RLock] = {}
        self.library_sources = [
            {
                "id": "pytorch_to_transformer",
                "title": "PyTorch 到 Transformer",
                "description": "从张量、训练循环一路走到 attention 和 decoder-only Transformer。",
                "path": self.root / "content" / "library" / "learning_tracks" / "pytorch_to_transformer",
            },
            {
                "id": "llm_agent_learning",
                "title": "AI 大模型接入与 Agent 学习系统",
                "description": "围绕 RAG、工具调用、工作流和评测构建大模型应用能力。",
                "path": self.root / "content" / "library" / "llm_agent_learning",
            },
        ]
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_json(
                self.index_path,
                {
                    "version": 2,
                    "projects": [],
                },
            )

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _to_relative_path(self, path: Path) -> str:
        return str(path.relative_to(self.root)).replace("\\", "/")

    def _load_index(self) -> dict[str, Any]:
        return self._read_json(self.index_path)

    def _save_index(self, index_payload: dict[str, Any]) -> None:
        self._write_json(self.index_path, index_payload)

    def _get_project_lock(self, project_id: str) -> threading.RLock:
        with self._project_lock_guard:
            return self._project_locks.setdefault(project_id, threading.RLock())

    def _default_research(self) -> dict[str, Any]:
        return {
            "status": "idle",
            "markdownPath": None,
            "parsedPath": None,
            "sourcesPath": None,
            "metadataPath": None,
            "sourceCount": 0,
            "sources": [],
            "document": None,
        }

    def _default_plan(self) -> dict[str, Any]:
        return {
            "status": "idle",
            "markdownPath": None,
            "parsedPath": None,
            "stageIndexPath": None,
            "metadataPath": None,
            "stageIndex": [],
            "document": None,
        }

    def _default_generation(self) -> dict[str, Any]:
        preview = {
            "kind": None,
            "title": "",
            "markdown": "",
            "document": None,
            "status": "idle",
            "updatedAt": None,
        }
        return {
            "active": False,
            "action": None,
            "title": "",
            "message": "",
            "targetGoalId": None,
            "startedAt": None,
            "updatedAt": None,
            "completedAt": None,
            "steps": [],
            "preview": preview,
        }

    def _default_artifacts(self, folder_name: str) -> dict[str, Any]:
        project_dir = self.data_root / folder_name
        return {
            "projectRoot": self._to_relative_path(project_dir),
            "sourcesPath": None,
            "stageIndexPath": None,
            "stagesRoot": self._to_relative_path(project_dir / "stages"),
            "metaRoot": self._to_relative_path(project_dir / "meta"),
        }

    def _build_stage_index(self, goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        stage_index: list[dict[str, Any]] = []
        for goal in goals:
            stage_index.append(
                {
                    "id": goal["id"],
                    "stageNumber": goal.get("stageNumber"),
                    "stageLabel": goal.get("stageLabel"),
                    "title": goal.get("title", ""),
                    "summary": goal.get("summary", ""),
                    "estimatedTime": goal.get("estimatedTime", ""),
                    "lessonStatus": goal.get("lessonStatus", "idle"),
                    "imageStatus": goal.get("imageStatus", "idle"),
                    "hasLesson": bool(goal.get("lesson")),
                }
            )
        return stage_index

    def _normalize_goal(self, goal: dict[str, Any], position: int) -> tuple[dict[str, Any], bool]:
        changed = False
        normalized = dict(goal)

        stage_number = normalized.get("stageNumber")
        if not isinstance(stage_number, int):
            try:
                stage_number = int(re.search(r"(\d+)$", normalized.get("id", "")).group(1))  # type: ignore[union-attr]
            except Exception:
                stage_number = position
            normalized["stageNumber"] = stage_number
            changed = True

        if "stageLabel" not in normalized:
            normalized["stageLabel"] = f"阶段 {stage_number}"
            changed = True

        for key in ("summary", "outcome", "estimatedTime"):
            if key not in normalized:
                normalized[key] = ""
                changed = True

        for key in ("prerequisites", "tasks", "deliverables"):
            if not isinstance(normalized.get(key), list):
                normalized[key] = []
                changed = True

        if "lessonStatus" not in normalized:
            normalized["lessonStatus"] = "ready" if normalized.get("lesson") else "idle"
            changed = True

        if "imageStatus" not in normalized:
            lesson = normalized.get("lesson") or {}
            image_status = lesson.get("image", {}).get("status") if isinstance(lesson, dict) else None
            normalized["imageStatus"] = image_status or "idle"
            changed = True

        return normalized, changed

    def _document_is_modern(self, document: Any) -> bool:
        if not isinstance(document, dict):
            return False
        if "introBlocks" not in document:
            return False

        sections = document.get("sections")
        if not isinstance(sections, list):
            return False

        for section in sections:
            if not isinstance(section, dict) or "blocks" not in section:
                return False
            for subsection in section.get("subsections", []) or []:
                if not isinstance(subsection, dict) or "blocks" not in subsection:
                    return False

        return True

    def _refresh_document_from_markdown(self, markdown_path: str | None, parsed_path: str | None = None) -> dict[str, Any] | None:
        if not markdown_path:
            return None

        resolved_markdown_path = self.root / markdown_path
        if not resolved_markdown_path.exists():
            return None

        parsed_document = parse_markdown_document(resolved_markdown_path.read_text(encoding="utf-8"))
        if parsed_path:
            self._write_json(self.root / parsed_path, parsed_document)
        return parsed_document

    def _normalize_project_payload(self, project_payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        changed = False
        normalized = dict(project_payload)

        if "repositoryVersion" not in normalized:
            normalized["repositoryVersion"] = 2
            changed = True

        if "brief" not in normalized or not isinstance(normalized["brief"], dict):
            normalized["brief"] = {"initialMessage": ""}
            changed = True

        folder_name = normalized.get("folderName")
        if not folder_name:
            folder_name = f"{slugify(normalized.get('topic', 'learning-project'))}-{normalized['id']}"
            normalized["folderName"] = folder_name
            changed = True

        if "research" not in normalized or not isinstance(normalized["research"], dict):
            normalized["research"] = self._default_research()
            changed = True
        else:
            merged_research = self._default_research()
            merged_research.update(normalized["research"])
            normalized["research"] = merged_research

        if "plan" not in normalized or not isinstance(normalized["plan"], dict):
            normalized["plan"] = self._default_plan()
            changed = True
        else:
            merged_plan = self._default_plan()
            merged_plan.update(normalized["plan"])
            normalized["plan"] = merged_plan

        if "artifacts" not in normalized or not isinstance(normalized["artifacts"], dict):
            normalized["artifacts"] = self._default_artifacts(folder_name)
            changed = True
        else:
            merged_artifacts = self._default_artifacts(folder_name)
            merged_artifacts.update(normalized["artifacts"])
            normalized["artifacts"] = merged_artifacts

        if "generation" not in normalized or not isinstance(normalized["generation"], dict):
            normalized["generation"] = self._default_generation()
            changed = True
        else:
            merged_generation = self._default_generation()
            merged_generation.update(normalized["generation"])
            preview_payload = normalized["generation"].get("preview")
            if isinstance(preview_payload, dict):
                merged_preview = dict(merged_generation["preview"])
                merged_preview.update(preview_payload)
                merged_generation["preview"] = merged_preview
            normalized["generation"] = merged_generation

        goals = normalized.get("goals") or []
        normalized_goals: list[dict[str, Any]] = []
        for position, goal in enumerate(goals, start=1):
            goal_payload, goal_changed = self._normalize_goal(goal, position)
            normalized_goals.append(goal_payload)
            changed = changed or goal_changed
        normalized["goals"] = normalized_goals

        if not self._document_is_modern(normalized["research"].get("document")):
            refreshed_research_document = self._refresh_document_from_markdown(
                normalized["research"].get("markdownPath"),
                normalized["research"].get("parsedPath"),
            )
        else:
            refreshed_research_document = None
        if refreshed_research_document:
            normalized["research"]["document"] = refreshed_research_document
            changed = True

        if not self._document_is_modern(normalized["plan"].get("document")):
            refreshed_plan_document = self._refresh_document_from_markdown(
                normalized["plan"].get("markdownPath"),
                normalized["plan"].get("parsedPath"),
            )
        else:
            refreshed_plan_document = None
        if refreshed_plan_document:
            normalized["plan"]["document"] = refreshed_plan_document
            changed = True

        for goal_payload in normalized_goals:
            lesson = goal_payload.get("lesson")
            if not isinstance(lesson, dict):
                continue

            if "images" not in lesson and lesson.get("image"):
                lesson["images"] = [lesson["image"]]
                changed = True

            detail = lesson.get("detail")
            if isinstance(detail, dict) and "images" not in detail and detail.get("image"):
                detail["images"] = [detail["image"]]
                changed = True

            if self._document_is_modern(lesson.get("document")):
                continue
            refreshed_lesson_document = self._refresh_document_from_markdown(
                lesson.get("markdownPath"),
                lesson.get("parsedPath"),
            )
            if not refreshed_lesson_document:
                continue

            lesson["document"] = refreshed_lesson_document
            detail = lesson.get("detail")
            if isinstance(detail, dict):
                detail["document"] = refreshed_lesson_document
                stage_detail_path = lesson.get("stageDetailPath")
                if stage_detail_path:
                    self._write_json(self.root / stage_detail_path, detail)
            changed = True

        if not normalized["plan"]["stageIndex"] and normalized_goals:
            normalized["plan"]["stageIndex"] = self._build_stage_index(normalized_goals)
            changed = True

        if not normalized["artifacts"]["stageIndexPath"] and normalized["plan"]["stageIndexPath"]:
            normalized["artifacts"]["stageIndexPath"] = normalized["plan"]["stageIndexPath"]
            changed = True

        if not normalized["artifacts"]["sourcesPath"] and normalized["research"]["sourcesPath"]:
            normalized["artifacts"]["sourcesPath"] = normalized["research"]["sourcesPath"]
            changed = True

        return normalized, changed

    def _project_path(self, project_id: str) -> Path:
        index_payload = self._load_index()
        for project in index_payload["projects"]:
            if project["id"] == project_id:
                return self.data_root / project["folderName"]
        raise FileNotFoundError(f"Project {project_id} was not found.")

    def _load_project(self, project_id: str) -> dict[str, Any]:
        project_path = self._project_path(project_id) / "project.json"
        payload = self._read_json(project_path)
        normalized, changed = self._normalize_project_payload(payload)
        if changed:
            self._write_json(project_path, normalized)
        return normalized

    def _save_project(self, project_payload: dict[str, Any]) -> None:
        normalized, _ = self._normalize_project_payload(project_payload)
        project_path = self._project_path(normalized["id"]) / "project.json"
        self._write_json(project_path, normalized)
        self._sync_index_summary(normalized)
        self._publish_project(normalized)

    def _project_event_payload(self, project_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "project": project_payload,
            "llm": self.llm.describe(),
        }

    def _publish_project(self, project_payload: dict[str, Any]) -> None:
        event_payload = self._project_event_payload(project_payload)
        project_id = project_payload["id"]
        with self._subscriber_lock:
            subscribers = list(self._project_subscribers.get(project_id, set()))

        for subscriber in subscribers:
            try:
                if subscriber.full():
                    subscriber.get_nowait()
                subscriber.put_nowait(event_payload)
            except queue.Empty:
                subscriber.put_nowait(event_payload)
            except queue.Full:
                continue

    def subscribe_project(self, project_id: str) -> queue.Queue[dict[str, Any]]:
        project_payload = self._load_project(project_id)
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=8)
        subscriber.put_nowait(self._project_event_payload(project_payload))
        with self._subscriber_lock:
            self._project_subscribers.setdefault(project_id, set()).add(subscriber)
        return subscriber

    def unsubscribe_project(self, project_id: str, subscriber: queue.Queue[dict[str, Any]]) -> None:
        with self._subscriber_lock:
            subscribers = self._project_subscribers.get(project_id)
            if not subscribers:
                return
            subscribers.discard(subscriber)
            if not subscribers:
                self._project_subscribers.pop(project_id, None)

    def _sync_index_summary(self, project_payload: dict[str, Any]) -> None:
        index_payload = self._load_index()
        for project in index_payload["projects"]:
            if project["id"] == project_payload["id"]:
                project.update(
                    {
                        "topic": project_payload["topic"],
                        "updatedAt": project_payload["updatedAt"],
                        "researchStatus": project_payload["research"]["status"],
                        "planStatus": project_payload["plan"]["status"],
                        "generationActive": project_payload["generation"]["active"],
                        "generationAction": project_payload["generation"]["action"],
                        "goalsCount": len(project_payload["goals"]),
                        "lessonReadyCount": len(
                            [goal for goal in project_payload["goals"] if goal.get("lessonStatus") == "ready"]
                        ),
                        "sourceCount": project_payload["research"].get("sourceCount", 0),
                        "lastAssistantMessage": next(
                            (
                                message["content"]
                                for message in reversed(project_payload["conversation"])
                                if message["role"] == "assistant"
                            ),
                            "",
                        ),
                    }
                )
                break
        self._save_index(index_payload)

    def _load_library_config(self, library_id: str) -> dict[str, Any]:
        library = next((item for item in self.library_sources if item["id"] == library_id), None)
        if library is None:
            raise FileNotFoundError(f"Library {library_id} was not found.")
        if not library["path"].exists():
            raise FileNotFoundError(f"Library path {library['path']} was not found.")
        return library

    def _build_library_document(self, library_root: Path, file_path: Path) -> dict[str, Any]:
        raw = file_path.read_text(encoding="utf-8")
        parsed = parse_markdown_document(raw)
        relative_path = file_path.relative_to(library_root).as_posix()
        slug = relative_path.removesuffix(".md").replace("/", "--").lower()
        return {
            "slug": slug,
            "title": parsed["title"],
            "relativePath": relative_path,
            "path": self._to_relative_path(file_path),
            "isOverview": file_path.name.lower() == "readme.md",
            "document": parsed,
        }

    def _build_library_payload(self, library_config: dict[str, Any], *, include_documents: bool) -> dict[str, Any]:
        library_root = library_config["path"]
        markdown_files = sorted(
            library_root.rglob("*.md"),
            key=lambda path: (path.name.lower() != "readme.md", path.relative_to(library_root).as_posix().lower()),
        )
        documents = [self._build_library_document(library_root, path) for path in markdown_files]
        overview = next((item for item in documents if item["isOverview"]), documents[0] if documents else None)
        summary = (
            overview["document"]["intro"][0]
            if overview and overview["document"].get("intro")
            else library_config["description"]
        )

        payload = {
            "id": library_config["id"],
            "title": library_config["title"],
            "description": summary,
            "sourcePath": self._to_relative_path(library_root),
            "documentCount": len(documents),
            "activeDocumentSlug": overview["slug"] if overview else None,
            "documents": [
                {
                    "slug": document["slug"],
                    "title": document["title"],
                    "relativePath": document["relativePath"],
                    "isOverview": document["isOverview"],
                }
                for document in documents
            ],
        }

        if include_documents:
            payload["documents"] = documents

        return payload

    def _write_generation_metadata(
        self,
        path: Path,
        kind: str,
        *,
        status: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "kind": kind,
            "status": status,
            "generatedAt": utc_now(),
            "configured": self.llm.configured,
            "model": self.llm.model,
            "imageModel": self.llm.image_model,
        }
        if extra:
            payload.update(extra)
        self._write_json(path, payload)

    def _generation_step(self, step_id: str, label: str, detail: str, status: str = "pending") -> dict[str, str]:
        return {
            "id": step_id,
            "label": label,
            "detail": detail,
            "status": status,
        }

    def _begin_generation(
        self,
        project_payload: dict[str, Any],
        *,
        action: str,
        title: str,
        message: str,
        steps: list[dict[str, str]],
        target_goal_id: str | None = None,
    ) -> None:
        now = utc_now()
        project_payload["generation"] = {
            "active": True,
            "action": action,
            "title": title,
            "message": message,
            "targetGoalId": target_goal_id,
            "startedAt": now,
            "updatedAt": now,
            "completedAt": None,
            "steps": steps,
            "preview": {
                "kind": action,
                "title": title,
                "markdown": "",
                "document": None,
                "status": "pending",
                "updatedAt": now,
            },
        }
        project_payload["updatedAt"] = now

    def _update_generation(
        self,
        project_payload: dict[str, Any],
        *,
        message: str | None = None,
        title: str | None = None,
        action: str | None = None,
        target_goal_id: str | None = None,
        steps: list[dict[str, str]] | None = None,
        preview: dict[str, Any] | None = None,
    ) -> None:
        generation = project_payload.get("generation") or self._default_generation()
        if title is not None:
            generation["title"] = title
        if message is not None:
            generation["message"] = message
        if action is not None:
            generation["action"] = action
        if target_goal_id is not None:
            generation["targetGoalId"] = target_goal_id
        if steps is not None:
            generation["steps"] = steps
        if preview is not None:
            generation["preview"] = preview
        generation["updatedAt"] = utc_now()
        project_payload["generation"] = generation
        project_payload["updatedAt"] = generation["updatedAt"]

    def _set_generation_step(
        self,
        project_payload: dict[str, Any],
        step_id: str,
        *,
        status: str,
        detail: str | None = None,
        message: str | None = None,
    ) -> None:
        generation = project_payload.get("generation") or self._default_generation()
        steps = generation.get("steps") or []
        for step in steps:
            if step.get("id") == step_id:
                step["status"] = status
                if detail is not None:
                    step["detail"] = detail
                break
        self._update_generation(project_payload, message=message, steps=steps)

    def _set_generation_preview(
        self,
        project_payload: dict[str, Any],
        *,
        kind: str,
        title: str,
        markdown: str,
        status: str = "streaming",
    ) -> None:
        generation = project_payload.get("generation") or self._default_generation()
        preview_payload = dict(generation.get("preview") or {})
        parsed_document = None
        cleaned_markdown = markdown.strip()

        if cleaned_markdown:
            try:
                parsed_document = parse_markdown_document(cleaned_markdown)
            except Exception:
                parsed_document = None

            if parsed_document and parsed_document.get("title") == "Untitled":
                parsed_document["title"] = title

        preview_payload.update(
            {
                "kind": kind,
                "title": title,
                "markdown": markdown,
                "document": parsed_document,
                "status": status,
                "updatedAt": utc_now(),
            }
        )
        self._update_generation(project_payload, preview=preview_payload)

    def _finish_generation(self, project_payload: dict[str, Any], *, message: str = "") -> None:
        generation = project_payload.get("generation") or self._default_generation()
        now = utc_now()
        preview_payload = dict(generation.get("preview") or {})
        if preview_payload.get("markdown"):
            preview_payload["status"] = "complete"
            preview_payload["updatedAt"] = now
        generation.update(
            {
                "active": False,
                "message": message,
                "updatedAt": now,
                "completedAt": now,
                "preview": preview_payload,
            }
        )
        project_payload["generation"] = generation
        project_payload["updatedAt"] = now

    def _fail_generation(self, project_payload: dict[str, Any], *, message: str) -> None:
        generation = project_payload.get("generation") or self._default_generation()
        now = utc_now()
        preview_payload = dict(generation.get("preview") or {})
        if preview_payload:
            preview_payload["status"] = "error"
            preview_payload["updatedAt"] = now
        generation.update(
            {
                "active": False,
                "message": message,
                "updatedAt": now,
                "completedAt": now,
                "preview": preview_payload,
            }
        )
        for step in generation.get("steps", []):
            if step.get("status") == "running":
                step["status"] = "error"
        project_payload["generation"] = generation
        project_payload["updatedAt"] = now

    def _persist_stage_index(self, project_payload: dict[str, Any], project_dir: Path) -> None:
        stage_index = self._build_stage_index(project_payload["goals"])
        stage_index_path = project_dir / "stage_index.json"
        self._write_json(stage_index_path, stage_index)
        project_payload["plan"]["stageIndex"] = stage_index
        project_payload["plan"]["stageIndexPath"] = self._to_relative_path(stage_index_path)
        project_payload["artifacts"]["stageIndexPath"] = self._to_relative_path(stage_index_path)

    def _project_stage_directory(self, project_dir: Path, goal_id: str) -> Path:
        return project_dir / "stages" / goal_id

    def _stream_markdown(
        self,
        builder: Any,
        *,
        on_flush: Any | None = None,
    ) -> str:
        stream_state = {
            "markdown": "",
            "last_flush": 0.0,
        }

        def flush(force: bool = False) -> None:
            markdown = stream_state["markdown"]
            if not markdown.strip():
                return

            now = time.monotonic()
            if not force and now - stream_state["last_flush"] < 0.35:
                return

            if on_flush is not None:
                on_flush(markdown, force=force)
            stream_state["last_flush"] = now

        def on_delta(delta: str) -> None:
            if not delta:
                return
            stream_state["markdown"] += delta
            if (
                "\n\n" in delta
                or "\n## " in delta
                or "\n### " in delta
                or len(delta) >= 48
                or time.monotonic() - stream_state["last_flush"] >= 0.45
            ):
                flush()

        final_markdown = builder(on_delta if self.llm.configured else None)
        if final_markdown and final_markdown != stream_state["markdown"]:
            stream_state["markdown"] = final_markdown
        flush(force=True)
        return final_markdown

    def _generate_with_streaming_preview(
        self,
        project_payload: dict[str, Any],
        *,
        kind: str,
        title: str,
        step_id: str,
        detail_prefix: str,
        builder: Any,
    ) -> str:
        stream_state = {
            "markdown": "",
            "last_flush": 0.0,
        }

        def flush(force: bool = False) -> None:
            markdown = stream_state["markdown"]
            if not markdown.strip():
                return

            now = time.monotonic()
            if not force and now - stream_state["last_flush"] < 0.35:
                return

            self._set_generation_preview(
                project_payload,
                kind=kind,
                title=title,
                markdown=markdown,
                status="streaming",
            )
            self._set_generation_step(
                project_payload,
                step_id,
                status="running",
                detail=f"{detail_prefix} · 已流式写入 {max(len(markdown.strip()), 1)} 字",
            )
            self._save_project(project_payload)
            stream_state["last_flush"] = now

        def on_delta(delta: str) -> None:
            if not delta:
                return
            stream_state["markdown"] += delta
            if (
                "\n\n" in delta
                or "\n## " in delta
                or "\n### " in delta
                or len(delta) >= 48
                or time.monotonic() - stream_state["last_flush"] >= 0.45
            ):
                flush()

        final_markdown = builder(on_delta if self.llm.configured else None)
        if final_markdown and final_markdown != stream_state["markdown"]:
            stream_state["markdown"] = final_markdown
        flush(force=True)
        return final_markdown

    def list_projects(self) -> dict[str, Any]:
        index_payload = self._load_index()
        return {
            "projects": index_payload["projects"],
            "llm": self.llm.describe(),
        }

    def list_libraries(self) -> dict[str, Any]:
        libraries = [
            self._build_library_payload(library_config, include_documents=False)
            for library_config in self.library_sources
            if library_config["path"].exists()
        ]
        return {"libraries": libraries}

    def get_library(self, library_id: str) -> dict[str, Any]:
        library_config = self._load_library_config(library_id)
        return {"library": self._build_library_payload(library_config, include_documents=True)}

    def create_project(self, topic: str, initial_message: str) -> dict[str, Any]:
        project_id = uuid.uuid4().hex[:12]
        folder_name = f"{slugify(topic)}-{project_id}"
        project_dir = self.data_root / folder_name
        (project_dir / "stages").mkdir(parents=True, exist_ok=False)
        (project_dir / "meta").mkdir(parents=True, exist_ok=True)

        created_at = utc_now()
        user_message = {
            "id": uuid.uuid4().hex[:12],
            "role": "user",
            "content": initial_message,
            "createdAt": created_at,
        }
        assistant_message = {
            "id": uuid.uuid4().hex[:12],
            "role": "assistant",
            "content": self.llm.reply_in_chat(topic, [user_message]),
            "createdAt": utc_now(),
        }

        project_payload = {
            "id": project_id,
            "repositoryVersion": 2,
            "folderName": folder_name,
            "topic": topic,
            "createdAt": created_at,
            "updatedAt": utc_now(),
            "brief": {
                "initialMessage": initial_message,
                "primaryObjective": "frontend-product-experience",
            },
            "conversation": [user_message, assistant_message],
            "research": self._default_research(),
            "plan": self._default_plan(),
            "generation": self._default_generation(),
            "goals": [],
            "artifacts": self._default_artifacts(folder_name),
        }

        self._write_json(project_dir / "project.json", project_payload)

        index_payload = self._load_index()
        index_payload["projects"].insert(
            0,
            {
                "id": project_id,
                "folderName": folder_name,
                "topic": topic,
                "createdAt": created_at,
                "updatedAt": project_payload["updatedAt"],
                "researchStatus": "idle",
                "planStatus": "idle",
                "generationActive": False,
                "generationAction": None,
                "goalsCount": 0,
                "lessonReadyCount": 0,
                "sourceCount": 0,
                "lastAssistantMessage": assistant_message["content"],
            },
        )
        self._save_index(index_payload)
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict[str, Any]:
        project_payload = self._load_project(project_id)
        return {
            "project": project_payload,
            "llm": self.llm.describe(),
        }

    def append_message(self, project_id: str, content: str) -> dict[str, Any]:
        project_payload = self._load_project(project_id)
        project_payload["conversation"].append(
            {
                "id": uuid.uuid4().hex[:12],
                "role": "user",
                "content": content,
                "createdAt": utc_now(),
            }
        )
        assistant_reply = self.llm.reply_in_chat(project_payload["topic"], project_payload["conversation"])
        project_payload["conversation"].append(
            {
                "id": uuid.uuid4().hex[:12],
                "role": "assistant",
                "content": assistant_reply,
                "createdAt": utc_now(),
            }
        )
        project_payload["updatedAt"] = utc_now()
        self._save_project(project_payload)
        return self.get_project(project_id)

    def generate_research(self, project_id: str) -> dict[str, Any]:
        project_payload = self._load_project(project_id)
        self._begin_generation(
            project_payload,
            action="research",
            title="正在研究主题资料",
            message="正在联网搜集相关资料，并整理成稳定的研究文档。",
            steps=[
                self._generation_step("collect", "搜集资料", "正在抓取主题相关资料。", status="running"),
                self._generation_step("structure", "整理文档", "等待研究材料返回。"),
            ],
        )
        project_payload["research"]["status"] = "running"
        self._save_project(project_payload)

        try:
            project_dir = self._project_path(project_id)
            research_markdown = self._generate_with_streaming_preview(
                project_payload,
                kind="research",
                title=project_payload["generation"]["title"],
                step_id="collect",
                detail_prefix="正在整理研究草稿",
                builder=lambda on_delta: build_research_markdown(
                    project_payload["topic"],
                    project_payload["brief"]["initialMessage"],
                    self.llm,
                    on_delta=on_delta,
                ),
            )
            parsed_document = parse_markdown_document(research_markdown)
            sources = extract_markdown_links(research_markdown)

            markdown_path = project_dir / "research.md"
            parsed_path = project_dir / "research.parsed.json"
            sources_path = project_dir / "sources.json"
            metadata_path = project_dir / "meta" / "research.generation.json"

            markdown_path.write_text(research_markdown, encoding="utf-8")
            self._write_json(parsed_path, parsed_document)
            self._write_json(sources_path, sources)

            self._set_generation_step(
                project_payload,
                "collect",
                status="complete",
                detail=f"已提取 {len(sources)} 条资料来源。",
                message="研究资料已返回，正在整理结构化文档。",
            )
            self._set_generation_step(
                project_payload,
                "structure",
                status="running",
                detail="正在保存 research.md、sources.json 与解析结果。",
            )
            project_payload["research"] = {
                "status": "running",
                "markdownPath": self._to_relative_path(markdown_path),
                "parsedPath": self._to_relative_path(parsed_path),
                "sourcesPath": self._to_relative_path(sources_path),
                "metadataPath": self._to_relative_path(metadata_path),
                "sourceCount": len(sources),
                "sources": sources,
                "document": parsed_document,
            }
            project_payload["artifacts"]["sourcesPath"] = self._to_relative_path(sources_path)
            self._save_project(project_payload)

            self._write_generation_metadata(
                metadata_path,
                "research",
                status="ready",
                extra={
                    "topic": project_payload["topic"],
                    "sourceCount": len(sources),
                    "mode": "web-search-or-llm" if self.llm.configured else "local-template",
                },
            )

            project_payload["research"]["status"] = "ready"
            project_payload["conversation"].append(
                {
                    "id": uuid.uuid4().hex[:12],
                    "role": "assistant",
                    "content": f"研究整理已经完成，当前主题提取了 {len(sources)} 条来源，并写入了 sources.json。接下来可以生成阶段式学习路径。",
                    "createdAt": utc_now(),
                }
            )
            self._set_generation_step(
                project_payload,
                "structure",
                status="complete",
                detail="研究文档与来源列表已保存。",
            )
            self._finish_generation(project_payload, message="研究完成，研究文档与来源列表已同步更新。")
            self._save_project(project_payload)
            return self.get_project(project_id)
        except Exception as error:
            failed_payload = self._load_project(project_id)
            failed_payload["research"]["status"] = "error"
            self._fail_generation(failed_payload, message=f"研究生成失败：{error}")
            self._save_project(failed_payload)
            raise

    def generate_plan(self, project_id: str) -> dict[str, Any]:
        project_payload = self._load_project(project_id)
        if project_payload["research"]["document"] is None:
            raise ValueError("Research must be generated before creating a plan.")

        self._begin_generation(
            project_payload,
            action="plan",
            title="正在拆分阶段计划",
            message="正在把研究结果整理成阶段式学习路径。",
            steps=[
                self._generation_step("outline", "生成阶段结构", "正在根据研究结果拆分阶段。", status="running"),
                self._generation_step("sync", "同步项目文件", "等待阶段计划生成完成。"),
            ],
        )
        project_payload["plan"]["status"] = "running"
        self._save_project(project_payload)

        try:
            project_dir = self._project_path(project_id)
            research_markdown = (self.root / project_payload["research"]["markdownPath"]).read_text(encoding="utf-8")
            plan_markdown = self._generate_with_streaming_preview(
                project_payload,
                kind="plan",
                title=project_payload["generation"]["title"],
                step_id="outline",
                detail_prefix="正在生成阶段计划草稿",
                builder=lambda on_delta: build_plan_markdown(
                    project_payload["topic"],
                    research_markdown,
                    self.llm,
                    on_delta=on_delta,
                ),
            )
            goals = extract_goals_from_plan(plan_markdown)
            if not goals:
                plan_markdown = build_fallback_plan_markdown(project_payload["topic"])
                goals = extract_goals_from_plan(plan_markdown)

            parsed_document = parse_markdown_document(plan_markdown)
            markdown_path = project_dir / "learning_plan.md"
            parsed_path = project_dir / "learning_plan.parsed.json"
            metadata_path = project_dir / "meta" / "plan.generation.json"

            markdown_path.write_text(plan_markdown, encoding="utf-8")
            self._write_json(parsed_path, parsed_document)

            self._set_generation_step(
                project_payload,
                "outline",
                status="complete",
                detail=f"已拆分出 {len(goals)} 个阶段。",
                message="阶段结构已生成，正在同步项目文件。",
            )
            self._set_generation_step(
                project_payload,
                "sync",
                status="running",
                detail="正在保存 learning_plan.md 与阶段索引。",
            )
            project_payload["plan"] = {
                "status": "running",
                "markdownPath": self._to_relative_path(markdown_path),
                "parsedPath": self._to_relative_path(parsed_path),
                "stageIndexPath": None,
                "metadataPath": self._to_relative_path(metadata_path),
                "stageIndex": [],
                "document": parsed_document,
            }
            project_payload["goals"] = goals
            self._persist_stage_index(project_payload, project_dir)
            self._save_project(project_payload)

            self._write_generation_metadata(
                metadata_path,
                "plan",
                status="ready",
                extra={
                    "topic": project_payload["topic"],
                    "stageCount": len(goals),
                    "mode": "llm" if self.llm.configured else "local-template",
                },
            )

            project_payload["plan"]["status"] = "ready"
            project_payload["conversation"].append(
                {
                    "id": uuid.uuid4().hex[:12],
                    "role": "assistant",
                    "content": f"学习路径已经生成，共拆成 {len(goals)} 个阶段。你现在可以打开任一阶段，按需懒生成讲解和图示。",
                    "createdAt": utc_now(),
                }
            )
            self._set_generation_step(
                project_payload,
                "sync",
                status="complete",
                detail="阶段计划、阶段索引与项目状态已同步。",
            )
            self._finish_generation(project_payload, message="阶段计划已更新，现在可以逐阶段展开学习。")
            self._save_project(project_payload)
            return self.get_project(project_id)
        except Exception as error:
            failed_payload = self._load_project(project_id)
            failed_payload["plan"]["status"] = "error"
            self._fail_generation(failed_payload, message=f"阶段计划生成失败：{error}")
            self._save_project(failed_payload)
            raise

    def _placeholder_stage_images(self, project_payload: dict[str, Any], goal: dict[str, Any]) -> list[dict[str, Any]]:
        stage_label = goal.get("stageLabel") or f"阶段 {goal.get('stageNumber') or ''}".strip()
        return [
            {
                "status": "pending",
                "path": None,
                "url": None,
                "mimeType": None,
                "prompt": "",
                "metadataPath": None,
                "title": f"{stage_label} 图示 {index + 1}",
                "caption": "图示会和正文并行生成，并在完成后自动刷新到当前阶段。",
                "alt": f"{project_payload['topic']} | {goal.get('title', stage_label)} | 图示 {index + 1}",
            }
            for index in range(STAGE_IMAGE_COUNT)
        ]

    def _build_stage_detail_payload_multi(
        self,
        project_payload: dict[str, Any],
        goal: dict[str, Any],
        parsed_document: dict[str, Any],
        *,
        lesson_markdown_path: Path,
        lesson_parsed_path: Path,
        detail_path: Path,
        generation_path: Path,
        image_payloads: list[dict[str, Any]],
        image_meta_paths: list[Path],
    ) -> dict[str, Any]:
        stage_label = goal.get("stageLabel") or f"阶段 {goal.get('stageNumber') or ''}".strip()
        normalized_images: list[dict[str, Any]] = []

        for index, image_payload in enumerate(image_payloads):
            raw_path = image_payload.get("path")
            resolved_path = raw_path if isinstance(raw_path, Path) else Path(raw_path) if raw_path else None
            relative_path = self._to_relative_path(resolved_path) if resolved_path else None
            meta_path = image_meta_paths[index] if index < len(image_meta_paths) else None
            normalized_images.append(
                {
                    "status": image_payload.get("status", "pending"),
                    "path": relative_path,
                    "url": f"/api/projects/{project_payload['id']}/goals/{goal['id']}/images/{index}"
                    if relative_path
                    else None,
                    "mimeType": image_payload.get("mimeType"),
                    "prompt": image_payload.get("prompt", ""),
                    "metadataPath": self._to_relative_path(meta_path) if meta_path else None,
                    "variantId": image_payload.get("variantId"),
                    "title": image_payload.get("title") or f"{stage_label} 图示 {index + 1}",
                    "caption": image_payload.get("caption") or "图示会与正文一起展示，便于边读边理解。",
                    "alt": image_payload.get("alt")
                    or f"{project_payload['topic']} | {goal.get('title', stage_label)} | 图示 {index + 1}",
                    "revisedPrompt": image_payload.get("revisedPrompt", ""),
                    "fallbackReason": image_payload.get("fallbackReason", ""),
                }
            )

        if not normalized_images:
            normalized_images = self._placeholder_stage_images(project_payload, goal)

        primary_image = normalized_images[0]
        return {
            "id": goal["id"],
            "stageNumber": goal.get("stageNumber"),
            "stageLabel": goal.get("stageLabel"),
            "title": goal.get("title", ""),
            "summary": goal.get("summary", ""),
            "outcome": goal.get("outcome", ""),
            "estimatedTime": goal.get("estimatedTime", ""),
            "prerequisites": goal.get("prerequisites", []),
            "tasks": goal.get("tasks", []),
            "deliverables": goal.get("deliverables", []),
            "document": parsed_document,
            "files": {
                "lessonMarkdownPath": self._to_relative_path(lesson_markdown_path),
                "lessonParsedPath": self._to_relative_path(lesson_parsed_path),
                "stageDetailPath": self._to_relative_path(detail_path),
                "generationPath": self._to_relative_path(generation_path),
                "imagePath": primary_image.get("path"),
                "imageMetadataPath": primary_image.get("metadataPath"),
                "imagePaths": [image.get("path") for image in normalized_images],
                "imageMetadataPaths": [image.get("metadataPath") for image in normalized_images],
            },
            "image": primary_image,
            "images": normalized_images,
            "generatedAt": utc_now(),
        }

    def _update_goal_lesson_state(
        self,
        project_payload: dict[str, Any],
        goal_id: str,
        *,
        lesson_status: str | None = None,
        image_status: str | None = None,
        document: dict[str, Any] | None = None,
        detail: dict[str, Any] | None = None,
        lesson_paths: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
    ) -> None:
        for goal_item in project_payload["goals"]:
            if goal_item["id"] != goal_id:
                continue

            if lesson_status is not None:
                goal_item["lessonStatus"] = lesson_status
            if image_status is not None:
                goal_item["imageStatus"] = image_status

            lesson_payload = dict(goal_item.get("lesson") or {})
            if lesson_paths:
                lesson_payload.update(lesson_paths)
            if document is not None:
                lesson_payload["document"] = document
            if detail is not None:
                lesson_payload["detail"] = detail
            if images is not None:
                lesson_payload["images"] = images
                if images:
                    lesson_payload["image"] = images[0]

            if lesson_payload:
                goal_item["lesson"] = lesson_payload
            break

    def _update_batch_generation_state(
        self,
        project_payload: dict[str, Any],
        *,
        final: bool = False,
        message: str | None = None,
    ) -> None:
        generation = project_payload.get("generation") or {}
        if generation.get("action") != "lesson-batch":
            return

        goals = project_payload.get("goals") or []
        total_goals = len(goals)
        started_goals = [
            goal
            for goal in goals
            if goal.get("lessonStatus") in {"running", "ready", "error"}
            or goal.get("imageStatus") in {"running", "ready", "error"}
        ]
        content_ready = [goal for goal in goals if goal.get("lessonStatus") == "ready"]
        content_errors = [goal for goal in goals if goal.get("lessonStatus") == "error"]
        running_goals = [
            goal for goal in goals if goal.get("lessonStatus") == "running" or goal.get("imageStatus") == "running"
        ]

        image_items = [
            image
            for goal in goals
            for image in ((goal.get("lesson") or {}).get("images") or [])
        ]
        total_images = max(total_goals * STAGE_IMAGE_COUNT, len(image_items))
        image_ready_count = len([image for image in image_items if image.get("status") in {"ready", "fallback"}])
        image_error_count = len([image for image in image_items if image.get("status") == "error"])

        preview_lines = [
            "# 批量生成进度",
            "",
            "## 当前概况",
            f"- 已启动阶段：{len(started_goals)}/{total_goals}",
            f"- 正文完成：{len(content_ready)}/{total_goals}",
            f"- 图片完成：{image_ready_count}/{total_images}",
        ]
        if running_goals:
            preview_lines.extend(["", "## 正在生成"])
            preview_lines.extend(
                f"- {(goal.get('stageLabel') or goal.get('title') or goal['id'])}：{goal.get('title', '')}"
                for goal in running_goals[:4]
            )
        elif final:
            preview_lines.extend(["", "## 状态", "- 所有阶段已完成并同步到项目中。"])

        steps = [
            self._generation_step(
                "dispatch",
                "启动并发任务",
                f"已启动 {len(started_goals)}/{total_goals} 个阶段的生成任务。",
                status="complete" if started_goals or final else "running",
            ),
            self._generation_step(
                "content",
                "并发生成阶段正文",
                f"已完成 {len(content_ready)}/{total_goals} 个阶段正文，当前并发中 {len(running_goals)} 个阶段。",
                status="complete" if len(content_ready) == total_goals and total_goals else "running",
            ),
            self._generation_step(
                "image",
                "并发生成讲解图示",
                f"已完成 {image_ready_count}/{total_images} 张图示。"
                + (f" 失败 {image_error_count} 张。" if image_error_count else ""),
                status="complete" if image_ready_count >= total_images and total_images else "running",
            ),
            self._generation_step(
                "sync",
                "同步阶段结果",
                "阶段详情、图示与索引会随着生成过程持续刷新。",
                status="complete" if final else "running",
            ),
        ]

        self._update_generation(
            project_payload,
            message=message
            or (
                "多个阶段正在并发生成，阶段卡片会分段刷新。"
                if not final
                else "多个阶段的正文与图示已全部生成，可直接逐阶段阅读。"
            ),
            steps=steps,
            preview={
                "kind": "lesson-batch",
                "title": generation.get("title") or "正在并发生成多个阶段",
                "markdown": "\n".join(preview_lines),
                "document": parse_markdown_document("\n".join(preview_lines)),
                "status": "complete" if final else "streaming",
                "updatedAt": utc_now(),
            },
        )

    def _build_stage_detail_payload(
        self,
        project_payload: dict[str, Any],
        goal: dict[str, Any],
        parsed_document: dict[str, Any],
        *,
        lesson_markdown_path: Path,
        lesson_parsed_path: Path,
        detail_path: Path,
        generation_path: Path,
        image_payload: dict[str, Any],
        image_meta_path: Path,
    ) -> dict[str, Any]:
        image_path = image_payload.get("path")
        image_relative_path = self._to_relative_path(image_path) if image_path else None
        return {
            "id": goal["id"],
            "stageNumber": goal.get("stageNumber"),
            "stageLabel": goal.get("stageLabel"),
            "title": goal.get("title", ""),
            "summary": goal.get("summary", ""),
            "outcome": goal.get("outcome", ""),
            "estimatedTime": goal.get("estimatedTime", ""),
            "prerequisites": goal.get("prerequisites", []),
            "tasks": goal.get("tasks", []),
            "deliverables": goal.get("deliverables", []),
            "document": parsed_document,
            "files": {
                "lessonMarkdownPath": self._to_relative_path(lesson_markdown_path),
                "lessonParsedPath": self._to_relative_path(lesson_parsed_path),
                "stageDetailPath": self._to_relative_path(detail_path),
                "generationPath": self._to_relative_path(generation_path),
                "imagePath": image_relative_path,
                "imageMetadataPath": self._to_relative_path(image_meta_path),
            },
            "image": {
                "status": image_payload["status"],
                "path": image_relative_path,
                "url": f"/api/projects/{project_payload['id']}/goals/{goal['id']}/image" if image_relative_path else None,
                "mimeType": image_payload.get("mimeType"),
                "prompt": image_payload.get("prompt", ""),
                "metadataPath": self._to_relative_path(image_meta_path),
                "alt": f"{project_payload['topic']}｜{goal['title']} 图示",
            },
            "images": [
                {
                    "status": image_payload["status"],
                    "path": image_relative_path,
                    "url": f"/api/projects/{project_payload['id']}/goals/{goal['id']}/image"
                    if image_relative_path
                    else None,
                    "mimeType": image_payload.get("mimeType"),
                    "prompt": image_payload.get("prompt", ""),
                    "metadataPath": self._to_relative_path(image_meta_path),
                    "alt": f"{project_payload['topic']} | {goal['title']}",
                }
            ],
            "generatedAt": utc_now(),
        }

    def _generate_goal_lesson(self, project_id: str, goal_id: str, *, batch_mode: bool = False) -> None:
        project_lock = self._get_project_lock(project_id)
        with project_lock:
            project_payload = self._load_project(project_id)
            goal = next((item for item in project_payload["goals"] if item["id"] == goal_id), None)
            if goal is None:
                raise FileNotFoundError(f"Goal {goal_id} was not found.")
            if project_payload["research"]["document"] is None or project_payload["plan"]["document"] is None:
                raise ValueError("Research and plan must exist before generating a lesson.")

            project_dir = self._project_path(project_id)
            if not batch_mode:
                self._begin_generation(
                    project_payload,
                    action="lesson",
                    title=f"正在生成「{goal['title']}」",
                    message="先分段生成正文，再并发生成多张讲解图示。",
                    target_goal_id=goal_id,
                    steps=[
                        self._generation_step("content", "生成阶段正文", "正在整理本阶段的知识讲解。", status="running"),
                        self._generation_step("image", "并发生成图示", "等待正文生成完成。"),
                    ],
                )

            placeholder_images = self._placeholder_stage_images(project_payload, goal)
            self._update_goal_lesson_state(
                project_payload,
                goal_id,
                lesson_status="running",
                image_status="pending",
                document=(goal.get("lesson") or {}).get("document"),
                images=placeholder_images,
            )
            if batch_mode:
                self._update_batch_generation_state(
                    project_payload,
                    message=f"正在并发生成多个阶段，当前推进：{goal.get('title', goal_id)}",
                )
            self._persist_stage_index(project_payload, project_dir)
            self._save_project(project_payload)

            research_markdown_path = project_payload["research"]["markdownPath"]
            plan_markdown_path = project_payload["plan"]["markdownPath"]
            topic = project_payload["topic"]
            generation_title = project_payload["generation"]["title"]

        stage_dir = self._project_stage_directory(project_dir, goal_id)
        assets_dir = stage_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        lesson_markdown_path = stage_dir / "lesson.md"
        lesson_parsed_path = stage_dir / "lesson.parsed.json"
        detail_path = stage_dir / "stage_detail.json"
        generation_path = stage_dir / "generation.json"
        image_meta_paths = [assets_dir / f"diagram-{index + 1:02d}.meta.json" for index in range(STAGE_IMAGE_COUNT)]

        research_markdown = (self.root / research_markdown_path).read_text(encoding="utf-8")
        plan_markdown = (self.root / plan_markdown_path).read_text(encoding="utf-8")

        def push_live_markdown(markdown: str, *, force: bool = False) -> None:
            try:
                parsed_document = parse_markdown_document(markdown)
            except Exception:
                return

            with project_lock:
                latest = self._load_project(project_id)
                latest_goal = next((item for item in latest["goals"] if item["id"] == goal_id), None)
                if latest_goal is None:
                    return

                current_images = ((latest_goal.get("lesson") or {}).get("images") or placeholder_images)
                self._update_goal_lesson_state(
                    latest,
                    goal_id,
                    lesson_status="running",
                    image_status="pending",
                    document=parsed_document,
                    images=current_images,
                )

                if not batch_mode:
                    self._set_generation_preview(
                        latest,
                        kind="lesson",
                        title=generation_title,
                        markdown=markdown,
                        status="complete" if force else "streaming",
                    )
                    self._set_generation_step(
                        latest,
                        "content",
                        status="running",
                        detail=f"正在分段写入「{goal['title']}」的阶段正文。",
                    )
                else:
                    self._update_batch_generation_state(
                        latest,
                        message=f"正在并发生成多个阶段，当前推进：{goal.get('title', goal_id)}",
                    )

                self._persist_stage_index(latest, project_dir)
                self._save_project(latest)

        try:
            lesson_markdown = self._stream_markdown(
                lambda on_delta: build_lesson_markdown(
                    topic,
                    goal,
                    research_markdown,
                    plan_markdown,
                    self.llm,
                    on_delta=on_delta,
                ),
                on_flush=push_live_markdown,
            )
            parsed_document = parse_markdown_document(lesson_markdown)
            lesson_markdown_path.write_text(lesson_markdown, encoding="utf-8")
            self._write_json(lesson_parsed_path, parsed_document)

            raw_image_payloads = [
                {
                    "status": "pending",
                    "path": None,
                    "mimeType": None,
                    "prompt": "",
                    "title": placeholder["title"],
                    "caption": placeholder["caption"],
                }
                for placeholder in placeholder_images
            ]
            lesson_paths = {
                "markdownPath": self._to_relative_path(lesson_markdown_path),
                "parsedPath": self._to_relative_path(lesson_parsed_path),
                "stageDetailPath": self._to_relative_path(detail_path),
                "generationPath": self._to_relative_path(generation_path),
            }
            partial_stage_detail = self._build_stage_detail_payload_multi(
                project_payload,
                goal,
                parsed_document,
                lesson_markdown_path=lesson_markdown_path,
                lesson_parsed_path=lesson_parsed_path,
                detail_path=detail_path,
                generation_path=generation_path,
                image_payloads=raw_image_payloads,
                image_meta_paths=image_meta_paths,
            )
            self._write_json(detail_path, partial_stage_detail)
            self._write_generation_metadata(
                generation_path,
                "stage-lesson",
                status="running",
                extra={
                    "goalId": goal_id,
                    "stageTitle": goal["title"],
                    "phase": "content-ready",
                    "imageStatus": "running",
                    "imageCount": STAGE_IMAGE_COUNT,
                },
            )

            with project_lock:
                latest = self._load_project(project_id)
                self._update_goal_lesson_state(
                    latest,
                    goal_id,
                    lesson_status="ready",
                    image_status="running",
                    document=parsed_document,
                    detail=partial_stage_detail,
                    lesson_paths=lesson_paths,
                    images=partial_stage_detail["images"],
                )
                if not batch_mode:
                    self._set_generation_step(
                        latest,
                        "content",
                        status="complete",
                        detail="阶段正文已生成，正在并发补充讲解图示。",
                        message="阶段正文已写入，现在开始并发生成图示。",
                    )
                    self._set_generation_step(
                        latest,
                        "image",
                        status="running",
                        detail=f"正在生成 {STAGE_IMAGE_COUNT} 张图示。",
                    )
                else:
                    self._update_batch_generation_state(
                        latest,
                        message=f"正在为「{goal['title']}」补充并发图示。",
                    )
                self._persist_stage_index(latest, project_dir)
                self._save_project(latest)

            image_state_lock = threading.Lock()

            def persist_image_result(index: int, image_payload: dict[str, Any]) -> None:
                with image_state_lock:
                    raw_image_payloads[index] = image_payload
                    self._write_json(
                        image_meta_paths[index],
                        {
                            "status": image_payload.get("status", "pending"),
                            "model": image_payload.get("model"),
                            "mimeType": image_payload.get("mimeType"),
                            "prompt": image_payload.get("prompt", ""),
                            "revisedPrompt": image_payload.get("revisedPrompt", ""),
                            "fallbackReason": image_payload.get("fallbackReason", ""),
                            "generatedAt": utc_now(),
                        },
                    )
                    live_stage_detail = self._build_stage_detail_payload_multi(
                        project_payload,
                        goal,
                        parsed_document,
                        lesson_markdown_path=lesson_markdown_path,
                        lesson_parsed_path=lesson_parsed_path,
                        detail_path=detail_path,
                        generation_path=generation_path,
                        image_payloads=raw_image_payloads,
                        image_meta_paths=image_meta_paths,
                    )
                    self._write_json(detail_path, live_stage_detail)

                with project_lock:
                    latest = self._load_project(project_id)
                    self._update_goal_lesson_state(
                        latest,
                        goal_id,
                        lesson_status="ready",
                        image_status="running",
                        document=parsed_document,
                        detail=live_stage_detail,
                        lesson_paths=lesson_paths,
                        images=live_stage_detail["images"],
                    )
                    completed_images = len(
                        [
                            payload
                            for payload in raw_image_payloads
                            if payload.get("status") in {"ready", "fallback"}
                        ]
                    )
                    if not batch_mode:
                        self._set_generation_step(
                            latest,
                            "image",
                            status="running",
                            detail=f"已完成 {completed_images}/{STAGE_IMAGE_COUNT} 张图示。",
                        )
                    else:
                        self._update_batch_generation_state(
                            latest,
                            message=f"正在为「{goal['title']}」补充并发图示。",
                        )
                    self._persist_stage_index(latest, project_dir)
                    self._save_project(latest)

            final_image_payloads = self.llm.generate_stage_diagrams(
                topic,
                goal,
                lesson_markdown,
                assets_dir,
                image_count=STAGE_IMAGE_COUNT,
                on_result=persist_image_result,
            )

            final_stage_detail = self._build_stage_detail_payload_multi(
                project_payload,
                goal,
                parsed_document,
                lesson_markdown_path=lesson_markdown_path,
                lesson_parsed_path=lesson_parsed_path,
                detail_path=detail_path,
                generation_path=generation_path,
                image_payloads=final_image_payloads,
                image_meta_paths=image_meta_paths,
            )
            self._write_json(detail_path, final_stage_detail)
            self._write_generation_metadata(
                generation_path,
                "stage-lesson",
                status="ready",
                extra={
                    "goalId": goal_id,
                    "stageTitle": goal["title"],
                    "imageStatus": "ready",
                    "imageCount": len(final_image_payloads),
                },
            )

            with project_lock:
                latest = self._load_project(project_id)
                self._update_goal_lesson_state(
                    latest,
                    goal_id,
                    lesson_status="ready",
                    image_status="ready",
                    document=parsed_document,
                    detail=final_stage_detail,
                    lesson_paths=lesson_paths,
                    images=final_stage_detail["images"],
                )
                if not batch_mode:
                    latest["conversation"].append(
                        {
                            "id": uuid.uuid4().hex[:12],
                            "role": "assistant",
                            "content": f"「{goal['title']}」的阶段讲解与多张图示已经生成完成，可直接阅读。",
                            "createdAt": utc_now(),
                        }
                    )
                    self._set_generation_step(
                        latest,
                        "image",
                        status="complete",
                        detail=f"{len(final_image_payloads)} 张图示已全部生成并写入阶段详情。",
                    )
                    self._finish_generation(latest, message="阶段讲解、公式与图示都已同步完成。")
                else:
                    self._update_batch_generation_state(
                        latest,
                        message=f"已完成「{goal['title']}」的正文与图示生成。",
                    )
                self._persist_stage_index(latest, project_dir)
                self._save_project(latest)
        except Exception as error:
            with project_lock:
                failed = self._load_project(project_id)
                failed_goal = next((item for item in failed["goals"] if item["id"] == goal_id), None)
                has_document = bool((failed_goal or {}).get("lesson", {}).get("document")) if failed_goal else False
                self._update_goal_lesson_state(
                    failed,
                    goal_id,
                    lesson_status="ready" if has_document else "error",
                    image_status="error",
                )
                if not batch_mode:
                    self._fail_generation(failed, message=f"阶段生成失败：{error}")
                else:
                    self._update_batch_generation_state(
                        failed,
                        message=f"阶段「{goal.get('title', goal_id)}」生成失败：{error}",
                    )
                self._persist_stage_index(failed, self._project_path(project_id))
                self._save_project(failed)
            raise

    def generate_all_lessons(self, project_id: str) -> dict[str, Any]:
        project_lock = self._get_project_lock(project_id)
        with project_lock:
            project_payload = self._load_project(project_id)
            if project_payload["research"]["document"] is None or project_payload["plan"]["document"] is None:
                raise ValueError("Research and plan must exist before generating lessons.")
            if not project_payload["goals"]:
                raise ValueError("Plan must contain at least one stage before generating lessons.")

            self._begin_generation(
                project_payload,
                action="lesson-batch",
                title="正在并发生成多个阶段",
                message="多个阶段的正文与图示会并发生成，并持续刷新到页面中。",
                steps=[
                    self._generation_step("dispatch", "启动并发任务", "正在分配阶段生成任务。", status="running"),
                    self._generation_step("content", "并发生成阶段正文", "等待阶段任务启动。"),
                    self._generation_step("image", "并发生成讲解图示", "等待正文生成完成。"),
                    self._generation_step("sync", "同步阶段结果", "阶段详情会随着生成过程持续落盘。"),
                ],
            )
            for goal in project_payload["goals"]:
                placeholder_images = self._placeholder_stage_images(project_payload, goal)
                existing_lesson = dict(goal.get("lesson") or {})
                existing_detail = dict(existing_lesson.get("detail") or {})
                goal["lessonStatus"] = "idle"
                goal["imageStatus"] = "idle"
                if existing_lesson:
                    existing_lesson["images"] = placeholder_images
                    existing_lesson["image"] = placeholder_images[0]
                    if existing_detail:
                        existing_detail["images"] = placeholder_images
                        existing_detail["image"] = placeholder_images[0]
                        existing_lesson["detail"] = existing_detail
                    goal["lesson"] = existing_lesson
            self._update_batch_generation_state(project_payload)
            self._persist_stage_index(project_payload, self._project_path(project_id))
            self._save_project(project_payload)
            goal_ids = [goal["id"] for goal in project_payload["goals"]]

        failures: list[tuple[str, str]] = []
        with ThreadPoolExecutor(max_workers=min(MAX_STAGE_GENERATION_WORKERS, len(goal_ids))) as executor:
            future_map = {
                executor.submit(self._generate_goal_lesson, project_id, goal_id, batch_mode=True): goal_id
                for goal_id in goal_ids
            }
            for future, goal_id in list(future_map.items()):
                try:
                    future.result()
                except Exception as error:  # noqa: BLE001 - surface partial failure after all workers finish
                    failures.append((goal_id, str(error)))

        with project_lock:
            latest = self._load_project(project_id)
            if failures:
                self._update_batch_generation_state(
                    latest,
                    final=True,
                    message=f"批量生成已完成，但有 {len(failures)} 个阶段失败，可单独重试。",
                )
                latest["generation"]["active"] = False
                latest["generation"]["completedAt"] = utc_now()
                latest["generation"]["updatedAt"] = latest["generation"]["completedAt"]
            else:
                latest["conversation"].append(
                    {
                        "id": uuid.uuid4().hex[:12],
                        "role": "assistant",
                        "content": f"全部 {len(goal_ids)} 个阶段的正文与多图讲解已经并发生成完成，可逐阶段查看。",
                        "createdAt": utc_now(),
                    }
                )
                self._update_batch_generation_state(latest, final=True)
                self._finish_generation(latest, message="全部阶段的正文、公式与图示都已生成完成。")
            self._persist_stage_index(latest, self._project_path(project_id))
            self._save_project(latest)

        return self.get_project(project_id)

    def generate_lesson(self, project_id: str, goal_id: str) -> dict[str, Any]:
        self._generate_goal_lesson(project_id, goal_id, batch_mode=False)
        return self.get_project(project_id)

    def get_goal_image_path(self, project_id: str, goal_id: str, image_index: int = 0) -> Path:
        project_payload = self._load_project(project_id)
        goal = next((item for item in project_payload["goals"] if item["id"] == goal_id), None)
        if goal is None:
            raise FileNotFoundError(f"Goal {goal_id} was not found.")

        lesson = goal.get("lesson") or {}
        images = lesson.get("images") or []
        if 0 <= image_index < len(images):
            image = images[image_index]
        elif image_index == 0:
            image = lesson.get("image") or {}
        else:
            image = {}
        image_path = image.get("path")
        if not image_path:
            raise FileNotFoundError(f"Goal {goal_id} does not have image #{image_index + 1} yet.")

        return self.root / image_path
