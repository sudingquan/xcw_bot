import os
import re
import time
import random
import numpy as np
import copy
import hoshino
from itertools import combinations
from PIL import Image

from nonebot import on_command, CommandSession, MessageSegment as ms, NoneBot
from nonebot.exceptions import CQHttpError

from hoshino import R, Service, MessageSegment
from hoshino import util

from hoshino.modules.poker import th_poker_ranking as poker_rank
from hoshino.modules.haogan.haogan import ImpressionValue

try:
    import ujson as json
except:
    import json

res_dir = os.path.expanduser(hoshino.config.RES_DIR)
image_dir = os.path.join(res_dir, 'poker')
iv = ImpressionValue()


sv = Service('poker', enable_on_default=True, visible=True)
poker_folder = R.img('poker/').path

cardList = ['AH', '2H', '3H', '4H', '5H', '6H', '7H', '8H', '9H', 'TH', 'JH', 'QH', 'KH',
            'AS', '2S', '3S', '4S', '5S', '6S', '7S', '8S', '9S', 'TS', 'JS', 'QS', 'KS',
            'AC', '2C', '3C', '4C', '5C', '6C', '7C', '8C', '9C', 'TC', 'JC', 'QC', 'KC',
            'AD', '2D', '3D', '4D', '5D', '6D', '7D', '8D', '9D', 'TD', 'JD', 'QD', 'KD']

_cardDict = {
    'AH':'红桃A',
    '2H':'红桃2', 
    '3H':'红桃3', 
    '4H':'红桃4', 
    '5H':'红桃5',
    '6H':'红桃6',
    '7H':'红桃7',
    '8H':'红桃8',
    '9H':'红桃9',
    'TH':'红桃10',
    'JH':'红桃J',
    'QH':'红桃Q',
    'KH':'红桃K',
    'AS':'黑桃A',
    '2S':'黑桃2', 
    '3S':'黑桃3', 
    '4S':'黑桃4', 
    '5S':'黑桃5',
    '6S':'黑桃6',
    '7S':'黑桃7',
    '8S':'黑桃8',
    '9S':'黑桃9',
    'TS':'黑桃10',
    'JS':'黑桃J',
    'QS':'黑桃Q',
    'KS':'黑桃K',
    'AD':'方片A',
    '2D':'方片2', 
    '3D':'方片3', 
    '4D':'方片4', 
    '5D':'方片5',
    '6D':'方片6',
    '7D':'方片7',
    '8D':'方片8',
    '9D':'方片9',
    'TD':'方片10',
    'JD':'方片J',
    'QD':'方片Q',
    'KD':'方片K',
    'AC':'梅花A',
    '2C':'梅花2', 
    '3C':'梅花3', 
    '4C':'梅花4', 
    '5C':'梅花5',
    '6C':'梅花6',
    '7C':'梅花7',
    '8C':'梅花8',
    '9C':'梅花9',
    'TC':'梅花10',
    'JC':'梅花J',
    'QC':'梅花Q',
    'KC':'梅花K'
}

stateList = ['enlist', 'start', 'turn1', 'turn2', 'turn3', 'nextgame']

_maxBet = 20
_maxP = 8

state = ''
players = []
cards = dict()
cards['deck'] = copy.copy(cardList)
cards['pool'] = []
prize = 0
pool = []
ori_buttonP = 0
ori_players = []
buttonP = 0
lastP = 0
currentP = 0
lastbet = 1

@sv.on_rex(re.compile(r'来[局盘把]德州'), normalize=True)
async def start(bot:NoneBot, ctx):
    # start a game.
    global state
    global players
    if state!='':
        return
    # add first user id to player list
    uid = ctx['user_id']
    players.append(uid)
    # now start recruiting players
    state = 'enlist'
    welcomeWords = f'{ms.at(uid)}发起了一场德州扑克，输入「in」加入游戏，输入「go」开始游戏，支持游戏人数2~{_maxP}人。'
    #welcomeWords += f'\n*输入「德州规则」可以查看简单的规则说明。'
    welcomeWords += f'\n已加入的玩家：'
    for player in players:
        welcomeWords += f'\n{ms.at(player)}'
    await bot.send(ctx, welcomeWords)

