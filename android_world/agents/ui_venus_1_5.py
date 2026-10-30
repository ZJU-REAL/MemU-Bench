

"""UI_Venus_1_5 based agent for Android interaction."""

import json
import re
import time
from typing import List, Tuple

from absl import logging
from android_world.agents import agent_utils
from android_world.agents import base_agent
from android_world.agents import infer
from android_world.agents import m3a_utils
from android_world.env import interface
from android_world.env import json_action
from typing import Optional
USER_PROMPT = """
**You are a GUI Agent.**
Your task is to analyze a given user task, review current screenshot and previous actions, and determine the next action to complete the task.

### Available Actions
You may execute one of the following functions:
- Click(box=(x1,y1))
- Drag(start=(x1,y1), end=(x2,y2))
- Scroll(start=(x1,y1), end=(x2,y2))
- Type(content='')
- Launch(app='')
- Wait()
- Finished(content='')
- CallUser(content='')
- LongPress(box=(x1,y1))
- PressBack()
- PressHome()
- PressEnter()
- PressRecent()

### User Task
{user_task}

{user_history}
### Previous Actions
{previous_actions}

### Output Format
​think your thinking process ​/think
<action> the next action </action>
<conclusion> the conclusion about the next action </conclusion>

### Instruction
- Make sure you understand the task goal to avoid wrong actions.
- Make sure you carefully examine the the current screenshot. Sometimes the summarized history might not be reliable, over-claiming some effects.
- For requests that are questions (or chat messages), remember to use the `CallUser` action to reply to user explicitly before finishing! Then, after you have replied, use the Finished action if the goal is achieved.
- Consider exploring the screen by using the `scroll` action with different directions to reveal additional content.
- To copy some text: first select the exact text you want to copy, which usually also brings up the text selection bar, then click the `copy` button in bar.
- To paste text into a text box, first long press the text box, then usually the text selection bar will appear with a `paste` button in it.
"""

ASK_USER_PROMPT = "None"

def parse_coordinates(coord_str: str) -> Optional[Tuple[float, float]]:
    if not coord_str:
        return None, None

    coord_str_clean = coord_str.replace(" ", "")
    match = re.match(r"\(([\d.]+),([\d.]+)\)", coord_str_clean)
    if match:
        return float(match.group(1)), float(match.group(2))

    match = re.match(r"\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", coord_str)
    if match:
        return float(match.group(1)), float(match.group(2))

    return None, None

def _split_parameters(params_str: str) -> list:
    param_parts = []
    current_part = ""

    in_quotes = False
    quote_char = None
    bracket_level = 0

    for char in params_str:
        if char in ['"', "'"] and not in_quotes:
            in_quotes = True
            quote_char = char
        elif char == quote_char and in_quotes:
            in_quotes = False
            quote_char = None

        elif not in_quotes:
            if char == '(':
                bracket_level += 1
            elif char == ')':
                bracket_level -= 1
            elif char == ',' and bracket_level == 0:
                param_parts.append(current_part.strip())
                current_part = ""
                continue

        current_part += char

    if current_part.strip():
        param_parts.append(current_part.strip())

    return param_parts

