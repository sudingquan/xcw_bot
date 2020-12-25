#
# Texas Holdem Poker Ranking System
#    by Joseph A Young
#
# rules taken from World Series of Poker: http://www.wsop.com/poker-games/texas-holdem/rules/
#
# winner is the one with the best five card hand made out of the possible 5, 6, or 7 cards:
#    set ranking:    Royal Flush, Straight Flush, Four of a Kind, Full House, Flush, Straight,
#                    Three of a Kind, Two Pairs, One Pair, High Card
#    number ranking: A, K, Q, J, 10, 9, 8, 7, 6, 5 ,4 ,3, 2
#    suit ranking:   S, H, D, C
#
# statistics:
#    max score: 9144
#    average score after 1,000,000 trials was 1626.356483
#    test results show a normal distribution with a high center peak
#    over 133,784,560 hands for 7 hand poker (52 C 7)
#
# Notes:
# too many loops and repeated calculations
#

import random
import math

import matplotlib.pyplot as plt



def is_pairs(hand):
    numbers = [r for r, s in hand]
    counter = {i: numbers.count(i) for i in numbers if numbers.count(i) > 1}
    pairs = [i for i in hand if i[0] in counter.keys()]
    score = 0

    if len(counter) > 0:
        score = is_high_card(pairs)[2] + is_high_suit(pairs)[2]

    # 4 of a kind: 4 cards of the same number
    if 4 in counter.values():
        return True, counter, score + 7000

    # Full House: 3 of a Kind and 2 of a Kind
    elif 3 in counter.values() and 2 in counter.values():
        return True, counter, score + 6000

    # 3 of a Kind: 3 cards of the same number
    elif 3 in counter.values():
        return True, counter, score + 3000

    # 2 Pairs: 2 Pairs of 2 of a kind (One Pair): 2 cards of the same number
    elif list(counter.values()).count(2) == 2:
        return True, counter, score + 2000

    # 2 of a Kind (One Pair): 2 cards of the same number
    elif 2 in counter.values():
        return True, counter, score + 1000

    return False, counter, score


def is_high_card(current_hand):
    # number ranking (Most to Least): A, K, Q, J, 10, 9, 8, 7, 6, 5 ,4 ,3, 2
    number_list = [r for r, s in current_hand]
    card_values = dict((r, i) for i, r in enumerate('..23456789TJQKA'))
    num_scores = sorted(set([card_values[i]*10 for i in number_list]))
    return True, number_list, max(num_scores)


def is_high_suit(current_hand):
    # suit ranking (Most to Least): S, H, D, C
    suit_list = [s for r, s in current_hand]
    suit_values = dict((r, i) for i, r in enumerate('.CDHS'))
    suit_scores = sorted(set([suit_values[i] for i in suit_list]))
    return True, suit_list, max(suit_scores)


def is_flush(hand):
    # find all suits in hand and count to see if there are 5 or greater
    # find all suit values in hand and return a list of all cards containing that suit (5, 6, or 7 possible cards)
    suits = [s for r, s in hand]

    for i in set(suits):
        if suits.count(i) >= 5:
            flush_hand_cards = sorted([j for j in hand if i in j])
            score = is_high_card(flush_hand_cards)[2] + is_high_suit(flush_hand_cards)[2]
            return True, flush_hand_cards, score + 5000
    return False, [], 0


def is_straight(hand):
    numbers = [r for r, s in hand]
    card_values = dict((r, i) for i, r in enumerate('..23456789TJQKA'))
    num_list = sorted(set([card_values[i] for i in numbers]))
    straight_hand_cards =[]

    # can only be len(num_list) from 7 to 5 - straight has to be 5 cards in a row
    # will account for multiple straights (2,3,4,5,6,7,8), then the whole list will be returned
    # will return duplicate card values for the straight (to help match if straight/flush)
    # counts Ace as 14 so does not count A, 2, 3, 4, 5 as a straight (using Ace Low Rule)
    if len(num_list) >= 5:
        for i in range(len(num_list) - 4):
            temp = num_list[i:i+5]
            if (temp[4] - temp[0]) == 4:
                # have to account for multiple straights in a given set of 7, unable to return value at this point
                straight_hand_cards += [j for j in hand if card_values[j[0]] in temp]

    straight_hand_cards = sorted(set(straight_hand_cards))

    if len(straight_hand_cards) >= 5:
        score = is_high_card(straight_hand_cards)[2] + is_high_suit(straight_hand_cards)[2]
        return True, straight_hand_cards, score + 4000
    return False, [], 0


def is_straight_flush(hand):
    flush = is_flush(hand)
    straight = is_straight(hand)
    straight_flush_cards = [j for j in flush[1] if j in straight[1]]

    if (flush[0] and straight[0]) and (len(straight_flush_cards) >=5):
        score = is_high_card(straight_flush_cards)[2] + is_high_suit(straight_flush_cards)[2]
        return (True, straight_flush_cards, score + 8000), flush, straight
    return (False, [], 0), flush, straight


def is_royal_flush(hand):
    straight_flush, flush, straight = is_straight_flush(hand)
    royals_list = ['A', 'K', 'Q', 'J', 'T']
    royals_check = [i[0] for i in straight_flush[1]]
    royals_test = all(royals_check.count(i) == 1 for i in royals_list)

    if royals_test and len(royals_check) >= 5:
        score = is_high_card(straight_flush[1])[2] + is_high_suit(straight_flush[1])[2]
        return (True, straight_flush[1], score + 9000), straight_flush, flush, straight
    return (False, [], 0), straight_flush, flush, straight


def ranker(hand):
    hand = hand.split()

    royal_flush, straight_flush, flush, straight = is_royal_flush(hand)
    pairs = is_pairs(hand)
    high_card_suit = is_high_card(hand)[2] + is_high_suit(hand)[2]
    score = max(royal_flush[2], straight_flush[2], flush[2], straight[2], pairs[2], high_card_suit)

    # print("Current hand:  ", hand)
    # print("Royal Flush:   ", royal_flush)
    # print("Straight Flush:", straight_flush)
    # print("Flush:         ", flush)
    # print("Straight:      ", straight)
    # print("Pairs:         ", pairs)
    # print("High Card/Suit:", high_card_suit)
    # print("Score:         ", score)

    return score

def help(hand):
    hand = hand.split()

    royal_flush, straight_flush, flush, straight = is_royal_flush(hand)
    pairs = is_pairs(hand)
    high_card_suit = is_high_card(hand)[2] + is_high_suit(hand)[2]
    score = max(royal_flush[2], straight_flush[2], flush[2], straight[2], pairs[2], high_card_suit)

    return hand, royal_flush, straight_flush, flush, straight, pairs, high_card_suit, score

# enter card numbers into hand
# hand = "AH KH QH JH TH 9H 8H"
# print(ranker(hand))

# def main():
#     hand = ""
#     card = ""
#     n = 7
#
#     # Ace, Jack, Queen, King
#     card_num = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
#     # Hearts, Clubs, Spades, Diamonds
#     card_suit = ['H', 'C', 'S', 'D']
#
#     # generate n number of random card
#     while len(hand) != 3*(n):
#         card += random.choice(card_num)
#         card += random.choice(card_suit)
#         # leave a space for parsing
#         card += ' '
#
#         # make sure there are no duplicates
#         if card not in hand:
#             hand += card
#         card = ""
#
#     return ranker(hand)
#
# main()