@sv.on_command('in', only_to_me=False)
async def enlist(session):
    global state
    global players
    global buttonP
    global ori_buttonP
    global ori_players
    uid = session.ctx['user_id']
    if uid in ori_players:
        await session.bot.send(session.ctx, '你已经加入游戏了')
        return
    if state=='nextgame':
        await session.bot.send(session.ctx, '暂不支持在该阶段加入')
        return
    elif len(players)>=_maxP:
        await session.bot.send(session.ctx, '游戏人数已达上限！')
        return
    elif state!='enlist': # join in
        ori_players.insert(ori_buttonP, uid)
        print(ori_players)
        ori_buttonP += 1
        msg = f'{ms.at(uid)}将在该轮游戏结束后加入！'
        await session.bot.send(session.ctx, msg)
        return
    # add user id to player list
    players.append(uid)
    buttonP = len(players)-1
    ori_buttonP = buttonP
    random.shuffle(players)
    ori_players = copy.copy(players)
    if len(players)>=_maxP:
        await go(session)
        return
    msg = f'{ms.at(uid)}加入了游戏！'
    msg += f'\n已加入的玩家：'
    for player in players:
        msg += f'\n{ms.at(player)}'
    await session.bot.send(session.ctx, msg)

@sv.on_command('out', only_to_me=False)
async def leave(session):
    global state
    global players
    global buttonP
    global ori_buttonP
    global ori_players
    uid = session.ctx['user_id']
    if uid not in players:
        return
    if state=='enlist': # exit the waiting list
        # remove user id from player list
        removeP = players.index(uid)
        del players[removeP]
        buttonP = len(players)-1
        ori_buttonP = buttonP
        ori_players = copy.copy(players)
        msg = f'{ms.at(uid)}离开了游戏！'
        await session.bot.send(session.ctx, msg)
        if len(players)==0:
            await endgame(session=session)
        return
    elif state=='nextgame':
        await session.bot.send(session.ctx, '暂不支持在该阶段退出（要退早点说呀！这个时候才退改代码挺烦的')
        return
    else: # exit after next game
        removeP = players.index(uid)
        if removeP<ori_buttonP:
            ori_buttonP -= 1
        ori_buttonP = len(players)-2 if ori_buttonP<0 else ori_buttonP
        del ori_players[removeP]
        msg = f'{ms.at(uid)}将在该轮游戏结束后离开！'
        await session.bot.send(session.ctx, msg)
        return

