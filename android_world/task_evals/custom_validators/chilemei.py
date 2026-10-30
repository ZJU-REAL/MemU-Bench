from android_world.task_evals import task_eval
import time
from typing import Any, Optional
import tempfile
import os
import json
import shutil
import re
import struct

from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals.custom_validators import llm_as_judge


# LLM 验证收货信息的 Prompt 模板
CHILEMEI_RECEIVER_VALIDATION_PROMPT = """You are an order validation assistant. Please determine whether the actual receiver information matches the expected information.

Expected Information:
{expected_info}

Actual Information:
{actual_info}

Judgment Rules:
1. The actual information must convey EXACTLY the same core information as the expected information
2. For address: minor differences in formatting, spacing, or punctuation are acceptable (e.g., "Road" vs "Rd", "District" vs "Dist.")
3. For phone number: the actual number should match exactly, but formatting differences (e.g., with/without spaces, dashes) are acceptable
4. For contact name: the actual name should match exactly, case-insensitive
5. Extra information in the actual data is acceptable IF it doesn't change the core meaning (e.g., additional address details)
6. Missing critical information is a FAILURE
7. Examples of SUCCESS:
   - Expected address: "Weigongcun Road", Actual: "Weigongcun Rd" -> SUCCESS (abbreviation)
   - Expected phone: "13344556677", Actual: "133-4455-6677" -> SUCCESS (formatting difference)
   - Expected name: "Barbara Jones", Actual: "barbara jones" -> SUCCESS (case difference)
8. Examples of FAILURE:
   - Expected address: "Beijing", Actual: "Shanghai" -> FAILURE (different city)
   - Expected phone: "13344556677", Actual: "13344556678" -> FAILURE (different number)
   - Expected name: "Barbara Jones", Actual: "Mary Jones" -> FAILURE (different person)
"""


# ============================================================================
# 封装验证函数：检查 Chilemei 外卖订单操作是否成功
# ============================================================================

# 外卖应用包名
_PACKAGE_NAME = "com.test.chilemei"

# Leveldb 数据路径
_LEVELDB_PATH = "/data/data/com.test.chilemei/app_webview/Default/Local Storage/leveldb"


