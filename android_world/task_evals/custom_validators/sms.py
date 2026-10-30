

"""Tasks for Simple SMS Messenger."""

import random
import time
from android_env.proto import adb_pb2
from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals.custom_validators import llm_as_judge


SMS_CONTENT_PROMPT = """You are an SMS content validation assistant. Please determine whether the actual SMS content matches the expected content.

Expected Content:
{expected_body}

Actual Content:
{actual_body}

Judgment Rules:
1. Focus on whether the core information is conveyed - minor wording differences are acceptable
2. The actual content should express the same general idea as expected
3. Examples of SUCCESS:
   - Expected: "Meeting at 3pm", Actual: "We have a meeting at 3pm" -> SUCCESS
   - Expected: "Buy milk", Actual: "Remember to buy milk" -> SUCCESS
   - Expected: "Meeting at 3pm", Actual: "Meeting scheduled for 3pm" -> SUCCESS
   - Expected: "Call John", Actual: "Please call John later" -> SUCCESS
4. Examples of FAILURE:
   - Expected: "Call John", Actual: "Call Mary" -> FAILURE (different person)
   - Expected: "Meeting at 3pm", Actual: "Meeting at 5pm" -> FAILURE (wrong time)
   - Expected: "Buy milk and eggs", Actual: "Buy milk" -> FAILURE (major info missing)
5. Judge as SUCCESS if the core information is similar, even if phrased differently
"""


def _parse_sms_line_output(output: str) -> list[dict[str, str]]:
    """解析 sqlite3 -line 格式的输出，返回字典列表。

    每条记录的字段（address, date, body 等）以 "key = value" 形式各占一行，
    记录之间以空行分隔。body 字段可能跨多行。

    Args:
        output: sqlite3 -line 命令的完整输出。

    Returns:
        字典列表，每个字典包含一条短信的字段。
    """
    if not output.strip():
        return []

    messages = []
    current = {}
    body_lines = []
    in_body = False

    for line in output.split('\n'):
        stripped = line.strip()

        if stripped.startswith('_id = '):
            # 新记录开始，保存上一条
            if current:
                if body_lines:
                    current['body'] = '\n'.join(body_lines)
                messages.append(current)
            current = {'_id': stripped[6:].strip()}
            body_lines = []
            in_body = False
        elif stripped.startswith('address = '):
            current['address'] = stripped[10:].strip()
            in_body = False
        elif stripped.startswith('date = '):
            current['date'] = stripped[7:].strip()
            in_body = False
        elif stripped.startswith('body = '):
            body_lines.append(stripped[7:])
            in_body = True
        elif in_body:
            # body 的后续行（包括空行），直到遇到 _id = 才停止
            body_lines.append(line.rstrip())

    # 保存最后一条记录
    if current:
        if body_lines:
            current['body'] = '\n'.join(body_lines)
        messages.append(current)

    return messages


def get_sent_messages(
    env: interface.AsyncEnv,
    phone_number: str | None = None,
    since_ms: int | None = None,
) -> list[dict[str, str]]:
    """查询已发送的短信。

    直接用 SQL 过滤号码和时间，避免在 Python 侧遍历所有短信。

    Args:
        env: Android 环境接口。
        phone_number: 可选，只返回此号码的短信（已标准化）。
        since_ms: 可选，只返回此时间戳之后的短信（毫秒）。

    Returns:
        字典列表，每个字典包含 _id, address, date, body 字段。
    """
    db_path = "/data/data/com.android.providers.telephony/databases/mmssms.db"

    conditions = ["type=2"]
    if phone_number:
        conditions.append(f"address='{phone_number}'")
    if since_ms is not None:
        conditions.append(f"date>={since_ms}")

    where = " AND ".join(conditions)
    query = f"SELECT _id, address, date, body FROM sms WHERE {where} ORDER BY date DESC LIMIT 50"

    response = adb_utils.issue_generic_request(
        f"shell sqlite3 -line {db_path} '{query}'".split(),
        env.controller,
    )

    output = response.generic.output.decode('utf-8', errors='ignore')
    return _parse_sms_line_output(output)


def get_android_time(env: interface.AsyncEnv) -> int:
    """获取 Android 设备的当前时间（毫秒）。"""
    adb_output = adb_utils.issue_generic_request(
        ["shell", "date", "+%s"],
        env.controller,
    )
    return int(adb_output.generic.output.strip()) * 1000


def validate_sms_sent(
    env: interface.AsyncEnv,
    goal: str,
    phone_number: str,
    expected_body: str,
    time_mins: int = 5,
) -> bool:
    """验证是否成功发送短信到指定号码，使用 LLM 判断内容是否匹配。

    号码使用精确匹配，内容使用 LLM 判断是否信息一致（不多不少）。

    Args:
        env: Android 环境接口。
        goal: 任务目标描述。
        phone_number: 目标手机号码。
        expected_body: 期望的短信内容。
        time_mins: 时间窗口（分钟），只检查最近这么多分钟内发送的短信。

    Returns:
        True 如果验证通过（短信已发送且内容匹配），False 否则。
    """
    current_time_ms = get_android_time(env)
    n_minutes_ms = time_mins * 60 * 1000
    since_ms = current_time_ms - n_minutes_ms

    # 标准化号码格式
    normalized_phone_number = phone_number.replace("+", "").replace("-", "").replace(" ", "")

    print(f"[DEBUG] Checking for SMS to: {phone_number} (normalized: {normalized_phone_number})")

    # 直接在 SQL 中按号码和时间过滤
    messages = get_sent_messages(env, phone_number=normalized_phone_number, since_ms=since_ms)

    matching_bodies = []
    for msg in messages:
        body = msg.get('body', '')
        if body:
            matching_bodies.append(body)
            print(f"[DEBUG] Found matching SMS, full body:\n{body}")

    if not matching_bodies:
        print(f"[DEBUG] No SMS found to number: {phone_number}")
        return False

    # 使用 LLM 判断内容是否匹配
    for actual_body in matching_bodies:
        prompt = SMS_CONTENT_PROMPT.format(
            expected_body=expected_body,
            actual_body=actual_body,
        )

        print(f"[DEBUG] Calling LLM to validate SMS content...")
        is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
        print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

        if is_match:
            print(f"[DEBUG] SMS content validated as matching")
            return True

    print(f"[DEBUG] No SMS content matched the expected content")
    return False