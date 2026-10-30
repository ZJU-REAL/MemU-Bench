"""固定任务：长任务集合。

包含以下任务：
- User0Long_CalendarModifyMeeting: 修改会议日程时间
- User0Long_SMSSendCancelHangout: 给 William Jones 发短信取消出去玩
- User0Long_SMSSendInviteHangout: 给 Sarah Jones 发短信邀请出去玩
- User0Long_ClockSetAlarmBeforeFlight: 定航班前2小时的闹钟
- User0Long_TaodianOrderTShirt: 在淘店下单运动透气性T恤
- User0Long_TaodianOrderWhiteTShirt: 在淘店下单经典白色T恤
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import sms as sms_validator
from android_world.task_evals.custom_validators import taodian as taodian_validator


class User0Long_CalendarModifyMeeting(fixed_task_eval.TaskEval):
  """固定任务：修改会议日程时间。

  Agent 需要在日历应用中将下周三的会议改到下周四的同一时间。
  验证方式：检查日历事件的时间是否被正确修改。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "Online Meeting"
  _NEW_START_TS = 1778162400
  _NEW_END_TS = 1778169600
  _SNAPSHOT_NAME = "snapshot_0_long"

  @property
  def goal(self) -> str:
    return f"Change the meeting time in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Move the meeting from next Wednesday to next Thursday at the same time in {self.app_name} app."

  @property
  def information(self) -> str:
    return "William Jones texted me via simple sms messenger app saying the meeting time has changed."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar modify meeting task...")
    print(f"[DEBUG] Before events: {len(self._before_events)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar_validator.validate_event_time_modified(
        env=env,
        before_events=self._before_events,
        expected_title=self._EVENT_TITLE,
        expected_start_ts=self._NEW_START_TS,
    )
    return 1.0 if result else 0.0


