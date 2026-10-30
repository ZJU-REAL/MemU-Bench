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

"""Debug evaluators for Taodian (淘店) app tasks.

These evaluators verify shopping operations by checking
the LevelDB data stored by the WebView-based app.
"""

import time
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import taodian as taodian_validator


class DebugTaodianOrderProduct(fixed_task_eval.TaskEval):
  """固定任务：验证商品订单是否被正确创建。

  Agent 需要在淘店应用中下单指定商品。
  验证方式：检查 LevelDB 中的订单数据。
  """

  complexity = 2.0

  # 固定的订单参数（根据实际数据库格式）
  _EXPECTED_ORDER = {
      "prodId": "2",  # 实际数据库中是字符串
      "skuId": "2001",  # 实际数据库中是字符串
      "prodCount": 1,
      "shopId": 1,
  }

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Taodian app, order product ID '{self._EXPECTED_ORDER['prodId']}'")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空所有订单，存储初始状态。"""
    print("[DEBUG] Clearing all orders...")
    taodian_validator.clear_orders(env)
    time.sleep(1)  # 等待清除完成
    print("[DEBUG] Orders cleared")
    self._before_orders = taodian_validator.get_orders(env)
    print(f"[DEBUG] Stored before state: {len(self._before_orders)} orders")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = taodian_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected=self._EXPECTED_ORDER,
    )
    return 1.0 if result else 0.0



class DebugTaodianAddToCart(fixed_task_eval.TaskEval):
  """固定任务：验证商品是否被正确添加到购物车。

  Agent 需要在淘店应用中将指定商品添加到购物车。
  验证方式：检查 LevelDB 中的购物车数据。
  tip: 购物车里已经有的商品，再添加一件验证不了。
  """

  complexity = 1.5

  # 固定的商品参数
  _EXPECTED_ITEM = {
      "prodId": "1",
      "prodName": "经典白色T恤",
      "skuName": "S码",
      "price": 89,
      "skuId": "1001",
      "prodCount": 1,
  }

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Taodian app, add product ID '{self._EXPECTED_ITEM['prodId']}' to cart")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空购物车，存储初始状态。"""
    print("[DEBUG] Clearing cart...")
    taodian_validator.clear_cart(env)
    time.sleep(1)
    print("[DEBUG] Cart cleared")
    self._before_cart = taodian_validator.get_cart(env)
    print(f"[DEBUG] Stored before state: {len(self._before_cart)} items in cart")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_cart'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = taodian_validator.validate_cart_item_added(
        env=env,
        before_cart=self._before_cart,
        expected=self._EXPECTED_ITEM,
    )
    return 1.0 if result else 0.0

'''
app不支持从购物车结算商品检测的逻辑，从购物车里面下单商品，不会加到订单数据库里面
'''