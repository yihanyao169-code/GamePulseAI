from __future__ import annotations

import os

from anthropic import Anthropic

from src.models import CLAUDE_MODEL


class ClaudeClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("未配置 Claude API Key")

        self.model = model or os.getenv("CLAUDE_MODEL") or CLAUDE_MODEL
        self.client = Anthropic(api_key=self.api_key)

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        request = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if "sonnet-5" not in self.model:
            request["temperature"] = 0

        message = self.client.messages.create(**request)

        return "\n".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
