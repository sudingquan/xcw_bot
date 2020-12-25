import pytz
import random
import os
from datetime import datetime
import hoshino
from hoshino import Service, R
from nonebot import MessageSegment

sv = Service('hourcall', enable_on_default=False, help_='时报')
tz = pytz.timezone('Asia/Shanghai')
record_folder = R.get('record/hourcall/').path
record_pre = ('181a-', '185-', '283a-')

def get_hour_call():
    """挑出一组时报，每日更换，一日之内保持相同"""
    cfg = hoshino.config.hourcall
    now = datetime.now(tz)
    hc_groups = cfg.HOUR_CALLS_ON
    g = hc_groups[ now.day % len(hc_groups) ]
    return cfg.HOUR_CALLS[g]


@sv.scheduled_job('cron', hour='*')
async def hour_call():
    now = datetime.now(tz)
    if 2 <= now.hour <= 4:
        return  # 宵禁 免打扰
    msg = get_hour_call()[now.hour]
    chosen_file = random.choice(record_pre) + str(now.hour).zfill(2) + '00.mp3'
    record_path = os.path.join(record_folder, chosen_file)
    record = MessageSegment.record(f'file:///{os.path.abspath(record_path)}')
    await sv.broadcast(msg, 'hourcall', 0)
    await sv.broadcast(record, 'hourcall_record', 0)
