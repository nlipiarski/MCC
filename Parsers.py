import sublime, re
from .Blocks import BLOCKS
from .Data import BYTE_TAGS, SHORT_TAGS, INTEGER_TAGS, LONG_TAGS, FLOAT_TAGS, DOUBLE_TAGS, STRING_TAGS, COMPOUND_TAGS, STRING_LIST_TAGS, INTEGER_LIST_TAGS, FLOAT_LIST_TAGS, PARTICLES

add_regions_flags = sublime.DRAW_NO_OUTLINE
regex = {
	"vec3d" : re.compile("(\d+(?:\.\d+)?)[ \t\n]+(\d+(?:\.\d+)?)[ \t\n]+(\d+(?:\.\d+)?)"),
	"vec2d" : re.compile("(\d+(?:\.\d+)?)[ \t\n]+(\d+(?:\.\d+)?)"),
	"float" : re.compile("(-?\d+\.\d+)"),
	"integer" : re.compile("(-?\d+)"),
	"namespace" : re.compile("([a-z_\-1-9]+:)([a-z_\-1-9]+(?:\/[a-z_\-1-9]+)*)(\/?)"),
	"string" : re.compile("\"(?:[^\\\"]|(\\.))*\""),
	"username" : re.compile("\w{3,16}"),
	"axes" : re.compile("([xyz]+)"),
	"integer_range" : re.compile("(?:(\d+)(\.\.))?(\d+)"), #used in entity selectors for the 55..66 type deal (integer only though)
	"float_range" : re.compile("(?:(\d+(?:\.\d+)?)(\.\.))?(\d+(?:\.\d+)?)"), # used in entity selectors for float ranges, similar to previous comment
	"entity_tag" : re.compile("\w+"),
	"entity_tag_key" : re.compile("([a-z]+)\s*(=)"),
	"entity_tag_advancement_key" : re.compile("([a-z_\-1-9]+:)?([a-z]+)\s*(=)") 
}
# start is inclusive while end is exclusive, like string slices
def add_region(view, region, start, end, scope, token_id):
	new_region = sublime.Region(region.begin() + start, region.begin() + end)
	view.add_regions("token" + str(token_id), [new_region], scope, flags=add_regions_flags)
	return (token_id+1, end)

# Returns the next value of current where string[current] is not whitespace.  If the end of the string is reached,
# this will error highlight the section from err_start until the end of the string
def skip_whitespace(view, region, string, current, token_id, err_start):
	if current >= len(string):
		return add_region(view, region, err_start, current, "invalid.illegal", token_id)
	while string[current] in " \n\t":
		current += 1
		if current >= len(string):
			return add_region(view, region, err_start, current, "invalid.illegal", token_id)
	return (token_id, current)

def namespace_parser(view, region, string, current, token_id, properties={}): #all parsers return (token_id, newStart)
	namespace_match = regex["namespace"].match(string, current)
	if namespace_match:
		add_region(view, region, namespace_match.start(1), namespace_match.end(1),"mccstring",token_id)
		token_id, current = add_region(view, region, namespace_match.start(2), namespace_match.end(2),"mccliteral",token_id+1)
		if namespace_match.start(3) > -1:
			return add_region(view, region, namespace_match.start(3), namespace_match.end(3), "invalid.illegal",token_id)
	return (token_id, current)

