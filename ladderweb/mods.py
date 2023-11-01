mods = dict(
    ra=dict(
        label="Red Alert",
        icon="icon-ra.png",
        url="https://github.com/OpenRA/OpenRA/releases/tag/release-20231010",
        release="release-20231010",
        # supports_analysis=True,
        mappacks=(
            dict(
                label="2023.2 v2 (rel20231010)",
                filename="ladder-map-pack-2023.2-release20231010.zip",
                changelog="""
                    Updated Version of the 2023.2 map pack for new OpenRA game release (20231010).
                """,
                maps=(
                    ("A Gardens 1vs1", "J MegaTank"),
                    ("Amsterdamned", "wippie"),
                    ("Algeria", "Pinkthoth"),
                    ("Arctic Assault", "Tux"),
                    ("Borrowed Time", "Omnom"),
                    ("Calming Lakes", "Pinkthoth"),
                    ("Crestfells", "Pinkthoth"),
                    ("Enthrall", "Blackened"),
                    ("Lonely Land", "Blackened"),
                    ("Nachtlicht", "Blackened"),
                    ("Pleasant Plains", "Lad"),
                    ("River of Blood", "Lad"),
                    ("Scorched Earth II", "J MegaTank"),
                    ("Shadegrown", "Pinkthoth"),
                    ("Snake Woods", "Pinkthoth"),
                    ("The Great Divide", "SoScared"),
                    ("The Highlands", "Lad"),
                    ("The Space Between", "Blackened"),
                    ("Two Towns", "Blackened"),
                    ("Woodlands", "Lad"),
                ),
            ),
            dict(
                label="2023.2 v2 (2023-09-01)",
                filename="ladder-map-pack-2023.2-v2.zip",
                changelog="""
                    Version 2 of the 2023.2 map pack extends the previous version by 6 new maps for added variety in
                    the 20th RA Ladder season.
                """,
                maps=(
                    ("Amsterdamned", "wippie"),
                    ("Arctic Assault", "Tux"),
                    ("Calming Lakes", "Pinkthoth"),
                    ("Crestfells", "Pinkthoth"),
                    ("Pleasant Plains", "Lad"),
                    ("The Highlands", "Lad"),
                    ("A Gardens 1vs1", "J MegaTank"),
                    ("Algeria", "Pinkthoth"),
                    ("Borrowed Time", "Omnom"),
                    ("Enthrall", "Blackened"),
                    ("Lonely Land", "Blackened"),
                    ("Megara", "Pinkthoth"),
                    ("Nachtlicht", "Blackened"),
                    ("River of Blood", "Lad"),
                    ("Scorched Earth II", "J MegaTank"),
                    ("Shadegrown", "Pinkthoth"),
                    ("Snake Woods", "Pinkthoth"),
                    ("Two Towns", "Blackened"),
                    ("The Space Between", "Blackened"),
                    ("The Great Divide", "SoScared"),
                    ("Woodlands", "Lad"),
                ),
            ),
            dict(
                label="2023.2 (2023-07-01)",
                filename="ladder-map-pack-2023.2.zip",
                changelog="""
                    New map pack to start of RA Ladder season 19. Features some all-new maps as well as beloved classics
                    from past Red Alert Global League seasons, all updated to latest Balance patch,
                    <a href="https://github.com/tttppp/ora-balance-iteration/blob/3.6/CHANGELOG.md#36" target="_blank">v3.6</a>.
                """,
                maps=(
                    ("A Gardens 1vs1", "J MegaTank"),
                    ("Algeria", "Pinkthoth"),
                    ("Borrowed Time", "Omnom"),
                    ("Enthrall", "Blackened"),
                    ("Lonely Land", "Blackened"),
                    ("Megara", "Pinkthoth"),
                    ("Nachtlicht", "Blackened"),
                    ("River of Blood", "Lad"),
                    ("Scorched Earth II", "J MegaTank"),
                    ("Shadegrown", "Pinkthoth"),
                    ("Snake Woods", "Pinkthoth"),
                    ("Two Towns", "Blackened"),
                    ("The Space Between", "Blackened"),
                    ("The Great Divide", "SoScared"),
                    ("Woodlands", "Lad"),
                ),
            ),
            dict(
                label="2023.1 (2023-03-05)",
                filename="ladder-map-pack-2023.1.zip",
                changelog="""
                    The 2023.1 map pack extends the previous by adding another 15 maps while cycling out 3 meme
                    maps for 3 new meme maps. Compatible with OpenRA Release version 20230225. Balance rules have
                    been updated to <a href="https://github.com/tttppp/ora-balance-iteration/blob/3.5.2/CHANGELOG.md#352" target="_blank">v3.5.2</a>
                    (which does not contain any actual changes but is optimized for the new game version)
                """,
                maps=(
                    ("Almighty Petrodollar", "Lucian"),
                    ("Amok", "Pinkthoth"),
                    ("Autumn Mix", "Blackened"),
                    ("Below Zero", "Lad"),
                    ("Clearing", "Pinkthoth"),
                    ("Conyard", "Blackened"),
                    ("Cow Level", "Pinkthoth"),
                    ("Dead of Winter", "Pinkthoth"),
                    ("Deciduous Ring", "Blackened"),
                    ("Desert Strike", "Lad"),
                    ("Duskwood", "i like men"),
                    ("Endless Night", "Pinkthoth"),
                    ("Excavations", "Pinkthoth"),
                    ("Gem Lord", "MicroBit/MegaTank"),
                    ("Island Konflict", "MegaTank-Westwood Studios"),
                    ("Jimmy got paid", "J MegaTank"),
                    ("Jungle Boogie", "Pinkthoth"),
                    ("Kitsunegari", "Pinkthoth"),
                    ("Malevolence", "Blackened"),
                    ("Military Mind", "J MegaTank"),
                    ("Orthos", "Blackened"),
                    ("Paradisio", "Pinkthoth"),
                    ("Pulverize", "J MegaTank"),
                    ("Queen of the Hill", "Pinkthoth"),
                    ("Strashno", "Pinkthoth"),
                    ("Syzygy", "Pinkthoth"),
                    ("Thales", "Strauss"),
                    ("The Long Night", "Lad"),
                    ("Timian", "Widow"),
                    ("Toxicity", "Pinkthoth"),
                    ("Twisted River of Gold", "netnazgul"),
                    ("Ultra Islands", "J MegaTank"),
                    ("War Factory", "Blackened"),
                    ("Wormrot", "Blackened"),
                ),
            ),
            dict(
                label="2023.0 v2 (2023-02-25)",
                filename="ladder-map-pack-2023.0_release20230225.zip",
                changelog="""
                    This map pack is the same as 2023.0 below, updated to be compatible with OpenRA release-20230225.
                """,
                maps=(
                    ("Almighty petrodollar", "Lucian"),
                    ("Autumn Mix", "Blackened"),
                    ("Below Zero", "Lad"),
                    ("Clearing", "Pinkthoth"),
                    ("Deciduous Ring", "Blackened"),
                    ("Desert Strike", "Lad"),
                    ("Excavations", "Pinkthoth"),
                    ("Jungle Boogie", "Pinkthoth"),
                    ("Paradisio", "Pinkthoth"),
                    ("Pulverize", "J MegaTank"),
                    ("Strashno", "Pinkthoth"),
                    ("Thales", "Strauss"),
                    ("The Long Night", "Lad"),
                    ("Timian", "Widow"),
                    ("Twisted River of Gold", "netnazgul"),
                    ("The Pooper Bowl 1v1", "Poop"),
                    ("4 Nukes", "J MegaTank"),
                    ("Duel", "Lane Madsen"),
                ),
            ),
            dict(
                label="2023.0 (2023-01-07)",
                filename="ladder-map-pack-2023.0.zip",
                changelog="""
                    The 2023.0 map pack contains an entirely new selection of maps with a broad variety in style.
                    Most notably, a set of "fun" maps have been added to the pool that drastically differ from
                    established competitive 1v1 layout. All maps have been updated to
                    <a href="https://github.com/tttppp/ora-balance-iteration/blob/master/CHANGELOG.md#35">Balance Iteration 3.5</a>.
                """,
                maps=(
                    ("Almighty petrodollar", "Lucian"),
                    ("Autumn Mix", "Blackened"),
                    ("Below Zero", "Lad"),
                    ("Clearing", "Pinkthoth"),
                    ("Deciduous Ring", "Blackened"),
                    ("Desert Strike", "Lad"),
                    ("Excavations", "Pinkthoth"),
                    ("Jungle Boogie", "Pinkthoth"),
                    ("Paradisio", "Pinkthoth"),
                    ("Pulverize", "J MegaTank"),
                    ("Strashno", "Pinkthoth"),
                    ("Thales", "Strauss"),
                    ("The Long Night", "Lad"),
                    ("Timian", "Widow"),
                    ("Twisted River of Gold", "netnazgul"),
                    ("The Pooper Bowl 1v1", "Poop"),
                    ("4 Nukes", "J MegaTank"),
                    ("Duel", "Lane Madsen"),
                ),
            ),
            dict(
                label="2022.1 (2022-10-30)",
                filename="ladder-map-pack-2022.1.zip",
                changelog="""
                    The 2022.1 map pack is an updated version that adds the latest
                    <a href="https://github.com/tttppp/ora-balance-iteration/blob/master/CHANGELOG.md#35">Balance Iteration 3.5</a>
                    and RAGL Season 13 maps to the selection.
                """,
                maps=(
                    ("Abendland", "Pinkthoth"),
                    ("Agita", "kazu"),
                    ("Anar", "Pinkthoth"),
                    ("Argon", "kazu"),
                    ("Assault", "Lad"),
                    ("Barentsøya (BB)", "Lucian"),
                    ("Bucharest", "poop"),
                    ("Circulate", "i like men"),
                    ("Cog of War", "netnazgul"),
                    ("Dirge", "Pinkthoth"),
                    ("Discovery", "Lad"),
                    ("Elevation", "i like men"),
                    ("Fairyland", "Lad"),
                    ("Forgotten Plains", "Eskimo"),
                    ("Greener Pastures", "Lad"),
                    ("Infection", "wippie"),
                    ("Isle of Wight", "Lad"),
                    ("Krakow", "poop"),
                    ("Moonopoly", "Lad"),
                    ("Overkill", "MegaTank"),
                    ("Pity Light", "Widow"),
                    ("Race Tracks", "Blackened"),
                    ("Scorched Earth", "J MegaTank"),
                    ("Sompio", "Pinkthoth"),
                    ("Sun Struggle", "Lad"),
                    ("Territorial", "Lad"),
                    ("Trapped", "Blackened"),
                    ("Yukon Territory", "wippie"),
                ),
            ),
            dict(
                label="2022.0 (2022-01-07)",
                filename="ladder-map-pack-2022.0.zip",
                changelog="""
                    This map pack is selected out of 40 maps by the community
                    <a href="https://forum.openra.net/viewtopic.php?f=82&t=21545&p=313637">
                    with public voting</a>. Feel to participate to the upcoming
                    polls. Events will be announced on forum and on the OpenRA
                    Competitive Discord server, #ladder channel.
                """,
                maps=(
                    ("Agita", "kazu"),
                    ("Argon", "kazu"),
                    ("Barentsøya (BB)", "Lucian"),
                    ("Bucharest", "poop"),
                    ("Cog of War", "netnazgul"),
                    ("Dirge", "Pinkthoth"),
                    ("Discovery", "Lad"),
                    ("Fairyland", "Lad"),
                    ("Krakow", "poop"),
                    ("Moonopoly", "Lad"),
                    ("Race Tracks", "Blackened"),
                    ("Scorched Earth", "J MegaTank"),
                    ("Sun Struggle", "Lad"),
                    ("Trapped", "Blackened"),
                    ("Yukon Territory", "wippie"),
                ),
            ),
            dict(
                label="2021.1 (2021-04-26)",
                filename="ladder-map-pack-2021.1.zip",
                changelog="""
                    Same map pack as 2021.0 with the following changes:
                    <ul>
                        <li>Overlay adjusted to make the minimap more visible</li>
                        <li>Blitz bumped from 1.3 to 1.4 (rev4 to rev5)</li>
                        <li>Kosovo updated to address symmetry issues notably</li>
                        <li>Fix shadowlands extra buildable sandbags (thanks Goremented)</li>
                    </ul>
                """,
                maps=(),
            ),
            dict(
                label="2021.0 (2021-04-06)",
                filename="ladder-map-pack-2021.0.zip",
                changelog="""
                    This pack is a selection of 15 maps curated by the RA
                    Competitive Maps Committee to celebrate the end of RAGL. It
                    includes a few popular old maps and some brand new. The
                    balance is the same as previously (affecting Ranger, Dome
                    and LongBow) with an additional fix for the missing phase
                    transport sound notification. ERCC 2.1/BCC 1.0 modding is
                    also still present.
                """,
                maps=(
                    ("Blitz", "kazu"),
                    ("Breaking Bad", "Goremented"),
                    ("Clover", "Lad"),
                    ("Crownsbury", "Pinkthoth"),
                    ("Eden Lake", "kazu"),
                    ("Eternal Warriors", "J MegaTank"),
                    ("Forgotten Plains", "eskimo"),
                    ("Kosovo", "poop"),
                    ("Marigold Town", "Super Newbie"),
                    ("Mountain Range Redux", "Blackened"),
                    ("Offensive Operation", "Lad"),
                    ("Onyx", "eskimo"),
                    ("Shadowlands", "Lad"),
                    ("Styx", "Pinkthoth"),
                    ("Treasure Hunt", "Lad"),
                ),
            ),
            dict(
                label="2021-03-29",
                filename="ladder-map-pack-2021-03-29.zip",
                changelog="""
                    Temporarily removed the S9 maps as they are causing too much
                    crashes. Only RAGL X maps remain.
                """,
                maps=(
                    ("Amsterdamned[RAGL-X]", "wippie"),
                    ("Annihilate[RAGL-X]", "poop"),
                    ("Behind The Curtain[RAGL-X]", "WhoCares & Kyrylo Silin"),
                    ("Darkside Aftermath[RAGL-X]", "J MegaTank"),
                    ("Devils Marsh[RAGL-X]", "N/a"),
                    ("Mounds[RAGL-X]", "Pinkthoth"),
                    ("Nomad[RAGL-X]", "Upps"),
                    ("Off My Lawn, Punks ![RAGL-X]", "WhoCares & Hamb"),
                    ("Pitfight[RAGL-X]", "kazu."),
                    ("Polemos[RAGL-X]", "KOYK"),
                    ("Timian[RAGL-X]", "Widow"),
                    ("Winding Woods[RAGL-X]", "Pinkthoth"),
                ),
            ),
            dict(
                label="2020-12-28",
                filename="ladder-map-pack-2020-12-28.zip",
                changelog="""
                    <strong>Warning</strong>: this map pack contains broken S9
                    maps: the light tank husks will cause crashes.
                """,
                maps=(
                    ("Agita RAGL S9", "kazu."),
                    ("Amsterdamned[RAGL-X]", "wippie"),
                    ("Annihilate[RAGL-X]", "poop"),
                    ("Behind The Curtain[RAGL-X]", "WhoCares & Kyrylo Silin"),
                    ("Darkside Aftermath[RAGL-X]", "J MegaTank"),
                    ("Devils Marsh[RAGL-X]", "N/a"),
                    ("Discovery RAGL S9", "Lad"),
                    ("Dual Cold Front RAGL S9", "PizzaAtomica"),
                    ("Mounds[RAGL-X]", "Pinkthoth"),
                    ("Mountain Ridge Redux RAGL S9", "Blackened"),
                    ("Nomad[RAGL-X]", "Upps"),
                    ("Off My Lawn, Punks ![RAGL-X]", "WhoCares & Hamb"),
                    ("Ore Egano RAGL S9", "kazu."),
                    ("Pitfight[RAGL-X]", "kazu."),
                    ("Polemos[RAGL-X]", "KOYK"),
                    ("Shadowfiend II RAGL S9", "kazu."),
                    ("Sonora RAGL S9", "wippie"),
                    ("Teared Strait RAGL S9", "mo"),
                    ("The Swamp RAGL S9", "kazu."),
                    ("Three and a half woods RAGL S9", "WhoCares (based on SN's Seventh woods)"),
                    ("Timian[RAGL-X]", "Widow"),
                    ("Trail of Thought RAGL S9", "netnazgul"),
                    ("Wetlands RAGL S9", "i like men"),
                    ("Winding Woods[RAGL-X]", "Pinkthoth"),
                ),
            ),
        ),
    ),
    td=dict(
        label="Tiberian Dawn",
        icon="icon-td.png",
        url="https://github.com/OpenRA/OpenRA/releases/tag/release-20231010",
        release="release-20231010",
        mappacks=(
            dict(
                label="2023.0 v2",
                filename="ladder-map-pack-td-2023.0-release20231010.zip",
                changelog="""
                    Updated map pack for OpenRA Release 20231010.
                """,
                maps=(
                    ("16:9", "norman"),
                    ("African Gambit", "MASTER, Jay"),
                    ("A New Winter", "J MegaTank"),
                    ("Blue Winter 1995", "J MegaTank"),
                    ("CrackPoint", "MASTER"),
                    ("Desert Cross", "J MegaTank"),
                    ("Desert Mandarins", "MASTER"),
                    ("Matchpoint", "ZxGanon"),
                    ("Mountain Town Madness", "Blackened"),
                    ("Rumble in the Jungle", "J MegaTank"),
                    ("Tiberium Rift", "ZxGanon"),
                    ("WarZoneX", "J MegaTank"),
                ),
            ),
            dict(
                label="2023.0",
                filename="ladder-map-pack-td-2023.0.zip",
                changelog="""
                    Map pack for OpenRA Release 20230225. Maps contain no custom balance rules
                    because all the latest TD balance changes have been merged into the base game.
                """,
                maps=(
                    ("16:9", "norman"),
                    ("African Gambit", "MASTER, Jay"),
                    ("A New Winter", "J MegaTank"),
                    ("Blue Winter 1995", "J MegaTank"),
                    ("CrackPoint", "MASTER"),
                    ("Desert Cross", "J MegaTank"),
                    ("Desert Mandarins", "MASTER"),
                    ("Matchpoint", "ZxGanon"),
                    ("Mountain Town Madness", "Blackened"),
                    ("Rumble in the Jungle", "J MegaTank"),
                    ("Tiberium Rift", "ZxGanon"),
                    ("WarZoneX", "J MegaTank"),
                ),
            ),
            dict(
                label="2021-04-05",
                filename="ladder-map-pack-td-2021-04-05.zip",
                changelog="""
                    First map pack with TDGL2+ maps (minus the disliked
                    <strong>Masters Frontline</strong>) and custom balance
                    removed.
                """,
                maps=(
                    ("16:9[Ladder]", "norman"),
                    ("African Gambit[Ladder]", "MASTER, Jay"),
                    ("Badland Ridges[Ladder]", "The Echo of Damnation"),
                    ("CrackPoint[Ladder]", "MASTER"),
                    ("Desert Mandarins[Ladder]", "MASTER"),
                    ("Tiberium Rift[Ladder]", "ZxGanon"),
                ),
            ),
        ),
    ),
)
