import os
import re

_overrides = dict(
    ra="""
Player:
	Shroud:
		ExploredMapCheckboxEnabled: true
		ExploredMapCheckboxLocked: true
		FogCheckboxEnabled: true
		FogCheckboxLocked: true
	PlayerResources:
		DefaultCash: 5000
		DefaultCashDropdownLocked: true
	DeveloperMode:
		CheckboxEnabled: false
		CheckboxLocked: true
	LobbyPrerequisiteCheckbox@GLOBALBOUNTY:
		Enabled: true
		Locked: false
	LobbyPrerequisiteCheckbox@REUSABLEENGINEERS:
		Enabled: true
		Locked: false
	LobbyPrerequisiteCheckbox@GLOBALFACTUNDEPLOY:
		Enabled: true
		Locked: true

World:
	CrateSpawner:
		CheckboxEnabled: false
		CheckboxLocked: true
	MapBuildRadius:
		AllyBuildRadiusCheckboxEnabled: true
		AllyBuildRadiusCheckboxLocked: true
		BuildRadiusCheckboxEnabled: true
		BuildRadiusCheckboxLocked: true
	MapOptions:
		ShortGameCheckboxEnabled: true
		ShortGameCheckboxLocked: true
		TechLevel: unrestricted
		TechLevelDropdownLocked: true
		GameSpeed: default
		GameSpeedDropdownLocked: true
	MPStartLocations:
		SeparateTeamSpawnsCheckboxEnabled: true
		SeparateTeamSpawnsCheckboxLocked: true
	SpawnMPUnits:
		StartingUnitsClass: none
		DropdownLocked: true
	TimeLimitManager:
		TimeLimitLocked: true
""",
    cnc="""
Player:
	Shroud:
		ExploredMapCheckboxEnabled: true
		ExploredMapCheckboxLocked: true
		FogCheckboxEnabled: true
		FogCheckboxLocked: true
	PlayerResources:
		DefaultCash: 7500
		DefaultCashDropdownLocked: true
	DeveloperMode:
		CheckboxEnabled: false
		CheckboxLocked: true
	LobbyPrerequisiteCheckbox@GLOBALC17STEALTH
		Enabled: true
		Locked: true
	LobbyPrerequisiteCheckbox@GLOBALFACTUNDEPLOY:
		Enabled: true
		Locked: true

World:
	CrateSpawner:
		CheckboxEnabled: false
		CheckboxLocked: true
	MapBuildRadius:
		AllyBuildRadiusCheckboxEnabled: true
		AllyBuildRadiusCheckboxLocked: true
		BuildRadiusCheckboxEnabled: true
		BuildRadiusCheckboxLocked: true
	MapOptions:
		ShortGameCheckboxEnabled: true
		ShortGameCheckboxLocked: true
		TechLevel: unrestricted
		TechLevelDropdownLocked: true
		GameSpeed: default
		GameSpeedDropdownLocked: true
	MPStartLocations:
		SeparateTeamSpawnsCheckboxEnabled: true
		SeparateTeamSpawnsCheckboxLocked: true
	SpawnMPUnits:
		StartingUnitsClass: none
		DropdownLocked: true
	TimeLimitManager:
		TimeLimitLocked: true
""",
)


def _patched_rules(mod, mod_file_path, overrides_rel_path):
    mod_file_content = ""
    with open(mod_file_path) as f:
        for line in f:
            mod_file_content += line
            if line.startswith("Rules:"):
                # Add overrides at the end of the rules to make sure it is
                # overriden
                for line in f:
                    if not line.strip().startswith(f"{mod}|"):
                        mod_file_content += f"\t{mod}|{overrides_rel_path}\n"
                        mod_file_content += line
                        break
                    mod_file_content += line
    return mod_file_content


def patch():
    mod = os.getenv("Mod", "ra")
    mod_base_path = f"/home/openra/lib/openra/mods/{mod}/"
    overrides_file = "server_settings.yaml"
    mod_file_path = mod_base_path + "mod.yaml"
    with open(mod_base_path + overrides_file, "w") as f:
        f.write(_overrides[mod])
    mod_file_content = _patched_rules(mod, mod_file_path, overrides_file)
    with open(mod_file_path, "w") as f:
        f.write(mod_file_content)


def apply_bans(source_file: str):
    with open(source_file) as bans_file:
        _banned_profile_re = re.compile(r'^\d+')
        profile_ids = [int(_banned_profile_re.search(line).group()) for line in bans_file]
    ban_str = ','.join(str(profile_id) for profile_id in profile_ids)
    os.environ["ProfileIDBlacklist"] = ban_str
    print(ban_str)