# Entity tags
#
# gamemode
#	survival, creative, spectator, adventure
# level
#	integer (range)
# x, y, z, x_rotation, y_rotation, distance
#	float(range)
# tag
#	unquoted, one word string
# name
# 	either unquoted, one word string or a quoted string
# sort
#	nearest, furthest, random, arbitrary
# scores
# 	compound list of arbitrary tags with integer range values.
#	eg scores={foo=1,bar=1..5} (taken from minecraft wiki)
# advancements
#	combound list of boolean tags whose key is an advancement.  Can have keys with colons in them
#	advancements={foo=true,bar=false,custom:something={criterion=true}} (taken from minecraft wiki)
def entity_parser(view, region, string, current, token_id, properties={}):
	if string[current] == "*" and "has_wildcard" in properties and properties["has_wildcard"]:
		return add_region(view, region, current, current+1, "mccentity", token_id)

	if string[current] != "@" or (current + 1 < len(string) and not string[current+1] in "earp"): #Checks to see if it's a valid entity selector
		return (token_id, current)

	token_id, current = add_region(view, region, current, current+2, "mccentity", token_id)
	if (current < len(string) and string[current] == "["):
		token_id, current = add_region(view, region, current, current+1, "mccentity", token_id)
		bracket_start = current

		token_id, current = skip_whitespace(view, region, string, current, token_id, bracket_start)
		if current == len(string):
			return (token_id, current)

		while (string[current] != "]"):
			
			start_of_key = current
			key_match = regex["entity_tag_key"].match(string, current)
			if not key_match:
				return (token_id, current)

			key = key_match.group(1)
			token_id, _ = add_region(view, region, key_match.start(2), key_match.end(2), "mcccommand", token_id) #the command scope is used here because that's the legacy highlghting of '='
			token_id, _ = add_region(view, region, key_match.start(1), key_match.end(1), "mccstring", token_id)
			token_id, current = skip_whitespace(view, region, string, key_match.end(), token_id, start_of_key)
			if current == len(string):
				return (token_id, current)

			if key == "level":
				int_range_match = regex["integer_range"].match(string, current)
				if not int_range_match:
					return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)
				token_id, _ = add_region(view, region, int_range_match.start(1), int_range_match.end(1), "mccconstant", token_id)
				token_id, _ = add_region(view, region, int_range_match.start(2), int_range_match.end(2), "mcccommand", token_id)
				token_id, current = add_region(view, region, int_range_match.start(3), int_range_match.end(3), "mccconstant", token_id)

			elif key in ["x", "y", "z", "x_rotation", "y_rotation", "distance"]:
				float_range_match = regex["float_range"].match(string, current)
				if not float_range_match:
					return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)
				token_id, _ = add_region(view, region, float_range_match.start(1), float_range_match.end(1), "mccconstant", token_id)
				token_id, _ = add_region(view, region, float_range_match.start(2), float_range_match.end(2), "mcccommand", token_id)
				token_id, current = add_region(view, region, float_range_match.start(3), float_range_match.end(3), "mccconstant", token_id)

			elif key == "tag":
				if string[current] == "!":
					token_id, current = add_region(view, region, current, current+1, "mcccommand", token_id) #Similar deal to the '=' earlier
					token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
					if current == len(string):
						return (token_id, current)


				tag_value_match = regex["entity_tag"].match(string, current)
				if not tag_value_match:
					return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)
				token_id, current = add_region(view, region, tag_value_match.start(), tag_value_match.end(), "mccstring", token_id)

			elif key == "name":
				if string[current] == "!":
					token_id, current = add_region(view, region, current, current+1, "mcccommand", token_id) #Similar deal to the '=' earlier
					token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
					if current == len(string):
						return (token_id, current)

				tag_value_match = None
				if string[current] == "\"":
					#print("using string name thing")
					tag_value_match = regex["string"].match(string, current)
				else:
					#print("using tag name thing")
					tag_value_match = regex["entity_tag"].match(string, current) #it's the same deal as tags bruh

				if not tag_value_match:
					return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)
				token_id, current = add_region(view, region, tag_value_match.start(), tag_value_match.end(), "mccstring", token_id)

			elif key == "scores":
				if string[current] != "{":
					return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)
				score_bracket_start = current

				token_id, current = skip_whitespace(view, region, string, current, token_id, score_bracket_start)
				if current == len(string):
					return (token_id, current)

				current += 1
				while string[current] != "}":

					start_of_score = current
					score_match = regex["entity_tag_key"].match(string, current)
					if not score_match:
						return (token_id, current)

					token_id, _ = add_region(view, region, score_match.start(2), score_match.end(2), "mcccommand", token_id)
					token_id, _ = add_region(view, region, score_match.start(1), score_match.end(1), "mccstring", token_id)
					current = score_match.end()

					token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
					if current == len(string):
						return (token_id, current)

					int_range_match = regex["integer_range"].match(string, current)
					if not int_range_match:
						return add_region(view, region, start_of_score, current, "invalid.illegal", token_id)
					token_id, _ = add_region(view, region, int_range_match.start(1), int_range_match.end(1), "mccconstant", token_id)
					token_id, _ = add_region(view, region, int_range_match.start(2), int_range_match.end(2), "mcccommand", token_id)
					token_id, current = add_region(view, region, int_range_match.start(3), int_range_match.end(3), "mccconstant", token_id)

					token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
					if current == len(string):
						return (token_id, current)

					if string[current] == ",":
						current += 1
					elif string[current] != "}":
						return add_region(view, region, current, current + 1, "invalid.illegal", token_id)

					token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
					if current == len(string):
						return (token_id, current)

				current += 1

			elif key == "advancements":
				token_id, current = advancement_tag_parser(view, region, string, current, token_id)
				if string[current - 1] != "}": #Make sure the parse was good
					return (token_id, current)

			else:
				return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)

			token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
			if current == len(string):
				return token_id, current

			if string[current] == ",":
				current += 1
			elif string[current] != "]":
				return add_region(view, region, current, current + 1, "invalid.illegal", token_id)

			token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_key)
			if current == len(string):
				return (token_id, current)

		return add_region(view, region, current, current+1, "mccentity", token_id)

	return (token_id, current)

