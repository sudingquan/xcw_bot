from hoshino import Service
from hoshino.typing import CQEvent
from hoshino.priv import *
from nonebot import MessageSegment as ms

import hoshino
import sqlite3, os

sv = Service('haogan', bundle='pcr娱乐', help_='''
贴贴 | 显示好感度
贴贴排行 | 显示好感度的群排行榜(只显示前十名)
'''.strip())


DB_PATH = os.path.expanduser('~/.hoshino/haogan.db')


class ImpressionValue:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._create_table()


    def _connect(self):
        return sqlite3.connect(DB_PATH)


    def _create_table(self):
        try:
            self._connect().execute('''CREATE TABLE IF NOT EXISTS IMPRESSION
                          (GID             INT    NOT NULL,
                           UID             INT    NOT NULL,
                           VALUE           INT    NOT NULL,
                           PRIMARY KEY(GID, UID));''')
        except:
            raise Exception('创建表发生错误')
    
    
    def _increase_impression_value(self, gid, uid, val):
        try:
            impression_value = self._get_impression_value(gid, uid)
            conn = self._connect()
            conn.execute("INSERT OR REPLACE INTO IMPRESSION (GID,UID,VALUE) \
                                VALUES (?,?,?)", (gid, uid, impression_value+val))
            conn.commit()       
        except:
            raise Exception('更新表发生错误')


    def _decrease_impression_value(self, gid, uid, val):
        try:
            impression_value = self._get_impression_value(gid, uid)
            conn = self._connect()
            conn.execute("INSERT OR REPLACE INTO IMPRESSION (GID,UID,VALUE) \
                                VALUES (?,?,?)", (gid, uid, impression_value-val))
            conn.commit()       
        except:
            raise Exception('更新表发生错误')


    def _get_impression_value(self, gid, uid):
        try:
            r = self._connect().execute("SELECT VALUE FROM IMPRESSION WHERE GID=? AND UID=?",(gid,uid)).fetchone()
            if r is None:
                self._set_impression_value(gid, uid, 20)
                return 20
            else: 
                return r[0]
        except:
            raise Exception('查找表发生错误')


    def _set_impression_value(self, gid, uid, val):
        try:
            conn = self._connect()
            conn.execute("INSERT OR REPLACE INTO IMPRESSION (GID,UID,VALUE) \
                                VALUES (?,?,?)", (gid, uid, val))
            conn.commit()       
        except:
            raise Exception('更新表发生错误')


async def get_user_card_dict(bot, group_id):
    mlist = await bot.get_group_member_list(group_id=group_id)
    d = {}
    for m in mlist:
        d[m['user_id']] = m['card'] if m['card']!='' else m['nickname']
    return d


@sv.on_fullmatch(('贴贴排行'))
async def impression_value_group_ranking(bot, ev: CQEvent):
    try:
        user_card_dict = await get_user_card_dict(bot, ev.group_id)
        card_impressionvalue_dict = {}
        print ("before class")
        impression_value = ImpressionValue()
        print ("after class")
        for uid in user_card_dict.keys():
            if uid != ev.self_id:
                card_impressionvalue_dict[user_card_dict[uid]] = impression_value._get_impression_value(ev.group_id, uid)
        group_ranking = sorted(card_impressionvalue_dict.items(), key = lambda x:x[1], reverse = True)
        msg = '此群好感度排行为:\n'
        for i in range(min(len(group_ranking), 10)):
            if group_ranking[i][1] != 0:
                msg += f'第{i+1}名: {group_ranking[i][0]}, 好感度: {group_ranking[i][1]}\n'
        await bot.send(ev, msg.strip())
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))


@sv.on_fullmatch(('贴贴'), only_to_me=True)
async def get_impression_value(bot, ev: CQEvent):
    try:
        impression_value = ImpressionValue()
        uid = ev.user_id
        gid = ev.group_id
        val = impression_value._get_impression_value(gid, uid)
        await bot.send(ev, f'你的好感度为{val}', at_sender=True)
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))


@sv.on_rex((r'^好感度?([+-])(\d*)$'))
async def set_impression_value(bot, ev: CQEvent):
    if get_user_priv(ev) < ADMIN:
        await bot.send(ev, '管理限定功能')
        return
    impression_value = ImpressionValue()
    gid = ev.group_id
    match = ev['match']
    raw_msg = ev.raw_message
    msg = ev.message
    if '[CQ:at,qq=' not in raw_msg:
        return
    val = int(match.group(2))
    for m in msg:
        if m.type == 'at' and m.data['qq'] != 'all':
            uid = m.data['qq']
            if '+' in match.group(1):
                impression_value._increase_impression_value(gid, uid, val)
                await bot.send(ev, f'已为{ms.at(uid)}冲值{val}好感')
            elif '-' in match.group(1): 
                impression_value._decrease_impression_value(gid, uid, val)
                await bot.send(ev, f'已为{ms.at(uid)}扣除{val}好感')
        else:
            continue
    return
