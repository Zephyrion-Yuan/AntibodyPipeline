from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class UIMessage:
    level: str
    message: str


@dataclass
class UIContext:
    payload: Dict[str, Any]
    messages: List[UIMessage]

    @classmethod
    def from_env(cls) -> "UIContext":
        raw = os.getenv("ANTIBODY_UI_PAYLOAD", "").strip()
        if raw:
            payload = json.loads(raw)
            return cls(payload=payload, messages=[])
        return cls(payload={}, messages=[])

    def _get_bucket(self, key: str) -> Dict[str, Any]:
        bucket = self.payload.get(key, {})
        if not isinstance(bucket, dict):
            return {}
        return bucket

    def require_input(self, key: str) -> str:
        value = self._get_bucket("inputs").get(key)
        if not value:
            raise ValueError(f"缺少输入文件: {key}")
        return str(value)

    def optional_input(self, key: str) -> Optional[str]:
        value = self._get_bucket("inputs").get(key)
        return str(value) if value else None

    def require_param(self, key: str) -> Any:
        value = self._get_bucket("params").get(key)
        if value is None or value == "":
            raise ValueError(f"缺少参数: {key}")
        return value

    def optional_param(self, key: str, default: Any = None) -> Any:
        value = self._get_bucket("params").get(key, default)
        return value if value != "" else default

    def output_dir(self, fallback_path: Optional[str] = None) -> str:
        output_dir = self.payload.get("output_dir") or fallback_path
        if not output_dir:
            raise ValueError("缺少输出目录")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return str(output_dir)

    def info(self, message: str) -> None:
        self.messages.append(UIMessage(level="info", message=message))
        print(message)

    def warn(self, message: str) -> None:
        self.messages.append(UIMessage(level="warning", message=message))
        print(message)

    def error(self, message: str) -> None:
        self.messages.append(UIMessage(level="error", message=message))
        raise ValueError(message)

    def list_inputs(self, key: str) -> List[str]:
        value = self._get_bucket("inputs").get(key)
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    def ensure_files_exist(self, paths: Iterable[str]) -> None:
        missing = [path for path in paths if not Path(path).exists()]
        if missing:
            raise FileNotFoundError(f"输入文件不存在: {', '.join(missing)}")