def advancement_tag_parser(view, region, string, current, token_id, do_nested=True):
	if string[current] != "{":
		return add_region(view, region, start_of_key, current, "invalid.illegal", token_id)
	bracket_start = current
	
	token_id, current = skip_whitespace(view, region, string, current, token_id, bracket_start)
	if current == len(string):
		return (token_id, current)

	current += 1
	while string[current] != "}":
		start_of_advancement = current

		advancement_match = regex["entity_tag_advancement_key"].match(string, current)
		if not advancement_match:
			return (token_id, current)

		elif not do_nested and advancement_match.group(1): # if theres a nested advancement thing in a nested advancement thing that's not good
			return add_region(view, region, current, advancement_match.end(), "invalid.illegal", token_id)

		token_id, _ = add_region(view, region, advancement_match.start(3), advancement_match.end(3), "mcccommand", token_id)
		token_id, _ = add_region(view, region, advancement_match.start(2), advancement_match.end(2), "mccstring", token_id)
		current = advancement_match.end()

		token_id, current = skip_whitespace(view, region, string, advancement_match.end(), token_id, start_of_advancement)
		if current == len(string):
			return (token_id, current)

		if advancement_match.group(1) != None:
			token_id, _ = add_region(view, region, advancement_match.start(1), advancement_match.end(1), "mccliteral", token_id)
			token_id, current = advancement_tag_parser(view, region, string, current, token_id, do_nested=False)
			if string[current - 1] != "}": #This tests to see if the parse was successful
				return (token_id, current)
		else:
			new_token_id, new_current = boolean_parser(view, region, string, current, token_id)
			if new_token_id == token_id:
				return add_region(view, region, start_of_advancement, current, "invalid.illegal", token_id)
			token_id = new_token_id
			current = new_current

		token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_advancement)
		if current == len(string):
			return (token_id, current)

		if string[current] == ",":
			current += 1
		elif string[current] != "}":
			return add_region(view, region, current, current + 1, "invalid.illegal", token_id)

		token_id, current = skip_whitespace(view, region, string, current, token_id, start_of_advancement)
		if current == len(string):
			return (token_id, current)

	current += 1
	return (token_id, current)

def string_parser(view, region, string, current, token_id, properties={}):
	if string[current] != "\"":
		return (token_id, current)
	string_match = regex["string"].match(string, current);
	if string_match:
		return add_region(view, region, current, string_match.end(), "mccstring", token_id)
	return (token_id, current)

def username_parser(view, region, string, current, token_id, properties={}):
	username_match = regex["username"].match(string, current)
	if (username_match):
		return add_region(view, region, current, username_match.end(), "mccstring", token_id)
	return (token_id, current)

def message_parser(view, region, string, current, token_id, properties={}):
	return add_region(view, region, current, len(string), "mccstring", token_id)