@sv.on_command('go', only_to_me=False)
async def go(session):
    global state
    global players
    global cards
    global currentP
    global buttonP
    global lastP
    global pool
    global prize
    uid = session.ctx['user_id']
    if state=='nextgame':
        if uid != players[buttonP]:
            return
        await session.bot.send(session.ctx, f'马上开始下一局！')
        time.sleep(1)
        await reset(True,session)
        return
    if state!='enlist':
        return
    if len(players)<2:
        await session.bot.send(session.ctx, f'{ms.at(uid)} 游戏人数不足！最少需要2位玩家！')
        return
    state = 'start'
    await session.bot.send(session.ctx, '游戏开始！')
    time.sleep(1)
    # shuffle player list
    smallBlindP = buttonP + 1
    smallBlindP = 0 if smallBlindP>=len(players) else smallBlindP
    bigBlindP = smallBlindP + 1
    bigBlindP = 0 if bigBlindP>=len(players) else bigBlindP
    # the first player(who plays after big blind) will be the last player of the turn
    lastP = bigBlindP # the turn finishes after he plays
    currentP = bigBlindP
    msg = f'这轮游戏由{ms.at(players[buttonP])}坐庄，{ms.at(players[smallBlindP])}下1好感小盲注，'
    pool = [0]*len(players)
    pool[smallBlindP] = 1
    iv._increase_impression_value(session.ctx['group_id'],players[smallBlindP],-1)
    modifyRecord(uid=players[smallBlindP])
    msg += f'{ms.at(players[bigBlindP])}下2好感大盲注。'
    pool[bigBlindP] = 2
    iv._increase_impression_value(session.ctx['group_id'],players[bigBlindP],-2)
    modifyRecord(uid=players[bigBlindP]) 
    prize += 3
    await session.bot.send(session.ctx, msg)
    for player in players:
        time.sleep(0.5)
        random.shuffle(cards['deck'])
        cards[player] = [cards['deck'].pop(),cards['deck'].pop()]
        #concat = concat_poker(cards[player])
        #CQ1 = R.img('poker/', cards[player][0] + '.jpg').cqcode
        #CQ2 = R.img('poker/', cards[player][1] + '.jpg').cqcode
        print(f'{ms.at(player)}{_cardDict[cards[player][0]]}{_cardDict[cards[player][1]]}')
        modifyRecord(uid=player, playT=1)
        #await session.bot.send_private_msg(user_id=player, message=f'{concat}')# self_id=session.self_id,
        #await session.bot.send_private_msg(user_id=player, message=f'您的手牌：{_cardDict[cards[player][0]]}{_cardDict[cards[player][1]]}') # self_id=session.self_id,
        await session.bot.send(session.ctx, f'已为{ms.at(player)}发牌，请主动私聊镜华「发牌」')
    #await session.bot.send(session.ctx, f'爱梅斯有时会发牌失败，没收到请私聊爱梅斯「没牌」')
    state = 'turn1'
    time.sleep(1)
    nextP()
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    msg += '\n✦ 输入「跟」来跟注，自动加注到当前赌注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await session.bot.send(session.ctx, msg)

@sv.on_command('gg', only_to_me=False)
async def gg(session):
    global state
    global players
    global pool
    global prize
    global cards
    global lastP
    global currentP
    global buttonP
    global ori_players
    global ori_buttonP
    uid = session.ctx['user_id']
    if state=='nextgame':
        if uid != players[buttonP]:
            return
        await reset()
        await session.bot.send(session.ctx, f'已结束游戏！')
        return
    if 'turn' not in state:
        return
    if uid != players[currentP]:
        return
    # current player quit the game
    modifyRecord(uid=uid, loseT=1, losepoint=pool[currentP])
    flagLastP = (currentP==lastP)
    if currentP<=lastP:
        lastP -= 1
    lastP = len(players)-2 if lastP<0 else lastP
    if currentP<=buttonP:
        buttonP -= 1
    buttonP = len(players)-2 if buttonP<0 else buttonP
    del players[currentP]
    del pool[currentP]
    await session.bot.send(session.ctx, f'{ms.at(uid)}已退出游戏！')
    if currentP >= len(players):
        currentP = 0
    if len(players)==1:
        await win(session=session, uid=players[currentP])
        modifyRecord(uid=players[currentP], winT=1, winpoint=prize-pool[currentP])
        time.sleep(1)
        players = copy.copy(ori_players)
        buttonP = ori_buttonP
        if len(players)==1:
            await session.bot.send(session.ctx, '由于只剩下一人，游戏即将关闭！')
            time.sleep(1)
            await endgame(session=session)
            return
        buttonP += 1
        buttonP = 0 if buttonP>=len(players) else buttonP
        ori_buttonP = buttonP
        await session.bot.send(session.ctx, f'{ms.at(players[buttonP])}将要坐庄！输入「go」继续游戏，或输入「gg」结束游戏。')
        state = 'nextgame'
        return
    # if currentP==lastP and len(set(pool))==1:
        # await session.bot.send(session.ctx, f'本轮下注已结束！')
        # await draw(session=session)# <- next turn
        # return
    time.sleep(1)
    if flagLastP and len(set(pool))==1: # if the quitted is the lastP and all bets are the same
        await session.bot.send(session.ctx, f'本轮下注已结束！')
        await draw(session=session)# <- next turn
        return
    # case 1: the quitted is not the lastP; case 2: the bets are not the same
    # in these other cases, it should be next player to take action
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    if pool[currentP] < max(pool):
        msg += '\n✦ 输入「跟」来跟注，自动加注到当前赌注。'
    if pool[currentP] >= max(pool):
        msg += '\n✦ 输入「过」放弃加注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await session.bot.send(session.ctx, msg)

