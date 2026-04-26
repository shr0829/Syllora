from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CONFIG_RELATIVE_PATH = Path("config") / "ai.config.toml"
CONFIG_TEMPLATE_RELATIVE_PATH = Path("config") / "ai.config.template.toml"

DEFAULT_TEXT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TEXT_MODEL = "gpt-4.1-mini"
DEFAULT_IMAGE_MODEL = "gpt-image-1"


def _read_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def normalize_reasoning_effort(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "xhigh":
        return "high"
    if normalized in {"low", "medium", "high"}:
        return normalized
    return ""


def _normalize_base_url(url: str, *, append_v1_if_missing: bool = True) -> str:
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        return ""
    if not append_v1_if_missing:
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.path in {"", "/"}:
        return f"{cleaned}/v1"
    return cleaned


def _relative_to_project(project_root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class TextRuntimeConfig:
    provider: str
    base_url: str
    wire_api: str
    api_key: str
    model: str
    review_model: str
    reasoning_effort: str
    disable_response_storage: bool
    network_access: str
    windows_wsl_setup_acknowledged: bool
    model_context_window: int | None
    model_auto_compact_token_limit: int | None
    requires_openai_auth: bool = True

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def applied_reasoning_effort(self) -> str:
        return normalize_reasoning_effort(self.reasoning_effort)


@dataclass(frozen=True)
class ImageChannelConfig:
    provider_type: str
    raw_url: str
    base_url: str
    api_key: str
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


@dataclass(frozen=True)
class ImageRuntimeConfig:
    model: str
    channels: tuple[ImageChannelConfig, ...]

    @property
    def configured(self) -> bool:
        return any(channel.configured for channel in self.channels)

    @property
    def primary_channel(self) -> ImageChannelConfig:
        configured = next((channel for channel in self.channels if channel.configured), None)
        if configured is not None:
            return configured
        return self.channels[0]


@dataclass(frozen=True)
class RuntimeConfig:
    project_root: Path
    text: TextRuntimeConfig
    image: ImageRuntimeConfig
    source_path: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return "config-file" if self.source_path else "environment"

    def describe(self) -> dict[str, Any]:
        return {
            "configured": self.text.configured,
            "imageConfigured": self.image.configured,
            "source": self.source,
            "configPath": _relative_to_project(self.project_root, self.source_path),
            "provider": self.text.provider,
            "baseUrl": self.text.base_url,
            "wireApi": self.text.wire_api,
            "model": self.text.model,
            "reviewModel": self.text.review_model,
            "reasoningEffort": self.text.reasoning_effort,
            "appliedReasoningEffort": self.text.applied_reasoning_effort,
            "disableResponseStorage": self.text.disable_response_storage,
            "networkAccess": self.text.network_access,
            "contextWindow": self.text.model_context_window,
            "autoCompactTokenLimit": self.text.model_auto_compact_token_limit,
            "imageModel": self.image.model,
            "imageProviderType": self.image.primary_channel.provider_type,
            "imageBaseUrl": self.image.primary_channel.base_url,
            "imageChannelCount": len(self.image.channels),
            "imageChannels": [
                {
                    "providerType": channel.provider_type,
                    "baseUrl": channel.base_url,
                    "configured": channel.configured,
                    "model": channel.model,
                }
                for channel in self.image.channels
            ],
        }


def _build_image_channel(
    image_table: dict[str, Any],
    connection_table: dict[str, Any],
    *,
    fallback_base_url: str,
    fallback_api_key: str,
    fallback_model: str,
) -> ImageChannelConfig:
    raw_url = (
        _as_str(connection_table.get("url"))
        or _as_str(image_table.get("base_url"))
        or _read_env("LEARNING_IMAGE_BASE_URL", "OPENAI_IMAGE_BASE_URL")
        or fallback_base_url
    )
    return ImageChannelConfig(
        provider_type=_as_str(connection_table.get("_type"))
        or _as_str(image_table.get("provider_type"))
        or "openai-image",
        raw_url=raw_url,
        base_url=_normalize_base_url(raw_url, append_v1_if_missing=bool(raw_url)),
        api_key=(
            _as_str(connection_table.get("key"))
            or _as_str(image_table.get("api_key"))
            or _read_env(
                "LEARNING_IMAGE_API_KEY",
                "OPENAI_IMAGE_API_KEY",
                "LEARNING_API_KEY",
                "OPENAI_API_KEY",
            )
            or fallback_api_key
        ),
        model=_as_str(connection_table.get("model_id"))
        or _as_str(image_table.get("model_id"))
        or fallback_model,
    )


def load_runtime_config(project_root: Path) -> RuntimeConfig:
    config_path = project_root / CONFIG_RELATIVE_PATH
    raw = _read_toml(config_path) if config_path.exists() else {}

    text_table = raw.get("text") if isinstance(raw.get("text"), dict) else {}
    text_provider_table = text_table.get("provider") if isinstance(text_table.get("provider"), dict) else {}
    image_table = raw.get("image") if isinstance(raw.get("image"), dict) else {}
    image_connection_table = (
        image_table.get("connection") if isinstance(image_table.get("connection"), dict) else {}
    )
    image_channels_table = image_table.get("channels") if isinstance(image_table.get("channels"), list) else []

    text_base_url = _normalize_base_url(
        _as_str(text_provider_table.get("base_url"))
        or _as_str(text_table.get("base_url"))
        or _read_env("LEARNING_BASE_URL", "OPENAI_BASE_URL")
        or DEFAULT_TEXT_BASE_URL
    )
    text_api_key = (
        _as_str(text_provider_table.get("api_key"))
        or _as_str(text_table.get("api_key"))
        or _read_env("LEARNING_API_KEY", "OPENAI_API_KEY")
    )
    text_model = _as_str(text_table.get("model")) or _read_env("LEARNING_MODEL", "OPENAI_MODEL") or DEFAULT_TEXT_MODEL

    text_config = TextRuntimeConfig(
        provider=_as_str(text_table.get("model_provider"))
        or _read_env("LEARNING_MODEL_PROVIDER", "OPENAI_PROVIDER")
        or _as_str(text_provider_table.get("name"))
        or "OpenAI",
        base_url=text_base_url,
        wire_api=_as_str(text_provider_table.get("wire_api"))
        or _as_str(text_table.get("wire_api"))
        or _read_env("LEARNING_WIRE_API", "OPENAI_WIRE_API")
        or "chat/completions",
        api_key=text_api_key,
        model=text_model,
        review_model=_as_str(text_table.get("review_model"))
        or _read_env("LEARNING_REVIEW_MODEL", "OPENAI_REVIEW_MODEL")
        or text_model,
        reasoning_effort=_as_str(text_table.get("model_reasoning_effort"))
        or _read_env("LEARNING_MODEL_REASONING_EFFORT", "OPENAI_MODEL_REASONING_EFFORT"),
        disable_response_storage=_as_bool(
            text_table.get("disable_response_storage"),
            default=_as_bool(_read_env("LEARNING_DISABLE_RESPONSE_STORAGE", "OPENAI_DISABLE_RESPONSE_STORAGE")),
        ),
        network_access=_as_str(text_table.get("network_access"))
        or _read_env("LEARNING_NETWORK_ACCESS", "OPENAI_NETWORK_ACCESS")
        or "disabled",
        windows_wsl_setup_acknowledged=_as_bool(
            text_table.get("windows_wsl_setup_acknowledged"),
            default=_as_bool(
                _read_env(
                    "LEARNING_WINDOWS_WSL_SETUP_ACKNOWLEDGED",
                    "OPENAI_WINDOWS_WSL_SETUP_ACKNOWLEDGED",
                )
            ),
        ),
        model_context_window=_as_int(text_table.get("model_context_window"))
        or _as_int(_read_env("LEARNING_MODEL_CONTEXT_WINDOW", "OPENAI_MODEL_CONTEXT_WINDOW")),
        model_auto_compact_token_limit=_as_int(text_table.get("model_auto_compact_token_limit"))
        or _as_int(
            _read_env(
                "LEARNING_MODEL_AUTO_COMPACT_TOKEN_LIMIT",
                "OPENAI_MODEL_AUTO_COMPACT_TOKEN_LIMIT",
            )
        ),
        requires_openai_auth=_as_bool(
            text_provider_table.get("requires_openai_auth"),
            default=_as_bool(_read_env("LEARNING_REQUIRES_OPENAI_AUTH", "OPENAI_REQUIRES_OPENAI_AUTH"), default=True),
        ),
    )

    image_model = _as_str(image_table.get("model_id")) or _read_env("LEARNING_IMAGE_MODEL", "OPENAI_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL
    image_channels: list[ImageChannelConfig] = []

    if image_connection_table:
        image_channels.append(
            _build_image_channel(
                image_table,
                image_connection_table,
                fallback_base_url=text_base_url,
                fallback_api_key=text_api_key,
                fallback_model=image_model,
            )
        )

    for channel_table in image_channels_table:
        if not isinstance(channel_table, dict):
            continue
        image_channels.append(
            _build_image_channel(
                image_table,
                channel_table,
                fallback_base_url=text_base_url,
                fallback_api_key=text_api_key,
                fallback_model=image_model,
            )
        )

    if not image_channels:
        image_channels.append(
            _build_image_channel(
                image_table,
                {},
                fallback_base_url=text_base_url,
                fallback_api_key=text_api_key,
                fallback_model=image_model,
            )
        )

    image_config = ImageRuntimeConfig(
        model=image_model,
        channels=tuple(image_channels),
    )

    return RuntimeConfig(
        project_root=project_root,
        text=text_config,
        image=image_config,
        source_path=config_path if config_path.exists() else None,
        raw=raw,
    )
