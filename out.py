import csv

# List to store the tuples
card_data = []

# Open the CSV file and read the data
with open('hand_rankings.csv', 'r') as file:
    reader = csv.reader(file)
    next(reader)  # Skip the header
    for row in reader:
        # Convert each row into a tuple and append it to the list
        cards = tuple(row[:3])  # The first three columns are cards
        value = float(row[3])   # The fourth column is the float value
        card_data.append((cards, value))

# Write the list of tuples to a text file
with open('output.txt', 'w') as file:
    file.write(str(card_data))

print("Data written to 'output.txt'.")
