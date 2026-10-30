# Copyright 2026 The android_world Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base classes for log summarization."""

import base64
import io
import json
import os
import time
from typing import Optional

import numpy as np
from PIL import Image
import requests

from memory_generation.utils import format_action_qwen3_5, format_action_qwen3vl, format_action_agentic, format_action_mai_ui, format_action_ui_venus_1_5, format_action_gui_owl_1_5


ERROR_CALLING_LLM = 'Error calling LLM'

_WIDTH, _HEIGHT = 672, 1492
def load_image(image_path: str) -> np.ndarray:
    """Load an image from file and return as numpy array.

    Args:
        image_path: Path to the image file.

    Returns:
        Image as numpy array.
    """
    image = Image.open(image_path).convert('RGB')
    return np.array(image)


def image_to_jpeg_bytes(image: np.ndarray) -> bytes:
    """Convert numpy array to JPEG bytes."""
    pil_image = Image.fromarray(image)
    # Resize image to 672x1492
    pil_image = pil_image.resize((_WIDTH, _HEIGHT))
    in_mem_file = io.BytesIO()
    pil_image.save(in_mem_file, format='JPEG')
    in_mem_file.seek(0)
    return in_mem_file.read()


def encode_image(image: np.ndarray) -> str:
    """Encode image to base64 string."""
    return base64.b64encode(image_to_jpeg_bytes(image)).decode('utf-8')


