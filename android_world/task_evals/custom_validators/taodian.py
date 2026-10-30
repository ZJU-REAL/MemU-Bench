from android_world.task_evals import task_eval
import time
from typing import Any, Optional
import tempfile
import os
import json
import shutil

from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals.custom_validators import vlm_as_judge


# VLM 验证收货信息的 Prompt 模板
TAODIAN_RECEIVER_VALIDATION_PROMPT = """You are an order validation assistant. You will be given screenshots from an e-commerce app (Taodian) showing the order checkout or confirmation page.

Your task is to check whether the receiver information shown in the screenshots matches the expected information.

Expected Receiver Information:
{expected_info}

Judgment Rules:
1. Carefully examine the screenshots for any receiver/delivery information fields, such as contact name, phone number, and delivery address.
2. The actual information must convey EXACTLY the same core information as the expected information.
3. For address: minor differences in formatting, spacing, or punctuation are acceptable (e.g., "Road" vs "Rd", "District" vs "Dist.").
4. For phone number: the actual number should match exactly, but formatting differences (e.g., with/without spaces, dashes) are acceptable.
5. For contact name: the actual name should match exactly, case-insensitive.
6. Extra information in the actual data is acceptable IF it doesn't change the core meaning (e.g., additional address details like postal code).
7. Missing critical information is a FAILURE.
8. If the receiver information is not visible in ANY of the screenshots, judge as Failure.
9. Examples of SUCCESS:
   - Expected address: "Weigongcun Road", Actual: "Weigongcun Rd" -> SUCCESS (abbreviation)
   - Expected phone: "13344556677", Actual: "133-4455-6677" -> SUCCESS (formatting difference)
   - Expected name: "Barbara Jones", Actual: "barbara jones" -> SUCCESS (case difference)
10. Examples of FAILURE:
   - Expected address: "Beijing", Actual: "Shanghai" -> FAILURE (different city)
   - Expected phone: "13344556677", Actual: "13344556678" -> FAILURE (different number)
   - Expected name: "Barbara Jones", Actual: "Mary Jones" -> FAILURE (different person)
"""


# ============================================================================
# 封装验证函数：检查 Taodian 淘店订单操作是否成功
# ============================================================================

# 淘店应用包名
_PACKAGE_NAME = "com.testmall.app"
_LEVELDB_PATH = "/data/data/com.testmall.app/app_webview/Default/Local Storage/leveldb"


def _extract_data_from_leveldb(env: interface.AsyncEnv) -> dict:
    """提取 LevelDB 中的购物车和订单数据。

    Returns:
      包含购物车和订单数据的字典:
      {
        'cart': [...],  # 购物车商品列表
        'orders': [...]  # 订单数据列表
      }
    """
    import plyvel

    adb_utils.set_root_if_needed(env.controller)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    android_world_dir = os.path.dirname(os.path.dirname(current_dir))
    tmp_base_dir = os.path.join(android_world_dir, "tmp")
    os.makedirs(tmp_base_dir, exist_ok=True)

    local_temp_dir = tempfile.mkdtemp(prefix="taodian_leveldb_", dir=tmp_base_dir)
    print(f"[DEBUG] 创建临时目录: {local_temp_dir}")

    try:
        from android_env.proto import adb_pb2
        try:
            pull_result = adb_utils.issue_generic_request(
                ["pull", _LEVELDB_PATH, local_temp_dir],
                env.controller
            )
        except Exception as e:
            print(f"[DEBUG] adb pull 异常 (可能路径不存在): {e}")
            return {'cart': [], 'orders': []}

        if pull_result.status != adb_pb2.AdbResponse.Status.OK:
            print(f"[DEBUG] adb pull 失败 (可能路径不存在)")
            return {'cart': [], 'orders': []}

        print(f"[DEBUG] adb pull 成功")

        db_path = os.path.join(local_temp_dir, "leveldb")
        if not os.path.exists(db_path):
            db_path = local_temp_dir

        try:
            db = plyvel.DB(db_path, create_if_missing=False)
        except Exception as e:
            print(f"[DEBUG] 无法打开 LevelDB: {e}")
            return {'cart': [], 'orders': []}

        all_data = {}

        try:
            for key, value in db:
                key_str = key.decode('utf-8', errors='ignore')

                if len(value) > 1 and value[0] == 0:
                    json_bytes = value[1:]
                    value_str = json_bytes.decode('utf-16-le', errors='ignore')
                else:
                    value_str = value.decode('utf-8', errors='ignore')

                json_start = -1
                for i, c in enumerate(value_str):
                    if c in '[{':
                        json_start = i
                        break

                if json_start >= 0:
                    json_str = value_str[json_start:]
                    try:
                        data = json.loads(json_str)
                        all_data[key_str] = data
                    except json.JSONDecodeError:
                        all_data[key_str] = value_str
                else:
                    all_data[key_str] = value_str

        finally:
            db.close()

        # 打印所有 key 和对应的数据类型
        # print(f"[DEBUG] LevelDB 中的所有 keys:")
        # for key, value in all_data.items():
        #     value_type = type(value).__name__
        #     if isinstance(value, (list, dict)):
        #         value_preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        #     else:
        #         value_preview = str(value)[:100]
        #     print(f"[DEBUG]   {key} ({value_type}): {value_preview}")

        # 提取购物车数据
        cart_data = []
        for key in all_data:
            if 'mall4uni_cart' in key:
                cart_data = all_data[key] or []
                break

        # 提取订单数据（可能有多个 orderItem）
        orders_data = []
        for key in all_data:
            if 'orderItem' in key:
                order_data = all_data[key]
                print(f"[DEBUG] Found orderItem data: {order_data}")
                if isinstance(order_data, list):
                    orders_data.extend(order_data)
                elif isinstance(order_data, dict):
                    orders_data.append(order_data)

        print(f"[DEBUG] 从 LevelDB 解析出 {len(orders_data)} 个订单项")

        return {
            'cart': cart_data,
            'orders': orders_data
        }

    finally:
        if os.path.exists(local_temp_dir):
            shutil.rmtree(local_temp_dir, ignore_errors=True)


