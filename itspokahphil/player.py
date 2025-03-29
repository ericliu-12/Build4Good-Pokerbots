from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import STARTING_STACK
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random
import numpy as np

RANKS = '23456789TJQKA'
SUITS = 'cdhs'
DECK = [r + s for r in RANKS for s in SUITS]

FIVE_CARD_COMBOS = [
    (0,1,2,3,4), (0,1,2,3,5), (0,1,2,3,6), (0,1,2,4,5), (0,1,2,4,6), (0,1,2,5,6),
    (0,1,3,4,5), (0,1,3,4,6), (0,1,3,5,6), (0,1,4,5,6), (0,2,3,4,5), (0,2,3,4,6),
    (0,2,3,5,6), (0,2,4,5,6), (0,3,4,5,6), (1,2,3,4,5), (1,2,3,4,6), (1,2,3,5,6),
    (1,2,4,5,6), (1,3,4,5,6), (2,3,4,5,6)
]

def parse_card(card):
    return (RANKS.index(card[0]), SUITS.index(card[1]))

def hand_rank(cards):
    ranks = np.array([c[0] for c in cards])
    suits = np.array([c[1] for c in cards])

    unique_ranks = np.unique(ranks)
    if 12 in unique_ranks:
        unique_ranks = np.append(unique_ranks, -1)

    unique_sorted = np.sort(unique_ranks)
    straights = []
    for i in range(len(unique_sorted) - 4):
        window = unique_sorted[i:i+5]
        if np.all(np.diff(window) == 1):
            straights.append(window[-1])

    is_straight = len(straights) > 0
    straight_high = max(straights) if is_straight else -1

    flush_suit = None
    for s in range(4):
        if np.sum(suits == s) >= 5:
            flush_suit = s
            break

    flush_cards = [c for c in cards if c[1] == flush_suit] if flush_suit is not None else []

    if len(flush_cards) >= 5:
        flush_ranks = np.array([c[0] for c in flush_cards])
        unique_flush = np.unique(flush_ranks)
        if 12 in unique_flush:
            unique_flush = np.append(unique_flush, -1)
        unique_sorted = np.sort(unique_flush)
        for i in range(len(unique_sorted) - 4):
            window = unique_sorted[i:i+5]
            if np.all(np.diff(window) == 1):
                return (8, [window[-1]])

    counts = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    count_list = sorted(counts.items(), key=lambda x: (-x[1], -x[0]))
    count_values = tuple([c[1] for c in count_list])
    ordered_ranks = []
    for r, c in count_list:
        ordered_ranks.extend([r] * c)

    if count_values[0] == 4:
        return (7, ordered_ranks)
    elif count_values[0] == 3 and count_values[1] >= 2:
        return (6, ordered_ranks)
    elif flush_suit is not None:
        flush_sorted = sorted([c[0] for c in flush_cards], reverse=True)[:5]
        return (5, flush_sorted)
    elif is_straight:
        return (4, [straight_high])
    elif count_values[0] == 3:
        return (3, ordered_ranks)
    elif count_values[0] == 2 and count_values[1] == 2:
        return (2, ordered_ranks)
    elif count_values[0] == 2:
        return (1, ordered_ranks)
    else:
        return (0, sorted(ranks, reverse=True))

def best_five(cards):
    best = (0, [])
    for idxs in FIVE_CARD_COMBOS:
        combo = [cards[i] for i in idxs]
        score = hand_rank(combo)
        if score > best:
            best = score
    return best

def estimate_strength(my_cards, board_cards, iterations=10):
    parsed_my = [parse_card(c) for c in my_cards]
    parsed_board = [parse_card(c) for c in board_cards]
    known = set(my_cards + board_cards)
    unknown = [c for c in DECK if c not in known]

    wins = 0
    for _ in range(iterations):
        sampled = np.random.choice(unknown, 5 - len(board_cards) + 3, replace=False)
        opp_cards = [parse_card(c) for c in sampled[:3]]
        rem_board = [parse_card(c) for c in sampled[3:]]
        full_board = parsed_board + rem_board

        my_best = best_five(parsed_my + full_board)
        opp_best = best_five(opp_cards + full_board)

        if my_best > opp_best:
            wins += 1
        elif my_best == opp_best:
            wins += 0.5

    return wins / iterations

def classify_hand(hand):
    ranks = sorted([parse_card(c)[0] for c in hand], reverse=True)
    if ranks[0] == ranks[1] == ranks[2]:
        return "trips"
    elif ranks[0] == ranks[1] or ranks[1] == ranks[2] or ranks[0] == ranks[2]:
        return "pair"
    elif all(r >= 10 for r in ranks):
        return "broadway"
    elif max(ranks) < 8:
        return "trash"
    else:
        return "neutral"

class Player(Bot):
    def __init__(self):
        self.opp_aggression = 0
        self.rounds_played = 0

    def handle_new_round(self, game_state, round_state, active):
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        prev = terminal_state.previous_state
        opp_pip = prev.pips[1 - active]
        if opp_pip > STARTING_STACK * 0.6:
            self.opp_aggression += 1
        self.rounds_played += 1

    def get_action(self, game_state, round_state, active):
        legal_actions = round_state.legal_actions()
        street = round_state.street
        my_cards = round_state.hands[active]
        board_cards = round_state.deck[:street]
        my_pip = round_state.pips[active]
        opp_pip = round_state.pips[1 - active]
        continue_cost = opp_pip - my_pip
        pot_total = sum(round_state.pips) + continue_cost
        my_stack = round_state.stacks[active]

        if RaiseAction in legal_actions:
            min_raise, max_raise = round_state.raise_bounds()
            min_cost = min_raise - my_pip
            max_cost = max_raise - my_pip

        # Preflop logic
        if street == 0:
            category = classify_hand(my_cards)
            if category in ["trips", "broadway"]:
                if RaiseAction in legal_actions:
                    return RaiseAction(max_raise)
            elif category == "pair":
                if RaiseAction in legal_actions:
                    return RaiseAction(min_raise)
            elif category == "trash":
                if CheckAction in legal_actions:
                    return CheckAction()
                return FoldAction()
            else:
                if CallAction in legal_actions and continue_cost <= STARTING_STACK * 0.1:
                    return CallAction()
                elif CheckAction in legal_actions:
                    return CheckAction()
                return FoldAction()

        # Postflop logic
        iters = 3 if street == 0 else 5 if street == 3 else 10
        strength = estimate_strength(my_cards, board_cards, iterations=iters)
        pot_odds = continue_cost / (pot_total + 1e-9)
        bluff_chance = 0.15 if self.rounds_played > 5 and self.opp_aggression / self.rounds_played > 0.5 else 0.05

        if RaiseAction in legal_actions and strength > 0.85:
            return RaiseAction(max_raise)
        if RaiseAction in legal_actions and strength < 0.3 and random.random() < bluff_chance:
            return RaiseAction(min_raise)

        if strength >= pot_odds:
            if CallAction in legal_actions and continue_cost > 0:
                return CallAction()
            elif CheckAction in legal_actions:
                return CheckAction()

        if CheckAction in legal_actions:
            return CheckAction()
        elif FoldAction in legal_actions:
            return FoldAction()
        elif CallAction in legal_actions:
            return CallAction()
        return FoldAction()

if __name__ == '__main__':
    run_bot(Player(), parse_args())