@sv.on_command('过', aliases=('pass', ), only_to_me=False)
async def wait(session):
    global state
    global players
    global pool
    global prize
    global cards
    global currentP
    global betpool
    if 'turn' not in state:
        return
    uid = session.ctx['user_id']
    if uid != players[currentP]:
        return
    if pool[currentP] < max(pool):
        return
    # current player pass
    await session.bot.send(session.ctx, f'{ms.at(uid)}决定观察一会儿')
    if nextP():
        await session.bot.send(session.ctx, f'本轮下注已结束！')
        await draw(session=session)# <- next turn
        return
    time.sleep(1)
    while True:
        if pool[currentP]>=_maxBet:
            if nextP():
                await session.bot.send(session.ctx, f'本轮下注已结束！')
                await draw(session=session)# <- next turn
                return
        else:
            break
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    if pool[currentP] < max(pool):
        msg += '\n✦ 输入「跟」来跟注，自动加注到当前赌注。'
    if pool[currentP] >= max(pool):
        msg += '\n✦ 输入「过」放弃加注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await session.bot.send(session.ctx, msg)

@sv.on_rex(re.compile('^下注([1-5])$'), normalize=False)
async def bet(bot:NoneBot, ctx):
    global state
    global players
    global pool
    global prize
    global cards
    global currentP
    if 'turn' not in state:
        return
    uid = ctx['user_id']
    if uid != players[currentP]:
        return
    # bet 1~5 friend points
    match = ctx['match'].group(1)
    print(match)
    bet = int(match)
    if pool[currentP]+bet<max(pool):
        await bot.send(ctx, '不能下注比前面的人还少！')
        return
    elif pool[currentP]+bet>_maxBet:
        await bot.send(ctx, f'心跳已经太快了！每个人的注金总额请不要超过{_maxBet}！')
        return
    elif pool[currentP]+bet>max(pool):
        await bot.send(ctx, f'{ms.at(uid)}已加注！所有人须重新下注！')
    iv._increase_impression_value(ctx['group_id'],uid, -bet)
    modifyRecord(uid)
    pool[currentP] += bet
    prize += bet
    if nextP():
        await bot.send(ctx, f'本轮下注已结束！')
        await draw(bot=bot,ctx=ctx)# <- next turn
        return
    time.sleep(1)
    while True:
        if pool[currentP]>=_maxBet:
            if nextP():
                await bot.send(ctx, f'本轮下注已结束！')
                await draw(bot=bot,ctx=ctx)# <- next turn
                return
        else:
            break
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    if pool[currentP] < max(pool):
        msg += '\n✦ 输入「跟」来跟注，自动加注到当前赌注。'
    if pool[currentP] >= max(pool):
        msg += '\n✦ 输入「过」放弃加注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await bot.send(ctx, msg)

@sv.on_command('跟', aliases=('follow', ), only_to_me=False)
async def follow(session):
    global state
    global players
    global pool
    global prize
    global cards
    global currentP
    bot = session.bot
    ctx = session.ctx
    if 'turn' not in state:
        return
    uid = ctx['user_id']
    if uid != players[currentP]:
        return
    bet = max(pool) - pool[currentP]
    iv._increase_impression_value(session.ctx['group_id'],uid, -bet)
    modifyRecord(uid)
    pool[currentP] += bet
    prize += bet
    if nextP():
        await bot.send(ctx, f'本轮下注已结束！')
        await draw(bot=bot,ctx=ctx)# <- next turn
        return
    time.sleep(1)
    while True:
        if pool[currentP]>=_maxBet:
            if nextP():
                await bot.send(ctx, f'本轮下注已结束！')
                await draw(session=session)# <- next turn
                return
        else:
            break
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    if pool[currentP] < max(pool):
        msg += '\n✦ 输入「跟」来跟注，自动加注到当前赌注。'
    if pool[currentP] >= max(pool):
        msg += '\n✦ 输入「过」放弃加注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await bot.send(ctx, msg)

