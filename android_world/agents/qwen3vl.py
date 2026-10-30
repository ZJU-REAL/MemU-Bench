

"""Qwen3-VL based agent for Android interaction."""

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

SYSTEM_PROMPT = "\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{\"type\": \"function\", \"function\": {\"name\": \"mobile_use\", \"description\": \"Use a touchscreen to interact with a mobile device, and take screenshots.\\n* This is an interface to a mobile device with touchscreen. You can perform actions like clicking, typing, swiping, etc.\\n* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.\\n* The screen's resolution is 999x999.\\n* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.\", \"parameters\": {\"properties\": {\"action\": {\"description\": \"The action to perform. The available actions are:\\n* `click`: Click the point on the screen with coordinate (x, y).\\n* `long_press`: Press the point on the screen with coordinate (x, y) for specified seconds.\\n* `swipe`: Swipe from the starting point with coordinate (x, y) to the end point with coordinates2 (x2, y2).\\n* `type`: Input the specified text into the activated input box.\\n* `answer`: Output the answer.\\n* `system_button`: Press the system button.\\n* `wait`: Wait specified seconds for the change to happen.\\n* `terminate`: Terminate the current task and report its completion status.\\n* `open_app`: Open a specified application by its name.\", \"enum\": [\"click\", \"long_press\", \"swipe\", \"type\", \"answer\", \"system_button\", \"wait\", \"terminate\", \"open_app\"], \"type\": \"string\"}, \"app_name\": {\"description\": \"The name identifier of the application to open. Required only by `action=open_app`.\", \"type\": \"string\"}, \"coordinate\": {\"description\": \"(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=click`, `action=long_press`, and `action=swipe`.\", \"type\": \"array\"}, \"coordinate2\": {\"description\": \"(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=swipe`.\", \"type\": \"array\"}, \"text\": {\"description\": \"Required only by `action=type` and `action=answer`.\", \"type\": \"string\"}, \"time\": {\"description\": \"The seconds to wait. Required only by `action=long_press` and `action=wait`.\", \"type\": \"number\"}, \"button\": {\"description\": \"Back means returning to the previous interface, Home means returning to the desktop, Menu means opening the application background menu, and Enter means pressing the enter. Required only by `action=system_button`\", \"enum\": [\"Back\", \"Home\", \"Menu\", \"Enter\"], \"type\": \"string\"}, \"status\": {\"description\": \"The status of the task. Required only by `action=terminate`.\", \"type\": \"string\", \"enum\": [\"success\", \"failure\"]}}, \"required\": [\"action\"], \"type\": \"object\"}}}\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>\n\n# Response format\n\nResponse format for every step:\n1) Thought: one concise sentence explaining the next move (no multi-step reasoning).\n2) Action: a short imperative describing what to do in the UI.\n3) A single <tool_call>...</tool_call> block containing only the JSON: {\"name\": <function-name>, \"arguments\": <args-json-object>}.\n\nRules:\n- Output exactly in the order: Thought, Action, <tool_call>.\n- Be brief: one sentence for Thought, one for Action.\n- Do not output anything else outside those three parts.\n- If finishing, use action=terminate in the tool call."

