

"""Agent for human playing with step counting.

Each time the user presses Enter counts as one step.
Type 'done' to finish the task and trigger evaluation.
Type 'q' to quit.
"""

import sys

from android_world.agents import base_agent
from android_world.env import interface
from android_world.env import json_action


class HumanCountStepAgent(base_agent.EnvironmentInteractingAgent):
  """Human agent that counts each interaction as a step.

  Unlike HumanAgent which always returns done=True on the first step,
  this agent records each Enter press as a separate step and only
  signals completion when the user types 'done'.
  """

  def step(self, goal: str, **kwargs) -> base_agent.AgentInteractionResult:
    del goal
    response = input(
        'Press Enter to record a step, type "done" to finish,'
        ' or "q" to quit: '
    )
    if response == 'q':
      sys.exit()
    is_done = response.strip().lower() == 'done'
    action_details = {'action_type': 'answer', 'text': response}
    self.env.execute_action(json_action.JSONAction(**action_details))

    state = self.get_post_transition_state()
    result = {}
    result['elements'] = state.ui_elements
    result['pixels'] = state.pixels
    result['raw_screenshot'] = state.pixels.copy()
    return base_agent.AgentInteractionResult(is_done, result)

  def get_post_transition_state(self) -> interface.State:
    return self.env.get_state()