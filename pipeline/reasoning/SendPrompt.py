from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


class SendPrompt:
    """
    Send one prompt payload JSON (from GeneratePrompt.py) to an LLM endpoint.

    Expected input JSON shape:
    {
      "id": "REA-01#4",
      "system_prompt": "...",
      "user_prompt": "..."
    }
    """

    def __init__(
        self,
        env_path: str | Path,
        model_name: str = "gpt-5",
        api_url: str = "https://api.openai.com/v1/chat/completions",
        timeout_seconds: int = 240,
        max_retries: int = 3,
        enable_prompt_cache: bool = True,
        prompt_cache_retention: str = "24h",
    ) -> None:
        self.env_path = Path(env_path).expanduser().resolve()
        self.model_name = model_name
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(1, int(max_retries))
        self.enable_prompt_cache = bool(enable_prompt_cache)
        self.prompt_cache_retention = str(prompt_cache_retention or "24h").strip()

    @staticmethod
    def _normalize_key_value(raw: Any) -> str:
        value = str(raw or "").strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1].strip()
        return value

    def _candidate_env_paths(self) -> list[Path]:
        candidates: list[Path] = []
        explicit = self.env_path / ".env" if self.env_path.is_dir() else self.env_path
        candidates.append(explicit)
        candidates.append(Path(__file__).resolve().parent / ".env")
        candidates.append(Path.cwd().resolve() / ".env")

        out: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
        return out

    def _load_api_key(self) -> str:
        for env_file in self._candidate_env_paths():
            if not env_file.exists():
                continue
            env_values = dotenv_values(env_file)
            for name in ("OPENAI_API_KEY", "API_KEY"):
                key = self._normalize_key_value(env_values.get(name, ""))
                if key:
                    return key

        for name in ("OPENAI_API_KEY", "API_KEY"):
            key = self._normalize_key_value(os.getenv(name, ""))
            if key:
                return key
        raise ValueError("No API key found in .env or env vars OPENAI_API_KEY/API_KEY.")

    @staticmethod
    def _load_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _is_retryable_http_status(status_code: int) -> bool:
        return status_code in {429, 500, 502, 503, 504}

    @staticmethod
    def _build_ssl_context(use_certifi: bool = False) -> ssl.SSLContext:
        if use_certifi:
            try:
                import certifi

                return ssl.create_default_context(cafile=certifi.where())
            except Exception:
                return ssl.create_default_context()
        return ssl.create_default_context()

    @staticmethod
    def _is_ssl_cert_error(exc: urllib.error.URLError) -> bool:
        reason_obj = exc.reason
        reason_text = str(reason_obj).lower()
        if isinstance(reason_obj, ssl.SSLCertVerificationError):
            return True
        return "certificate verify failed" in reason_text or ("cert" in reason_text and "verify" in reason_text)

    @staticmethod
    def _extract_text_from_response(payload: dict[str, Any]) -> str:
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""
        msg = choices[0].get("message", {})
        if not isinstance(msg, dict):
            return ""
        return str(msg.get("content", "")).strip()

    @staticmethod
    def _build_prompt_cache_key(system_prompt: str, model_name: str) -> str:
        """
        Stable cache key for shared instruction prefix.
        Keeping this based on system prompt helps route repeated prompts
        with identical instruction prefixes to the same cache.
        """
        digest = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:24]
        model_norm = str(model_name).strip().lower()
        return f"deviation-prompt::{model_norm}::{digest}"

    def _supports_extended_cache_retention(self, model_name: str) -> bool:
        """
        Best-effort model gate for 24h prompt cache retention.
        """
        name = str(model_name or "").strip().lower()
        if name.startswith("gpt-5"):
            return True
        if name.startswith("gpt-4.1"):
            return True
        return False

    def _post_json(self, body: dict[str, Any]) -> dict[str, Any]:
        api_key = self._load_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8")
        ssl_ctx = self._build_ssl_context(use_certifi=False)
        used_certifi = False

        last_error: str | None = None
        for attempt in range(1, self.max_retries + 1):
            req = urllib.request.Request(self.api_url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds, context=ssl_ctx) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
            except urllib.error.HTTPError as exc:
                status = int(getattr(exc, "code", 0) or 0)
                error_body = exc.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {status}: {error_body}"
                if attempt < self.max_retries and self._is_retryable_http_status(status):
                    time.sleep(min(2**attempt, 10))
                    continue
                raise RuntimeError(last_error) from exc
            except urllib.error.URLError as exc:
                last_error = f"URL error: {exc}"
                if self._is_ssl_cert_error(exc) and not used_certifi:
                    ssl_ctx = self._build_ssl_context(use_certifi=True)
                    used_certifi = True
                    continue
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 10))
                    continue
                raise RuntimeError(last_error) from exc

        raise RuntimeError(last_error or "Unknown request failure.")

    def send_prompt_json(
        self,
        prompt_json_path: str | Path,
        output_json_path: str | Path | None = None,
        temperature: float | None = None,
    ) -> Path:
        prompt_path = Path(prompt_json_path).expanduser().resolve()
        payload = self._load_json(prompt_path)
        if not isinstance(payload, dict):
            raise ValueError(f"Prompt JSON must be an object: {prompt_path}")

        system_prompt = str(payload.get("system_prompt", "")).strip()
        user_prompt = str(payload.get("user_prompt", "")).strip()
        if not system_prompt or not user_prompt:
            raise ValueError("Prompt JSON must contain non-empty 'system_prompt' and 'user_prompt'.")

        request_body: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if temperature is not None:
            request_body["temperature"] = float(temperature)

        if self.enable_prompt_cache:
            request_body["prompt_cache_key"] = self._build_prompt_cache_key(
                system_prompt=system_prompt,
                model_name=self.model_name,
            )
            if self.prompt_cache_retention:
                if self.prompt_cache_retention == "24h":
                    if self._supports_extended_cache_retention(self.model_name):
                        request_body["prompt_cache_retention"] = "24h"
                elif self.prompt_cache_retention == "in_memory":
                    request_body["prompt_cache_retention"] = "in_memory"

        try:
            response_payload = self._post_json(request_body)
        except RuntimeError as exc:
            # Backward-compatible fallback if endpoint/model rejects cache params.
            err = str(exc).lower()
            if "prompt_cache" in err or "unknown parameter" in err or "unrecognized request argument" in err:
                request_body.pop("prompt_cache_key", None)
                request_body.pop("prompt_cache_retention", None)
                response_payload = self._post_json(request_body)
            else:
                raise
        response_text = self._extract_text_from_response(response_payload)

        out_path = (
            Path(output_json_path).expanduser().resolve()
            if output_json_path is not None
            else prompt_path.with_name(f"{prompt_path.stem}_llm_response.json")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_payload = {
            "id": str(payload.get("id", "")).strip(),
            "prompt_json": str(prompt_path),
            "model": self.model_name,
            "api_url": self.api_url,
            "prompt_cache": {
                "enabled": self.enable_prompt_cache,
                "key": request_body.get("prompt_cache_key", ""),
                "retention": request_body.get("prompt_cache_retention", ""),
            },
            "sent_messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_text": response_text,
            "raw_response": response_payload,
        }
        out_path.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one prompt payload JSON to LLM.")
    parser.add_argument("prompt_json", help="Path to prompt json, e.g. rea-01#4_prompt.json")
    parser.add_argument("--output-json", default="", help="Optional output response json path.")
    parser.add_argument("--model", default="gpt-5", help="Model name (default: gpt-5)")
    parser.add_argument(
        "--env-path",
        default="/Users/my/Documents/projects/detectionDeviation/pipeline/reasoning/.env",
        help="Path to .env file or directory containing .env",
    )
    parser.add_argument("--temperature", type=float, default=None, help="Optional temperature override")
    parser.add_argument("--timeout", type=int, default=240, help="HTTP timeout seconds")
    parser.add_argument("--max-retries", type=int, default=3, help="Retry count for transient failures")
    parser.add_argument(
        "--disable-prompt-cache",
        action="store_true",
        help="Disable prompt cache parameters on request.",
    )
    parser.add_argument(
        "--prompt-cache-retention",
        default="24h",
        choices=["24h", "in_memory", ""],
        help="Prompt cache retention policy (default: 24h).",
    )
    args = parser.parse_args()

    sender = SendPrompt(
        env_path=Path(args.env_path).expanduser().resolve(),
        model_name=str(args.model).strip(),
        timeout_seconds=max(10, int(args.timeout)),
        max_retries=max(1, int(args.max_retries)),
        enable_prompt_cache=not args.disable_prompt_cache,
        prompt_cache_retention=str(args.prompt_cache_retention).strip(),
    )
    saved = sender.send_prompt_json(
        prompt_json_path=Path(args.prompt_json).expanduser().resolve(),
        output_json_path=Path(args.output_json).expanduser().resolve() if args.output_json else None,
        temperature=args.temperature,
    )
    print(f"Saved: {saved}")


if __name__ == "__main__":
    main()
