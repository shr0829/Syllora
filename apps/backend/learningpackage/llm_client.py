from __future__ import annotations

import base64
import html
import json
import textwrap
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .config import ImageChannelConfig, RuntimeConfig, load_runtime_config
from .markdown_tools import extract_markdown_links, extract_goals_from_plan, parse_markdown_document


SYSTEM_CHAT_PROMPT = """你是学习系统里的课程规划助手。你的职责不是长篇教学，而是帮助用户明确想学的主题、学习边界、阶段产出和学习节奏。
回答要求：
1. 只使用中文。
2. 语气像产品里的学习教练，直接、清晰、不空泛。
3. 如果用户目标还不够清楚，优先收束主题边界、最终产出和学习周期。
4. 不要写标题，不要写代码块。
5. 最多 3 段；如果需要列选项，只允许 1 到 3 条短编号。"""

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) LearningPackage/1.0"
)

RESEARCH_SECTION_ORDER = (
    "主题定位",
    "为什么值得学",
    "核心问题",
    "核心概念",
    "推荐资源",
    "学习风险",
    "阶段建议",
)


def _normalize_multiline(value: str) -> str:
    return textwrap.dedent(value).strip()


STAGE_DIAGRAM_VARIANTS = (
    {
        "id": "overview",
        "title": "阶段结构总览",
        "caption": "用结构化图示快速建立本阶段的概念地图、核心目标与关键产出。",
        "focus": "突出核心概念、先后关系、阶段目标与最终产出，适合先建立整体地图。",
    },
    {
        "id": "workflow",
        "title": "阶段学习流程",
        "caption": "把学习步骤、输入输出、检查点与练习路径放到同一张流程图中。",
        "focus": "突出学习步骤、输入输出、检查点和练习路径，适合边学边执行。",
    },
)


def _clean_text(value: str) -> str:
    lines = [line.rstrip() for line in value.replace("\r\n", "\n").strip().split("\n")]
    return "\n".join(lines).strip()


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _extract_output_text(payload: dict[str, Any]) -> str:
    output_text = str(payload.get("output_text") or "").strip()
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text") or content.get("value") or ""
            if text:
                chunks.append(str(text))

    return "\n".join(chunks).strip()


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks).strip()
    return ""


def _extract_responses_stream_delta(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "")
    if event_type.endswith(".delta") and isinstance(event.get("delta"), str):
        return event["delta"]
    return ""


def _extract_responses_stream_final_text(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "")
    if event_type == "response.completed":
        response = event.get("response")
        if isinstance(response, dict):
            return _extract_output_text(response)
    return ""


def _extract_chat_completions_stream_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""

    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content") or ""
            if text:
                chunks.append(str(text))
        return "".join(chunks)
    return ""


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _contains_japanese_kana(value: str) -> bool:
    return any(("\u3040" <= char <= "\u309f") or ("\u30a0" <= char <= "\u30ff") for char in value)


def _looks_garbled(value: str) -> bool:
    text = value.strip()
    if not text:
        return True

    suspicious_phrases = (
        "乱码",
        "问号",
        "message looks garbled",
        "看起来你的消息有些乱码",
        "我这边看到你的消息是乱码",
    )
    if any(phrase in text for phrase in suspicious_phrases):
        return True

    if "�" in text:
        return True

    question_count = text.count("?")
    if question_count >= 4 and question_count / max(len(text), 1) > 0.1 and not _contains_cjk(text):
        return True

    return False


def _needs_language_fallback(system_prompt: str, user_prompt: str, output: str) -> bool:
    combined_prompt = f"{system_prompt}\n{user_prompt}"
    if _looks_garbled(output):
        return True
    if _contains_cjk(combined_prompt) and _contains_japanese_kana(output):
        return True
    if "中文" in combined_prompt and not _contains_cjk(output):
        return True
    return False


def _find_section(document: dict[str, Any], *titles: str) -> dict[str, Any] | None:
    normalized = {title.strip() for title in titles}
    for section in document.get("sections", []):
        if section.get("title", "").strip() in normalized:
            return section
    return None


def _section_to_paragraphs(section: dict[str, Any] | None) -> list[str]:
    if section is None:
        return []
    parts: list[str] = []
    parts.extend([paragraph.strip() for paragraph in section.get("paragraphs", []) if paragraph.strip()])
    return _dedupe_preserve(parts)


def _section_to_bullets(section: dict[str, Any] | None) -> list[str]:
    if section is None:
        return []
    bullets = [bullet.strip() for bullet in section.get("bullets", []) if bullet.strip()]
    if bullets:
        return _dedupe_preserve(bullets)
    return _dedupe_preserve(_section_to_paragraphs(section))


def _render_paragraph_block(paragraphs: list[str], fallback: str) -> str:
    cleaned = _dedupe_preserve(paragraphs)
    if not cleaned:
        cleaned = [fallback]
    return "\n\n".join(cleaned)


def _render_bullet_block(items: list[str], fallback: list[str]) -> str:
    cleaned = _dedupe_preserve(items)
    if not cleaned:
        cleaned = fallback
    return "\n".join(f"- {item}" for item in cleaned)


def _normalize_goal(goal: dict[str, Any], stage_number: int) -> dict[str, Any]:
    title = str(goal.get("title") or f"阶段 {stage_number}").strip()
    summary = str(goal.get("summary") or "").strip() or f"围绕“{title}”完成本阶段最关键的理解与实践动作。"
    outcome = str(goal.get("outcome") or "").strip() or f"能够独立完成“{title}”对应的最小产出。"
    estimated_time = str(goal.get("estimatedTime") or "").strip() or "1 周"

    prerequisites = _dedupe_preserve([str(item).strip() for item in goal.get("prerequisites", []) if str(item).strip()])
    tasks = _dedupe_preserve([str(item).strip() for item in goal.get("tasks", []) if str(item).strip()])
    deliverables = _dedupe_preserve([str(item).strip() for item in goal.get("deliverables", []) if str(item).strip()])

    if not prerequisites:
        prerequisites = ["无特殊前置要求，建议先理解上一个阶段的核心概念。"] if stage_number > 1 else ["无"]
    if not tasks:
        tasks = [
            f"梳理“{title}”的关键概念与边界。",
            f"完成“{title}”对应的最小练习。",
            f"记录本阶段的卡点与下一步动作。",
        ]
    if not deliverables:
        deliverables = [f"一份与“{title}”对应的阶段产出记录。"]

    return {
        "id": goal.get("id") or f"goal-{stage_number:03d}",
        "stageNumber": stage_number,
        "stageLabel": f"阶段 {stage_number}",
        "title": title,
        "summary": summary,
        "outcome": outcome,
        "estimatedTime": estimated_time,
        "prerequisites": prerequisites,
        "tasks": tasks,
        "deliverables": deliverables,
        "lessonStatus": goal.get("lessonStatus", "idle"),
        "imageStatus": goal.get("imageStatus", "idle"),
    }