def position_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+8] == "position"):
		return add_region(view, region, current, current+8, "mccliteral", token_id)
	return (token_id, current)

def nbt_parser(view, region, string, current, token_id, properties={}):
	if (string[current] != "{"):
		return (token_id, current)
	braces_start = current

	current, token_id = skip_whitespace(view, region, string, current, token_id, braces_start)
	if current == len(string):
		return (current, token_id)

	current += 1
	while string[current] != "}":
		start_of_key = current

		key_match = regex["entity_tag_key"].match(string, current)
		if not key_match:
			return add_region(view, region, braces_start, current, "invalid.illegal", token_id)

		key = key_match.group(1)
		token_id, _ = add_region(view, region, key_match.start(1), key_match.end(1), "mccstring", token_id)
		token_id, current = add_region(view, region, key_match.start(2), key_match.end(2), "mcccommand", token_id)
		current, token_id = skip_whitespace(view, region, string, key_match.end(), token_id, start_of_key)
		if current == len(string):
			return (current, token_id)


		if key in STRING_LIST_TAGS:
			current, token_id = nbt_string_list_parser(view, region, string, current, token_id)
			if (string[current - 1] != ']'):
				return (current, token_id)

		elif key in INTEGER_LIST_TAGS:
			current, token_id = nbt_integer_list_parser(view, region, string, current, token_id)
			if (string[current - 1] != "]"):
				return (current, token_id)

		elif key in DOUBLE_TAGS:

		elif key in FLOAT_LIST_TAGS:
			current, token_id = nbt_float_list_parser(view, region, string, current, token_id)

		elif key in FLOAT_TAGS:

		elif key in LONG_TAGS:

		elif key in SHORT_TAGS:

		elif key in STRING_TAGS:

		elif key in COMPOUND_TAGS:
			current, token_id = nbt_parser(view, region, string, current, token_id)
			if string[current-1] != "}":
				return (current, token_id)

		elif key in BYTE_TAGS:

		elif key in INTEGER_TAGS:

		

	return (token_id, current)

def item_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+4] == "item"):
		return add_region(view, region, current, current+4, "mccstring", token_id)
	return (token_id, current)

def integer_parser(view, region, string, current, token_id, properties={}):
	integer_match = regex["integer"].match(string, current)
	if integer_match:
		value = int(integer_match.group(1))
		if "min" in properties and value < properties["min"] or "max" in properties and value > properties["max"]:
			return add_region(view, region, integer_match.start(1), integer_match.end(1), "invalid.illegal", token_id)
		return add_region(view, region, integer_match.start(1), integer_match.end(1), "mccconstant", token_id)
	return (token_id, current)

def block_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+5] == "block"):
		return add_region(view, region, current, current+5, "mccstring", token_id)
	return (token_id, current)

def nbt_path_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+7] == "nbtpath"):
		return add_region(view, region, current, current+7, "mccstring", token_id)
	return (token_id, current)

def float_parser(view, region, string, current, token_id, properties={}):
	float_match = regex["float"].match(string, current)
	if float_match:
		value = float(float_match.group(1))
		if ("min" in properties and value < properties["min"]) or ("max" in properties and value > properties["max"]):
			return add_region(view, region, float_match.start(1), float_match.end(1), "invalid.illegal", token_id)
		return add_region(view, region, float_match.start(1), float_match.end(1), "mccconstant", token_id)
	return (token_id, current)

def boolean_parser(view, region, string, current, token_id, properties={}):
	if (current + 4 < len(string) and string[current:current+4] == "true"):
		return add_region(view, region, current, current+4, "mccconstant", token_id)
	elif (current + 5 < len(string) and string[current:current+5] == "false"):
		return add_region(view, region, current, current+5, "mccconstant", token_id)
	return (token_id, current)

def axes_parser(view, region, string, current, token_id, properties={}):
	axes = set("xyz")
	axes_match = regex["axes"].match(string, current)
	if axes_match and len(set(axes_match.group(1))) == len(axes_match.group(1)) and axes.issuperset(axes_match.group(1)):
		return add_region(view, region, current, axes_match.end(1), "mccconstant", token_id)
	return (token_id, current)

