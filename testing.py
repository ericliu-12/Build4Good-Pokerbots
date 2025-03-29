import eval7
import random
from collections import defaultdict
import csv

# Number of simulations
NUM_SIMULATIONS = 10000000  # Start with 100k, can increase for better accuracy

# Dictionaries to track win/loss counts
hand_win_counts = defaultdict(int)
hand_play_counts = defaultdict(int)

# Run Monte Carlo simulations
for _ in range(NUM_SIMULATIONS):
    deck = eval7.Deck()
    deck.shuffle()

    # Deal two random 3-card hands
    hand1_cards = deck.deal(3)
    hand2_cards = deck.deal(3)

    # Convert to hashable representation for dictionary keys
    hand1_key = tuple(sorted([str(card) for card in hand1_cards]))
    hand2_key = tuple(sorted([str(card) for card in hand2_cards]))

    # Draw board (2-card flop, 2-card turn, no river)
    board_cards = deck.deal(4)

    # Evaluate hands (In eval7, LOWER score is better)
    score1 = eval7.evaluate(hand1_cards + board_cards)
    score2 = eval7.evaluate(hand2_cards + board_cards)

    # Track hands played
    hand_play_counts[hand1_key] += 1
    hand_play_counts[hand2_key] += 1

    # Track wins (note the reversed comparison from your original code)
    if score1 < score2:  # Lower score is better in eval7
        hand_win_counts[hand1_key] += 1
    elif score2 < score1:
        hand_win_counts[hand2_key] += 1
    else:  # Handle ties
        hand_win_counts[hand1_key] += 0.5
        hand_win_counts[hand2_key] += 0.5

# Compute win rates for each hand
hand_win_rates = {hand: hand_win_counts[hand] / hand_play_counts[hand]
                  for hand in hand_play_counts if hand_play_counts[hand] > 10}  # Only include hands with sufficient samples

# Normalize win rates to a 0-1 scale, reversing the scale
hand_power_scale = {}
if hand_win_rates:  # Check if dictionary is not empty
    max_win_rate = max(hand_win_rates.values())
    min_win_rate = min(hand_win_rates.values())
    hand_power_scale = {hand: 1 - (win_rate - min_win_rate) / (max_win_rate - min_win_rate)
                        for hand, win_rate in hand_win_rates.items()}

    # Prepare data for CSV
    csv_data = []
    for hand_tuple, power in sorted(hand_power_scale.items(), key=lambda x: -x[1]):
        card1, card2, card3 = hand_tuple
        csv_data.append([card1, card2, card3, f"{power:.9f}"])

    # Write to CSV
    csv_file = "hand_rankings.csv"
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Card 1", "Card 2", "Card 3", "Score"])  # Write header row
        writer.writerows(csv_data)

    print(f"\nHand rankings saved to {csv_file}")
else:
    print("Not enough data collected to determine hand rankings.")