def _render_canonical_research_markdown(topic: str, raw: str) -> str:
    document = parse_markdown_document(_clean_text(raw))
    links = extract_markdown_links(raw)

    positioning = _render_paragraph_block(
        _section_to_paragraphs(_find_section(document, "主题定位")),
        f"围绕“{topic}”建立清晰的学习边界、应用场景和最终产出预期。",
    )
    why_learn = _render_paragraph_block(
        _section_to_paragraphs(_find_section(document, "为什么值得学", "为什么学")),
        f"“{topic}”兼具概念理解与实际落地价值，适合用阶段化方式系统学习。",
    )
    core_questions = _render_bullet_block(
        _section_to_bullets(_find_section(document, "核心问题")),
        [
            f"“{topic}”的最小知识边界是什么？",
            "学完后应该能独立完成什么结果？",
            "哪些概念必须先掌握，哪些内容可以后补？",
        ],
    )
    core_concepts = _render_bullet_block(
        _section_to_bullets(_find_section(document, "核心概念")),
        [
            "先建立主题定义与应用场景。",
            "再梳理关键概念、工具与方法之间的关系。",
            "最后把概念映射到可执行的学习动作与阶段产出。",
        ],
    )
    resource_lines = [f"- [{item['title']}]({item['url']})" for item in links]
    if not resource_lines:
        resource_lines = [
            "- 暂未提取到真实资源链接，请重新生成研究内容。",
        ]
    risks = _render_bullet_block(
        _section_to_bullets(_find_section(document, "学习风险", "常见风险")),
        [
            "容易一开始就堆工具，而没有先收束主题边界。",
            "如果没有阶段产出，很难判断自己是否真正掌握。",
        ],
    )
    stage_advice = _render_bullet_block(
        _section_to_bullets(_find_section(document, "阶段建议", "学习建议")),
        [
            "先完成主题定位与术语梳理。",
            "再设计分阶段路线与每阶段产出。",
            "最后按阶段生成讲解页与图示资源。",
        ],
    )

    blocks = [
        "# 主题研究",
        "## 主题定位",
        positioning,
        "## 为什么值得学",
        why_learn,
        "## 核心问题",
        core_questions,
        "## 核心概念",
        core_concepts,
        "## 推荐资源",
        "\n".join(resource_lines),
        "## 学习风险",
        risks,
        "## 阶段建议",
        stage_advice,
    ]
    return "\n\n".join(blocks).strip()


def _render_canonical_plan_markdown(topic: str, goals: list[dict[str, Any]]) -> str:
    normalized_goals = [_normalize_goal(goal, index) for index, goal in enumerate(goals, start=1)]
    stage_blocks: list[str] = []

    for goal in normalized_goals:
        prerequisites = "\n".join(f"  - {item}" for item in goal["prerequisites"])
        tasks = "\n".join(f"  - {item}" for item in goal["tasks"])
        deliverables = "\n".join(f"  - {item}" for item in goal["deliverables"])
        stage_blocks.append(
            _normalize_multiline(
                f"""
                ### 阶段 {goal["stageNumber"]}｜{goal["title"]}
                - 摘要：{goal["summary"]}
                - 完成标志：{goal["outcome"]}
                - 预计时长：{goal["estimatedTime"]}
                - 前置知识：
                {prerequisites}
                - 学习动作：
                {tasks}
                - 阶段产出：
                {deliverables}
                """
            )
        )

    blocks = [
        "# 学习路径计划",
        "## 学习目标",
        f"围绕“{topic}”建立一个从主题边界、核心概念到阶段实践的完整学习闭环，并在每个阶段保留可检查的产出。",
        "## 建议节奏",
        "建议按“收束目标 → 建立结构 → 动手实践 → 复盘扩展”的节奏推进；每完成一个阶段，就沉淀一份明确产出，再进入下一阶段。",
        "## 阶段概览",
        "\n\n".join(stage_blocks),
    ]
    return "\n\n".join(blocks).strip()


def _repair_plan_markdown(topic: str, raw: str, llm: "LLMClient") -> str:
    repair_system_prompt = _normalize_multiline(
        """
        你是 Markdown 结构修复器。你的任务不是扩展内容，而是把已有学习计划整理成稳定可解析的固定模板。
        只输出 Markdown，不要解释，不要代码块，不要额外标题。
        必须严格使用以下结构：
        # 学习路径计划
        ## 学习目标
        ## 建议节奏
        ## 阶段概览
        ### 阶段 1｜标题
        - 摘要：
        - 完成标志：
        - 预计时长：
        - 前置知识：
          - ...
        - 学习动作：
          - ...
        - 阶段产出：
          - ...

        必须输出 4 到 6 个阶段。
        """
    )
    repair_user_prompt = (
        f"学习主题：{topic}\n"
        "请把下面这份已有内容整理成严格模板，保留原意，补齐缺失字段：\n\n"
        f"{raw}"
    )
    return llm.generate_markdown(repair_system_prompt, repair_user_prompt, temperature=0.2)