class User0Long_SMSSendCancelHangout(fixed_task_eval.TaskEval):
  """固定任务：给 William Jones 发短信取消出去玩。

  Agent 需要在 Simple SMS Messenger 中给 William Jones 发短信，
  告诉他有点事情不能一起出去了。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "William Jones"
  _PHONE_NUMBER = "5557521924"
  _MESSAGE_BODY = "I have something to do, I can't play with you next weekend."
  _SNAPSHOT_NAME = "snapshot_0_long"

  @property
  def goal(self) -> str:
    return f"Send a message to my friend via {self.app_name} app, telling him I have something to do and can't play with him next weekend."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying: {self._MESSAGE_BODY}"

  @property
  def information(self) -> str:
    return "I texted a friend via simple sms messenger app and we agreed to play next weekend."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send cancel hangout task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")
    print(f"[DEBUG] Message: {self._MESSAGE_BODY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0


class User0Long_SMSSendInviteHangout(fixed_task_eval.TaskEval):
  """固定任务：给 Sarah Jones 发短信邀请出去玩。

  Agent 需要在 Simple SMS Messenger 中给 Sarah Jones 发短信，
  问她今天是否出来玩，并告知地点是 Center Park。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Sarah Jones"
  _PHONE_NUMBER = "5556635514"
  _MESSAGE_BODY = "Are you coming out to hang out with us today? The place is Center Park."
  _SNAPSHOT_NAME = "snapshot_0_long"

  @property
  def goal(self) -> str:
    return f"I forgot to text a friend to ask if she's coming out to hang out today, please send a text message to ask her, and tell her the location via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying: {self._MESSAGE_BODY}"

  @property
  def information(self) -> str:
    return "Jennifer Smith and I texted about where to hang out. Mary Johnson asked me to invite Sarah Jones, but I forgot."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send invite hangout task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")
    print(f"[DEBUG] Message: {self._MESSAGE_BODY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0


class User0Long_ClockSetAlarmBeforeFlight(fixed_task_eval.TaskEval):
  """固定任务：定航班前2小时的闹钟。

  Agent 需要在 Clock 应用中定一个今天下午7点的闹钟。
  验证方式：通过 UI 检查闹钟是否被正确添加。
  """

  app_name = "clock"

  complexity = 4.0

  _ALARM_HOUR = 19
  _ALARM_MINUTE = 0
  _FUZZY_MINUTES = 3
  _SNAPSHOT_NAME = "snapshot_0_long"
  _REQUIRED_TEXT = ["Today"]

  @property
  def goal(self) -> str:
    return f"Set an alarm 2 hours before my flight in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Set an alarm for 7:00 PM today in {self.app_name} app."

  @property
  def information(self) -> str:
    return "Charles Martinez texted me via simple sms messenger app reminding me about the flight time."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing clock set alarm before flight task...")
    print(f"[DEBUG] Expected alarm: {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = clock_validator.validate_alarm_added(
        env=env,
        expected_hour=self._ALARM_HOUR,
        expected_minute=self._ALARM_MINUTE,
        fuzzy_minutes=self._FUZZY_MINUTES,
        required_texts=self._REQUIRED_TEXT
    )
    return 1.0 if result else 0.0


class User0Long_TaodianOrderTShirt(fixed_task_eval.TaskEval):
  """固定任务：在淘店下单运动透气性T恤。

  Agent 需要在 Taodian 淘店中购买一件 S 码的运动透气性T恤，
  收件联系人填 Xiao Wang，号码填 13344556677，
  地址是 Room 404, Building 3, No. 1288 zhongxing Street, Shanghai。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "taodian"

  complexity = 4.0

  _PROD_NAME = "运动透气性T恤"
  _SKU_NAME = "S码"
  _PRODID = "2"
  _SKUID = "2001"
  _SHOPID = "1"
  _PROD_COUNT = 1
  _CONTACT_NAME = "Xiao Wang"
  _PHONE = "13344556677"
  _ADDRESS = "Room 404, Building 3, No. 1288 zhongxing Street, Shanghai"
  _SNAPSHOT_NAME = "snapshot_0_long"

  @property
  def goal(self) -> str:
    return f"Buy a gift for {self._CONTACT_NAME} on {self.app_name} app, size S. Fill in {self._CONTACT_NAME}'s contact info. Payment password is 123456."

  @property
  def full_goal(self) -> str:
    return (f"Buy one {self._SKU_NAME} {self._PROD_NAME} on {self.app_name} app, "
            f"contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}, "
            f"address is {self._ADDRESS}. Payment password is 123456.")

  @property
  def information(self) -> str:
    return (f"Jennifer Smith and I texted about what gift to get for Xiao Wang, "
            f"and I texted Xiao Wang to ask for the shipping address via simple sms messenger.")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = taodian_validator.get_orders(env)
    print(f"[DEBUG] Initializing taodian order t-shirt task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = taodian_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'prodId': self._PRODID,
            'skuId': self._SKUID,
            'shopId': self._SHOPID,
            'prodCount': self._PROD_COUNT,
            'contact_name': self._CONTACT_NAME,
            'phone': self._PHONE,
            'address': self._ADDRESS,
        },
        save_img_path=self.save_img_path,
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User0Long_TaodianOrderWhiteTShirt(fixed_task_eval.TaskEval):
  """固定任务：在淘店下单经典白色T恤。

  Agent 需要在 Taodian 淘店中购买一件 S 码的经典白色T恤。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "taodian"

  complexity = 4.0

  _PROD_NAME = "经典白色T恤"
  _SKU_NAME = "S码"
  _PRODID = "1"  # TODO: 需要实际运行确认
  _SKUID = "1001"  # TODO: 需要实际运行确认
  _SHOPID = "1"
  _PROD_COUNT = 1
  _SNAPSHOT_NAME = "snapshot_0_long"

  @property
  def goal(self) -> str:
    return f"Buy the T-shirt I looked at many times today on {self.app_name} app. Payment password is 123456."

  @property
  def full_goal(self) -> str:
    return f"Order one {self._SKU_NAME} {self._PROD_NAME} on {self.app_name} app. Payment password is 123456."

  @property
  def information(self) -> str:
    return "I browsed many clothes on taodian app today, and there is a white T-shirt I looked at many times."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = taodian_validator.get_orders(env)
    print(f"[DEBUG] Initializing taodian order white t-shirt task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = taodian_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'prodId': self._PRODID,
            'skuId': self._SKUID,
            'shopId': self._SHOPID,
            'prodCount': self._PROD_COUNT,
        },
    )
    return 1.0 if result else 0.0