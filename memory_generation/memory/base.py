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

"""Base classes for memory generation."""

import base64
import io
import json
import os
import time
from typing import Optional
import re
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


class BaseMemoryGenerator:
    """Base class for memory generation.

    Selects the appropriate format_action function based on the model name.
    """

    RETRY_WAITING_SECONDS = 20

    # format_action -> list of model names
    _FORMAT_ACTION_MAP = {
        format_action_qwen3_5: ['Qwen3.5-397B-A17B', 'dashscope/qwen3.5-397b-a17b'],
        format_action_qwen3vl: ['Qwen3-VL-8B-Instruct', 'Qwen3-VL-32B-Instruct'],
        format_action_agentic: [
            'claude-opus-4-8',
            'claude-opus-4-7',
            'anthropic/claude-sonnet-4.6',
            'openai/gpt-5.5',
            'gemini-3.1-pro-preview',
            'google/gemini-3.1-pro-preview'
        ],
        format_action_mai_ui: ['./MAI-UI-8B'],
        format_action_ui_venus_1_5: ['./UI-Venus-1.5-8B'],
        format_action_gui_owl_1_5: ['./GUI-Owl-1.5-8B-Instruct']
        
    }

    # Model-to-generation_config mapping
    _GENERATION_CONFIG_MAP = {
        'Qwen3.5-397B-A17B': {'temperature': 0.0},
        'dashscope/qwen3.5-397b-a17b': {'temperature': 0.0},
        'Qwen3-VL-8B-Instruct': {'temperature': 0.0},
        'Qwen3-VL-32B-Instruct': {'temperature': 0.0},
        './MAI-UI-8B': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 16384},
        'openai/gpt-5.5': {},
        './UI-Venus-1.5-8B': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 10240},
        './GUI-Owl-1.5-8B-Instruct': {'temperature': 0.0, 'top_k': -1, 'top_p': 1.0, 'max_tokens': 10240},
        'claude-opus-4-8': {},
        'gemini-3.1-pro-preview': {'temperature': 0},
        'google/gemini-3.1-pro-preview': {'temperature': 0}
    }

    def __init__(
        self,
        model_name: str,
        max_retry: int = 3,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize the memory generator.

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
        self.memory_base = []
        self.memory_size = 0

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
                    if input_t > 15000:  # 异常高 token 时记录
                        print(f"[ALERT] High input tokens: {input_t}")
                        print(f"  Messages count: {len(messages)}")
                        for i, msg in enumerate(messages):
                            content = msg.get('content', '')
                            if isinstance(content, list):
                                img_count = sum(1 for c in content if c.get('type') == 'image_url')
                                text_len = sum(len(c.get('text', '')) for c in content if c.get('type') == 'text')
                                print(f"  Message[{i}]: role={msg['role']}, images={img_count}, text_len={text_len}")
                            else:
                                print(f"  Message[{i}]: role={msg['role']}, content_len={len(content)}")
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
        "You are analyzing a user's operation log on an Android device. "
    )

    BATCH_PROMPT = (
        "I will show you screenshots with the running app, and the actions the user performed before each screenshot. "
        "Please analyze the user's activity and generate a 'Memory Event' for each app.\n\n"
        "For each app, output in the following format:\n"
        "App: <app name>\n"
        "Event: <A descriptive summary of the user's journey and key interactions. "
        "DO NOT use over-generalized summaries like 'User browsed the app'. "
        "Preserve the sequence of key items/categories interacted with (e.g., 'Browsed T-shirts, compared a yellow one, then switched to sneakers'). "
        "Capture transitions: If the user changed their mind or compared items, reflect that in the event description.>\n"
        "Details: <Extract all specific data points as a plain text list. "
        "Focus on 'Hard Data': 1) Numeric values (verification codes, prices, quantities, durations); "
        "2) Proper nouns (brand names, restaurant names, item titles); "
        "3) Specific attributes (color, size, specifications). "
        "If no specific details are found, use None.>\n"
        "State: <finished or ongoing>\n"
        "Start Time: <start time in format 'Apr 22 14:30' or None if unknown>\n"
        "End Time: <end time in format 'Apr 22 14:45' or None if unknown>\n\n"
        "State Definition:\n"
        "- **finished**: The task within this app reached a terminal point (e.g., payment confirmed, message sent, '=' pressed in calculator, final search result selected).\n"
        "- **ongoing**: The task is incomplete or the user exited prematurely (e.g., form partially filled, still browsing, expression left hanging). "
        "If the last operation does not represent a definitive 'Commit' or 'Result' action, mark as 'ongoing'.\n\n"
        "Example:\n"
        "App: taodian\n"
        "Event: User searched for T-shirts, compared a white one (59 RMB) and a yellow one (Size L, 79 RMB), added the yellow T-shirt to the cart, then switched to viewing Nike Air Max shoes (799 RMB).\n"
        "Details: White T-shirt (59 RMB); Yellow T-shirt (Size L, 79 RMB); Nike Air Max (799 RMB).\n"
        "State: ongoing\n"
        "Start Time: Apr 22 14:30\n"
        "End Time: Apr 22 14:45\n\n"
        "Guidelines:\n"
        "1. The current system time is in the upper left corner.\n"
        "2. In the 'Details' field, prioritize recording 'hard information' (numbers, specific names) "
        "as this will serve as long-term memory for future retrieval.\n"
        "3. The name of the running app is provided along with the screenshot. Please do not modify the app name on your own. If no app is identified, use None as the app name.\n\n"
    )

    # CREATE_EVENT_PROMPT removed: batch prompt now directly outputs Event/Details/State,
    # so a separate generate_event LLM call is no longer needed.
    UPDATE_EVENT_PROMPT = (
        "Your goal is to integrate a NEW Memory Event into an EXISTING Memory Event. You must merge them into a single, cohesive narrative that reflects the entire journey within this app session.\n\n"

        "### 1. Integration Rules (Seamless Narrative):\n"
        "- **Identify Continuity**: If the new event continues the previous task (e.g., previously searched for shoes, now filtering by size), merge them into a single flow.\n"
        "- **Capture Pivots**: If the user abandoned the previous task for something new (e.g., stopped looking at shoes and started searching for electronics), reflect this transition (e.g., 'After looking at shoes, the user shifted focus to...').\n"
        "- **Deduplication**: If the new event repeats information from the existing event, do not list it twice; prioritize the most recent state or progress.\n\n"

        "### 2. Details Merging Rule:\n"
        "- Combine the 'Existing Details' with 'New Details' into one comprehensive list.\n"
        "- **Conflict Resolution**: If a value has changed (e.g., quantity updated from 1 to 2), keep the most recent data point.\n"
        "- Ensure all hard data (prices, codes, specs) from both sets are preserved unless they are outdated.\n\n"

        "### 3. State Re-evaluation:\n"
        "- **finished**: The combined journey has now reached a terminal point (e.g., payment completed, final result obtained).\n"
        "- **ongoing**: The task remains incomplete, or the user is still in the middle of a new workflow.\n"
        "- **Note**: Even if the previous state was 'ongoing', it can now become 'finished' if the new event completes the task.\n\n"

        "### Output Format:\n"
        "Event: <A single integrated summary combining existing and new events>\n"
        "Details: <Merged list of all specific data points (Numeric values, Proper nouns, Specific attributes).>\n"
        "State: <finished or ongoing>\n\n"

        "### Example:\n"
        "Existing Event: User browsed for laptops and compared two Dell models.\n"
        "Existing Details: Dell XPS 13 ($1200), Dell Inspiron ($800).\n"
        "New Event: User decided on the Dell XPS 13, configured it with 16GB RAM, and completed the checkout.\n"
        "New Details: Dell XPS 13 (16GB RAM upgrade, Total $1350).\n\n"
        "Output:\n"
        "Event: After comparing Dell laptops, the user selected the XPS 13 model, upgraded the RAM to 16GB, and successfully completed the purchase.\n"
        "Details: Dell XPS 13 (16GB RAM, $1350); Dell Inspiron ($800).\n"
        "State: finished\n\n"

        "### Input Data to Merge:\n"
        "App: {app_name}\n"
        "**[Existing Context]**\n"
        "Existing Event: {existing_event}\n"
        "Existing Details: {existing_details}\n\n"
        "**[New Information]**\n"
        "New Event: {new_event}\n"
        "New Details: {new_details}"
    )
    def get_system_prompt(self) -> str:
        """Get the system prompt with identity and task description.

        Subclasses can override this method or the SYSTEM_PROMPT class attribute.

        Returns:
            System prompt string.
        """
        return self.SYSTEM_PROMPT

    def get_batch_prompt(self) -> str:
        """Get the prompt for each batch (same for all batches).

        Subclasses can override this method or the BATCH_PROMPT class attribute.

        Returns:
            Prompt string for each batch.
        """
        return self.BATCH_PROMPT

    # get_create_event_prompt removed: batch prompt now directly outputs Event/Details/State

    def get_update_event_prompt(self) -> str:
        """Get the prompt for merging a new event into an existing event.

        Subclasses can override this method or the UPDATE_EVENT_PROMPT class attribute.

        Returns:
            Prompt string with {existing_event}, {existing_details}, {new_event}, {new_details} placeholders.
        """
        return self.UPDATE_EVENT_PROMPT
    def extract_update_event(self, response: str) -> tuple[str, str, str]:
        """Extract event info from LLM response when updating an existing event.

        Args:
            response: The raw response from the LLM.

        Returns:
            Tuple of (event, details, state).
        """
        event_match = re.search(r'Event:\s*(.+?)(?=\n(?:Details|State)|$)', response, re.DOTALL | re.IGNORECASE)
        details_match = re.search(r'Details:\s*(.+?)(?=\n(?:State|Event)|$)', response, re.DOTALL | re.IGNORECASE)
        state_match = re.search(r'State:\s*(.+?)(?=\n(?:Event|Details)|$)', response, re.DOTALL | re.IGNORECASE)

        event = event_match.group(1).strip() if event_match else ""
        details = details_match.group(1).strip() if details_match else ""
        state = "ongoing"
        if state_match:
            state_str = state_match.group(1).strip().lower()
            if state_str in ('finished', 'ongoing'):
                state = state_str

        return event, details, state

    # extract_create_event removed: batch response now directly contains Event/Details/State
    def parse_batch_events(self, response: str) -> list[dict]:
        """Parse the LLM batch response to extract event entries directly.

        Args:
            response: The raw response from the LLM.

        Returns:
            List of dictionaries, each containing:
            - app: App name
            - event: Event description
            - details: Key specific data
            - state: 'finished' or 'ongoing'
            - timestamp_start: Start time string
            - timestamp_end: End time string
        """
        result = []
        blocks = re.split(r'\n(?=App:)', response.strip(), flags=re.IGNORECASE)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            app = re.search(r'App:\s*(.+?)(?=\n(?:Event|Details|State|Start Time|End Time)|$)', block, re.DOTALL | re.IGNORECASE)
            event = re.search(r'Event:\s*(.+?)(?=\n(?:Details|State|Start Time|End Time|App)|$)', block, re.DOTALL | re.IGNORECASE)
            details = re.search(r'Details:\s*(.+?)(?=\n(?:State|Start Time|End Time|App|Event)|$)', block, re.DOTALL | re.IGNORECASE)
            state = re.search(r'State:\s*(.+?)(?=\n(?:Start Time|End Time|App|Event|Details)|$)', block, re.DOTALL | re.IGNORECASE)
            ts_start = re.search(r'Start Time:\s*(.+?)(?=\n(?:End Time|App|Event|Details|State)|$)', block, re.DOTALL | re.IGNORECASE)
            ts_end = re.search(r'End Time:\s*(.+?)(?=\n(?:App|Event|Details|State|Start Time)|$)', block, re.DOTALL | re.IGNORECASE)

            if app:
                state_str = "ongoing"
                if state:
                    s = state.group(1).strip().lower()
                    if s in ('finished', 'ongoing'):
                        state_str = s
                result.append({
                    'app': app.group(1).strip(),
                    'event': event.group(1).strip() if event else '',
                    'details': details.group(1).strip() if details else '',
                    'state': state_str,
                    'timestamp_start': ts_start.group(1).strip() if ts_start else '',
                    'timestamp_end': ts_end.group(1).strip() if ts_end else '',
                })

        return result
    # generate_event removed: batch prompt now directly outputs Event/Details/State,
    # so a separate LLM call to generate events from operations is no longer needed.
    def update_event(self, memory: dict, new_event: str, new_details: str = '', timestamp_end: Optional[str] = None) -> dict:
        """Merge a new event into an existing event.

        Args:
            memory: Memory dict containing the existing event.
            new_event: New event description to merge.
            new_details: Key specific data from the new batch analysis.
            timestamp_end: End timestamp for the updated event.

        Returns:
            Updated memory dict with merged event, details, state, and timestamp_end.
        """
        app_name = memory.get('app', '')
        event = memory.get('event', '')
        existing_details = memory.get('details', '')
        prompt = self.get_update_event_prompt().format(app_name=app_name, existing_event=event, existing_details=existing_details, new_event=new_event, new_details=new_details)
        messages = [
            {'role': 'system', 'content': self.get_system_prompt()},
            {'role': 'user', 'content': prompt},
        ]
        response = self.call_llm(messages)

        if response and response != ERROR_CALLING_LLM:
            event, details, state = self.extract_update_event(response)
            memory['event'] = event
            memory['details'] = details
            memory['state'] = state
            if timestamp_end:
                memory['timestamp_end'] = timestamp_end
        return memory
    def create(self, memory: dict) -> None:
        memory['index'] = self.memory_size
        self.memory_base.append(memory)
        self.memory_size += 1
        print(f"[Create] New memory: {memory}")

    def delete(self, memory_idx) -> None:
        self.memory_base.pop(memory_idx)

    def update(self, memory_idx: int, memory: dict) -> None:
        """Update a memory entry at the specified index.

        Args:
            memory_idx: Index of the memory to update.
            memory: New memory dict to replace the old one.
        """
        for i, m in enumerate(self.memory_base):
            if m.get('index') == memory_idx:
                self.memory_base[i] = memory
                print(f"[Update] Memory at index {memory_idx}: {memory}")
                break

    def find_memories_by_app(self, app_name: str) -> list:
        """Find all memory entries for a specific app.

        Args:
            app_name: Name of the app to search for.

        Returns:
            List of memory entries (dicts) matching the app name.
        """
        return [memory for memory in self.memory_base if memory.get('app') == app_name]

    # Canonical app name -> list of possible aliases (all lowercased).
    APP_NAME_ALIASES: dict[str, list[str]] = {
        'simple sms messenger': ['simple sms', 'sms messenger', 'sms', 'simple sms'],
        '2048': ['2048', '2048 game', '2048 open ...'],
        'calculator': ['calculator', 'calc'],
        'tuantuanwaimai': ['tuantuanwaimai', 'tuantuan waimai', '团团外卖'],
        'broccoli': ['broccoli'],
        'jingdian': ['jingdian', '京店'],
        'taodian': ['taodian', '淘店'],
        'gauguin': ['gauguin'],
        'librera fd': ['librera fd'],
        'simple gallery': ['simple gallery', 'gallery'],
        'clock': ['clock'],
        'simple calendar': ['simple calendar'],
        'simple draw': ['simple draw', 'draw'],
        'contacts': ['contacts'],
        'pro expense': ['pro expense', 'expense'],
        'retro music': ['retro music'],
        'phone': ['phone', 'phone'],
        'settings': ['settings'],
        'opentracks': ['opentracks'],
        'joplin': ['joplin'],
        'files': ['files'],
        'markor': ['markor'],
        'chilemei': ['chilemei', '吃了没', ],
        'osmand': ['osmand'],

    }

    def normalize_app_name(self, app_name: str) -> str:
        """Normalize app name to a standard format.

        Args:
            app_name: App name to normalize.

        Returns:
            Normalized (canonical) app name.
        """
        key = app_name.lower().strip()
        for canonical, aliases in self.APP_NAME_ALIASES.items():
            if key == canonical or key in aliases:
                return canonical
        return key
    def build_batch_message(
        self,
        events: list[dict],
        screenshots_dir: str,
        start_idx: int,
        batch_size: int,
    ) -> tuple[list[dict], int]:
        """Build a message for one batch of screenshots and actions.

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

        # Use unified prompt for all batches
        prompt = self.get_batch_prompt()
        content.append({'type': 'text', 'text': prompt})


        # Process events until we have batch_size screenshots
        while current_idx < len(events) and screenshot_count < batch_size:
            event = events[current_idx]

            if event['type'] == 'screenshot':
                # Load screenshot to get dimensions for formatting actions
                screenshot_path = os.path.join(screenshots_dir, event['screenshot_path'].replace('\\', os.sep))
                if os.path.exists(screenshot_path):
                    image = load_image(screenshot_path)

                    # Add actions BEFORE screenshot (chronological order)
                    if actions_before_screenshot:
                        actions_text = "Actions performed:\n" + "\n".join(
                            f"  - {self.format_action(a, _WIDTH, _HEIGHT)}" for a in actions_before_screenshot
                        )
                        content.append({'type': 'text', 'text': actions_text + "\n"})
                        actions_before_screenshot = []

                    # Then add screenshot
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
                # Collect actions
                actions_before_screenshot.append(event)

            current_idx += 1

        # Add any remaining actions after the last screenshot
        if actions_before_screenshot and screenshot_count > 0:
            actions_text = "\nActions after last screenshot:\n" + "\n".join(
                f"  - {self.format_action(a, _WIDTH, _HEIGHT)}" for a in actions_before_screenshot
            )
            content.append({'type': 'text', 'text': actions_text})

        messages = [
            {'role': 'system', 'content': self.get_system_prompt()},
            {'role': 'user', 'content': content},
        ]
        return messages, current_idx

    def generate_memory(
        self,
        log_path: str,
        screenshots_dir: Optional[str] = None,
        batch_size: int = 10,
        verbose: bool = True,
        calc_token: bool = False,
    ) -> dict:
        """Generate memory from a user operation log.

        Args:
            log_path: Path to the processed.jsonl file.
            screenshots_dir: Directory containing screenshots. If None, inferred from log_path.
            batch_size: Number of screenshots to process per batch.
            verbose: Whether to print progress information.
            calc_token: Whether to track per-batch input/output token counts.

        Returns:
            Dict with 'memory' and optional 'error_batch_id'.
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
            return {"memory": "No events found in log."}

        if verbose:
            print(f"Loaded {len(events)} events from {log_path}")
            screenshot_count = sum(1 for e in events if e['type'] == 'screenshot')
            print(f"Found {screenshot_count} screenshots")
            print(f"Processing in batches of {batch_size} screenshots...")

        # Process in batches
        current_idx = 0
        batch_num = 0
        input_tokens_list = [] if calc_token else None
        output_tokens_list = [] if calc_token else None

        # Count total screenshots
        total_screenshots = sum(1 for e in events if e['type'] == 'screenshot')

        while current_idx < len(events):
            batch_num += 1
            if verbose:
                print(f"\nProcessing batch {batch_num}...")

            messages, current_idx = self.build_batch_message(
                events,
                screenshots_dir,
                current_idx,
                batch_size,
            )

            response = self.call_llm(messages)

            if response == ERROR_CALLING_LLM:
                self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)
                result = {
                    "memory": self.memory_base,
                    "error_batch_id": batch_num,
                }
                self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
                return result
            if verbose:
                print(f"=======current response========\n{response}")

            # Parse the response to extract event entries directly from batch output
            try:
                parsed_events = self.parse_batch_events(response)
            except Exception as e:
                print(f"[Warning] Failed to parse batch {batch_num} response: {e}")
                parsed_events = []

            for entry in parsed_events:
                try:
                    app_name = entry.get('app', 'None')
                    if app_name == 'None':
                        continue
                    app_name = self.normalize_app_name(app_name)
                    event = entry.get('event', '')
                    details = entry.get('details', '')
                    state = entry.get('state', 'ongoing')
                    ts_start = entry.get('timestamp_start', '')
                    ts_end = entry.get('timestamp_end', '')
                    memories = self.find_memories_by_app(app_name)
                    if memories:
                        latest_memory = memories[-1]
                        if latest_memory.get('state') == "finished":
                            # Previous event finished, create new memory directly from batch output
                            self.create({
                                "app": app_name,
                                "state": state,
                                "event": event,
                                "details": details,
                                "timestamp_start": ts_start,
                                "timestamp_end": ts_end,
                            })
                        elif latest_memory.get('state') == "ongoing":
                            # Merge new event into existing ongoing event
                            self.update(latest_memory.get('index'), self.update_event(latest_memory, event, details, ts_end))
                    else:
                        # No existing memory, create directly from batch output
                        self.create({
                            "app": app_name,
                            "state": state,
                            "event": event,
                            "details": details,
                            "timestamp_start": ts_start,
                            "timestamp_end": ts_end,
                        })
                except Exception as e:
                    print(f"[Warning] Failed to process entry in batch {batch_num}: {e}")

            self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)

            if verbose:
                processed = sum(1 for e in events[:current_idx] if e['type'] == 'screenshot')
                print(f"Processed {processed}/{total_screenshots} screenshots")
        # Return successful result - return the last batch's parsed events (preliminary)
        result = {"memory": self.memory_base}
        self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
        return result

    def generate_memory_from_batch(
        self,
        log_path: str,
        screenshots_dir: Optional[str] = None,
        batch_size: int = 10,
        start_batch: int = 1,
        previous_memory: list = None,
        verbose: bool = True,
        calc_token: bool = False,
    ) -> dict:
        """Continue generating memory from a specific batch (after error).

        Args:
            log_path: Path to the processed.jsonl file.
            screenshots_dir: Directory containing screenshots. If None, inferred from log_path.
            batch_size: Number of screenshots to process per batch.
            start_batch: The batch number to start from (after the failed batch).
            previous_memory: The memory list from previous batches before the error.
            verbose: Whether to print progress information.
            calc_token: Whether to track per-batch input/output token counts.

        Returns:
            Dict with 'memory' and optional 'error_batch_id'.
            When calc_token is True, also includes 'input_tokens' and 'output_tokens' lists.
        """
        # Restore previous memory state
        if previous_memory is not None:
            self.memory_base = previous_memory
            self.memory_size = len(previous_memory)
        else:
            self.memory_base = []
            self.memory_size = 0

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
            return {"memory": self.memory_base}

        if verbose:
            print(f"Loaded {len(events)} events from {log_path}")
            screenshot_count = sum(1 for e in events if e['type'] == 'screenshot')
            print(f"Found {screenshot_count} screenshots")
            print(f"Continuing from batch {start_batch} with batch_size={batch_size}...")

        # Find the starting index (skip events before the start_batch)
        current_idx = 0
        screenshot_counter = 0
        target_screenshots = (start_batch - 1) * batch_size

        # Advance to the first screenshot of start_batch
        while current_idx < len(events) and screenshot_counter < target_screenshots:
            if events[current_idx]['type'] == 'screenshot':
                screenshot_counter += 1
            current_idx += 1

        # Count total screenshots
        total_screenshots = sum(1 for e in events if e['type'] == 'screenshot')
        batch_num = start_batch - 1
        input_tokens_list = [] if calc_token else None
        output_tokens_list = [] if calc_token else None

        while current_idx < len(events):
            batch_num += 1
            if verbose:
                print(f"\nProcessing batch {batch_num}...")

            messages, current_idx = self.build_batch_message(
                events,
                screenshots_dir,
                current_idx,
                batch_size,
            )

            response = self.call_llm(messages)

            if response == ERROR_CALLING_LLM:
                self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)
                result = {
                    "memory": self.memory_base,
                    "error_batch_id": batch_num,
                }
                self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
                return result
            if verbose:
                print(f"=======current response========\n{response}")

            # Parse the response to extract event entries directly from batch output
            try:
                parsed_events = self.parse_batch_events(response)
            except Exception as e:
                print(f"[Warning] Failed to parse batch {batch_num} response: {e}")
                parsed_events = []

            for entry in parsed_events:
                try:
                    app_name = entry.get('app', 'None')
                    if app_name == 'None':
                        continue
                    event = entry.get('event', '')
                    details = entry.get('details', '')
                    state = entry.get('state', 'ongoing')
                    ts_start = entry.get('timestamp_start')
                    ts_end = entry.get('timestamp_end')
                    memories = self.find_memories_by_app(app_name)
                    if memories:
                        latest_memory = memories[-1]
                        if latest_memory.get('state') == "finished":
                            # Previous event finished, create new memory directly from batch output
                            self.create(
                                {
                                    "app": app_name,
                                    "state": state,
                                    "event": event,
                                    "details": details,
                                    "timestamp_start": ts_start,
                                    "timestamp_end": ts_end,
                            })
                        elif latest_memory.get('state') == "ongoing":
                            # Merge new event into existing ongoing event
                            self.update(latest_memory.get('index'), self.update_event(latest_memory, event, details, ts_end))
                    else:
                        # No existing memory, create directly from batch output
                        self.create(
                            {
                                "app": app_name,
                                "state": state,
                                "event": event,
                                "details": details,
                                "timestamp_start": ts_start,
                                "timestamp_end": ts_end,
                        })
                except Exception as e:
                    print(f"[Warning] Failed to process entry in batch {batch_num}: {e}")

            self._collect_round_tokens(calc_token, input_tokens_list, output_tokens_list, f"Batch {batch_num}", verbose)

            if verbose:
                processed = sum(1 for e in events[:current_idx] if e['type'] == 'screenshot')
                print(f"Processed {processed}/{total_screenshots} screenshots")

        # Return successful result
        result = {"memory": self.memory_base}
        self._attach_tokens(result, calc_token, input_tokens_list, output_tokens_list)
        return result