def _extract_orders_from_leveldb(env: interface.AsyncEnv) -> list:
    """使用 plyvel 库正确解析 LevelDB 数据。

    Args:
        env: Android 环境接口。

    Returns:
        订单列表。
    """
    import plyvel

    # 1. 获取 root 权限
    adb_utils.set_root_if_needed(env.controller)

    # 2. 创建本地临时目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    android_world_dir = os.path.dirname(os.path.dirname(current_dir))
    tmp_base_dir = os.path.join(android_world_dir, "tmp")
    os.makedirs(tmp_base_dir, exist_ok=True)

    local_temp_dir = tempfile.mkdtemp(prefix="chilemei_leveldb_", dir=tmp_base_dir)
    print(f"[DEBUG] 创建临时目录: {local_temp_dir}")

    try:
        # 3. 将 leveldb 目录拉取到本地
        from android_env.proto import adb_pb2
        try:
            pull_result = adb_utils.issue_generic_request(
                ["pull", _LEVELDB_PATH, local_temp_dir],
                env.controller
            )
        except Exception as e:
            print(f"[DEBUG] adb pull 异常 (可能路径不存在): {e}")
            return []

        if pull_result.status != adb_pb2.AdbResponse.Status.OK:
            print(f"[DEBUG] adb pull 失败 (可能路径不存在): {pull_result}")
            return []

        print(f"[DEBUG] adb pull 成功")

        # pull 成功后，leveldb 数据在 local_temp_dir/leveldb/ 目录下
        db_path = os.path.join(local_temp_dir, "leveldb")

        if not os.path.exists(db_path):
            db_path = local_temp_dir

        print(f"[DEBUG] LevelDB 路径: {db_path}")

        # 4. 使用 plyvel 打开 LevelDB
        try:
            db = plyvel.DB(db_path, create_if_missing=False)
        except Exception as e:
            print(f"[DEBUG] 无法打开 LevelDB: {e}")
            return []

        orders_data = []

        try:
            # 遍历所有键值对
            for key, value in db:
                key_str = key.decode('utf-8', errors='ignore')

                # 查找 demo_orders 相关的数据
                if 'demo_orders' in key_str:
                    print(f"[DEBUG] 找到 key: {key_str}")

                    # WebView Local Storage 使用 UTF-16 LE 编码
                    if len(value) > 1 and value[0] == 0:
                        json_bytes = value[1:]
                        value_str = json_bytes.decode('utf-16-le', errors='ignore')
                    else:
                        value_str = value.decode('utf-8', errors='ignore')

                    try:
                        data = json.loads(value_str)
                        if isinstance(data, list):
                            orders_data.extend(data)
                        else:
                            orders_data.append(data)
                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] JSON 解析失败: {e}")

        finally:
            db.close()

        # 5. 格式化订单数据
        formatted_orders = []
        for order in orders_data:
            if not isinstance(order, dict):
                continue

            foods = []
            for food in order.get('foods', []):
                if isinstance(food, dict):
                    foods.append({
                        'name': food.get('name', ''),
                        'price': food.get('price', 0),
                        'num': food.get('num', 1),
                        'food_id': food.get('food_id', '')
                    })

            formatted_orders.append({
                'id': order.get('id'),
                'status': order.get('status'),
                'created_at': order.get('created_at'),
                'shop_id': order.get('shop_id', ''),
                'shop_name': order.get('shop_name', ''),
                'foods': foods,
                'total_price': order.get('total_price', 0),
                'delivery_fee': order.get('delivery_fee', 0),
                'packing_fee': order.get('packing_fee', 0),
                'remark': order.get('remark', ''),
                'invoice': order.get('invoice', ''),
                'address': order.get('address', ''),
                'phone': order.get('phone', ''),
                'contact_name': order.get('contact_name', ''),
                'address_id': order.get('address_id', 0),
            })

        # 6. 去重逻辑
        seen_signatures = {}
        for order in formatted_orders:
            food_names = tuple(sorted([f['name'] for f in order.get('foods', [])]))
            signature = (
                order.get('shop_id', ''),
                order.get('shop_name', ''),
                order.get('created_at', ''),
                food_names
            )

            if signature in seen_signatures:
                existing_order = seen_signatures[signature]
                if existing_order.get('status') == 'pending' and order.get('status') == 'paid':
                    seen_signatures[signature] = order
            else:
                seen_signatures[signature] = order

        unique_orders = list(seen_signatures.values())
        unique_orders.sort(key=lambda x: x.get('created_at', ''))

        print(f"[DEBUG] 从 LevelDB 解析出 {len(unique_orders)} 个订单")
        return unique_orders

    finally:
        # 7. 清理临时目录
        if os.path.exists(local_temp_dir):
            shutil.rmtree(local_temp_dir, ignore_errors=True)


def get_orders(env: interface.AsyncEnv) -> list:
    """获取所有订单列表。

    Args:
        env: Android 环境接口。

    Returns:
        订单字典列表。
    """
    orders = _extract_orders_from_leveldb(env)
    print(f"[DEBUG] Found {len(orders)} orders")
    return orders


def clear_orders(env: interface.AsyncEnv) -> None:
    """清空所有订单（通过清除应用数据）。

    Args:
        env: Android 环境接口。
    """
    adb_utils.clear_app_data(_PACKAGE_NAME, env.controller)
    print("[DEBUG] All orders cleared")


def _normalize_food_name(name: str) -> str:
    """标准化商品名称用于匹配。"""
    return name.lower().strip()