class BaseSummarizer:
    """Base class for log summarizers.

    Selects the appropriate format_action function based on the model name.
    """

    RETRY_WAITING_SECONDS = 20

    # format_action -> list of model names
    _FORMAT_ACTION_MAP = {
        format_action_qwen3_5: ['Qwen3.5-397B-A17B', 'dashscope/qwen3.8-max'],
        format_action_qwen3vl: ['Qwen3-VL-8B-Instruct', 'Qwen3-VL-32B-Instruct'],
        format_action_agentic: [
            'claude-opus-4-8',
            'claude-opus-4-7',
            'anthropic/claude-sonnet-4.6',
            'openai/gpt-5.5',
            'gemini-3.1-pro-preview',
            'google/gemini-3.1-pro-preview',
            
        ],
        format_action_mai_ui: ['./MAI-UI-8B'],
        format_action_ui_venus_1_5: ['./UI-Venus-1.5-8B'],
        format_action_gui_owl_1_5: ['./GUI-Owl-1.5-8B-Instruct']
    }

    _GENERATION_CONFIG_MAP = {
        'Qwen3.5-397B-A17B': {'temperature': 0.0},
        'Qwen3-VL-8B-Instruct': {'temperature': 0.0},
        'Qwen3-VL-32B-Instruct': {'temperature': 0.0},
        './MAI-UI-8B': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 16384},
        'openai/gpt-5.5': {},
        './UI-Venus-1.5-8B': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 16384},
        './GUI-Owl-1.5-8B-Instruct': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 10240},
        'claude-opus-4-8': {},
        'gemini-3.1-pro-preview': {'temperature': 0},
        'google/gemini-3.1-pro-preview': {'temperature': 0},
        'dashscope/qwen3.8-max': {'temperature': 0}
    }

    def __init__(
        self,
        model_name: str,
        max_retry: int = 3,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize the summarizer.

        Args:
            model_name: Name of the model to use.
            max_retry: Maximum number of retries on API failure.
            temperature: Temperature for model generation.
            api_key: API key. If None, reads from API_KEY environment variable.
            base_url: Base URL for the API endpoint. If None, reads from BASE_URL
                environment variable or uses default.
        """
        self.api_key = api_key or os.environ.get('API_KEY')
        if not self.api_key:
            raise RuntimeError(
                'API key not set. Set API_KEY environment variable or pass api_key parameter.'
            )

        self.base_url = base_url or os.environ.get('BASE_URL', '')
        self.model = model_name or os.environ.get('MODEL', '')
        self.max_retry = min(max(max_retry, 1), 5)
        self._round_input_tokens = 0
        self._round_output_tokens = 0

        # Build reverse mapping: model_name -> format_action
        self._format_action = None
        for fmt_fn, model_list in self._FORMAT_ACTION_MAP.items():
            if self.model in model_list:
                self._format_action = fmt_fn
                break
        if self._format_action is None:
            raise RuntimeError(f'Unknown model format_action: {self.model}')
        # Select generation_config based on model
        self.generation_config = self._GENERATION_CONFIG_MAP.get(self.model, {})
        print(f"Apply base_url: {self.base_url}, model: {self.model}, format_action: {self._format_action.__name__}")

    def _consume_round_tokens(self) -> tuple[int, int]:
        """Return accumulated token counts for this round and reset counters."""
        it, ot = self._round_input_tokens, self._round_output_tokens
        self._round_input_tokens = 0
        self._round_output_tokens = 0
        return it, ot

    def _collect_round_tokens(
        self, calc_token: bool, input_tokens_list: list | None, output_tokens_list: list | None, batch_label: str = "", verbose: bool = False,
    ) -> None:
        """Consume round tokens and append to lists. Always resets counters regardless of calc_token."""
        it, ot = self._consume_round_tokens()
        if not calc_token:
            return
        input_tokens_list.append(it)
        output_tokens_list.append(ot)
        if verbose:
            print(f"  {batch_label} tokens: input={it}, output={ot}")

    def _attach_tokens(self, result: dict, calc_token: bool, input_tokens_list: list | None, output_tokens_list: list | None) -> None:
        """Attach token lists to result dict. No-op when calc_token is False."""
        if calc_token:
            result["input_tokens"] = input_tokens_list
            result["output_tokens"] = output_tokens_list

    def format_action(self, event: dict, width: int, height: int) -> str:
        """Format an action event to human-readable string.

        Args:
            event: Action event dictionary.
            width: Width of the screenshot image.
            height: Height of the screenshot image.

        Returns:
            Formatted string describing the action.
        """
        return self._format_action(event, width, height)


    def call_llm(
        self,
        messages: list[dict],
    ) -> str:
        """Call the LLM API with retry logic.

        Args:
            messages: List of message dictionaries with role and content.
            max_tokens: Maximum tokens to generate.

        Returns:
            Response text, or ERROR_CALLING_LLM on failure.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': 32768,
        }

        for key in ('temperature', 'top_k', 'top_p', 'max_tokens'):
            if key in self.generation_config:
                payload[key] = self.generation_config[key]

        counter = self.max_retry
        wait_seconds = self.RETRY_WAITING_SECONDS

        while counter > 0:
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=180,
                )
                if response.ok and 'choices' in response.json():
                    result = response.json()
                    usage = result.get('usage', {})
                    input_t = usage.get('prompt_tokens', 0)
                    output_t = usage.get('completion_tokens', 0)
                    self._round_input_tokens += input_t
                    self._round_output_tokens += output_t
                    # if input_t > 15000:
                    #     print(f"[ALERT] High input tokens: {input_t}")
                    #     print(f"  Messages count: {len(messages)}")
                        
                    #     # 统计总图片数和历史消息
                    #     total_images = 0
                    #     total_text_chars = 0
                    #     for i, msg in enumerate(messages):
                    #         content = msg.get('content', '')
                    #         if isinstance(content, list):
                    #             img_count = sum(1 for c in content if c.get('type') == 'image_url')
                    #             text_len = sum(len(c.get('text', '')) for c in content if c.get('type') == 'text')
                    #             total_images += img_count
                    #             total_text_chars += text_len
                    #             if img_count > 0 or text_len > 0:
                    #                 print(f"  Message[{i}]: role={msg['role']}, images={img_count}, text_len={text_len}")
                    #         else:
                    #             total_text_chars += len(content)
                    #             print(f"  Message[{i}]: role={msg['role']}, content_len={len(content)}")
                        
                    #     print(f"  === TOTAL: images={total_images}, text_chars={total_text_chars} ===")
                    #     print(f"  === ROLES: {[msg['role'] for msg in messages]} ===")
                    print(f"  [token] usage={usage}, this call: input={input_t}, output={output_t}; round accumulate: input={self._round_input_tokens}, output={self._round_output_tokens}")
                    return result['choices'][0]['message']['content']
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                print(f'Error calling LLM API: {error_msg}')
                time.sleep(wait_seconds)
                wait_seconds *= 2
            except Exception as e:
                time.sleep(wait_seconds)
                wait_seconds *= 2
                counter -= 1
                print(f'Error calling LLM, will retry soon...: {e}')

        return ERROR_CALLING_LLM

    # Default prompt templates (can be overridden by subclasses)
    SYSTEM_PROMPT = (
        "You are a helpful GUI Assistant."
    )

    GENERATE_SUMMARY_INSTRUCTION = (
        '''
        Your task is to analyze the provided screenshots and actions, then generate a concise summary describing what the user did and the current state.

        Requirements:
        1. Focus on the user's goal and the actions taken to achieve it
        2. Describe the key UI elements and changes observed
        3. Summarize the outcome of the actions

        Output ONLY the summary text, no additional explanation.
        '''.strip()
    )

    # GENERATE_SUMMARY_INSTRUCTION = (
    #     '''
    #     You are analyzing a user's operation log on an Android device based on the provided screenshots and the actions performed before each screenshot.

    #     Your task is to generate a detailed, cohesive narrative summary of what happened in this batch. Write it as flowing prose, but preserve the richness of detail that matters for later retrieval.

    #     Cover the following dimensions as applicable:

    #     1. Apps involved: Identify which app(s) the user was operating in, using the app name provided (do not modify it on your own; use None if not identifiable). If multiple apps appear, describe them in chronological order.

    #     2. User journey and sequence: Describe what the user did step by step. Preserve the order of key items, screens, categories, and interactions the user passed through (e.g., "opened Settings, then went to Display, then adjusted font size"). Do NOT collapse this into a vague "user browsed the app". When the user changed their mind, compared options, or switched tasks, reflect that transition in the narrative.

    #     3. Specific details (hard data): Preserve all concrete data points that are likely to matter later — numeric values (prices, quantities, durations, verification codes, dates), proper nouns (brand names, item titles, restaurant names, contact names, place names), and specific attributes (color, size, specifications, addresses, model numbers). These should appear inline in the prose naturally.

    #     4. Outcome / state: Make clear whether the task within each app reached a terminal point (finished: payment confirmed, message sent, result obtained, "=" pressed in calculator, final item selected) or remains incomplete (ongoing: still browsing, form half-filled, expression left hanging, exited without committing). If the last operation is not a definitive commit/result action, lean toward "ongoing".

    #     5. Time range: If a system clock is visible in the upper-left corner of the screenshots, mention the start and end time of the activity in 'Apr 22 14:30' style; omit if not inferable.

    #     Output ONLY the summary narrative. No preamble, no field labels, no bullet-point scaffolding. The result should read like a well-written detailed recap that someone could read afterwards and know exactly what the user did, what they looked at, what they decided, and whether it wrapped up — so it can serve as long-term memory for future retrieval.
    #     '''.strip()
    # )

    MERGE_SUMMARY_INSTRUCTION = (
        '''
        Your task is to merge the "Previous Summary" and the "New Summary" into a SINGLE cohesive narrative.

        Requirements:
        1. If the new summary is a continuation of the previous summary, merge them smoothly
        2. If the new summary describes a different task, combine them as a sequence
        3. Maintain the logical flow of the entire session

        Output ONLY the final merged summary text.
        '''.strip()
    )

    def get_system_prompt(self) -> str:
        """Get the system prompt with identity and task description.

        Subclasses can override this method or the SYSTEM_PROMPT class attribute.

        Returns:
            System prompt string.
        """
        return self.SYSTEM_PROMPT

    def get_generate_summary_instruction(self) -> str:
        """Get the instruction for generating a new summary from screenshots and actions.

        Subclasses can override this method or the GENERATE_SUMMARY_INSTRUCTION class attribute.

        Returns:
            Instruction string.
        """
        return self.GENERATE_SUMMARY_INSTRUCTION

    def get_merge_summary_instruction(self) -> str:
        """Get the instruction for merging previous and new summaries.

        Subclasses can override this method or the MERGE_SUMMARY_INSTRUCTION class attribute.

        Returns:
            Instruction string.
        """
        return self.MERGE_SUMMARY_INSTRUCTION

    def build_batch_message(
        self,
        events: list[dict],
        screenshots_dir: str,
        start_idx: int,
        batch_size: int,
    ) -> tuple[list[dict], int]:
        """Build a message for generating a summary from screenshots and actions.

        Args:
            events: List of all events.
            screenshots_dir: Directory containing screenshots.
            start_idx: Starting index in events list.
            batch_size: Number of screenshots to include in this batch.

        Returns:
            Tuple of (messages list, next_start_idx).
        """
        content = []
        screenshot_count = 0
        current_idx = start_idx
        actions_before_screenshot = []

        # 1. System prompt (identity and task)
        system_prompt = self.get_system_prompt()
        content.append({'type': 'text', 'text': system_prompt})

        while current_idx < len(events) and screenshot_count < batch_size:
            event = events[current_idx]

            if event['type'] == 'screenshot':
                screenshot_path = os.path.join(screenshots_dir, event['screenshot_path'].replace('\\', os.sep))
                if os.path.exists(screenshot_path):
                    image = load_image(screenshot_path)

                    if actions_before_screenshot:
                        actions_text = "Actions performed:\n" + "\n".join(
                            f"  - {self.format_action(a, _WIDTH, _HEIGHT)}" for a in actions_before_screenshot
                        )
                        content.append({'type': 'text', 'text': actions_text + "\n"})
                        actions_before_screenshot = []

                    app_name = event.get('app_name')
                    app_str = app_name if app_name else 'None'
                    screenshot_info = f"\nScreenshot {screenshot_count + 1} (app: {app_str}):\n"
                    content.append({
                        'type': 'text',
                        'text': screenshot_info
                    })
                    content.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{encode_image(image)}'
                        }
                    })
                    screenshot_count += 1
            else:
                actions_before_screenshot.append(event)

            current_idx += 1

        if actions_before_screenshot and screenshot_count > 0:
            actions_text = "\nActions after last screenshot:\n" + "\n".join(
                f"  - {self.format_action(a, _WIDTH, _HEIGHT)}" for a in actions_before_screenshot
            )
            content.append({'type': 'text', 'text': actions_text})

        # Add instruction
        instruction = self.get_generate_summary_instruction()
        content.append({'type': 'text', 'text': instruction})

        messages = [{'role': 'user', 'content': content}]
        return messages, current_idx

    def update_summary(self, previous_summary: str, new_summary: str) -> str:
        """Merge previous and new summaries into one.

        Args:
            previous_summary: The previous summary from earlier batches.
            new_summary: The newly generated summary from current batch.

        Returns:
            Merged summary string.
        """
        content = []

        # System prompt
        system_prompt = self.get_system_prompt()
        content.append({'type': 'text', 'text': system_prompt})

        # Merge instruction
        merge_instruction = (
            f"Previous summary:\n{previous_summary}\n\n"
            f"New summary:\n{new_summary}\n\n"
            f"{self.get_merge_summary_instruction()}"
        )
        content.append({'type': 'text', 'text': merge_instruction})

        messages = [{'role': 'user', 'content': content}]
        merged_summary = self.call_llm(messages)

        if merged_summary == ERROR_CALLING_LLM:
            return previous_summary

        return merged_summary

    def summarize_log(
        self,
        log_path: str,
        screenshots_dir: Optional[str] = None,
        batch_size: int = 10,
        verbose: bool = True,
        calc_token: bool = False,
    ) -> dict:
        """Summarize a user operation log.

        Args:
            log_path: Path to the processed.jsonl file.
            screenshots_dir: Directory containing screenshots. If None, inferred from log_path.
            batch_size: Number of screenshots to process per batch.
            verbose: Whether to print progress information.
            calc_token: Whether to track per-batch input/output token counts.

        Returns:
            Dict with 'summary' and optional 'error_batch_id'.
            When calc_token is True, also includes 'input_tokens' and 'output_tokens' lists.
        """
        # Infer screenshots directory
        if screenshots_dir is None:
            log_dir = os.path.dirname(log_path)
            screenshots_dir = log_dir  # screenshots are referenced with 'screenshots/' prefix in events

        # Load events
        events = []
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        if not events:
            return {"summary": "No events found in log."}

        if verbose:
            print(f"Loaded {len(events)} events from {log_path}")
            screenshot_count = sum(1 for e in events if e['type'] == 'screenshot')
            print(f"Found {screenshot_count} screenshots")
            print(f"Processing in batches of {batch_size} screenshots...")

        # Process in batches
        current_idx = 0
        batch_num = 0
        accumulated_summary = ""
        input_tokens_list = [] if calc_token else None
        output_tokens_list = [] if calc_token else None

        # Count total screenshots
        total_screenshots = sum(1 for e in events if e['type'] == 'screenshot')

        while current_idx < len(events):
            batch_num += 1

            if verbose:
                print(f"\nProcessing batch {batch_num}...")

            start_idx = current_idx

            # Step 1: Generate new summary from screenshots and actions
            messages, current_idx = self.build_batch_message(
                events,
                screenshots_dir,
                current_idx,
                batch_size,
            )

            if verbose:
                print(f"  Processed events {start_idx} to {current_idx - 1}")

            new_summary = self.call_llm(messages)

            if new_summary == ERROR_CALLING_LLM:
                self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)
                result = {
                    "summary": accumulated_summary,
                    "error_batch_id": batch_num,
                }
                self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
                return result

            if verbose:
                print(f"=======new summary========\n{new_summary}")

            # Step 2: Merge with previous summary if exists
            if accumulated_summary:
                merged_summary = self.update_summary(accumulated_summary, new_summary)

                if merged_summary == ERROR_CALLING_LLM:
                    self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)
                    result = {
                        "summary": accumulated_summary,
                        "error_batch_id": batch_num,
                    }
                    self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
                    return result

                accumulated_summary = merged_summary
                if verbose:
                    print(f"=======merged summary========\n{merged_summary}")
            else:
                accumulated_summary = new_summary

            self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)

            if verbose:
                processed = sum(1 for e in events[:current_idx] if e['type'] == 'screenshot')
                print(f"Processed {processed}/{total_screenshots} screenshots")

        # Return successful result (no error)
        result = {"summary": accumulated_summary}
        self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
        return result

    def summarize_log_from_batch(
        self,
        log_path: str,
        screenshots_dir: Optional[str] = None,
        batch_size: int = 5,
        start_batch: int = 1,
        previous_summary: str = "",
        verbose: bool = True,
        calc_token: bool = False,
    ) -> dict:
        """Continue summarizing from a specific batch (after error).

        Args:
            log_path: Path to the processed.jsonl file.
            screenshots_dir: Directory containing screenshots. If None, inferred from log_path.
            batch_size: Number of screenshots to process per batch.
            start_batch: The batch number to start from (after the failed batch).
            previous_summary: The summary from previous batches before the error.
            verbose: Whether to print progress information.
            calc_token: Whether to track per-batch input/output token counts.

        Returns:
            Dict with 'summary' and optional 'error_batch_id'.
            When calc_token is True, also includes 'input_tokens' and 'output_tokens' lists.
        """
        # Infer screenshots directory
        if screenshots_dir is None:
            log_dir = os.path.dirname(log_path)
            screenshots_dir = log_dir

        # Load events
        events = []
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        if not events:
            return {"summary": "No events found in log."}

        if verbose:
            print(f"Loaded {len(events)} events from {log_path}")
            screenshot_count = sum(1 for e in events if e['type'] == 'screenshot')
            print(f"Found {screenshot_count} screenshots")
            print(f"Continuing from batch {start_batch} with batch_size={batch_size}...")

        # Find the starting index (skip events before the start_batch)
        # We need to count screenshots to find where to start
        current_idx = 0
        batch_num = 0
        screenshot_counter = 0
        target_screenshots = (start_batch - 1) * batch_size

        # Advance to the first screenshot of start_batch
        while current_idx < len(events) and screenshot_counter < target_screenshots:
            if events[current_idx]['type'] == 'screenshot':
                screenshot_counter += 1
            current_idx += 1

        # Now current_idx points to the first screenshot of start_batch
        accumulated_summary = previous_summary
        input_tokens_list = [] if calc_token else None
        output_tokens_list = [] if calc_token else None

        # Count total screenshots
        total_screenshots = sum(1 for e in events if e['type'] == 'screenshot')

        while current_idx < len(events):
            batch_num += 1

            if verbose:
                print(f"\nProcessing batch {start_batch + batch_num - 1}...")

            start_idx = current_idx

            # Step 1: Generate new summary from screenshots and actions
            messages, current_idx = self.build_batch_message(
                events,
                screenshots_dir,
                current_idx,
                batch_size,
            )

            if verbose:
                print(f"  Processed events {start_idx} to {current_idx - 1}")

            new_summary = self.call_llm(messages)

            if new_summary == ERROR_CALLING_LLM:
                batch_label = f"Batch {start_batch + batch_num - 1}"
                self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, batch_label, verbose)
                result = {
                    "summary": accumulated_summary,
                    "error_batch_id": start_batch + batch_num - 1,
                }
                self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
                return result

            if verbose:
                print(f"=======new summary========\n{new_summary}")

            # Step 2: Merge with previous summary if exists
            if accumulated_summary:
                merged_summary = self.update_summary(accumulated_summary, new_summary)

                if merged_summary == ERROR_CALLING_LLM:
                    batch_label = f"Batch {start_batch + batch_num - 1}"
                    self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, batch_label, verbose)
                    result = {
                        "summary": accumulated_summary,
                        "error_batch_id": start_batch + batch_num - 1,
                    }
                    self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
                    return result

                accumulated_summary = merged_summary
                if verbose:
                    print(f"=======merged summary========\n{merged_summary}")
            else:
                accumulated_summary = new_summary

            batch_label = f"Batch {start_batch + batch_num - 1}"
            self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, batch_label, verbose)

            if verbose:
                processed = sum(1 for e in events[:current_idx] if e['type'] == 'screenshot')
                print(f"Processed {processed}/{total_screenshots} screenshots")

        # Return successful result (no error)
        result = {"summary": accumulated_summary}
        self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
        return result