def parse_answer(action_str: str):
    pattern = r"^(\w+)\((.*)\)$"
    match = re.match(pattern, action_str.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"Invalid action_str format: {action_str}")

    action_type = match.group(1)
    params_str = match.group(2).strip()
    params = {}

    if params_str:
        try:
            param_pairs = _split_parameters(params_str)

            for pair in param_pairs:
                if '=' in pair:
                    key, value = pair.split("=", 1)
                    value = value.strip("'").strip()
                    params[key.strip()] = value
                else:
                    params[pair.strip()] = None
        except Exception as e:
            print(f"Answer parse error: {e}")

    if action_type == 'Click':
        p_x, p_y = parse_coordinates(params.get("box", ""))
        if p_x is not None and p_y is not None:
            return 'Click', {'box': (p_x, p_y)}
        else:
            raise ValueError(f"action {action_type} Unknown click params: {repr(params)}")
    elif action_type == 'LongPress':
        p_x, p_y = parse_coordinates(params.get("box", ""))
        if p_x is not None and p_y is not None:
            return 'LongPress', {'box': (p_x, p_y)}
        else:
            raise ValueError(f"action {action_type} Unknown long press params: {repr(params)}")
    elif action_type == 'Drag':
        p_x, p_y = parse_coordinates(params.get("start", ""))
        e_x, e_y = parse_coordinates(params.get("end", ""))
        if p_x is not None and p_y is not None and e_x is not None and e_y is not None:
            return 'Drag', {'start': (p_x, p_y), 'end': (e_x, e_y)}
        else:
            raise ValueError(f"action {action_type} Unknown drag params: {repr(params)}")
    elif action_type == 'Scroll':
        p_x, p_y = parse_coordinates(params.get("start", ""))
        e_x, e_y = parse_coordinates(params.get("end", ""))
        if p_x is not None and p_y is not None and e_x is not None and e_y is not None:
            return 'Scroll', {'start': (p_x, p_y), 'end': (e_x, e_y), 'direction': ''}
        elif "direction" in params:
            direction = params.get("direction")
            return 'Scroll', {'start': (), 'end': (), 'direction': direction}
        else:
            raise ValueError(f"action {action_type} Unknown scroll params: {repr(params)}")
    elif action_type == 'Type':
        key = 'content'
        type_text = params.get(key)
        if type_text is not None:
            return 'Type', {'content': type_text}
        else:
            raise ValueError(f"action {action_type} Unknown type params: {repr(params)}")
    elif action_type == 'CallUser':
        key = 'content'
        call_text = params.get(key)
        if call_text is not None:
            return 'CallUser', {'content': call_text}
        else:
            raise ValueError(f"action {action_type} Unknown call user params: {repr(params)}")
    elif action_type == 'Launch':
        app = params.get("app", "")
        url = params.get("url", "")
        if app is not None:
            return 'Launch', {'app': app, 'url': url}
        else:
            raise ValueError(f"action {action_type} Unknown launch params: {repr(params)}")
    elif action_type == 'Finished':
        key = 'content'
        finished_text = params.get(key, "")
        return 'Finished', {'content': finished_text}
    elif action_type == 'Wait':
        return 'Wait', {}
    elif action_type == 'PressBack':
        return 'PressBack', {}
    elif action_type == 'PressHome':
        return 'PressHome', {}
    elif action_type == 'PressEnter':
        return 'PressEnter', {}
    elif action_type == 'PressRecent':
        return 'PressRecent', {}
    else:
        raise ValueError(f"action {action_type} Unknown action: {repr(params)}")

