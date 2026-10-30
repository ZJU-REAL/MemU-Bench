"""GUI_Owl_1_5 based agent for Android interaction."""

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

SYSTEM_PROMPT = '''# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name_for_human": "mobile_use", "name": "mobile_use", "description": "Use a touchscreen to interact with a mobile device, and take screenshots.
* This is an interface to a mobile device with touchscreen. You can perform actions like clicking, typing, swiping, etc.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.
* The screen's resolution is 1000x1000.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.", "parameters": {"properties": {"action": {"description": "The action to perform. The available actions are:
* `key`: Perform a key event on the mobile device.
    - This supports adb's `keyevent` syntax.
    - Examples: \\"volume_up\\", \\"volume_down\\", \\"power\\", \\"camera\\", \\"clear\\".
* `click`: Click the point on the screen with coordinate (x, y).
* `long_press`: Press the point on the screen with coordinate (x, y) for specified seconds.
* `swipe`: Swipe from the starting point with coordinate (x, y) to the end point with coordinates2 (x2, y2).
* `type`: Input the specified text into the activated input box.
* `system_button`: Press the system button.
* `open`: Open an app on the device.
* `wait`: Wait specified seconds for the change to happen.
* `answer`: Terminate the current task and output the answer.
* `interact`: Resolve the blocking window by interacting with the user.
* `terminate`: Terminate the current task and report its completion status.", "enum": ["key", "click", "long_press", "swipe", "type", "system_button", "open", "wait", "answer", "interact", "terminate"], "type": "string"}, "coordinate": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=click`, `action=long_press`, and `action=swipe`.", "type": "array"}, "coordinate2": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=swipe`.", "type": "array"}, "text": {"description": "Required only by `action=key`, `action=type`, `action=open`, `action=answer`,and `action=interact`.", "type": "string"}, "time": {"description": "The seconds to wait. Required only by `action=long_press` and `action=wait`.", "type": "number"}, "button": {"description": "Back means returning to the previous interface, Home means returning to the desktop, Menu means opening the application background menu, and Enter means pressing the enter. Required only by `action=system_button`", "enum": ["Back", "Home", "Menu", "Enter"], "type": "string"}, "status": {"description": "The status of the task. Required only by `action=terminate`.", "type": "string", "enum": ["success", "failure"]}}, "required": ["action"], "type": "object"}, "args_format": "Format the arguments as a JSON object."}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

# Response format

Response format for every step:
1) Action: a short imperative describing what to do in the UI.
2) A single <tool_call>...</tool_call> block containing only the JSON: {"name": <function-name>, "arguments": <args-json-object>}.

Rules:
- Output exactly in the order: Action, <tool_call>.
- Be brief: one for Action.
- Do not output anything else outside those two parts.
- If finishing, use action=terminate in the tool call.'''
ASK_USER_PROMPT = "None"
def rescale_coordinates(action_parameter, resized_width, resized_height):
    """
    Convert normalized (0-1000) coordinates to actual pixel coordinates
    based on the resized image dimensions.
    """
    for key in ("coordinate", "coordinate1", "coordinate2"):
        if key in action_parameter:
            action_parameter[key][0] = int(
                action_parameter[key][0] / 1000 * resized_width
            )
            action_parameter[key][1] = int(
                action_parameter[key][1] / 1000 * resized_height
            )
    return action_parameter