def get_orders(env: interface.AsyncEnv) -> list:
    """获取所有订单列表。

    Args:
        env: Android 环境接口。

    Returns:
        订单字典列表。
    """
    data = _extract_data_from_leveldb(env)
    orders = data.get('orders', [])

    # 打印所有订单详情
    print(f"[DEBUG] Found {len(orders)} orders:")
    for i, order in enumerate(orders):
        print(f"[DEBUG] Order {i+1}:")
        for key, value in order.items():
            print(f"[DEBUG]   {key}: {value}")

    return orders


def get_cart(env: interface.AsyncEnv) -> list:
    """获取购物车商品列表。

    Args:
        env: Android 环境接口。

    Returns:
        购物车商品字典列表。
    """
    data = _extract_data_from_leveldb(env)
    cart = data.get('cart', [])

    # 打印购物车详情
    # print(f"[DEBUG] Found {len(cart)} items in cart:")
    # for i, item in enumerate(cart):
    #     print(f"[DEBUG] Cart item {i+1}:")
    #     for key, value in item.items():
    #         print(f"[DEBUG]   {key}: {value}, type: {type(value)}")

    return cart


def clear_cart(env: interface.AsyncEnv) -> None:
    """清空购物车。

    Args:
        env: Android 环境接口。
    """
    # 通过清除应用数据来清空购物车
    adb_utils.clear_app_data(_PACKAGE_NAME, env.controller)
    print("[DEBUG] Cart cleared")



def clear_orders(env: interface.AsyncEnv) -> None:
    """清空所有订单（通过清除应用数据）。

    Args:
        env: Android 环境接口。
    """
    adb_utils.clear_app_data(_PACKAGE_NAME, env.controller)
    print("[DEBUG] All orders cleared")


def _normalize_product_name(name: str) -> str:
    """标准化商品名称用于匹配。"""
    return name.lower().strip()



def _product_matches(product: dict, expected: dict) -> bool:
    """检查商品是否匹配预期条件。

    Args:
        product: 实际商品数据。
        expected: 期望的商品条件。

    Returns:
        True 如果匹配，False 否则。
    """
    # 检查商品ID（支持字符串和数字）
    if 'prodId' in expected:
        expected_id = str(expected['prodId'])
        actual_id = str(product.get('prodId', ''))
        if actual_id != expected_id:
            return False

    # 检查SKU ID（支持字符串和数字）
    if 'skuId' in expected:
        expected_sku = str(expected['skuId'])
        actual_sku = str(product.get('skuId', ''))
        if actual_sku != expected_sku:
            return False

    # 检查商品名称（支持部分匹配）
    if 'prodName' in expected:
        expected_name = _normalize_product_name(expected['prodName'])
        actual_name = _normalize_product_name(product.get('prodName', ''))
        if expected_name != actual_name:
            return False

    # 检查价格（支持浮点数比较）
    if 'price' in expected:
        expected_price = float(expected['price'])
        actual_price = float(product.get('price', 0))
        if abs(actual_price - expected_price) > 0.01:
            return False

    # 检查数量（支持字符串和数字）
    if 'prodCount' in expected:
        expected_count = int(expected['prodCount'])
        actual_count = int(product.get('prodCount', 1))
        if actual_count != expected_count:
            return False

    if 'shopId' in expected:
        expected_shop_id = str(expected['shopId'])
        actual_shop_id = str(product.get('shopId', ''))
        if actual_shop_id != expected_shop_id:
            return False
    return True