class UI_Venus_1_5(base_agent.EnvironmentInteractingAgent):
  """Agent powered by UI_Venus_1_5 model for Android interaction."""

  def __init__(
      self,
      env: interface.AsyncEnv,
      llm: infer.MultimodalLlmWrapper,
      name: str = 'UI_Venus_1_5',
      wait_after_action_seconds: float = 2.0,
  ):
    """Initializes a UI_Venus_1_5 Agent.

    Args:
      env: The environment.
      llm: The multimodal LLM wrapper.
      name: The agent name.
      wait_after_action_seconds: Seconds to wait for the screen to stablize
        after executing an action
    """
    super().__init__(env, name)
    self.llm = llm
    self.history = []
    self.additional_guidelines = None
    self.wait_after_action_seconds = wait_after_action_seconds
    self.coordinate_type = "relative"

  def set_task_guidelines(self, task_guidelines: list[str]) -> None:
    self.additional_guidelines = task_guidelines

  def reset(self, go_home_on_reset: bool = False):
    super().reset(go_home_on_reset)
    # Hide the coordinates on screen which might affect the vision model.
    self.env.hide_automation_ui()
    self.history = []

  def step(self, goal: str, information: str = '', filtered_user_history: str = '', ask: bool = False) -> base_agent.AgentInteractionResult:
    step_data = {
        'raw_screenshot': None,
        'action_prompt': None,
        'action_output': None,
        'action_output_json': None,
        'action_reason': None,
        'action': None,
        'action_raw_response': None,
        'user_response': None,
    }
    if ask:
      assert False, "unsupported ask for UI_Venus_1_5"
    state = self.get_post_transition_state()

    step_data['raw_screenshot'] = state.pixels.copy()


    # print("action_prompt: {}".format(action_prompt))
    history_entries = [
        f"Step {i}: <think>{step_info['action_reason']}</think><action>{step_info['action']}</action>" + (f" User response: {step_info['user_response']}" if step_info.get('user_response') else "")
        for i, step_info in enumerate(self.history)
    ]
    history_str = "\n".join(history_entries)
    # print(f"history: {history_str}")
    action_prompt = USER_PROMPT.format(
       user_task=goal, 
        previous_actions=history_str,
        user_history=f"###User Operations History\nHere is some generated information about the user's previous operations, which may help achieve the user's goals:\n{filtered_user_history}\n\n" if filtered_user_history else '')
    step_data['action_prompt'] = action_prompt
    action_output, is_safe, raw_response = self.llm.predict_mm(
        action_prompt,
        [
            step_data['raw_screenshot'],
        ],
        generation_config={
          "temperature": 0.0,
          "top_p": 1.0,
          "max_tokens": 4096,
        }
    )
    print('===== LLM RAW OUTPUT START =====')
    print(action_output)
    print('===== LLM RAW OUTPUT END =====')
    if is_safe == False:  # pylint: disable=singleton-comparison
      #  is_safe could be None
      action_output = f"""Reason: {m3a_utils.TRIGGER_SAFETY_CLASSIFIER}
Action: {{"action_type": "status", "goal_status": "infeasible"}}"""

    if not raw_response:
      raise RuntimeError('Error calling LLM in action selection phase.')
    step_data['action_output'] = action_output
    step_data['action_raw_response'] = raw_response

    original_width, original_height = step_data['raw_screenshot'].shape[1], step_data['raw_screenshot'].shape[0]

    size_params = {
        'original_width': original_width,
        'original_height': original_height,
    }

    try:
        think_text = action_output.split("<think>")[1].split("</think>")[0].strip("\n")
        if think_text == "":
          think_text = action_output.split("/think")[0].strip("\n").lstrip('think')
        if think_text == "":
          think_text = action_output.split("<action>")[0]
    except (IndexError, ValueError):
        think_text = ""
    try:
        answer_text = action_output.split("<action>")[1].split("</action>")[0].strip("\n")
    except (IndexError, ValueError):
        answer_text = ""
    try:
      action_name, action_params = parse_answer(answer_text)
      action_json = {'action': action_name, 'params': action_params}
    except Exception as e:
      return base_agent.AgentInteractionResult(
          False,
          step_data,
      )
    action_json = self._convert_coordinate(action_json, size_params)
    reason = think_text
    action = self.map_action(action_json)
    # print("action_json: {}".format(action_json))
    # print("mapped action: {}".format(action))
    # If the output is not in the right format, return.
    if (not reason) or (not action):
      print('Action prompt output is not in the correct format.')
      self.history.append(step_data)

      return base_agent.AgentInteractionResult(
          False,
          step_data,
      )


    step_data['action_reason'] = reason
    step_data['action'] = answer_text
    try:
      converted_action = json_action.JSONAction(**action)
      step_data['action_output_json'] = converted_action
    except Exception as e:  # pylint: disable=broad-exception-caught
      print('Failed to convert the output to a valid action.')
      print(str(e))
      self.history.append(step_data)

      return base_agent.AgentInteractionResult(
          False,
          step_data,
      )

    if converted_action.action_type == 'status':
      if converted_action.goal_status == 'infeasible':
        print('Agent stopped since it thinks mission impossible.')
      self.history.append(step_data)
      return base_agent.AgentInteractionResult(
          True,
          step_data,
      )

    if converted_action.action_type == 'answer':
      print('Agent answered with: %s', converted_action.text)

    if converted_action.action_type == 'ask':
      step_data['user_response'] = 'I cannot answer this question.'
      print('Agent asked: {}'.format(converted_action.text))
      print('User responded: {}'.format(step_data['user_response']))
      self.history.append(step_data)
      return base_agent.AgentInteractionResult(
          False,
          step_data,
      )

    try:
      self.env.execute_action(converted_action)
    except Exception as e:  # pylint: disable=broad-exception-caught
      print('Failed to execute action.')
      print(str(e))
      self.history.append(step_data)
      return base_agent.AgentInteractionResult(
          False,
          step_data,
      )

    time.sleep(self.wait_after_action_seconds)

    self.history.append(step_data)
    return base_agent.AgentInteractionResult(
        False,
        step_data,
    )

  def map_action(self, action_json: dict) -> dict:
    """Maps the model's action to JSONAction format.

    Args:
      action_json: The action from parse_answer, e.g.,
        {'action': 'Click', 'params': {'box': (x, y)}}

    Returns:
      A dict that can be used to create json_action.JSONAction.
    """
    action_name = action_json.get('action', '')
    params = action_json.get('params', {})

    if action_name == 'Click':
      box = params.get('box', (0, 0))
      return {
          'action_type': 'click',
          'x': int(box[0]),
          'y': int(box[1]),
      }
    elif action_name == 'LongPress':
      box = params.get('box', (0, 0))
      return {
          'action_type': 'long_press',
          'x': int(box[0]),
          'y': int(box[1]),
      }
    elif action_name == 'Drag':
      # Drag direction refers to finger movement, but android_world
      # scroll direction refers to content movement, so we need to reverse.
      start = params.get('start', (0, 0))
      end = params.get('end', (0, 0))
      dx = end[0] - start[0]
      dy = end[1] - start[1]
      if abs(dy) >= abs(dx):
        # dy > 0 means finger moves down, so content should scroll up
        direction = 'up' if dy > 0 else 'down'
      else:
        # dx > 0 means finger moves right, so content should scroll left
        direction = 'left' if dx > 0 else 'right'
      return {
          'action_type': 'scroll',
          'direction': direction,
      }
    elif action_name == 'Scroll':
      # Scroll direction in prompt refers to finger movement, but
      # android_world scroll direction refers to content movement.
      direction_map = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
      # If direction is explicitly provided, reverse it
      if 'direction' in params and params['direction']:
        direction = direction_map.get(params['direction'], params['direction'])
        return {
            'action_type': 'scroll',
            'direction': direction,
        }
      # Otherwise calculate from start/end (finger movement) and reverse
      start = params.get('start', (0, 0))
      end = params.get('end', (0, 0))
      if start and end:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if abs(dy) >= abs(dx):
          # dy > 0 means finger moves down, so content should scroll up
          direction = 'up' if dy > 0 else 'down'
        else:
          # dx > 0 means finger moves right, so content should scroll left
          direction = 'left' if dx > 0 else 'right'
        return {
            'action_type': 'scroll',
            'direction': direction,
        }
      return None
    elif action_name == 'Type':
      return {
          'action_type': 'input_text',
          'text': params.get('content', ''),
      }
    elif action_name == 'CallUser':
      return {
          'action_type': 'ask',
          'text': params.get('content', ''),
      }
    elif action_name == 'Launch':
      return {
          'action_type': 'open_app',
          'app_name': params.get('app', ''),
      }
    elif action_name == 'Finished':
      return {
          'action_type': 'status',
          'goal_status': 'complete',
      }
    elif action_name == 'Wait':
      return {
          'action_type': 'wait',
      }
    elif action_name == 'PressBack':
      return {
          'action_type': 'navigate_back',
      }
    elif action_name == 'PressHome':
      return {
          'action_type': 'navigate_home',
      }
    elif action_name == 'PressEnter':
      return {
          'action_type': 'keyboard_enter',
      }
    elif action_name == 'PressRecent':
      # PressRecent is not directly supported in JSONAction, map to wait
      print(f'PressRecent not directly supported, mapping to wait')
      return {
          'action_type': 'wait',
      }
    else:
      print(f'Unknown action: {action_name}')
      return None

  def _convert_coordinate(self, action_json: dict, size_params: dict):
    orig_w, orig_h = size_params['original_width'], size_params['original_height']
    action_type = action_json['action'].lower()
    try:
      if action_type == 'click' or action_type == 'longpress':
        x, y = action_json['params']['box']
        action_json['params']['box'] = (int(x / 999 * orig_w), int(y / 999 * orig_h))
      elif action_type == 'drag':
        x1, y1 = action_json['params']['start']
        x2, y2 = action_json['params']['end']
        action_json['params']['start'] = (int(x1 / 999 * orig_w), int(y1 / 999 * orig_h))
        action_json['params']['end'] = (int(x2 / 999 * orig_w), int(y2 / 999 * orig_h))
      elif action_type == 'scroll':
        if 'start' in action_json['params'] and len(action_json['params']['start']) > 0:
          x, y = action_json['params']['start']
          action_json['params']['start'] = (int(x / 999 * orig_w), int(y / 999 * orig_h))
        if 'end' in action_json['params'] and len(action_json['params']['end']) > 0:
          x, y = action_json['params']['end']
          action_json['params']['end'] = (int(x / 999 * orig_w), int(y / 999 * orig_h))
    except (KeyError, ValueError, TypeError) as e:
      logging.warning(f"convert failed: {e}, action_json={action_json}")

    return action_json

