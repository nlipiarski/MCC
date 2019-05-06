# Target Selector modifiers
TARGET_INT_RANGE = frozenset({"level"})
TARGET_INT = frozenset({"limit"})
TARGET_FLOAT_RANGE = frozenset({"x", "y", "z", "x_rotation", "y_rotation", "distance", "dx", "dy", "dz"})
TARGET_USERNAME = frozenset({"name", "tag", "team"})
TARGET_GAMEMODE = frozenset({"gamemode"})
TARGET_SORT = frozenset({"sort"})
TARGET_ENTITY = frozenset({"type"})
TARGET_SCORES = frozenset({"scores"})
TARGET_ADVANCEMENTS = frozenset({"advancements"})
TARGET_NBT = frozenset({"nbt"})

TARGET_KEY_LISTS = [TARGET_INT_RANGE,TARGET_INT,TARGET_FLOAT_RANGE,TARGET_USERNAME,TARGET_GAMEMODE,TARGET_SORT,TARGET_ENTITY,TARGET_SCORES,TARGET_ADVANCEMENTS,TARGET_NBT]

# Json keys
JSON_STRING_KEYS = frozenset({"text","author","command","insertion","keybind","title","translate"})
JSON_ENTITY_KEYS = frozenset({"markerTag","selector"})
JSON_BOOLEAN_KEYS = frozenset({"bold","italic","obfuscated","underlined","strikethrough"})
JSON_NESTED_KEYS = frozenset({"extra", "with"})

OBJECTIVE_CRITERIA = frozenset({"air","armor","deathCount","dummy","food","health","killedByTeam.aqua","killedByTeam.black","killedByTeam.blue","killedByTeam.dark_aqua","killedByTeam.dark_blue","killedByTeam.dark_gray","killedByTeam.dark_green","killedByTeam.dark_purple","killedByTeam.dark_red","killedByTeam.gold","killedByTeam.gray","killedByTeam.green","killedByTeam.light_purple","killedByTeam.red","killedByTeam.white","killedByTeam.yellow","level","playerKillCount","teamkill.aqua","teamkill.black","teamkill.blue","teamkill.dark_aqua","teamkill.dark_blue","teamkill.dark_gray","teamkill.dark_green","teamkill.dark_purple","teamkill.dark_red","teamkill.gold","teamkill.gray","teamkill.green","teamkill.light_purple","teamkill.red","teamkill.white","teamkill.yellow","totalKillCount","trigger","xp"})
CRITERIA_BLOCKS = frozenset({"minecraft.mined"})
CRITERIA_ITEMS = frozenset({"minecraft.crafted","minecraft.used","minecraft.broken","minecraft.picked_up","minecraft.dropped"})
CRITERIA_ENTITIES = frozenset({"minecraft.killed","minecraft.killed_by"})
CRITERIA_CUSTOM = frozenset({"minecraft.custom"})

AXES = frozenset({"x", "y", "z", "xy", "xz", "yx", "yz", "zx", "zy", "xyz", "xzy", "yxz", "yzx", "zxy", "zyx"})
COLORS = frozenset({"none","black","dark_blue","dark_green","dark_aqua","dark_red","dark_purple","gold","gray","dark_gray","blue","green","aqua","red","light_purple","yellow","white"})
ENTITY_ANCHORS = frozenset({"feet", "eyes"})
CLICK_EVENT_ACTIONS = frozenset({"run_command","suggest_command","open_url","change_page"})
HOVER_EVENT_ACTIONS = frozenset({"show_text","show_item","show_entity","show_achievement"})