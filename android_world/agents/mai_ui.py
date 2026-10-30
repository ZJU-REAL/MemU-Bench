

"""Mai-UI based agent for Android interaction."""

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

SYSTEM_PROMPT = """'You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task.\n\n## Output Format\nFor each function call, return the thinking process in <thinking> </thinking> tags, and a json object with function name and arguments within <tool_call></tool_call> XML tags:\n```\n<thinking>\n...\n</thinking>\n<tool_call>\n{"name": "mobile_use", "arguments": <args-json-object>}\n</tool_call>\n```\n\n## Action Space\n\n{"action": "click", "coordinate": [x, y]}\n{"action": "long_press", "coordinate": [x, y]}\n{"action": "type", "text": ""}\n{"action": "swipe", "direction": "up or down or left or right", "coordinate": [x, y]} # "coordinate" is optional. Use the "coordinate" if you want to swipe a specific UI element.\n{"action": "open", "text": "app_name"}\n{"action": "drag", "start_coordinate": [x1, y1], "end_coordinate": [x2, y2]}\n{"action": "system_button", "button": "button_name"} # Options: back, home, menu, enter\n{"action": "wait"}\n{"action": "terminate", "status": "success or fail"}\n{"action": "answer", "text": "xxx"} # Use escape characters \\\', \\", and \\n in text part to ensure we can parse the text in normal python string format.\n\n\n## Note\n- Write a small plan and finally summarize your next action (with its target element) in one sentence in <thinking></thinking> part.\nYou should use the `open` action to open the app as possible as you can, because it is the fast way to open the app.\n- You must follow the Action Space strictly, and return the correct json object within <thinking> </thinking> and <tool_call></tool_call> XML tags.'"""
ASK_USER_PROMPT = "None"
class MAI_UIAgent(base_agent.EnvironmentInteractingAgent):
  """Agent powered by Mai-UI model for Android interaction."""

  def __init__(
      self,
      env: interface.AsyncEnv,
      llm: infer.MultimodalLlmWrapper,
      name: str = 'MaiUI',
      wait_after_action_seconds: float = 2.0,
  ):
    """Initializes a Mai-UI Agent.

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
      assert False, "unsupported ask for mai-ui"
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
          "temperature": 0.0,
          "top_k": -1,
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
      self.history.append(step_data)
      return base_agent.AgentInteractionResult(
          True,
          step_data,
      )

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
  def parse_response(self, response, original_width, original_height):
    try:
        action_reason = response.split('<thinking>')[1].split('</thinking>')[0].strip() if '<thinking>' in response else None
        action = json.loads(response.split('<tool_call>\n')[1].split('\n</tool_call>')[0])["arguments"]
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
      # Mai-UI swipe direction refers to finger movement, but android_world
      # scroll direction refers to content movement, so we need to reverse.
      direction_map = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
      direction = direction_map.get(action.get('direction', 'up'), 'up')
      mapped_action = {
          'action_type': 'scroll',
          'direction': direction,
      }
    elif model_action == 'drag':
      # Mai-UI drag direction is finger movement, reverse for content scroll.
      start_coord = action.get('start_coordinate', [0, 0])
      end_coord = action.get('end_coordinate', [0, 0])
      dx = end_coord[0] - start_coord[0]
      dy = end_coord[1] - start_coord[1]
      if abs(dy) >= abs(dx):
        direction = 'up' if dy < 0 else 'down'
      else:
        direction = 'left' if dx < 0 else 'right'
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
      button = action.get('button', '').lower()
      if button == 'back':
        mapped_action = {'action_type': 'navigate_back'}
      elif button == 'home':
        mapped_action = {'action_type': 'navigate_home'}
      elif button == 'enter':
        mapped_action = {'action_type': 'keyboard_enter'}
      else:
        print(f'Unsupported system button: {button}')
        return action_reason, None
    elif model_action == 'wait':
      mapped_action = {'action_type': 'wait'}
    elif model_action == 'terminate':
      status = action.get('status', 'fail')
      mapped_action = {
          'action_type': 'status',
          'goal_status': 'complete' if status == 'success' else 'infeasible',
      }
    elif model_action == 'open':
      app_name = action.get('text', '')
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