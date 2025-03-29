from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState, STARTING_STACK
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random

class PokerBotMemory:
    def __init__(self):
        self.memory = []  # Stores past rounds
    
    def categorize_board(self, board):
        """Categorize the board based on structure rather than exact cards."""
        suits = [card[1] for card in board]
        ranks = [card[0] for card in board]
        is_triple_suited = len(set(suits)) == 1
        is_paired = len(ranks) != len(set(ranks))
        face_card_count = sum(rank in ['T', 'J', 'Q', 'K', 'A'] for rank in ranks)
        low_card_count = sum(rank in ['2', '3', '4', '5', '6', '7'] for rank in ranks)
        has_multiple_face_cards = face_card_count >= 2
        has_multiple_low_cards = low_card_count >= 2
        
        return {
            "triple_suited": is_triple_suited,
            "paired": is_paired,
            "multiple_face_cards": has_multiple_face_cards,
            "multiple_low_cards": has_multiple_low_cards
        }
    
    def find_similar_round(self, categorized_board, opponent_actions, street):
        """Find past rounds with a similar board structure and opponent actions up to the given street."""
        street_names = {0: "preflop", 3: "flop", 5: "river"}
        current_street_name = street_names.get(street)
        
        if not current_street_name:
            return None
        
        for past_round in self.memory:
            if current_street_name in past_round["opponent_actions"]:
                # Compare board structure
                if past_round["board_structure"] == categorized_board:
                    # Compare opponent actions for current street
                    if past_round["opponent_actions"][current_street_name] == opponent_actions:
                        return past_round
        return None
    
    def record_hand(self, round_number, opponent_actions, board, showdown_hand, winner):
        """Save the round data for future analysis."""
        hand_data = {
            "round_number": round_number,
            "opponent_actions": opponent_actions,
            "board_structure": self.categorize_board(board),
            "showdown_hand": showdown_hand,
            "winner": winner
        }
        self.memory.append(hand_data)

class Player(Bot):
    def __init__(self):
        self.memory = PokerBotMemory()
    
    def handle_new_round(self, game_state, round_state, active):
        pass  # No special setup needed at round start

    def handle_round_over(self, game_state, terminal_state, active):
        """Save round data after showdown."""
        previous_state = terminal_state.previous_state
        opponent_actions = {
            "preflop": previous_state.pips[1-active],
            "flop": previous_state.pips[1-active],
            "river": previous_state.pips[1-active]
        }
        winner = 1 if terminal_state.deltas[1] > 0 else 0  # 1 if opponent won, 0 if we won
        self.memory.record_hand(
            game_state.round_num,
            opponent_actions,
            previous_state.deck[:5],
            previous_state.hands[1-active] if previous_state.hands[1-active] else None,
            winner
        )

    def get_action(self, game_state, round_state, active):
        """Decide action based on past rounds."""
        legal_actions = round_state.legal_actions()
        street = round_state.street
        my_cards = round_state.hands[active]
        board_cards = round_state.deck[:street]
        opponent_pip = round_state.pips[1-active]
        my_pip = round_state.pips[active]
        
        # Categorize board structure
        categorized_board = self.memory.categorize_board(board_cards)
        
        # Check past rounds for patterns up to the current street
        similar_round = self.memory.find_similar_round(categorized_board, opponent_pip, street)
        if similar_round:
            # Predict future actions
            expected_river_action = similar_round["opponent_actions"].get("river", None)
            if expected_river_action and expected_river_action > 100 and similar_round["winner"] == 1:
                return FoldAction()  # Fold if they previously bet big on the river and won
            return CallAction()  # Call if they bluffed often and lost
        


        # Default random strategy
        if RaiseAction in legal_actions:
           min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
           min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
           max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
        if RaiseAction in legal_actions:
            return RaiseAction(max(min_raise, 50))
        if CheckAction in legal_actions:
            return CheckAction()
        return CallAction()

if __name__ == '__main__':
    run_bot(Player(), parse_args())