def validate_order_created(
    env: interface.AsyncEnv,
    before_orders: list,
    expected: dict,
    save_img_path: str = "",
    goal: str = "",
) -> bool:
    """验证订单是否被正确创建（单商品）。

    Args:
        env: Android 环境接口。
        before_orders: 任务执行前的订单列表。
        expected: 期望的订单数据，支持以下字段：
            - prodId: str - 商品ID
            - skuId: str - SKU ID
            - prodName: str - 商品名称
            - price: float - 商品价格
            - prodCount: int - 商品数量
            - contact_name: str - 收件人姓名（使用 VLM 验证）
            - phone: str - 收件人电话（使用 VLM 验证）
            - address: str - 收件地址（使用 VLM 验证）
        save_img_path: 截图保存目录路径（可选），用于 VLM 验证收货人信息。
        goal: 任务目标描述（可选），用于 VLM 验证。

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

    order = new_orders[0]
    print(f"[DEBUG] New order: {order}")
    # 验证商品字段
    if not _product_matches(order, expected):
        print(f"[DEBUG] Product does not match expected")
        return False

    # 验证收货人信息（使用 VLM 截图验证）
    receiver_fields = ['contact_name', 'phone', 'address']
    if save_img_path and any(field in expected for field in receiver_fields):
        receiver_result = validate_receiver_info_with_vlm(
            save_img_path=save_img_path,
            expected=expected,
            goal=goal,
        )
        if not receiver_result:
            print(f"[DEBUG] Receiver info VLM validation failed")
            return False

    print(f"[DEBUG] Order creation validated: True")
    print(f"[DEBUG] Order details: {order.get('prodName')} (¥{order.get('price')}) x {order.get('prodCount', 1)}")
    return True


def validate_receiver_info_with_vlm(
    save_img_path: str,
    expected: dict,
    goal: str = "",
) -> bool:
    """使用 VLM 验证收货人信息（联系人、电话、地址）是否正确。

    通过分析 Agent 操作过程中的截图，判断订单中的收货人信息是否与预期一致。

    Args:
        save_img_path: 截图保存目录路径。
        expected: 期望的收货人信息，支持以下字段：
            - contact_name: str - 收件人姓名
            - phone: str - 收件人电话
            - address: str - 收件地址
        goal: 任务目标描述（可选）。

    Returns:
        True 如果验证通过，False 否则。
    """
    # 收集截图文件
    if not os.path.isdir(save_img_path):
        print(f"[DEBUG] save_img_path does not exist: {save_img_path}")
        return False

    image_files = sorted([
        os.path.join(save_img_path, f)
        for f in os.listdir(save_img_path)
        if f.startswith('step_') and f.endswith('.jpg')
    ], key=lambda p: int(os.path.basename(p).replace('step_', '').replace('.jpg', '')))

    # 只取最后15张截图
    image_files = image_files[-15:]

    if not image_files:
        print(f"[DEBUG] No screenshots found in {save_img_path}")
        return False

    print(f"[DEBUG] Found {len(image_files)} screenshots for VLM validation")

    # 构建期望信息字符串
    expected_parts = []
    if 'contact_name' in expected:
        expected_parts.append(f"Contact Name: {expected['contact_name']}")
    if 'phone' in expected:
        expected_parts.append(f"Phone: {expected['phone']}")
    if 'address' in expected:
        expected_parts.append(f"Address: {expected['address']}")
    expected_info = "\n".join(expected_parts)

    prompt = TAODIAN_RECEIVER_VALIDATION_PROMPT.format(
        expected_info=expected_info,
    )

    print(f"[DEBUG] Expected receiver info for VLM: {expected_info}")
    print(f"[DEBUG] Calling VLM to validate receiver info from screenshots...")

    try:
        is_match, explanation = vlm_as_judge.vlm_judge(
            goal=goal,
            task_prompt=prompt,
            image_paths=image_files,
        )
        print(f"[DEBUG] VLM judgment for receiver info: {is_match}, Explanation: {explanation}")
    except Exception as e:
        print(f"[DEBUG] VLM validation failed with exception: {e}")
        return False

    return is_match


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
                    {'prodId': '22', 'prodName': '商品A'},
                    {'prodId': '33', 'prodName': '商品B'},
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
        print(f"[DEBUG] Actual Order {i}: prodName='{order.get('prodName')}', prodId={order.get('prodId')}, count={order.get('prodCount', 1)}")

    # 获取新订单
    new_orders = [o for o in after_orders if o not in before_orders]
    print(f"[DEBUG] New orders: {len(new_orders)}")

    expected_orders = expected.get('orders', [])
    expected_count = len(expected_orders)

    if len(new_orders) != expected_count:
        print(f"[DEBUG] Expected {expected_count} new orders, found {len(new_orders)}")
        return False

    # 验证每个预期订单都能在新订单中找到匹配
    matched_indices = set()
    for i, expected_order in enumerate(expected_orders):
        matched = False
        for j, new_order in enumerate(new_orders):
            if j in matched_indices:
                continue
            if _product_matches(new_order, expected_order):
                matched = True
                matched_indices.add(j)
                print(f"[DEBUG] Order {i+1} matched: prodName={new_order.get('prodName')}")
                break
        if not matched:
            print(f"[DEBUG] Order {i+1} not matched: {expected_order}")
            return False

    print(f"[DEBUG] All {expected_count} orders validated: True")
    return True