@sv.on_command('梭哈', aliases=('showhand', 'show hand', 'all in', 'allin', ), only_to_me=False)
async def showhand(session):
    global state
    global players
    global pool
    global prize
    global cards
    global currentP
    bot = session.bot
    ctx = session.ctx
    if 'turn' not in state:
        return
    uid = ctx['user_id']
    if uid != players[currentP]:
        return
    bet = _maxBet - pool[currentP]
    iv._increase_impression_value(session.ctx['group_id'],uid, -bet)
    modifyRecord(uid)
    pool[currentP] += bet
    prize += bet
    #await bot.send(ctx, f'{ms.at(players[currentP])}all in了！')
    if nextP():
        await bot.send(ctx, f'本轮下注已结束！')
        await draw(bot=bot,ctx=ctx)# <- next turn
        return
    time.sleep(1)
    while True:
        if pool[currentP]>=_maxBet:
            if nextP():
                await bot.send(ctx, f'本轮下注已结束！')
                await draw(session=session)# <- next turn
                return
        else:
            break
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    if pool[currentP] < max(pool):
        msg += '\n✦ 输入「跟」来跟注，自动加注到当前赌注。'
    if pool[currentP] >= max(pool):
        msg += '\n✦ 输入「过」放弃加注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await bot.send(ctx, msg)

def nextP(): # return True when turn ended
    global state
    global players
    global currentP
    global buttonP
    global lastP
    global pool
    if currentP==lastP and len(set(pool))==1:
        return True
    currentP += 1
    if currentP>=len(players):
        currentP = 0
    return False

async def draw(session='',bot='',ctx=''):
    # draw 1~3 new cards to the pool
    global state
    global players
    global pool
    global prize
    global cards
    global currentP
    if bot=='':
        bot = session.bot
        ctx = session.ctx
    if len(cards['pool'])>=5:
        await bot.send(ctx, '决胜...！')
        await checkwin(bot, ctx)# ← game end, decide winner
        return
    await bot.send(ctx, f'第{state[4]}回合')
    time.sleep(1)
    await bot.send(ctx, '镜华准备中...')
    time.sleep(1)
    random.shuffle(cards['deck'])
    if state=='turn1':
        cards['pool'] = [cards['deck'].pop(),cards['deck'].pop(),cards['deck'].pop()]
    else:
        cards['pool'].append(cards['deck'].pop())
    print(cards['pool'])
    msg = '公共牌：\n'
    tmp = []
    for ii in range(0,len(cards['pool'])):
        tmp.append(cards['pool'][ii])
        #msg += str(R.img('poker/', cards['pool'][ii] + '.jpg').cqcode)
    tmp = concat_poker(tmp)
    msg += str(tmp)
    await bot.send(ctx, msg)
    # old draw() called here
    newturn()
    time.sleep(1)
    while True:
        if pool[currentP]>=_maxBet:
            if nextP():
                await bot.send(ctx, f'本轮下注已结束！')
                await draw(bot=bot,ctx=ctx)# <- next turn
                return
        else:
            break
    msg = f'现在轮到{ms.at(players[currentP])}，您可以：'
    msg += '\n✦ 输入「下注」1~5的一个数字来加注，加注后数额不能小于之前下注的人。'
    msg += '\n✦ 输入「过」放弃加注。'
    msg += '\n✦ 输入「gg」来放弃游戏，你将不能拿回你已下的注。'
    msg += f'\n当前奖池额度：{prize}好感'
    msg += f'\n当前赌注：{max(pool)}好感'
    msg += f'\n您已下注：{pool[currentP]}好感'
    await bot.send(ctx, msg)