ASK_USER_PROMPT = "None"
class Qwen3VLAgent(base_agent.EnvironmentInteractingAgent):
  """Agent powered by Qwen3-VL model for Android interaction."""

  def __init__(
      self,
      env: interface.AsyncEnv,
      llm: infer.MultimodalLlmWrapper,
      name: str = 'Qwen3VL',
      wait_after_action_seconds: float = 2.0,
  ):
    """Initializes a Qwen3-VL Agent.

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
    }
    if ask:
      assert False, "unsupported ask for qwen3-vl"
    state = self.get_post_transition_state()

    step_data['raw_screenshot'] = state.pixels.copy()

    stage2_history = ''
    for idx, step_info in enumerate(self.history):
      stage2_history += (
          'Step ' + str(idx + 1) + ': '
          + str(step_info['action_output'].replace('\n', '').replace('"', ''))
          + '; '
      )

    action_prompt = (
      'The user query: ' + goal + '\n'
      + (f"Here is some generated information about the user's previous operations, which may help achieve the user's goals:\n{filtered_user_history}\n\n" if filtered_user_history else '')
      + 'Task progress (You have done the following operation on the current device): '
      + stage2_history + '.\n'
    )
    # print("action_prompt: {}".format(action_prompt))
    step_data['action_prompt'] = action_prompt
    action_output, is_safe, raw_response = self.llm.predict_mm(
        action_prompt,
        [
            step_data['raw_screenshot'],
        ],
        system_prompt=SYSTEM_PROMPT,
        generation_config={
          "temperature": 0,
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
    
    reason, action = self.parse_response(
        action_output,
        original_width=step_data['raw_screenshot'].shape[1],
        original_height=step_data['raw_screenshot'].shape[0],
    )

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

    # if converted_action.action_type == 'ask':
    #   user_response = information
    #   print('Agent asked: {}'.format(converted_action.text))
    #   print('User responded: {}'.format(user_response))
    #   self.history.append(step_data)
    #   return base_agent.AgentInteractionResult(
    #       False,
    #       step_data,
    #   )

    try:
      self.env.execute_action(converted_action)
    except Exception as e:  # pylint: disable=broad-exception-caught
      print('Failed to execute action.')
      print(str(e))
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
  def parse_response(self, response, original_width, original_height):
    try:
        action_result = re.search(
        r'Action:(.*)', response, flags=re.DOTALL
        )
        action_reason = action_result.group(1).split('<tool_call>')[0].strip() if action_result else None
        # Handle both <tool_call>{\n...} and <tool_call>{...} formats
        tool_call_match = re.search(r'<tool_call>(.*?)</tool_call>', response, flags=re.DOTALL)
        if not tool_call_match:
            return None, None
        action = json.loads(tool_call_match.group(1))["arguments"]
    except Exception as e:
      return None, None
    model_action = action.get('action', '')
    mapped_action = {}

    if model_action == 'click':
      coord = action.get('coordinate', [0, 0])
      mapped_action = {
          'action_type': 'click',
          'x': int(coord[0] * original_width / 999),
          'y': int(coord[1] * original_height / 999),
      }
    elif model_action == 'long_press':
      coord = action.get('coordinate', [0, 0])
      mapped_action = {
          'action_type': 'long_press',
          'x': int(coord[0] * original_width / 999),
          'y': int(coord[1] * original_height / 999),
      }
    elif model_action == 'swipe':
      coord1 = action.get('coordinate', [0, 0])
      coord2 = action.get('coordinate2', [0, 0])
      dx = coord2[0] - coord1[0]
      dy = coord2[1] - coord1[1]
      if abs(dy) >= abs(dx):
        direction = 'down' if dy < 0 else 'up'
      else:
        direction = 'right' if dx < 0 else 'left'
      mapped_action = {
          'action_type': 'scroll',
          'direction': direction,
      }
    elif model_action == 'type':
      mapped_action = {
          'action_type': 'input_text',
          'text': action.get('text', ''),
      }
    elif model_action == 'answer':
      mapped_action = {
          'action_type': 'answer',
          'text': action.get('text', ''),
      }
    elif model_action == 'system_button':
      button = action.get('button', '')
      if button == 'Back':
        mapped_action = {'action_type': 'navigate_back'}
      elif button == 'Home':
        mapped_action = {'action_type': 'navigate_home'}
      elif button == 'Enter':
        mapped_action = {'action_type': 'keyboard_enter'}
      else:
        print(f'Unsupported system button: {button}')
        return action_reason, None
    elif model_action == 'wait':
      mapped_action = {'action_type': 'wait'}
    elif model_action == 'terminate':
      status = action.get('status', 'failure')
      mapped_action = {
          'action_type': 'status',
          'goal_status': 'complete' if status == 'success' else 'infeasible',
      }
    elif model_action == 'open_app':
      app_name = action.get('app_name', '')
      mapped_action = {
          'action_type': 'open_app',
          'app_name': app_name,
      }
    else:
      print(f'Unknown action: {model_action}')
      return action_reason, None

    print('Reason: {}'.format(action_reason))
    print('Mapped action: {}'.format(mapped_action))

    return action_reason, mapped_action



