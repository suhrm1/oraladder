import os

config = dict(
    replay_folder="ratl/replays",
    config_folder="ratl",
)

for key, default_value in config.items():
    config[key] = os.getenv(key, default=default_value)

config["league_title_short"] = "RATL"
config["season"] = 3

config["teams"] = {
    "Team Blorb": [6430, 6748],  # Blackened, Orb
    "Team Yorrick Hunt": [3952, 8769],  # Anjew, Dying Fetus
    "Rise of the Minions": [18864, 18359],  # Fiwo, goldie
    "Slot Admin": [18246, 17239],  # Creo, Fazzar
    "Team Mensa": [16222, 15469],  # despro, Happy
    "Unstoppable Upps & Unano United, UUUU": [6793, 7304],  # Unano, Upps
    "MXNX ": [12760, 10755],  # Master, NewbieX
    "Black Tie Armada": [5292, 15899],  # Mo, Tux
    "Administroyers": [16066, 7387],  # Milkman, TripT
}

config["subs"] = {}

config["player_names"] = {
    6430: "Blackened",
    6748: "Orb",
    3952: "Anjew",
    8769: "Dying Fetus",
    18864: "Fiwo",
    18359: "Goldie",
    18246: "Creo",
    17239: "Fazzar",
    16222: "Despro",
    15469: "Happy",
    7304: "Upps",
    6793: "Unano",
    12760: "MASTER",
    10755: "NewbieX",
    15899: "Tux",
    5292: "Mo",
    16066: "milkman",
    7387: "TripT",
}

config["schedule"] = {
    "Week 1": [
        ("2023-12-11", "Unstoppable Upps & Unano United, UUUU", "Rise of the Minions", ""),
        ("2023-12-11", "Team Mensa", "Black Tie Armada", ""),
        ("2023-12-11", "MXNX", "Team Yorrick Hunt", ""),
        ("2023-12-11", "Slot Admin", "Black Tie Armada", ""),
        ("2023-12-11", "Team Blorb", "Administroyers", ""),
    ],
    "Week 2": [
        ("2023-12-18", "Slot Admin", "Administroyers", ""),
        ("2023-12-18", "Unstoppable Upps & Unano United, UUUU", "Team Mensa", ""),
        ("2023-12-18", "Slot Admin", "Team Yorrick Hunt", ""),
        ("2023-12-18", "Rise of the Minions", "MXNX", ""),
        ("2023-12-18", "Team Blorb", "Black Tie Armada", ""),
    ],
    "Week 3": [
        ("2024-01-01", "Black Tie Armada", "MXNX", ""),
        ("2024-01-01", "Slot Admin", "Team Blorb", ""),
        ("2024-01-01", "Team Yorrick Hunt", "Unstoppable Upps & Unano United, UUUU", ""),
        ("2024-01-01", "Team Mensa", "Administroyers", ""),
        ("2024-01-01", "Rise of the Minions", "Team Mensa", ""),
    ],
    "Week 4": [
        ("2024-01-08", "Rise of the Minions", "Administroyers", ""),
        ("2024-01-08", "Black Tie Armada", "Unstoppable Upps & Unano United, UUUU", ""),
        ("2024-01-08", "Administroyers", "Team Yorrick Hunt", ""),
        ("2024-01-08", "Team Mensa", "Team Blorb", ""),
        ("2024-01-08", "MXNX", "Slot Admin", ""),
    ],
    "Week 5": [
        ("2024-01-15", "MXNX", "Team Mensa", ""),
        ("2024-01-15", "Black Tie Armada", "Team Yorrick Hunt", ""),
        ("2024-01-15", "Administroyers", "Unstoppable Upps & Unano United, UUUU", ""),
        ("2024-01-15", "Rise of the Minions", "Slot Admin", ""),
        ("2024-01-15", "Team Blorb", "MXNX", ""),
    ],
    "Week 6": [
        ("2024-01-22", "MXNX", "Unstoppable Upps & Unano United, UUUU", ""),
        ("2024-01-22", "Team Yorrick Hunt", "Team Mensa", ""),
        ("2024-01-22", "Administroyers", "Black Tie Armada", ""),
        ("2024-01-22", "Unstoppable Upps & Unano United, UUUU", "Slot Admin", ""),
        ("2024-01-22", "Team Blorb", "Rise of the Minions", ""),
    ],
    "Week 7": [
        ("2024-01-29", "Team Mensa", "Slot Admin", ""),
        ("2024-01-29", "Unstoppable Upps & Unano United, UUUU", "Team Blorb", ""),
        ("2024-01-29", "Administroyers", "MXNX", ""),
        ("2024-01-29", "Team Yorrick Hunt", "Team Blorb", ""),
        ("2024-01-29", "Black Tie Armada", "Rise of the Minions", ""),
        ("2024-01-29", "Team Yorrick Hunt", "Rise of the Minions", ""),
    ],
}