async def checkwin(bot, ctx):
    global state
    global players
    global cards
    global currentP
    global buttonP
    global ori_players
    global ori_buttonP
    global prize
    await bot.send(ctx, '统计结果中...')
    bestScore = 0
    bestH = ''
    bestP = 0
    bestHigh = ''
    bestComebo = ''
    best = []
    for ii in range(0,len(players)):
        hand = cards[players[ii]] + cards['pool']
        score, hand, highcard, comboName = combo(hand)
        if score>bestScore:
            bestScore = score
            bestH = hand
            bestP = ii
            bestHigh = highcard
            bestComebo = comboName
            best = []
            best.append([bestScore, bestH, bestP, bestHigh, bestComebo])
        elif score==bestScore:
            if score<4000: # looking at highcard to decide
                if poker_rank.ranker(highcard)>poker_rank.ranker(bestHigh):
                    bestHigh = highcard
                    best = []
                    best.append([bestScore, bestH, bestP, bestHigh, bestComebo])
                elif poker_rank.ranker(highcard)==poker_rank.ranker(bestHigh):
                    bestScore = score
                    bestH = hand
                    bestP = ii
                    bestHigh = highcard
                    bestComebo = comboName
                    best.append([bestScore, bestH, bestP, bestHigh, bestComebo])
            else: # if score>=4000, no need to look at highcard
                bestScore = score
                bestH = hand
                bestP = ii
                bestHigh = highcard
                bestComebo = comboName
                best.append([bestScore, bestH, bestP, bestHigh, bestComebo])
    print(best)
    if len(best)>1:
        await bot.send(ctx, '平局！')
    for ii in range(0,len(best)): # handling winner
        await win(bot=bot, ctx=ctx, uid=players[best[ii][2]], num_winner=len(best))
        modifyRecord(uid=players[best[ii][2]], winT=1, winpoint=round((prize-pool[best[ii][2]])/len(best)), besthand=best[ii][1])
        msg = '获胜COMBO：' + best[ii][4] + '！\n'
        tmp = []
        for jj in range(0,len(best[ii][1])):
            tmp.append(best[ii][1][jj])
            #msg += str(R.img('poker/', best[ii][1][jj] + '.jpg').cqcode)
        tmp = concat_poker(tmp)
        msg += str(tmp)
        if best[ii][0]<4000:
            msg += f'\n高牌：{_cardDict[best[ii][3]]}'
        await bot.send(ctx, msg)
    for ii in range(0,len(players)): # handling loser
        flagLoser = True
        for jj in range(0,len(best)):
            if ii==best[jj][2]:
                flagLoser = False
                break
        if flagLoser:
            modifyRecord(uid=players[ii], loseT=1, losepoint=pool[ii])
    time.sleep(1)
    players = copy.copy(ori_players)
    buttonP = ori_buttonP
    if len(players)==1:
        await bot.send(ctx, '由于只剩下一人，游戏即将关闭！')
        time.sleep(1)
        await endgame(bot=bot,ctx=ctx)
        return
    buttonP += 1
    buttonP = 0 if buttonP>=len(players) else buttonP
    ori_buttonP = buttonP
    await bot.send(ctx, f'{ms.at(players[buttonP])}将要坐庄！输入「go」继续游戏，或输入「gg」结束游戏。')
    state = 'nextgame'
    