def _normalize_chat_reply(reply: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in _clean_text(reply).split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return "先告诉我你最想学的主题、最终想做到什么，以及你准备投入多久。"
    return "\n\n".join(paragraphs[:3])


def _render_core_explanation_blocks(goal: dict[str, Any], section: dict[str, Any] | None) -> str:
    subsections = section.get("subsections", []) if section else []
    blocks: list[str] = []

    def render_block(block: dict[str, Any]) -> str:
        block_type = block.get("type")
        if block_type == "paragraph":
            return str(block.get("text") or "").strip()
        if block_type == "list":
            marker = "1." if block.get("ordered") else "-"
            return "\n".join(f"{marker} {str(item).strip()}" for item in block.get("items", []) if str(item).strip())
        if block_type == "table":
            headers = [str(item).strip() for item in block.get("headers", [])]
            rows = block.get("rows", []) or []
            if not headers:
                return ""
            separator = " | ".join(["---"] * len(headers))
            row_lines = [
                f"| {' | '.join(str(cell).strip() for cell in row)} |"
                for row in rows
                if any(str(cell).strip() for cell in row)
            ]
            return "\n".join(
                [
                    f"| {' | '.join(headers)} |",
                    f"| {separator} |",
                    *row_lines,
                ]
            )
        return ""

    if subsections:
        for index, subsection in enumerate(subsections, start=1):
            title = subsection.get("title", "").strip() or f"知识点 {index}"
            if "｜" not in title and "|" not in title and "知识点" not in title:
                title = f"知识点 {index}｜{title}"
            elif "知识点" not in title:
                title = f"知识点 {index}｜{title}"

            content_lines: list[str] = []
            for block in subsection.get("blocks") or []:
                rendered = render_block(block)
                if rendered:
                    content_lines.append(rendered)
            if not content_lines:
                content_lines.append(goal["summary"])

            blocks.append(f"### {title}\n" + "\n\n".join(content_lines))

    if blocks:
        return "\n\n".join(blocks)

    return _normalize_multiline(
        f"""
        ### 知识点 1｜阶段作用
        {goal["summary"]}

        ### 知识点 2｜完成标准
        {goal["outcome"]}

        ### 知识点 3｜关键动作
        - {goal["tasks"][0]}
        - {goal["tasks"][1] if len(goal["tasks"]) > 1 else goal["deliverables"][0]}
        """
    )


def _render_canonical_lesson_markdown(topic: str, goal: dict[str, Any], raw: str) -> str:
    normalized_goal = _normalize_goal(goal, int(goal.get("stageNumber") or 1))
    document = parse_markdown_document(_clean_text(raw))

    goal_section = _find_section(document, "本阶段目标", "阶段目标", "学习目标")
    mastery_section = _find_section(document, "你会掌握什么", "你将掌握什么", "阶段收获")
    core_section = _find_section(document, "核心讲解", "核心内容", "讲解")
    steps_section = _find_section(document, "操作步骤", "步骤", "行动步骤")
    diagram_section = _find_section(document, "图示说明", "图示", "图示建议")
    practice_section = _find_section(document, "练习", "练习任务")
    checklist_section = _find_section(document, "自查清单", "检查清单", "自检清单")

    goal_block = _render_paragraph_block(
        _section_to_paragraphs(goal_section),
        f"本阶段围绕“{normalized_goal['title']}”展开，目标是把关键概念和实际动作连接起来，并产出可检查结果。",
    )
    mastery_block = _render_bullet_block(
        _section_to_bullets(mastery_section),
        [
            f"理解“{normalized_goal['title']}”在整条学习路径中的位置。",
            "知道本阶段必须完成的关键动作。",
            "能用阶段产出来判断自己是否完成本阶段。",
        ],
    )
    core_block = _render_core_explanation_blocks(normalized_goal, core_section)
    steps_block = _render_bullet_block(
        _section_to_bullets(steps_section),
        normalized_goal["tasks"],
    )
    diagram_block = _render_paragraph_block(
        _section_to_paragraphs(diagram_section),
        "图示应突出本阶段的核心概念、执行顺序、关键动作与最终产出之间的关系。",
    )
    practice_block = _render_bullet_block(
        _section_to_bullets(practice_section),
        [
            f"用自己的话复述“{normalized_goal['title']}”的目标与边界。",
            "完成一轮最小练习，并记录过程中的问题。",
            "把阶段产出整理成可复查的文档或脚本。",
        ],
    )
    checklist_block = _render_bullet_block(
        _section_to_bullets(checklist_section),
        [
            f"我是否能解释“{normalized_goal['title']}”要解决什么问题？",
            "我是否完成了本阶段的关键动作？",
            "我是否留下了可以复查的阶段产出？",
        ],
    )

    blocks = [
        "# 阶段学习详情",
        "## 本阶段目标",
        goal_block,
        "## 你会掌握什么",
        mastery_block,
        "## 核心讲解",
        core_block,
        "## 操作步骤",
        steps_block,
        "## 图示说明",
        diagram_block,
        "## 练习",
        practice_block,
        "## 自查清单",
        checklist_block,
    ]
    return "\n\n".join(blocks).strip()


def _build_placeholder_diagram_svg(topic: str, goal: dict[str, Any], prompt: str) -> str:
    summary = goal.get("summary") or "将复杂主题拆成可执行的学习动作。"
    bullets = goal.get("tasks") or goal.get("deliverables") or ["识别关键概念", "建立阶段动作", "形成阶段产出"]
    bullets = bullets[:3]

    bullet_markup = []
    y_positions = [330, 500, 670]
    colors = ["#F5E7B8", "#E7E1D2", "#E9DAB5"]

    for index, bullet in enumerate(bullets):
        y = y_positions[index]
        color = colors[index % len(colors)]
        bullet_markup.append(
            f"""
            <g transform="translate(820 {y})">
              <rect x="0" y="0" width="560" height="110" rx="28" fill="{color}" opacity="0.96"/>
              <text x="36" y="46" font-size="24" font-family="Inter, Arial, sans-serif" fill="#191714">{html.escape(goal.get("stageLabel") or f"步骤 {index + 1}")}</text>
              <text x="36" y="80" font-size="32" font-family="Inter, Arial, sans-serif" font-weight="700" fill="#111111">{html.escape(str(bullet))}</text>
            </g>
            """
        )

    return _normalize_multiline(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
          <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#F7F4EE"/>
              <stop offset="55%" stop-color="#F4EFE5"/>
              <stop offset="100%" stop-color="#EDE6D7"/>
            </linearGradient>
            <linearGradient id="ink" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#191714"/>
              <stop offset="100%" stop-color="#A07B2D"/>
            </linearGradient>
          </defs>

          <rect width="1600" height="900" fill="url(#bg)"/>
          <rect x="64" y="64" width="1472" height="772" rx="36" fill="#FFFFFF" opacity="0.86" stroke="#D6C9AB"/>
          <rect x="112" y="112" width="612" height="676" rx="32" fill="#121212"/>
          <text x="160" y="210" font-size="24" font-family="Inter, Arial, sans-serif" fill="#C6B483">LearningPackage Diagram</text>
          <text x="160" y="292" font-size="62" font-family="Inter, Arial, sans-serif" font-weight="800" fill="#FFFFFF">{html.escape(goal.get("title") or "阶段讲解图示")}</text>
          <foreignObject x="160" y="340" width="500" height="180">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Inter, Arial, sans-serif;color:#E7E2D7;font-size:28px;line-height:1.5;">
              {html.escape(str(summary))}
            </div>
          </foreignObject>

          <line x1="724" y1="448" x2="820" y2="385" stroke="url(#ink)" stroke-width="6" stroke-linecap="round"/>
          <line x1="724" y1="560" x2="820" y2="555" stroke="url(#ink)" stroke-width="6" stroke-linecap="round"/>
          <line x1="724" y1="672" x2="820" y2="725" stroke="url(#ink)" stroke-width="6" stroke-linecap="round"/>

          {"".join(bullet_markup)}

          <text x="160" y="760" font-size="20" font-family="Inter, Arial, sans-serif" fill="#D8CFBB">Topic: {html.escape(topic)}</text>
          <text x="820" y="140" font-size="24" font-family="Inter, Arial, sans-serif" fill="#7B715E">Prompt</text>
          <foreignObject x="820" y="164" width="560" height="110">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Inter, Arial, sans-serif;color:#544D40;font-size:20px;line-height:1.5;">
              {html.escape(prompt)}
            </div>
          </foreignObject>
        </svg>
        """
    )


class LLMClient:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[3]
        self.runtime: RuntimeConfig = load_runtime_config(self.project_root)

        self.api_key = self.runtime.text.api_key
        self.base_url = self.runtime.text.base_url
        self.model = self.runtime.text.model
        self.review_model = self.runtime.text.review_model
        self.reasoning_effort = self.runtime.text.reasoning_effort
        self.wire_api = self.runtime.text.wire_api.lower()
        self.network_access = self.runtime.text.network_access.lower()
        self.disable_response_storage = self.runtime.text.disable_response_storage

        self.image_model = self.runtime.image.model
        self.image_channels = self.runtime.image.channels
        self.image_provider_type = self.runtime.image.primary_channel.provider_type
        self.image_base_url = self.runtime.image.primary_channel.base_url

    @property
    def configured(self) -> bool:
        return self.runtime.text.configured

    @property
    def image_configured(self) -> bool:
        return self.runtime.image.configured

    def _iter_configured_image_channels(self) -> list[ImageChannelConfig]:
        return [channel for channel in self.image_channels if channel.configured]

    def describe(self) -> dict[str, Any]:
        return self.runtime.describe()

    def _post_json(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        timeout: int = 120,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        resolved_base_url = (base_url or self.base_url).rstrip("/")
        resolved_api_key = (api_key or self.api_key).strip()
        if not resolved_api_key:
            raise RuntimeError("LLM client is not configured.")

        url = f"{resolved_base_url}/{endpoint.lstrip('/')}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {resolved_api_key}",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "Accept-Charset": "utf-8",
                "User-Agent": DEFAULT_USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM request failed with HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"LLM request failed: {error.reason}") from error

        return json.loads(raw)

    def _stream_json_events(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        timeout: int = 180,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> Iterable[dict[str, Any]]:
        resolved_base_url = (base_url or self.base_url).rstrip("/")
        resolved_api_key = (api_key or self.api_key).strip()
        if not resolved_api_key:
            raise RuntimeError("LLM client is not configured.")

        url = f"{resolved_base_url}/{endpoint.lstrip('/')}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {resolved_api_key}",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "text/event-stream",
                "Accept-Charset": "utf-8",
                "Cache-Control": "no-cache",
                "User-Agent": DEFAULT_USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                event_name = ""
                data_lines: list[str] = []
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="ignore")

                    if line in {"\n", "\r\n"}:
                        if not data_lines:
                            event_name = ""
                            continue

                        raw_data = "\n".join(data_lines).strip()
                        data_lines = []
                        if raw_data == "[DONE]":
                            break
                        if not raw_data:
                            event_name = ""
                            continue

                        try:
                            payload_item = json.loads(raw_data)
                        except json.JSONDecodeError:
                            payload_item = {"type": event_name or "message", "data": raw_data}
                        else:
                            if event_name and isinstance(payload_item, dict) and not payload_item.get("type"):
                                payload_item["type"] = event_name

                        if isinstance(payload_item, dict):
                            yield payload_item
                        event_name = ""
                        continue

                    stripped = line.strip()
                    if not stripped or stripped.startswith(":"):
                        continue
                    if stripped.startswith("event:"):
                        event_name = stripped.split(":", 1)[1].strip()
                        continue
                    if stripped.startswith("data:"):
                        data_lines.append(stripped.split(":", 1)[1].lstrip())
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM stream failed with HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"LLM stream failed: {error.reason}") from error

    def _download_binary(self, url: str, *, timeout: int = 240) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "*/*",
                "User-Agent": DEFAULT_USER_AGENT,
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()

    def _build_responses_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "temperature": temperature,
        }

        if self.disable_response_storage:
            payload["store"] = False

        if self.runtime.text.applied_reasoning_effort:
            payload["reasoning"] = {"effort": self.runtime.text.applied_reasoning_effort}

        if tools:
            payload["tools"] = tools

        return payload

    def _stream_via_responses(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        on_delta: Callable[[str], None],
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        payload = self._build_responses_payload(system_prompt, user_prompt, temperature=temperature, tools=tools)
        payload["stream"] = True

        aggregated: list[str] = []
        for event in self._stream_json_events("responses", payload, timeout=240):
            event_type = str(event.get("type") or "")
            if event_type == "error":
                raise RuntimeError(str(event.get("message") or "Responses stream failed."))

            delta = _extract_responses_stream_delta(event)
            if delta:
                aggregated.append(delta)
                on_delta(delta)
                continue

            final_text = _extract_responses_stream_final_text(event)
            if final_text:
                combined = "".join(aggregated)
                if final_text.startswith(combined):
                    missing = final_text[len(combined) :]
                    if missing:
                        aggregated.append(missing)
                        on_delta(missing)
                elif not combined:
                    aggregated.append(final_text)
                    on_delta(final_text)
                return "".join(aggregated)

        content = "".join(aggregated).strip()
        if not content:
            raise RuntimeError("Responses stream returned an empty body.")
        return content

    def _generate_via_responses(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        attempts = [self._build_responses_payload(system_prompt, user_prompt, temperature=temperature, tools=tools)]

        simplified = dict(attempts[0])
        simplified.pop("temperature", None)
        simplified.pop("reasoning", None)
        if simplified != attempts[0]:
            attempts.append(simplified)

        last_error: RuntimeError | None = None
        for payload in attempts:
            try:
                data = self._post_json("responses", payload, timeout=180)
            except RuntimeError as error:
                last_error = error
                continue

            content = _extract_output_text(data)
            if content:
                return content
            last_error = RuntimeError("Responses API returned an empty body.")

        raise last_error or RuntimeError("Responses API request failed.")

    def _generate_via_chat_completions(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
    ) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._post_json("chat/completions", payload, timeout=180)
        content = _extract_chat_completion_text(data)
        if not content:
            raise RuntimeError("Chat Completions API returned an empty body.")
        return content

    def _stream_via_chat_completions(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        on_delta: Callable[[str], None],
    ) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        aggregated: list[str] = []
        for item in self._stream_json_events("chat/completions", payload, timeout=240):
            if item.get("error"):
                raise RuntimeError(str(item["error"]))

            delta = _extract_chat_completions_stream_delta(item)
            if delta:
                aggregated.append(delta)
                on_delta(delta)

        content = "".join(aggregated).strip()
        if not content:
            raise RuntimeError("Chat Completions stream returned an empty body.")
        return content

    def generate_markdown(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.6) -> str:
        if self.wire_api == "responses":
            try:
                content = self._generate_via_responses(system_prompt, user_prompt, temperature=temperature)
                if not _needs_language_fallback(system_prompt, user_prompt, content):
                    return content
            except RuntimeError:
                pass

        return self._generate_via_chat_completions(system_prompt, user_prompt, temperature=temperature)

    def generate_markdown_with_web_search(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.4,
    ) -> str:
        if self.wire_api == "responses" and self.network_access == "enabled":
            try:
                content = self._generate_via_responses(
                    system_prompt,
                    user_prompt,
                    temperature=temperature,
                    tools=[{"type": "web_search_preview"}],
                )
                if not _needs_language_fallback(system_prompt, user_prompt, content):
                    return content
            except RuntimeError:
                pass

        return self.generate_markdown(system_prompt, user_prompt, temperature=temperature)

    def stream_markdown(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        on_delta: Callable[[str], None],
        temperature: float = 0.6,
    ) -> str:
        if self.wire_api == "responses":
            try:
                content = self._stream_via_responses(
                    system_prompt,
                    user_prompt,
                    temperature=temperature,
                    on_delta=on_delta,
                )
                if not _needs_language_fallback(system_prompt, user_prompt, content):
                    return content
            except RuntimeError:
                pass

        try:
            return self._stream_via_chat_completions(
                system_prompt,
                user_prompt,
                temperature=temperature,
                on_delta=on_delta,
            )
        except RuntimeError:
            return self.generate_markdown(system_prompt, user_prompt, temperature=temperature)

    def stream_markdown_with_web_search(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        on_delta: Callable[[str], None],
        temperature: float = 0.4,
    ) -> str:
        if self.wire_api == "responses" and self.network_access == "enabled":
            try:
                content = self._stream_via_responses(
                    system_prompt,
                    user_prompt,
                    temperature=temperature,
                    on_delta=on_delta,
                    tools=[{"type": "web_search_preview"}],
                )
                if not _needs_language_fallback(system_prompt, user_prompt, content):
                    return content
            except RuntimeError:
                pass

        return self.stream_markdown(system_prompt, user_prompt, on_delta=on_delta, temperature=temperature)

    def reply_in_chat(self, project_topic: str, conversation: list[dict[str, str]]) -> str:
        if not self.configured:
            last_user_message = next(
                (message["content"] for message in reversed(conversation) if message["role"] == "user"),
                project_topic,
            )
            return (
                f"我已经记录了你的学习主题：{project_topic}。\n\n"
                f"当前还没有配置联网模型，所以我先把需求留在本地项目里：{last_user_message}。\n\n"
                "你可以继续补充目标、限制条件和最终产出，我会基于这些信息继续整理学习路径。"
            )

        transcript = "\n".join(f"{message['role']}: {message['content']}" for message in conversation[-8:])
        user_prompt = (
            f"当前学习项目主题：{project_topic}\n"
            f"最近对话：\n{transcript}\n\n"
            "请给出一条适合直接显示在学习系统聊天窗口中的中文回复。"
        )
        return _normalize_chat_reply(self.generate_markdown(SYSTEM_CHAT_PROMPT, user_prompt, temperature=0.45))

    def generate_stage_diagram(
        self,
        topic: str,
        goal: dict[str, Any],
        lesson_markdown: str,
        output_dir: Path,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt = (
            f"为学习主题“{topic}”中的“{goal.get('title', '当前阶段')}”生成一张知识图示。"
            "画面风格参考专业学习产品：浅色背景、深色正文、清晰信息层级、无 emoji。"
            f"重点内容：{goal.get('summary') or '将阶段目标拆成 2 到 3 个动作'}。"
            "请把概念关系、学习动作和阶段产出体现在图中。"
        )

        if self.image_configured:
            last_error: Exception | None = None
            payload_variants = [
                {
                    "model": self.image_model,
                    "prompt": prompt,
                    "size": "1536x1024",
                    "response_format": "b64_json",
                },
                {
                    "model": self.image_model,
                    "prompt": prompt,
                    "size": "1536x1024",
                },
            ]

            for channel in self._iter_configured_image_channels():
                for payload in payload_variants:
                    channel_payload = dict(payload)
                    channel_payload["model"] = channel.model or self.image_model
                    try:
                        data = self._post_json(
                            "images/generations",
                            channel_payload,
                            timeout=240,
                            base_url=channel.base_url,
                            api_key=channel.api_key,
                        )
                        image_item = (data.get("data") or [{}])[0]
                        if image_item.get("b64_json"):
                            image_bytes = base64.b64decode(image_item["b64_json"])
                        elif image_item.get("url"):
                            image_bytes = self._download_binary(str(image_item["url"]))
                        else:
                            raise RuntimeError(
                                f"Image payload missing b64_json/url: {json.dumps(data, ensure_ascii=False)}"
                            )

                        output_path = output_dir / "diagram.png"
                        output_path.write_bytes(image_bytes)
                        return {
                            "status": "ready",
                            "path": output_path,
                            "mimeType": "image/png",
                            "prompt": prompt,
                            "model": channel_payload["model"],
                            "providerType": channel.provider_type,
                            "baseUrl": channel.base_url,
                            "revisedPrompt": image_item.get("revised_prompt", ""),
                        }
                    except Exception as error:  # noqa: BLE001 - preserve fallback behavior
                        last_error = RuntimeError(f"[{channel.base_url}] {error}")

            output_path = output_dir / "diagram.svg"
            output_path.write_text(_build_placeholder_diagram_svg(topic, goal, prompt), encoding="utf-8")
            return {
                "status": "fallback",
                "path": output_path,
                "mimeType": "image/svg+xml",
                "prompt": prompt,
                "model": "local-svg-fallback",
                "fallbackReason": str(last_error) if last_error else "unknown image generation failure",
            }

        output_path = output_dir / "diagram.svg"
        output_path.write_text(_build_placeholder_diagram_svg(topic, goal, prompt), encoding="utf-8")
        return {
            "status": "fallback",
            "path": output_path,
            "mimeType": "image/svg+xml",
            "prompt": prompt,
            "model": "local-svg-fallback",
            "fallbackReason": "image model not configured",
        }


    def _build_stage_diagram_prompt(
        self,
        topic: str,
        goal: dict[str, Any],
        lesson_markdown: str,
        *,
        variant: dict[str, str],
    ) -> str:
        summary = goal.get("summary") or "围绕本阶段目标建立清晰、可执行的学习结构。"
        tasks = goal.get("tasks") or []
        deliverables = goal.get("deliverables") or []
        lesson_excerpt = _clean_text(lesson_markdown)[:1800]
        task_lines = "\n".join(f"- {task}" for task in tasks[:4]) or "- 提炼本阶段关键任务"
        deliverable_lines = "\n".join(f"- {item}" for item in deliverables[:3]) or "- 呈现本阶段可检查的产出"

        return _normalize_multiline(
            f"""
            请为学习主题“{topic}”中的“{goal.get('title', '当前阶段')}”生成一张中文教学图示。
            图示用途：{variant['title']}
            图示重点：{variant['focus']}

            必须覆盖：
            - 阶段摘要：{summary}
            - 关键任务：
            {task_lines}
            - 阶段产出：
            {deliverable_lines}

            视觉要求：
            1. 极简、专业、留白充足，接近高质量学习产品与文档式界面。
            2. 浅色背景、深色正文、信息层级清晰，不要卡通、不要 emoji、不要水印。
            3. 中文标注尽量简短，优先使用结构图、流程图、关系图、检查清单式布局。
            4. 如果正文涉及公式、符号、变量或数学关系，请把必要公式整洁地放入图中。

            参考正文（节选）：
            {lesson_excerpt}
            """
        )

    def _generate_stage_diagram_asset(
        self,
        topic: str,
        goal: dict[str, Any],
        *,
        prompt: str,
        output_path: Path,
        variant: dict[str, str],
    ) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.image_configured:
            last_error: Exception | None = None
            payload_variants = [
                {
                    "model": self.image_model,
                    "prompt": prompt,
                    "size": "1536x1024",
                    "response_format": "b64_json",
                },
                {
                    "model": self.image_model,
                    "prompt": prompt,
                    "size": "1536x1024",
                },
            ]

            for channel in self._iter_configured_image_channels():
                for payload in payload_variants:
                    channel_payload = dict(payload)
                    channel_payload["model"] = channel.model or self.image_model
                    try:
                        data = self._post_json(
                            "images/generations",
                            channel_payload,
                            timeout=240,
                            base_url=channel.base_url,
                            api_key=channel.api_key,
                        )
                        image_item = (data.get("data") or [{}])[0]
                        if image_item.get("b64_json"):
                            image_bytes = base64.b64decode(image_item["b64_json"])
                        elif image_item.get("url"):
                            image_bytes = self._download_binary(str(image_item["url"]))
                        else:
                            raise RuntimeError(
                                f"Image payload missing b64_json/url: {json.dumps(data, ensure_ascii=False)}"
                            )

                        ready_path = output_path.with_suffix(".png")
                        ready_path.write_bytes(image_bytes)
                        return {
                            "status": "ready",
                            "path": ready_path,
                            "mimeType": "image/png",
                            "prompt": prompt,
                            "model": channel_payload["model"],
                            "providerType": channel.provider_type,
                            "baseUrl": channel.base_url,
                            "revisedPrompt": image_item.get("revised_prompt", ""),
                            "variantId": variant["id"],
                            "title": variant["title"],
                            "caption": variant["caption"],
                        }
                    except Exception as error:  # noqa: BLE001 - preserve fallback behavior
                        last_error = RuntimeError(f"[{channel.base_url}] {error}")

            fallback_path = output_path.with_suffix(".svg")
            fallback_path.write_text(_build_placeholder_diagram_svg(topic, goal, prompt), encoding="utf-8")
            return {
                "status": "fallback",
                "path": fallback_path,
                "mimeType": "image/svg+xml",
                "prompt": prompt,
                "model": "local-svg-fallback",
                "fallbackReason": str(last_error) if last_error else "unknown image generation failure",
                "variantId": variant["id"],
                "title": variant["title"],
                "caption": variant["caption"],
            }

        fallback_path = output_path.with_suffix(".svg")
        fallback_path.write_text(_build_placeholder_diagram_svg(topic, goal, prompt), encoding="utf-8")
        return {
            "status": "fallback",
            "path": fallback_path,
            "mimeType": "image/svg+xml",
            "prompt": prompt,
            "model": "local-svg-fallback",
            "fallbackReason": "image model not configured",
            "variantId": variant["id"],
            "title": variant["title"],
            "caption": variant["caption"],
        }

    def generate_stage_diagrams(
        self,
        topic: str,
        goal: dict[str, Any],
        lesson_markdown: str,
        output_dir: Path,
        *,
        image_count: int = 2,
        on_result: Callable[[int, dict[str, Any]], None] | None = None,
    ) -> list[dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        variants = list(STAGE_DIAGRAM_VARIANTS[: max(1, image_count)])
        if len(variants) < image_count:
            variants.extend(STAGE_DIAGRAM_VARIANTS[-1:] * (image_count - len(variants)))

        def run_variant(index: int, variant: dict[str, str]) -> dict[str, Any]:
            prompt = self._build_stage_diagram_prompt(topic, goal, lesson_markdown, variant=variant)
            return self._generate_stage_diagram_asset(
                topic,
                goal,
                prompt=prompt,
                output_path=output_dir / f"diagram-{index + 1:02d}",
                variant=variant,
            )

        with ThreadPoolExecutor(max_workers=min(2, len(variants))) as executor:
            future_map = {
                executor.submit(run_variant, index, variant): index for index, variant in enumerate(variants)
            }
            results: list[dict[str, Any] | None] = [None] * len(variants)
            for future in as_completed(future_map):
                index = future_map[future]
                result = future.result()
                results[index] = result
                if on_result is not None:
                    on_result(index, result)

        return [result for result in results if result is not None]


def build_research_markdown(
    topic: str,
    brief: str,
    llm: LLMClient,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    system_prompt = _normalize_multiline(
        """
        你是学习系统里的研究助手。请围绕用户要学习的主题整理成稳定可解析的 Markdown。
        只能输出 Markdown，不能输出解释、代码块、JSON、附言。

        必须严格使用以下一级结构，不能新增或改名：
        # 主题研究
        ## 主题定位
        ## 为什么值得学
        ## 核心问题
        ## 核心概念
        ## 推荐资源
        ## 学习风险
        ## 阶段建议

        约束：
        1. 全文只使用中文。
        2. “核心问题”“核心概念”“学习风险”“阶段建议”下优先使用短 bullet。
        3. “推荐资源”必须给出至少 4 条真实 Markdown 链接，格式只能是：
           - [资源标题](https://...)
        4. 不允许出现除上述结构外的新标题。
        5. 不要输出“说明”“备注”“总结”等附加段落。
        """
    )
    user_prompt = f"学习主题：{topic}\n用户补充：{brief or '无'}"

    if llm.configured:
        raw = (
            llm.stream_markdown_with_web_search(system_prompt, user_prompt, on_delta=on_delta, temperature=0.25)
            if on_delta
            else llm.generate_markdown_with_web_search(system_prompt, user_prompt, temperature=0.25)
        )
        return _render_canonical_research_markdown(topic, raw)

    return _render_canonical_research_markdown(
        topic,
        _normalize_multiline(
            f"""
            # 主题研究

            ## 主题定位
            围绕“{topic}”建立清晰的学习边界、应用场景和最终产出预期。

            ## 为什么值得学
            这个主题兼具概念理解与实践价值，适合用阶段化方式系统推进。

            ## 核心问题
            - 这个主题的最小知识边界是什么？
            - 学完之后应该能独立完成什么结果？
            - 哪些概念必须优先掌握？

            ## 核心概念
            - 明确主题定义与应用场景。
            - 梳理关键概念与方法之间的关系。
            - 将概念转成可执行的学习动作。

            ## 推荐资源
            - 暂未提取到真实资源链接，请配置联网模型后重新生成。

            ## 学习风险
            - 容易一上来就堆工具，而没有先收束主题边界。
            - 如果没有阶段产出，很难判断自己是否真正学会。

            ## 阶段建议
            - 先完成主题定位与术语梳理。
            - 再设计分阶段路线与每阶段产出。
            - 最后按阶段生成讲解页与图示资源。
            """
        ),
    )


def build_plan_markdown(
    topic: str,
    research_markdown: str,
    llm: LLMClient,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    system_prompt = _normalize_multiline(
        """
        你是学习路径设计师。请基于研究结果输出一个稳定可解析的阶段式学习计划。
        只能输出 Markdown，不能输出解释、代码块、JSON、附言。

        必须严格使用以下结构：
        # 学习路径计划
        ## 学习目标
        ## 建议节奏
        ## 阶段概览
        ### 阶段 1｜标题
        - 摘要：
        - 完成标志：
        - 预计时长：
        - 前置知识：
          - ...
        - 学习动作：
          - ...
        - 阶段产出：
          - ...

        约束：
        1. 全文只使用中文。
        2. 必须输出 4 到 6 个阶段。
        3. 每个阶段都必须包含上述 7 个字段，字段名不能改。
        4. 不允许新增其他标题。
        5. 学习动作与阶段产出必须具体，可执行、可检查。
        """
    )
    user_prompt = f"学习主题：{topic}\n研究材料：\n{research_markdown}"

    if llm.configured:
        raw = (
            llm.stream_markdown(system_prompt, user_prompt, on_delta=on_delta, temperature=0.25)
            if on_delta
            else llm.generate_markdown(system_prompt, user_prompt, temperature=0.25)
        )
        goals = extract_goals_from_plan(raw)
        if not 4 <= len(goals) <= 6:
            repaired = _repair_plan_markdown(topic, raw, llm)
            repaired_goals = extract_goals_from_plan(repaired)
            if 4 <= len(repaired_goals) <= 6:
                goals = repaired_goals

        if 4 <= len(goals) <= 6:
            return _render_canonical_plan_markdown(topic, goals)

    fallback_goals = extract_goals_from_plan(
        _normalize_multiline(
            f"""
            # 学习路径计划

            ## 学习目标
            围绕“{topic}”建立一个从主题边界、核心概念到阶段实践的完整学习闭环。

            ## 建议节奏
            建议按“理解主题 → 建立结构 → 动手实践 → 复盘扩展”的节奏推进，每个阶段保留明确产出。

            ## 阶段概览
            ### 阶段 1｜定义主题边界
            - 摘要：明确这个主题到底学什么、不学什么。
            - 完成标志：能用自己的话说明主题边界和最终目标。
            - 预计时长：0.5 周
            - 前置知识：
              - 无
            - 学习动作：
              - 阅读研究中的主题定位与核心问题。
              - 写出自己的主题说明。
            - 阶段产出：
              - 一份 200 字以内的主题定位说明。

            ### 阶段 2｜建立概念地图
            - 摘要：把核心概念和上下游关系串成结构图。
            - 完成标志：能说明各概念之间的关系与先后顺序。
            - 预计时长：1 周
            - 前置知识：
              - 阶段 1
            - 学习动作：
              - 提取关键术语。
              - 将概念分为基础、方法、实践三层。
            - 阶段产出：
              - 一张概念结构图。

            ### 阶段 3｜完成最小实践
            - 摘要：围绕主题做一次最小可运行练习。
            - 完成标志：跑通一个可验证的小案例。
            - 预计时长：1 周
            - 前置知识：
              - 阶段 2
            - 学习动作：
              - 选择一个最小案例。
              - 跑通完整流程并记录结果。
            - 阶段产出：
              - 一份最小实践记录。

            ### 阶段 4｜复盘与扩展
            - 摘要：总结收获、识别盲区，并规划下一阶段。
            - 完成标志：形成可复用的复盘文档。
            - 预计时长：0.5 周
            - 前置知识：
              - 阶段 3
            - 学习动作：
              - 回顾研究、计划与实践内容。
              - 写出后续深化方向。
            - 阶段产出：
              - 一份复盘与下一步计划。
            """
        )
    )
    return _render_canonical_plan_markdown(topic, fallback_goals)


def build_lesson_markdown(
    topic: str,
    goal: dict[str, Any],
    research_markdown: str,
    plan_markdown: str,
    llm: LLMClient,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    system_prompt = _normalize_multiline(
        """
        你是教学内容设计师。请围绕一个具体阶段输出稳定可解析的 Markdown 教学内容。
        只能输出 Markdown，不能输出解释、代码块、JSON、附言。

        必须严格使用以下结构：
        # 阶段学习详情
        ## 本阶段目标
        ## 你会掌握什么
        ## 核心讲解
        ### 知识点 1｜标题
        ## 操作步骤
        ## 图示说明
        ## 练习
        ## 自查清单

        约束：
        1. 全文只使用中文。
        2. 不允许新增其他标题。
        3. “操作步骤”“练习”“自查清单”必须使用短 bullet。
        4. “核心讲解”下至少输出 2 个 `### 知识点 x｜标题` 子段落。
        5. 内容必须具体，避免空话。
        6. 如需对比信息，可使用标准 Markdown 表格，但每一行必须单独换行；不要输出 HTML。
        """
    )
    system_prompt += "\n" + _normalize_multiline(
        """
        7. 如果涉及数学、统计、机器学习、物理或算法推导，必须使用 `$...$` 表示行内公式，使用 `$$...$$` 表示独立公式块。
        8. 公式必须能直接嵌入 Markdown 阅读流，不要输出原始 HTML，也不要用“见图示”替代公式本身。
        """
    )
    user_prompt = (
        f"学习主题：{topic}\n"
        f"当前阶段：{json.dumps(goal, ensure_ascii=False)}\n"
        f"研究材料：\n{research_markdown}\n\n"
        f"学习计划：\n{plan_markdown}"
    )

    if llm.configured:
        raw = (
            llm.stream_markdown(system_prompt, user_prompt, on_delta=on_delta, temperature=0.3)
            if on_delta
            else llm.generate_markdown(system_prompt, user_prompt, temperature=0.3)
        )
        return _render_canonical_lesson_markdown(topic, goal, raw)

    fallback_raw = _normalize_multiline(
        f"""
        # 阶段学习详情

        ## 本阶段目标
        围绕“{goal.get('title', '当前阶段')}”完成本阶段最关键的理解与实践动作，并留下可检查的产出。

        ## 你会掌握什么
        - 理解本阶段在整条学习路径中的位置。
        - 知道本阶段必须完成的关键动作。
        - 能用阶段产出判断自己是否完成本阶段。

        ## 核心讲解
        ### 知识点 1｜阶段作用
        {goal.get('summary') or '先理解本阶段要解决什么问题，再决定采用什么学习动作。'}

        ### 知识点 2｜完成标准
        {goal.get('outcome') or '本阶段结束时，应形成一个可以被检查的产出。'}

        ## 操作步骤
        - 先梳理本阶段的目标与边界。
        - 再完成本阶段最小练习。
        - 最后沉淀阶段产出。

        ## 图示说明
        图示应突出核心概念、关键动作和阶段产出之间的关系。

        ## 练习
        - 用自己的话复述本阶段目标。
        - 完成一轮最小练习并记录问题。

        ## 自查清单
        - 我是否理解本阶段要解决什么问题？
        - 我是否完成了关键动作？
        - 我是否留下了可复查的阶段产出？
        """
    )
    return _render_canonical_lesson_markdown(topic, goal, fallback_raw)