class GUIOwl15Agent(base_agent.EnvironmentInteractingAgent):
  """Agent powered by GUI_Owl_1_5 model for Android interaction."""

  def __init__(
      self,
      env: interface.AsyncEnv,
      llm: infer.MultimodalLlmWrapper,
      name: str = 'GUI_Owl_1_5',
      wait_after_action_seconds: float = 2.0,
  ):
    """Initializes a GUI_Owl_1_5 Agent.

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
        'action_raw_response': None,
        'user_response': None,
    }
    if ask:
      assert False, "unsupported ask for GUI_Owl_1_5"
    state = self.get_post_transition_state()

    step_data['raw_screenshot'] = state.pixels.copy()

    # Detect loop: if the last 3 steps have identical action_output, mark as failed
    if len(self.history) >= 3:
      last_three = [self.history[-i]['action_output'] for i in range(1, 4)]
      if last_three[0] == last_three[1] == last_three[2]:
        print('Detected loop: last 3 steps have identical output. Marking task as infeasible.')
        step_data['action_output'] = last_three[0]
        step_data['action_output_json'] = json_action.JSONAction(action_type='status', goal_status='infeasible')
        self.history.append(step_data)
        return base_agent.AgentInteractionResult(
            True,
            step_data,
        )

    previous_actions = []
    for i, step_info in enumerate(self.history):
      text = step_info["action_output"]
      if "Action:" in text and "<tool_call>" in text:
          text = text.split("Action:")[1].split("<tool_call>")[0].strip()
      step_text = f"Step {i + 1}: {text}"
      if step_info.get('user_response'):
        step_text += f" User response: {step_info['user_response']}"
      previous_actions.append(step_text)

    previous_actions_str = "\n".join(previous_actions) if previous_actions else "None"
    print(previous_actions_str)
    instruction_prompt = (
        f"Please generate the next move according to the UI screenshot, "
        f"instruction and previous actions.\n\n"
        f"Instruction: {goal}\n\n"
        f"Previous actions:\n{previous_actions_str}\n\n"
        + (f"Here is some generated information about the user's previous operations, which may help achieve the user's goals:\n{filtered_user_history}\n\n" if filtered_user_history else '')
    )
    # print(instruction_prompt)
    step_data['action_prompt'] = instruction_prompt
    action_output, is_safe, raw_response = self.llm.predict_mm(
        instruction_prompt,
        [
            step_data['raw_screenshot'],
        ],
        system_prompt=SYSTEM_PROMPT,
        generation_config={
          "temperature": 0.0,
          "top_p": 1.0,
          "max_tokens": 2048,
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

    original_width = step_data['raw_screenshot'].shape[1]
    original_height = step_data['raw_screenshot'].shape[0]

    reason = self.parse_reason(action_output)
    action = self.parse_action(action_output)
    action_parameter = action["arguments"]
    action_parameter = rescale_coordinates(action_parameter, original_width, original_height)
    action["arguments"] = action_parameter
    action = self.map_action(action)
    # If the output is not in the right format, return.
    if (not reason) or (not action):
      print('Action prompt output is not in the correct format.')
      self.history.append(step_data)

      return base_agent.AgentInteractionResult(
          False,
          step_data,
      )

    
    step_data['action_reason'] = reason

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
  def map_action(self, action: dict) -> dict | None:
    """Maps the GUI_Owl_1_5 model's action format to JSONAction format.

    Args:
      action: The parsed action dict with 'name' and 'arguments' keys,
        e.g. {"name": "mobile_use", "arguments": {"action": "click",
        "coordinate": [x, y]}}. Coordinates are already rescaled to
        actual pixel values by rescale_coordinates before this call.

    Returns:
      A dict that can be used to create json_action.JSONAction, or None
      if the action is not supported.
    """
    arguments = action.get('arguments', {})
    model_action = arguments.get('action', '')
    mapped_action = {}

    if model_action == 'click':
      coord = arguments.get('coordinate', [0, 0])
      mapped_action = {
          'action_type': 'click',
          'x': int(coord[0]),
          'y': int(coord[1]),
      }
    elif model_action == 'long_press':
      coord = arguments.get('coordinate', [0, 0])
      mapped_action = {
          'action_type': 'long_press',
          'x': int(coord[0]),
          'y': int(coord[1]),
      }
    elif model_action == 'swipe':
      # Swipe from coordinate to coordinate2 represents finger movement.
      # android_world scroll direction refers to content movement, so we
      # reverse: finger moves down -> content scrolls up, etc.
      coord1 = arguments.get('coordinate', [0, 0])
      coord2 = arguments.get('coordinate2', [0, 0])
      dx = coord2[0] - coord1[0]
      dy = coord2[1] - coord1[1]
      if abs(dy) >= abs(dx):
        direction = 'up' if dy > 0 else 'down'
      else:
        direction = 'left' if dx > 0 else 'right'
      mapped_action = {
          'action_type': 'scroll',
          'direction': direction,
      }
    elif model_action == 'type':
      mapped_action = {
          'action_type': 'input_text',
          'text': arguments.get('text', ''),
      }
    elif model_action == 'answer':
      # Model uses "answer" to indicate task completion with a result
      mapped_action = {
          'action_type': 'status',
          'goal_status': 'complete',
      }
    elif model_action == 'system_button':
      button = arguments.get('button', '')
      if button == 'Back':
        mapped_action = {'action_type': 'navigate_back'}
      elif button == 'Home':
        mapped_action = {'action_type': 'navigate_home'}
      elif button == 'Enter':
        mapped_action = {'action_type': 'keyboard_enter'}
      else:
        # Menu and other buttons are not supported in JSONAction.
        print(f'Unsupported system button: {button}')
        return None
    elif model_action in ('open', 'open_app'):
      # Prompt defines "open" but model may output "open_app"
      app_name = arguments.get('text', '') or arguments.get('app_name', '')
      mapped_action = {
          'action_type': 'open_app',
          'app_name': app_name,
      }
    elif model_action == 'wait':
      mapped_action = {'action_type': 'wait'}
    elif model_action == 'terminate':
      status = arguments.get('status', 'failure')
      mapped_action = {
          'action_type': 'status',
          'goal_status': 'complete' if status == 'success' else 'infeasible',
      }
    elif model_action == 'key':
      key = arguments.get('text', '')
      print(f'Key action not directly supported: {key}')
      return None
    elif model_action == 'interact':
      text = arguments.get('text', '')
      mapped_action = {
          'action_type': 'ask',
          'text': text,
      }
    else:
      print(f'Unknown action: {model_action}')
      return None

    print('Mapped action: {}'.format(mapped_action))
    return mapped_action

  def parse_action(self, output_text):
    """Extract the action dict from the model's output text.

    Expects a <tool_call> block containing JSON with nested 'arguments'.
    """
    try:
        tool_call_block = output_text.split("<tool_call>\n")[1]
        json_str = tool_call_block.split("}}\n")[0] + "}}"
        return json.loads(json_str)
    except (IndexError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse action from model output: {e}")

  def parse_reason(self, output_text):
    """Extract the reason from the model's output text.

    Expects the text before the <tool_call> block.
    """
    try:
        reason = output_text.split("<tool_call>\n")[0]
        return reason
    except (IndexError) as e:
        raise ValueError(f"Failed to parse reason from model output: {e}")

