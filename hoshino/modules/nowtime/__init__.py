import os
import time
from  datetime import datetime
from hoshino import util
from hoshino.service import Service
from .data_source import add_text,pic_to_b64

config_path = os.path.dirname(__file__)+'/config.json'
sv = Service('nowtime', enable_on_default=True)

@sv.on_keyword(keywords = ('报时','现在几点','几点钟啦','几点啦'))
async def showtime(bot,ctx):
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    hour_str = f' {hour}' if hour<10 else str(hour)
    minute_str = f' {minute}' if minute<10 else str(minute)
    template_path = os.path.join(os.path.dirname(__file__),'template.jpg')
    save_path = os.path.join(os.path.dirname(__file__),'nowtime.jpg')
    add_text(template_path,save_path,f'{hour_str}\n点\n{minute_str}\n分\n了\n !',textsize=48,textfill='black',position=(430,5))#修改此行调整文字大小位置
    '''
    textsize文字大小
    textfill 文字颜色，black 黑色，blue蓝色，white白色，yellow黄色，red红色
    position是距离图片左上角偏移量，第一个数是宽方向，第二个数是高方向
    f'{hour_str}\n点\n{minute_str}\n分\n了\n !' 代表报时文本，已设置为竖排，\n为换行  
    '''
    base64_str = pic_to_b64(save_path)
    reply = f'[CQ:image,file={base64_str}]'
    await bot.send(ctx,reply,at_sender=False)

