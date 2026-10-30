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

"""Debug evaluators for tuantuan (food delivery) app tasks.

These evaluators verify food ordering operations by checking
the LevelDB data stored by the WebView-based app.
"""

import time
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import tuantuan as tuantuan_validator


class DebugTuantuanOrderFood(fixed_task_eval.TaskEval):
  """固定任务：验证外卖订单是否被正确创建。

  Agent 需要在 tuantuan 应用中下单指定商品。
  验证方式：检查 LevelDB 中的订单数据。
  """

  complexity = 2.0

  # 固定的订单参数
  _EXPECTED_ORDER = {
      "shop_id": "1",           # str
      "shop_name": "好味道中餐馆",  # str
      "food_name": "宫保鸡丁",    # str
      "food_id": "10001",       # str
      "price": 28,              # int
      "num": 1,                 # int
    }

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the tuantuan app, order '{self._EXPECTED_ORDER['food_name']}' "
            f"from '{self._EXPECTED_ORDER['shop_name']}', ")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空所有订单，存储初始状态。"""
    print("[DEBUG] Clearing all orders...")
    tuantuan_validator.clear_orders(env)
    time.sleep(1)  # 等待清除完成
    print("[DEBUG] Orders cleared")
    self._before_orders = tuantuan_validator.get_orders(env)
    print(f"[DEBUG] Stored before state: {len(self._before_orders)} orders")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = tuantuan_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected=self._EXPECTED_ORDER,
    )
    return 1.0 if result else 0.0


class DebugTuantuanOrderMultipleFoods(fixed_task_eval.TaskEval):
  """固定任务：验证多个商品是否被正确下单。

  Agent 需要在 tuantuan 应用中下单多个商品。
  验证方式：检查 LevelDB 中的订单数据。
  """

  complexity = 2.5

  # 固定的订单参数
  _EXPECTED_ORDERS = {
          "orders": [
              {
                  "foods": [{"name": "宫保鸡丁", "price": 28, "num": 1}],
                  "shop_name": "好味道中餐馆",
              },
              {
                  "foods": [{"name": "香辣鸡腿堡", "price": 18}, {"name": "薯条(中份)", "price": 10}],
                  "shop_name": "美味汉堡王",
              },
          ]
      }

  @property
  def goal(self) -> str:
    """任务目标。"""
    orders = self._EXPECTED_ORDERS['orders']
    parts = []
    for order in orders:
        foods = order['foods']
        food_desc = ", ".join([f"{f['name']} x{f.get('num', 1)}" for f in foods])
        parts.append(f"from '{order['shop_name']}': {food_desc}")
    return f"In the tuantuan app, order {'; '.join(parts)}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空所有订单，存储初始状态。"""
    print("[DEBUG] Clearing all orders...")
    tuantuan_validator.clear_orders(env)
    time.sleep(1)  # 等待清除完成
    print("[DEBUG] Orders cleared")
    self._before_orders = tuantuan_validator.get_orders(env)
    print(f"[DEBUG] Stored before state: {len(self._before_orders)} orders")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = tuantuan_validator.validate_orders_created(
        env=env,
        before_orders=self._before_orders,
        expected=self._EXPECTED_ORDERS,
    )
    return 1.0 if result else 0.0
