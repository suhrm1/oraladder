import os

config = dict(
    replay_folder="ratl/replays",
    config_folder="ratl",
)

for key, default_value in config.items():
    config[key] = os.getenv(key, default=default_value)

config["teams"] = {
    "Gruesome Twosome": [17239, 12760],  # Fazzar & MASTER
    "Team 2nd Place": [6430, 6748],  # Blackened & Orb
    "Many Names": [16401, 9156],  # Margot, Radical Centrist
    "Hawkalypse": [18246, 13710],  # Creo, Mint
    "Pitchfork Penguins": [15899, 16066],  # Tux & Milkman
    "CrackheadHONKerz420": [17607, 15266],  # Holk, JockoChillink/cracksmoka420
    "Careless Cucks": [6771, 11855],  # Bain, Kaution
    "Team name": [3952, 7304],  # Anjew, Upps
    # "Testteam 1": [8860, 16401],  # moods / margot
    # "Testteam 2": [15899, 13710],  # Tux & Milkman
}

config["player_names"] = {
    17239: "Fazzar",
    12760: "MASTER",
    6430: "Blackened",
    6748: "Orb",
    16401: "Margot Honecker",
    9156: "Radical Centrist",
    18246: "Creo",
    13710: "Mint",
    15899: "Tux",
    16066: "milkman",
    17607: "BigHALK",
    15266: "cracksmoka420",
    6771: "Bain",
    11855: "Kaution",
    3952: "Anjew",
    7304: "Upps",
    # 8860: "moods",
}

config["schedule"] = {
    "Week 1": [
        ("2023-04-30", "CrackheadHONKerz420", "Gruesome Twosome", ""),
        ("2023-04-30", "Team name", "Team 2nd Place", ""),
        ("2023-04-30", "Pitchfork Penguins", "Careless Cucks", ""),
        ("2023-04-30", "Many Names ", "Hawkalypse", ""),
    ],
    "Week 2": [
        ("2023-05-07", "Hawkalypse", "Team name", ""),
        ("2023-05-07", "Careless Cucks", "Gruesome Twosome", ""),
        ("2023-05-07", "Team 2nd Place", "CrackheadHONKerz420", ""),
        ("2023-05-07", "Many Names", "Pitchfork Penguins", ""),
        ("2023-05-07", "CrackheadHONKerz420", "Careless Cucks", ""),
        ("2023-05-07", "Team 2nd Place", "Hawkalypse", ""),
        ("2023-05-07", "Gruesome Twosome", "Many Names", ""),
        ("2023-05-07", "Team name", "Pitchfork Penguins", ""),
    ],
    "Week 3": [
        ("2023-05-14", "Hawkalypse", "CrackheadHONKerz420", ""),
        ("2023-05-14", "Team 2nd Place", "Pitchfork Penguins", ""),
        ("2023-05-14", "Gruesome Twosome", "Team name", ""),
        ("2023-05-14", "Careless Cucks", "Many Names", ""),
    ],
    "Week 4": [
        ("2023-05-21", "CrackheadHONKerz420", "Many Names", ""),
        ("2023-05-21", "Hawkalypse", "Pitchfork Penguins", ""),
        ("2023-05-21", "Careless Cucks", "Team name", ""),
        ("2023-05-21", "Team 2nd Place", "Gruesome Twosome", ""),
        ("2023-05-21", "Team name", "Many Names", ""),
        ("2023-05-21", "Gruesome Twosome", "Hawkalypse", ""),
        ("2023-05-21", "Team 2nd Place", "Careless Cucks", ""),
        ("2023-05-21", "Pitchfork Penguins", "CrackheadHONKerz420", ""),
    ],
    "Week 5": [
        ("2023-05-28", "CrackheadHONKerz420", "Team name", ""),
        ("2023-05-28", "Pitchfork Penguins", "Gruesome Twosome", ""),
        ("2023-05-28", "Many Names", "Team 2nd Place", ""),
        ("2023-05-28", "Hawkalypse", "Careless Cucks", ""),
    ],
}
