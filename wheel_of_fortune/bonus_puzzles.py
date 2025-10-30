#Taken from https://www.playstationtrophies.org/forum/topic/163466-wheel-of-fortune-answer-list/

import random
from puzzles import PUZZLES 

BONUS_PUZZLES = {
    "Things": [
        "A SHINY NEW CAR",
        "GOLDEN OPPORTUNITY",
        "BOX OF CHOCOLATES",
        "MOUNTAIN OF PILLOWS",
        "SET OF GOLF CLUBS",
    ],
    "Places": [
        "TROPICAL ISLAND",
        "CROWDED MARKETPLACE",
        "WINTER CABIN",
        "BUSTLING CITY",
        "ANCIENT TEMPLE",
    ],
    "People": [
        "TEACHER OF THE YEAR",
        "FAMOUS CHEF",
        "MOVIE STAR",
        "CHESS GRANDMASTER",
        "OLYMPIC ATHLETE",
    ],
    "Events": [
        "MUSIC FESTIVAL",
        "SURPRISE PARTY",
        "WEDDING RECEPTION",
        "GRADUATION CEREMONY",
        "CHARITY AUCTION",
    ],
    "Phrases": [
        "BETTER LATE THAN NEVER",
        "TIME IS MONEY",
        "EASY COME EASY GO",
        "PRACTICE MAKES PERFECT",
        "WINNER TAKES ALL",
    ]
}

def get_bonus_puzzle(category=None):
    if category and category in BONUS_PUZZLES:
        puzzle = random.choice(BONUS_PUZZLES[category])
        return category, puzzle.upper()
    random_cat = random.choice(list(BONUS_PUZZLES.keys()))
    puzzle = random.choice(BONUS_PUZZLES[random_cat])
    return random_cat, puzzle.upper()