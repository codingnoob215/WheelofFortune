#Taken from https://www.playstationtrophies.org/forum/topic/163466-wheel-of-fortune-answer-list/
# puzzles.py

import random

puzzles = {
    "Phrase": [
        "A GOOD FIT",
        "BACK TO BASICS",
        "DRAWING A BLANK",
        "YOUR HEART IS IN THE RIGHT PLACE",
        "IT'S A DIRTY SHAME",
    ],
    "Place": [
        "ALOHA STATE",
        "BUSTLING CITY",
        "PRIVATE GYM",
        "THE CAPITAL OF ITALY",
        "WHITE SAND BEACH",
    ],
    "Thing": [
        "A FRIENDLY REMINDER",
        "ARCHERY",
        "CLASSICAL MUSIC",
        "ENGRAVED INVITATIONS",
        "SPARKLING SKYLINE",
    ],
    "Proper Name": [
        "BEN AFFLECK",
        "MICHELLE OBAMA",
        "THE ROLLING STONES",
        "WASHINGTON NATIONALS",
        "BUZZ ALDRIN",
    ],
    "What Are You Doing?": [
        "COOKING FRESHLY CAUGHT FISH",
        "SHOPPING IN SOHO",
        "RELAXING POOLSIDE",
        "TRAVELING IN A SNOWMOBILE",
        "SEEING A MOVIE",
    ]
}

def get_random_puzzle():
    category = random.choice(list(puzzles.keys()))
    phrase = random.choice(puzzles[category])
    return category, phrase
