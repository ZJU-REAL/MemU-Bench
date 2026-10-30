

"""LLM as Judge validation functions.

This module provides functions that use LLM to judge whether a task
has been completed correctly when exact string matching is not suitable.
"""

import json
import os
import time
import base64
from typing import Optional, Union

import requests
from PIL import Image
import io


# Load specific environment variables from .env file
_JUDGER_VARS = ['VLM_JUDGER_API_KEY', 'VLM_JUDGER_BASE_URL', 'VLM_JUDGER_MODEL']

def _load_judger_env_from_file():
    """Load JUDGER_* variables from .env file if not already set."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'fixed.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    if key in _JUDGER_VARS and not os.environ.get(key):
                        os.environ[key] = value.strip()

_load_judger_env_from_file()


# LLM API 配置 - 从环境变量读取，变量名以 JUDGER_ 为前缀
API_KEY = os.environ.get('VLM_JUDGER_API_KEY', '')

BASE_URL = os.environ.get('VLM_JUDGER_BASE_URL', '')

MODEL_NAME = os.environ.get('VLM_JUDGER_MODEL', '')


ERROR_CALLING_LLM = "Error calling LLM"


# Reply format template - fixed for all tasks
REPLY_FORMAT = """
Please reply in the following format:
Result: [Success/Failure]
Explanation: [Brief explanation of the judgment]
"""




def vlm_judge(
    goal: str,
    task_prompt: str,
    image_paths: list[str],
) -> tuple[bool, str]:
    """Use VLM (Vision Language Model) to judge whether screenshots match expected criteria.

    Sends text prompt along with images to the VLM API for visual verification.

    Args:
        goal: The task goal/objective describing what the agent was supposed to do.
        task_prompt: The task-specific prompt containing the judgment criteria.
            The reply format will be automatically added.
        image_paths: List of file paths to images (screenshots) to send to the VLM.

    Returns:
        A tuple of (is_match, explanation):
            - is_match: True if the VLM judges that the screenshots fulfill
              the expected requirements.
            - explanation: A string explaining the judgment.
    """
    # Build full prompt with goal and task-specific content
    full_prompt = f"Task Goal: {goal}\n\n" + task_prompt + REPLY_FORMAT

    # Build message content with text and images
    content = []
    content.append({"type": "text", "text": full_prompt})

    for img_path in image_paths:
        if os.path.exists(img_path):
            # Load and resize image to 672x1492
            img = Image.open(img_path).convert('RGB')
            img = img.resize((672, 1492))
            # Convert to JPEG bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG')
            img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
            # Determine image type from extension
            ext = os.path.splitext(img_path)[1].lower()
            mime_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{img_data}"},
            })
        else:
            print(f"[DEBUG] Image not found: {img_path}")

    # Call VLM
    response = _call_vlm(content)

    if response == ERROR_CALLING_LLM:
        raise RuntimeError(
            'VLM judge call failed after retries, skipping task.'
        )
    if not response or not response.strip():
        raise RuntimeError(
            'VLM judge returned empty response, skipping task.'
        )
    print("=================\nVLM response:", response)
    # Parse the response
    is_match, explanation = _parse_judge_response(response)

    return is_match, explanation


def build_default_prompt(
    expected_data: Union[str, dict, list],
    actual_data: Union[str, dict, list],
    task_description: Optional[str] = None,
) -> str:
    """Build a default prompt for LLM judge.

    This is a helper function to build a standard prompt. You can use this
    as a template and customize it for different apps.

    Args:
        expected_data: The expected data (task requirement). Can be a string,
            dict, or list. Will be serialized to JSON for comparison.
        actual_data: The actual data from database after agent operation.
            Can be a string, dict, or list. Will be serialized to JSON.
        task_description: Optional description of the task to provide context.

    Returns:
        A formatted prompt string.
    """
    # Serialize data to JSON string if needed
    if isinstance(expected_data, (dict, list)):
        expected_str = json.dumps(expected_data, ensure_ascii=False, indent=2)
    else:
        expected_str = str(expected_data)

    if isinstance(actual_data, (dict, list)):
        actual_str = json.dumps(actual_data, ensure_ascii=False, indent=2)
    else:
        actual_str = str(actual_data)

    prompt = """You are a judge. You need to determine whether the actual data meets the task requirements.

"""
    if task_description:
        prompt += f"""Task Description:
{task_description}

"""

    prompt += f"""Expected Data (Task Requirement):
{expected_str}

Actual Data (Result after Agent operation):
{actual_str}

Please determine whether the actual data has completed the task requirements.

Judgment Rules:
1. The information content must be equivalent - no missing information, no extra information, no incorrect information
2. Wording and expression style can be different (e.g., "milk, bread" vs "need to buy milk and bread" are equivalent)
3. If the actual data has extra information that was NOT in the expected data, judge as Failure
4. If the actual data is missing information from the expected data, judge as Failure
5. If the actual data has incorrect/modified information, judge as Failure
6. Only judge as Success when the actual data conveys exactly the same information as expected, just with different wording

Please reply in the following format:
Result: [Success/Failure]
Explanation: [Brief explanation of why you made this judgment]

Please reply directly without extra content."""

    return prompt




def _call_vlm(
    content: list[dict],
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 16384,
    max_retry: int = 3,
) -> str:
    """Call VLM API with text and image content.

    Args:
        content: The message content list containing text and image_url items.
        model_name: Model name to use. If not provided, will use default MODEL_NAME.
        temperature: Temperature for VLM generation.
        max_tokens: Maximum tokens in the response.
        max_retry: Maximum number of retries on failure.

    Returns:
        The VLM response text, or ERROR_CALLING_LLM on failure.
    """
    if model_name is None:
        model_name = MODEL_NAME

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    payload = {
        "model": model_name,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
        "max_tokens": max_tokens,
    }

    retry_delay = 1.0
    for attempt in range(max_retry):
        try:
            response = requests.post(
                BASE_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.ok:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    print(f"VLM response missing choices: {result}")
            else:
                print(f"VLM API error: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            print(f"VLM request timeout, attempt {attempt + 1}/{max_retry}")
        except requests.exceptions.RequestException as e:
            print(f"VLM request error: {e}")
        except Exception as e:
            print(f"Unexpected error calling VLM: {e}")

        if attempt < max_retry - 1:
            time.sleep(retry_delay)
            retry_delay *= 2

    return ERROR_CALLING_LLM


def _parse_judge_response(response: str) -> tuple[bool, str]:
    """Parse the LLM judge response to extract the judgment and explanation."""
    response = response.strip()

    # Default values
    is_match = False
    explanation = response

    # Try to parse the structured response
    lines = response.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if line_lower.startswith("result"):
            if "success" in line_lower or "true" in line_lower:
                is_match = True
            elif "fail" in line_lower or "false" in line_lower:
                is_match = False
        elif line_lower.startswith("explanation"):
            # Extract explanation from the rest
            explanation = "\n".join(lines[i + 1 :]).strip()
            break

    return is_match, explanation