def scoreHolder_parser(view, region, string, current, token_id, properties={}):
	return entity_parser(view, region, string, current, token_id, properties)

def objective_parser(view, region, string, current, token_id, properties={}):
	objective_match = regex["username"].match(string, current) #Objectives and usernames have the same restrictions on them
	if (objective_match):
		return add_region(view, region, current, objective_match.end(), "mccstring", token_id)
	return (token_id, current)

def vector_3d_parser(view, region, string, current, token_id, properties={}):
	vec3d_match = regex["vec3d"].match(string, current)
	if vec3d_match:
		add_region(view, region, vec3d_match.start(1), vec3d_match.end(1), "mccconstant", token_id)
		add_region(view, region, vec3d_match.start(2), vec3d_match.end(2), "mccconstant", token_id + 1)
		return add_region(view, region, vec3d_match.start(3), vec3d_match.end(3), "mccconstant", token_id + 2)
	return (token_id, current)

def vector_2d_parser(view, region, string, current, token_id, properties={}):
	vec2d_match = regex["vec2d"].match(string, current)
	if vec2d_match:
		add_region(view, region, vec2d_match.start(2), vec2d_match.end(2), "mccconstant", token_id)
		return add_region(view, region, vec2d_match.start(3), vec32d_match.end(3), "mccconstant", token_id + 1)
	return (token_id, current)

def particle_parser(view, region, string, current, token_id, properties={}):
	particle_match = regex["entity_tag"].match(string, current)
	if particle_match and particle.group() in PARTICLES:
		return add_region(view, region, current, particle_match.end(), "mccliteral", token_id)
	return (token_id, current)

def item_slot_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+8] == "itemslot"):
		return add_region(view, region, current, current+8, "mccstring", token_id)
	return (token_id, current)

def scoreboard_slot_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+14] == "scoreboardslot"):
		return add_region(view, region, current, current+14, "mccstring", token_id)
	return (token_id, current)

def team_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+4] == "team"):
		return add_region(view, region, current, current+4, "mccstring", token_id)
	return (token_id, current)

def color_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+5] == "color"):
		return add_region(view, region, current, current+5, "mccconstant", token_id)
	return (token_id, current)

def rotation_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+8] == "rotation"):
		return add_region(view, region, current, current+8, "mccconstant", token_id)
	return (token_id, current)

def json_parser(view, region, string, current, token_id, properties={}):
	if (string[current:current+4] == "json"):
		return add_region(view, region, current, current+4, "mccstring", token_id)
	return (token_id, current)

parsers = { #need to include the properties tag
	"minecraft:resource_location": namespace_parser,
	"minecraft:entity"           : entity_parser,
	"brigadier:string"           : string_parser, #type  = word and type= greedy
	"minecraft:game_profile"     : username_parser,
	"minecraft:message"          : message_parser,
	"minecraft:block_pos"        : position_parser,
	"minecraft:nbt"              : nbt_parser,
	"minecraft:item"             : item_parser,
	"brigadier:integer"          : integer_parser, #Properties has min and max
	"minecraft:block"            : block_parser,
	"minecraft:nbt_path"         : nbt_path_parser,
	"brigadier:float"            : float_parser, #Properties has min and max
	"brigadier:bool"             : boolean_parser,
	"minecraft:swizzle"          : axes_parser, # any cobination of x, y, and z e.g. x, xy, xz. AKA swizzle
	"minecraft:score_holder"     : scoreHolder_parser, #Has options to include wildcard or not
	"minecraft:objective"        : objective_parser,
	"minecraft:vec3"             : vector_3d_parser, #Assuming this doesn't include relative coords?
	"minecraft:vec2"             : vector_2d_parser, #Pretty sure these don't
	"minecraft:particle"         : particle_parser,
	"minecraft:item_slot"        : item_slot_parser, #Check the wiki on this one I guess
	"minecraft:scoreboard_slot"  : scoreboard_slot_parser,
	"minecraft:team"             : team_parser,
	"minecraft:color"            : color_parser,
	"minecraft:rotation"         : rotation_parser, # [yaw, pitch], includes relative changes
	"minecraft:component"        : json_parser #Almost sure this is just JSON
	
}