def combo(card): # return (score, cards, highcard, comboName)
    maxScore = 0
    combo = []
    for case in list(combinations(card,5)):
        tmp_case = poker_rank.help(' '.join(case))
        score = tmp_case[7]
        if score>maxScore:
            tmp = tmp_case
            maxScore = score
    if maxScore<4000:
        res = []
    else:
        res = copy.copy(card) # res = card if it's not pair
    if maxScore>=9000:
        # 1.royal flush
        combo = tmp[1][1]
        comboName = '皇家同花顺'
    elif maxScore>=8000:
        # 2.straight flush
        combo = tmp[2][1]
        comboName = '同花顺'
    elif maxScore>=7000:
        # 3.four of a kind
        pair = list(tmp[5][1].keys())
        for c in tmp[0]:
            for p in pair:
                if p in c:
                    combo.append(c)
        comboName = '四条'
    elif maxScore>=6000:
        # 4.full house
        pair = list(tmp[5][1].keys())
        for c in tmp[0]:
            for p in pair:
                if p in c:
                    combo.append(c)
        comboName = '葫芦'
    elif maxScore>=5000:
        # 5.flush
        combo = tmp[3][1]
        comboName = '同花'
    elif maxScore>=4000:
        # 6.straight
        combo = tmp[4][1]
        comboName = '顺子'
    elif maxScore>=3000:
        # 7.three of a kind
        pair = list(tmp[5][1].keys())
        for c in card:
            flagRes = False
            for p in pair:
                if p in c:
                    combo.append(c)
                    flagRes = True
            if not flagRes:
                res.append(c)
        comboName = '三条'
    elif maxScore>=2000:
        # 8.two pair
        pair = list(tmp[5][1].keys())
        for c in card:
            flagRes = False
            for p in pair:
                if p in c:
                    combo.append(c)
                    flagRes = True
            if not flagRes:
                res.append(c)
        comboName = '两对'
    elif maxScore>=1000:
        # 9.one pair
        pair = list(tmp[5][1].keys())
        for c in card:
            flagRes = False
            for p in pair:
                if p in c:
                    combo.append(c)
                    flagRes = True
            if not flagRes:
                res.append(c)
        comboName = '一对'
    print(res)
    # 10.high card
    if maxScore<1000:
        res = copy.copy(card)
    tmp = poker_rank.help(' '.join(res))
    t1 = tmp[6]//10
    card_num = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
    t1 = card_num[t1-2]
    highcard = ''
    for c in res:
        if t1 in c:
            highcard = c
            break
    if maxScore<1000:
        combo = [highcard]
        comboName = '高牌'
    return maxScore, combo, highcard, comboName

def findhigh(card):
    tmp = poker_rank.help(' '.join(card))
    t1 = tmp[6]//10
    card_num = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
    t1 = card_num[t1-2]
    highcard = ''
    for c in card:
        if t1 in c:
            highcard = c
            break
    score = tmp[7]
    return highcard, score

async def win(session='', bot='', ctx='', uid='', num_winner=1):
    global prize
    iv._increase_impression_value(ctx['group_id'], uid, round(prize/num_winner))
    time.sleep(1)
    if bot=='':
        bot = session.bot
        ctx = session.ctx
    await bot.send(ctx, f'恭喜{ms.at(uid)}获得这局的胜利！获得了奖池总计{round(prize/num_winner)}好感！')

async def reset(nextgame=False,session=''):
    global state
    global players
    global pool
    global prize
    global cards
    global currentP
    global lastP
    #global buttonP # will plus 1 when win
    cards = dict()
    cards['deck'] = copy.copy(cardList)
    cards['pool'] = []
    prize = 0
    if nextgame:
        state = 'enlist'
        await go(session)
    else:
        state = ''
        players = []
        pool = []

def newturn():
    global state
    global players
    global currentP
    global buttonP
    global lastP
    lastP = buttonP
    currentP = buttonP + 1
    currentP = 0 if currentP>=len(players) else currentP
    state = 'turn' + str(int(state[4])+1)

@sv.on_command('德州规则', only_to_me=False)
async def explain(session):
    await session.bot.send(session.ctx, f"{R.img('poker/', '德州规则.jpg').cqcode}")
    time.sleep(1)

@sv.on_command('结束游戏', aliases=('游戏结束', ), only_to_me=False)
async def endgame(session='',bot='',ctx=''):
    await reset()
    if bot=='':
        bot = session.bot
        ctx = session.ctx
    await bot.send(ctx, '已结束游戏！')

@on_command('我没牌', aliases=('没牌', '发牌', ))
async def nocard_private(session):
    global players
    global cards
    uid = session.ctx['user_id']
    if uid not in players:
        return
    #print(f'{ms.at(uid)}{_cardDict[cards[uid][0]]}{_cardDict[cards[uid][1]]}')
    concat = concat_poker(cards[uid])
    await session.send(user_id=uid, message=f'{concat}')
    await session.send(f'您的手牌：{_cardDict[cards[uid][0]]}{_cardDict[cards[uid][1]]}')

