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
    "NoobRush Buffoons": [16401, 9156],  # Margot, Radical Centrist
    "Hawkalypse": [18246, 13710],  # Creo, Mint
    "Pitchfork Penguins": [15899, 16066],  # Tux & Milkman
    "CrackheadHONKerz420": [17607, 15266],  # Holk, JockoChillink/cracksmoka420
    "Careless Cucks": [6771, 11855],  # Bain, Kaution
    "Team name": [3952, 7304],  # Anjew, Upps
    "Fashionably late": [13705, 8031],  # Kav, Stitch
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
    8031: "Stitch",
    13705: "Kav",
    # 8860: "moods",
}

config["schedule"] = {
    "Week 1": [
        ("2023-04-30", "CrackheadHONKerz420", "Gruesome Twosome", ""),
        ("2023-04-30", "Team name", "Team 2nd Place", ""),
        ("2023-04-30", "Pitchfork Penguins", "Careless Cucks", ""),
        ("2023-04-30", "NoobRush Buffoons", "Hawkalypse", ""),
    ],
    "Week 2": [
        ("2023-05-07", "CrackheadHONKerz420", "Careless Cucks", ""),
        ("2023-05-07", "Hawkalyypse", "Pitchfork Penguins", ""),
        ("2023-05-07", "Fashionably late", "Team name", ""),
        ("2023-05-07", "Pitchfork Penguins", "NoobRush Buffoons", ""),
        ("2023-05-07", "Fashionably late", "Gruesome Twosome", ""),
        ("2023-05-07", "Gruesome Twosome", "Team name", ""),
    ],
    "Week 3": [
        ("2023-05-14", "Careless Cucks", "Team name", ""),
        ("2023-05-14", "Pitchfork Penguins", "CrackheadHONKerz420", ""),
        ("2023-05-14", "Hawkalypse", "Team 2nd Place", ""),
        ("2023-05-14", "Gruesome Twosome", "NoobRush Buffoons", ""),
        ("2023-05-14", "Gruesome Twosome", "Careless Cucks", ""),
        ("2023-05-14", "Hawkalypse", "Fashionably late", ""),
        ("2023-05-14", "Fashionably late", "Team 2nd Place", ""),
    ],
    "Week 4": [
        ("2023-05-21", "Careless Cucks", "Fashionably late", ""),
        ("2023-05-21", "Fashionably late", "Pitchfork Penguins", ""),
        ("2023-05-21", "CrackheadHONKerz420", "Team name", ""),
        ("2023-05-21", "NoobRush Buffoons", "Careless Cucks", ""),
        ("2023-05-21", "Team name", "NoobRush Buffoons", ""),
        ("2023-05-21", "Team 2nd Place", "Gruesome Twosome", ""),
    ],
    "Week 5": [
        ("2023-05-28", "Team 2nd Place", "Careless Cucks", ""),
        ("2023-05-28", "NoobRush Buffoons", "CrackheadHONKerz420", ""),
        ("2023-05-28", "Fashionably late", "NoobRush Buffoons", ""),
        ("2023-05-28", "Hawkalypse", "CrackheadHONKerz420", ""),
        ("2023-05-28", "Team name", "Pitchfork Penguins", ""),
        ("2023-05-28", "Gruesome Twosome", "Hawkalypse", ""),
        ("2023-05-28", "Team 2nd Place", "Pitchfork Penguins", ""),
    ],
    "Week 6": [
        ("2023-06-04", "CrackheadHONKerz420", "Fashionably late", ""),
        ("2023-06-04", "Team 2nd Place", "CrackheadHONKerz420", ""),
        ("2023-06-04", "Team 2nd Place", "NoobRush Buffoons", ""),
        ("2023-06-04", "Careless Cucks", "Hawkalypse", ""),
        ("2023-06-04", "Hawkalypse", "Team name", ""),
        ("2023-06-04", "Pitchfork Penguins", "Gruesome Twosome", ""),
    ],
}
