import os
import threading
import time
from typing import Optional, Union

import requests


def _get_model_name() -> str:
    """Get model name from environment variable."""
    return os.environ.get('MODEL', '')


def _get_base_url() -> str:
    """Get base URL from environment variable."""
    return os.environ.get('BASE_URL', '')


def _get_api_key() -> str:
    """Get API key from environment variable."""
    return os.environ.get('API_KEY', '')

ERROR_CALLING_LLM = 'ERROR_CALLING_LLM'

# Thread-local token counter — each thread gets its own independent counters
_tls = threading.local()


def _get_counters():
    """Get thread-local counters, initializing on first access."""
    if not hasattr(_tls, 'input_tokens'):
        _tls.input_tokens = 0
        _tls.output_tokens = 0
    return _tls


def get_token_stats() -> tuple:
    """Get token counts for the current thread."""
    _get_counters()
    return _tls.input_tokens, _tls.output_tokens


def reset_token_stats() -> None:
    """Reset token counters for the current thread."""
    _get_counters()
    _tls.input_tokens = 0
    _tls.output_tokens = 0

_GENERATION_CONFIG_MAP = {
        'Qwen3.5-397B-A17B': {'temperature': 0.0},
        'Qwen3-VL-8B-Instruct': {'max_tokens': 16384},
        './MAI-UI-8B': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 16384},
        'openai/gpt-5.5': {'temperature': 1},
        './GUI-Owl-1.5-8B-Instruct': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 16384},
        './UI-Venus-1.5-8B': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 2048},
        'gemini-3.1-pro-preview': {'temperature': 0},
        'google/gemini-3.1-pro-preview': {'temperature': 0},
    }
def _call_llm(
    prompt: str,
    model_name: Optional[str] = None,
    max_retry: int = 3,
    count_tokens: bool = True,
) -> str:
    """Call LLM API with the given prompt.

    Args:
        prompt: The prompt to send to the LLM.
        model_name: Model name to use. If not provided, will use default MODEL_NAME.
        temperature: Temperature for LLM generation.
        max_tokens: Maximum tokens in the response.
        max_retry: Maximum number of retries on failure.

    Returns:
        The LLM response text, or ERROR_CALLING_LLM on failure.
    """
    if model_name is None:
        model_name = _get_model_name()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_api_key()}",
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    generation_config = _GENERATION_CONFIG_MAP.get(model_name, {})
    for key in ('temperature', 'top_k', 'top_p', 'max_tokens'):
        if key in generation_config:
            payload[key] = generation_config[key]
    retry_delay = 1.0
    for attempt in range(max_retry):
        try:
            response = requests.post(
                _get_base_url(),
                headers=headers,
                json=payload,
                timeout=180,
            )

            if response.ok:
                result = response.json()
                # print(f"[DEBUG] LLM raw response: {result}")

                # Count tokens if available
                if count_tokens and "usage" in result:
                    _get_counters()
                    usage = result["usage"]
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    _tls.input_tokens += input_tokens
                    _tls.output_tokens += output_tokens

                if "choices" in result and len(result["choices"]) > 0:
                    raw_content = result["choices"][0]["message"].get("content")
                    content = raw_content if raw_content is not None else ""
                    print(f"[LLM DEBUG] raw_content type: {type(raw_content)}, repr: {repr(raw_content)}")
                    return content
                else:
                    print(f"LLM response missing choices: {result}")
            else:
                print(f"LLM API error: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            print(f"LLM request timeout, attempt {attempt + 1}/{max_retry}")
        except requests.exceptions.RequestException as e:
            print(f"LLM request error: {e}")
        except Exception as e:
            print(f"Unexpected error calling LLM: {e}")

        if attempt < max_retry - 1:
            time.sleep(retry_delay)
            retry_delay *= 2

    return ERROR_CALLING_LLM