@sv.on_command('公共牌', aliases=('没有公共牌', ), only_to_me=False)
async def nocard_public(session):
    global players
    global cards
    uid = session.ctx['user_id']
    if uid not in players:
        return
    msg = '公共牌：'
    for ii in range(0,len(cards['pool'])):
        msg += f"{_cardDict[cards['pool'][ii]]}"
    await session.send(msg)

def concat_poker(card):
    des = Image.new('RGBA', (max(len(card)%3, len(card)//3*3)*105, (len(card)//4+1)*150), (255, 255, 255, 255))
    for ii in range(0, len(card)):
        cardname = card[ii]
        #cardpath = R.img('poker/', cardname + '.jpg').path
        src = R.img('poker/', cardname + '.jpg').open().convert('RGBA').resize((105, 150), Image.LANCZOS)
        des.paste(src, (ii%3 * 105, ii//3 * 150))
    #des = util.concat_pic(cardPIL)
    des = util.pic2b64(des)
    des = MessageSegment.image(des)
    return des

POKER_PATH = os.path.expanduser('~/.hoshino/poker_record.json')
#def modifyRecord(uid, playT=0, winT=0, winpoint=0, loseT=0, losepoint=0, borrow=0, besthand=[]):
def modifyRecord(uid, playT=0, winT=0, winpoint=0, loseT=0, losepoint=0, besthand=[]):
    # besthand = ['AS', '2C', '3H', '4D', '5S']
    uid = str(uid)
    if os.path.exists(POKER_PATH):
        with open(POKER_PATH, 'r') as f:
            record = json.load(f)
    else: 
        record = dict()
    if uid not in record:
        record[uid] = {
            'playT': playT,
            'winT': winT,
            'winpoint': winpoint,
            'loseT': loseT,
            'losepoint': losepoint,
            #'borrow': borrow,
            'besthand': besthand
        }
    else:
        hand1 = besthand
        hand2 = record[uid]['besthand']
        if hand1==[]:
            besthand = hand2
        elif hand2==[]:
            besthand = hand1
        else:
            tmp1 = combo(hand1) # tmp = (score, hand, highcard, comboName)
            tmp2 = combo(hand2)
            if tmp1[0]>=tmp2[0]:
                besthand = hand1
            else:
                besthand = hand2
        record[uid] = {
            'playT': record[uid]['playT'] + playT,
            'winT': record[uid]['winT'] + winT,
            'winpoint': record[uid]['winpoint'] + winpoint,
            'loseT': record[uid]['loseT'] + loseT,
            'losepoint': record[uid]['losepoint'] + losepoint,
            #'borrow': record[uid]['borrow'] + borrow,
            'besthand': besthand
        }
    with open(POKER_PATH, 'w') as f:
        json.dump(record, f)

@sv.on_command('德州战绩', aliases=('战绩', '查看战绩', ), only_to_me=False)
async def printRecord(session):
    # besthand = ['AS', '2C', '3H', '4D', '5S']
    uid = str(session.ctx['user_id'])
    if os.path.exists(POKER_PATH):
        with open(POKER_PATH, 'r') as f:
            record = json.load(f)
    else: 
        record = dict()
    if uid not in record:
        await session.send(f'您还未玩过德州呢！')
        return
    else:
        msg = f"{ms.at(uid)}\n"
        msg += f"游玩局数：{record[uid]['playT']}\n"
        msg += f"胜局：{record[uid]['winT']} 赢得：{record[uid]['winpoint']}好感\n"
        msg += f"败局：{record[uid]['loseT']} 输掉：{record[uid]['losepoint']}好感\n"
        #msg += f"向爱梅斯借过：{record[uid]['borrow']}好感\n"
        if record[uid]['besthand']!=[]:
            tmp = []
            for ii in range(0,len(record[uid]['besthand'])):
                tmp.append(record[uid]['besthand'][ii])
            tmp = concat_poker(tmp)
            msg += f"最好牌型：\n{tmp}"
        await session.send(msg)