def validate_order_created(
    env: interface.AsyncEnv,
    before_orders: list,
    expected: dict,
    goal: str = "",
) -> bool:
    """验证订单是否被正确创建（单订单单商品）。

    Args:
        env: Android 环境接口。
        before_orders: 任务执行前的订单列表。
        expected: 期望的订单数据。
        goal: 任务目标描述（可选），用于 LLM 验证收货信息。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_orders = get_orders(env)

    print(f"[DEBUG] Before orders: {len(before_orders)}")
    print(f"[DEBUG] After orders: {len(after_orders)}")
    print(f"[DEBUG] Expected: {expected}")

    # 检查新订单数量
    new_orders = [o for o in after_orders if o not in before_orders]
    if len(new_orders) != 1:
        print(f"[DEBUG] Expected 1 new order, found {len(new_orders)}")
        return False

    # 转换为 validate_order_matches 需要的格式
    check_expected = {
        'foods': [{
            'name': expected.get('food_name', ''),
            'food_id': expected.get('food_id'),
            'price': expected.get('price'),
            'num': expected.get('num', 1),
        }],
        'shop_id': expected.get('shop_id'),
        'shop_name': expected.get('shop_name'),
        'status': expected.get('status'),
        'total_price': expected.get('total_price'),
        'delivery_fee': expected.get('delivery_fee'),
        'packing_fee': expected.get('packing_fee'),
        'address': expected.get('address'),
        'phone': expected.get('phone'),
        'contact_name': expected.get('contact_name'),
        'address_id': expected.get('address_id'),
        'remark': expected.get('remark'),
        'invoice': expected.get('invoice'),
    }
    # 移除 None 值和空字符串
    check_expected = {k: v for k, v in check_expected.items() if v is not None and v != ''}
    check_expected['foods'] = [{k: v for k, v in check_expected['foods'][0].items() if v is not None and v != ''}]

    print(f"[DEBUG] check_expected after processing: {check_expected}")
    print(f"[DEBUG] check_expected['foods'][0]: {check_expected['foods'][0]}")

    order = new_orders[0]

    # 打印实际订单详情（用于调试）
    print(f"[DEBUG] Actual new order details:")
    print(f"[DEBUG]   shop_name: {order.get('shop_name')}")
    print(f"[DEBUG]   shop_id: {order.get('shop_id')}")
    print(f"[DEBUG]   status: {order.get('status')}")
    print(f"[DEBUG]   total_price: {order.get('total_price')}")
    print(f"[DEBUG]   address: {order.get('address')}")
    print(f"[DEBUG]   phone: {order.get('phone')}")
    print(f"[DEBUG]   contact_name: {order.get('contact_name')}")
    foods = order.get('foods', [])
    print(f"[DEBUG]   foods count: {len(foods)}")
    for i, food in enumerate(foods):
        print(f"[DEBUG]     food[{i}]: name='{food.get('name')}', price={food.get('price')}, num={food.get('num')}, food_id={food.get('food_id')}")

    matches, reason = validate_order_matches(order, check_expected, goal)

    if matches:
        print(f"[DEBUG] Order creation validated: True")
        food = order.get('foods', [{}])[0]
        print(f"[DEBUG] Order details: shop={order.get('shop_name')}, "
              f"food={food.get('name')}, price={food.get('price')}, num={food.get('num')}")
        return True
    else:
        print(f"[DEBUG] Validation failed: {reason}")
        return False


def _validate_order_info_with_llm(
    expected: dict,
    actual: dict,
    goal: str = "",
) -> tuple[bool, str]:
    """使用 LLM 验证订单信息（地址、电话、联系人、备注）是否匹配。

    Args:
        expected: 期望的订单信息，包含 address、phone、contact_name、remark 等字段。
        actual: 实际的订单信息。
        goal: 任务目标描述（可选）。

    Returns:
        (是否匹配, 解释)
    """
    # 构建期望信息字符串
    expected_parts = []
    if 'address' in expected:
        expected_parts.append(f"Address: {expected['address']}")
    if 'phone' in expected:
        expected_parts.append(f"Phone: {expected['phone']}")
    if 'contact_name' in expected:
        expected_parts.append(f"Contact Name: {expected['contact_name']}")
    if 'remark' in expected:
        expected_parts.append(f"Remark: {expected['remark']}")
    expected_info = "\n".join(expected_parts)

    # 构建实际信息字符串
    actual_parts = []
    if 'address' in expected:
        actual_parts.append(f"Address: {actual.get('address', 'Not specified')}")
    if 'phone' in expected:
        actual_parts.append(f"Phone: {actual.get('phone', 'Not specified')}")
    if 'contact_name' in expected:
        actual_parts.append(f"Contact Name: {actual.get('contact_name', 'Not specified')}")
    if 'remark' in expected:
        actual_parts.append(f"Remark: {actual.get('remark', 'Not specified')}")
    actual_info = "\n".join(actual_parts)

    prompt = CHILEMEI_RECEIVER_VALIDATION_PROMPT.format(
        expected_info=expected_info,
        actual_info=actual_info,
    )

    print(f"[DEBUG] Expected order info: {expected_info}")
    print(f"[DEBUG] Actual order info: {actual_info}")
    print(f"[DEBUG] Goal for LLM: {goal}")
    print(f"[DEBUG] Calling LLM to validate order info...")
    try:
        is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
        print(f"[DEBUG] LLM judgment for order info: {is_match}, Explanation: {explanation}")
    except Exception as e:
        print(f"[DEBUG] LLM validation failed with exception: {e}")
        is_match = False
        explanation = str(e)
    print(f"[DEBUG] LLM result: is_match={is_match}, explanation={explanation}")

    return is_match, explanation


def validate_order_matches(order: dict, expected: dict, goal: str = "") -> tuple[bool, str]:
    """检查单个订单是否匹配预期。

    Args:
        order: 实际订单数据。
        expected: 期望的订单数据。
        goal: 任务目标描述（可选），用于 LLM 验证。

    Returns:
        (是否匹配, 失败原因)
    """
    expected_foods = expected.get('foods', [])
    actual_foods = order.get('foods', [])

    # 检查商品数量
    if len(actual_foods) != len(expected_foods):
        return False, f"foods count mismatch: got {len(actual_foods)}, expected {len(expected_foods)}"

    # 检查店铺相关字段（精确匹配）
    if 'shop_id' in expected:
        if order.get('shop_id') != expected['shop_id']:
            return False, "shop_id mismatch"
    if 'shop_name' in expected:
        if expected['shop_name'] not in order.get('shop_name', ''):
            return False, "shop_name mismatch"

    # 检查订单相关字段（精确匹配）
    if 'status' in expected:
        if order.get('status') != expected['status']:
            return False, "status mismatch"
    if 'total_price' in expected:
        if order.get('total_price') != expected['total_price']:
            return False, "total_price mismatch"

    # 检查收货信息和备注（使用 LLM 验证）
    order_info_fields = ['address', 'phone', 'contact_name', 'remark']
    if any(field in expected for field in order_info_fields):
        is_match, explanation = _validate_order_info_with_llm(expected, order, goal)
        if not is_match:
            return False, f"order info mismatch: {explanation}"

    # 检查所有商品是否匹配（每个实际商品只能匹配一次）
    matched_actual_indices = set()

    for expected_food in expected_foods:
        food_found = False
        expected_name_normalized = _normalize_food_name(expected_food.get('name', ''))
        print(f"[DEBUG] Looking for food: expected='{expected_food.get('name')}' (normalized: '{expected_name_normalized}')")

        for i, food in enumerate(actual_foods):
            # 跳过已匹配的商品
            if i in matched_actual_indices:
                continue

            actual_name_normalized = _normalize_food_name(food.get('name', ''))
            print(f"[DEBUG]   Comparing with actual food[{i}]: name='{food.get('name')}' (normalized: '{actual_name_normalized}')")

            # 检查商品名称
            if 'name' in expected_food:
                if actual_name_normalized != expected_name_normalized:
                    print(f"[DEBUG]     Name mismatch: '{actual_name_normalized}' != '{expected_name_normalized}'")
                    continue
                else:
                    print(f"[DEBUG]     Name matched!")

            # 检查商品ID（只有当期望值非空时才检查）
            if expected_food.get('food_id'):
                if food.get('food_id') != expected_food['food_id']:
                    continue

            # 检查价格（只有当期望值非空时才检查）
            if expected_food.get('price') is not None:
                if food.get('price') != expected_food['price']:
                    continue

            # 检查数量（只有当期望值非空时才检查）
            if expected_food.get('num') is not None:
                if food.get('num') != expected_food['num']:
                    continue

            food_found = True
            matched_actual_indices.add(i)
            print(f"[DEBUG]   Food found and matched at index {i}")
            break

        if not food_found:
            print(f"[DEBUG] Food not found after checking all {len(actual_foods)} actual foods")
            return False, f"food not found: {expected_food.get('name')}"

    return True, ""


def validate_orders_created(
    env: interface.AsyncEnv,
    before_orders: list,
    expected: dict,
) -> bool:
    """验证多个订单是否被正确创建。

    Args:
        env: Android 环境接口。
        before_orders: 任务执行前的订单列表。
        expected: 期望的订单数据，格式：
            {
                'orders': [
                    {'foods': [{'name': '宫保鸡丁'}], 'shop_name': '店铺A'},
                    {'foods': [{'name': '汉堡'}, {'name': '薯条'}], 'shop_name': '店铺B'},
                ]
            }

    Returns:
        True 如果验证通过，False 否则。
    """
    after_orders = get_orders(env)

    print(f"[DEBUG] Before orders: {len(before_orders)}")
    print(f"[DEBUG] After orders: {len(after_orders)}")
    print(f"[DEBUG] Expected: {expected}")

    # 打印实际订单详情
    for i, order in enumerate(after_orders):
        foods = order.get('foods', [])
        food_strs = [f"{f.get('name')}(¥{f.get('price')},x{f.get('num', 1)})" for f in foods]
        print(f"[DEBUG] Actual Order {i}: shop='{order.get('shop_name')}', foods={food_strs}")

    # 获取新订单
    new_orders = [o for o in after_orders if o not in before_orders]
    print(f"[DEBUG] New orders: {len(new_orders)}")

    expected_orders = expected.get('orders', [])
    expected_count = len(expected_orders)

    if len(new_orders) != expected_count:
        print(f"[DEBUG] Expected {expected_count} new orders, found {len(new_orders)}")
        return False

    # 验证每个预期订单都能在新订单中找到匹配
    for i, expected_order in enumerate(expected_orders):
        matched = False
        for new_order in new_orders:
            matches, reason = validate_order_matches(new_order, expected_order)
            if matches:
                matched = True
                print(f"[DEBUG] Order {i+1} matched: shop={new_order.get('shop_name')}")
                break
        if not matched:
            print(f"[DEBUG] Order {i+1} not matched: {reason}")
            return False

    print(f"[DEBUG] All {expected_count} orders validated: True")
    return True


def find_order_by_food_name(
    orders: list,
    food_name: str,
    fuzzy_match: bool = True,
) -> Optional[dict]:
    """按商品名称查找订单。

    Args:
        orders: 订单列表。
        food_name: 要搜索的商品名称。
        fuzzy_match: 是否使用模糊匹配。

    Returns:
        第一个匹配的订单，如果未找到则返回 None。
    """
    normalized_name = _normalize_food_name(food_name)
    for order in orders:
        for food in order.get('foods', []):
            if fuzzy_match:
                if _normalize_food_name(food['name']) == normalized_name:
                    return order
            else:
                if food['name'] == food_name:
                    return order
    return None
