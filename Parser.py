import sublime, re
from .Blocks import BLOCKS
from .Data import *
from .CommandTree import COMMAND_TREE

class Parser:
	add_regions_flags = sublime.DRAW_NO_OUTLINE
	regex = {
		"vec3d" : re.compile("(\d+(?:\.\d+)?)[ \t\n]+(\d+(?:\.\d+)?)[ \t\n]+(\d+(?:\.\d+)?)"),
		"vec2d" : re.compile("(\d+(?:\.\d+)?)[ \t\n]+(\d+(?:\.\d+)?)"),
		"float" : re.compile("(-?\d+\.\d+)"),
		"integer" : re.compile("(-?\d+)"),
		"namespace" : re.compile("([a-z_\-1-9]+:)([a-z_\-1-9]+(?:\/[a-z_\-1-9]+)*)(\/?)"),
		"string" : re.compile("\w+|\"(?:[^\\\"]|(\\.))*\""),
		"username" : re.compile("\w{3,16}"),
		"axes" : re.compile("([xyz]+)"),
		"integer_range" : re.compile("(?:(\d+)(\.\.))?(\d+)"), #used in entity selectors for the 55..66 type deal (integer only though)
		"float_range" : re.compile("(?:(\d+(?:\.\d+)?)(\.\.))?(\d+(?:\.\d+)?)"), # used in entity selectors for float ranges, similar to previous comment
		"entity_tag" : re.compile("\w+"),
		"entity_tag_key" : re.compile("([a-z]+)\s*(=)"),
		"entity_tag_advancement_key" : re.compile("([a-z_\-1-9]+:)?([a-z]+)\s*(=)"),
		"nbt_key" : re.compile("(\w+)\s*:"),
		"nbt_boolean" : re.compile("[01]"),
		"color" : re.compile("none|black|dark_blue|dark_green|dark_aqua|dark_red|dark_purple|gold|gray|dark_gray|blue|green|aqua|red|light_purple|yellow|white"),
		"scoreboard_slot" : re.compile("belowName|list|sidebar(?:.team.(?:black|dark_blue|dark_green|dark_aqua|dark_red|dark_purple|gold|gray|dark_gray|blue|green|aqua|red|light_purple|yellow|white))?"),
		"item_slot" : re.compile("slot\.(?:container\.\d+|weapon\.(?:main|off)hand|\.(?:enderchest|inventory)\.(?:2[0-6]|1?[0-9])|hotbar.[0-8]|horse\.(?:saddle|chest|armor|1[0-4]|[0-9])|villager\.[0-7])"),
		"gamemode" : re.compile("survival|creative|adventure|spectator"),
		"sort" : re.compile("nearest|furthest|random|arbitrary"),
		"entity" : re.compile("item|xp_orb|area_effect_cloud|leash_knot|painting|item_frame|armor_stand|evocation_fangs|ender_crystal|egg|arrow|snowball|fireball|small_fireball|ender_pearl|eye_of_ender_signal|potion|xp_bottle|wither_skull|fireworks_rocket|spectral_arrow|shulker_bullet|dragon_fireball|llama_spit|tnt|falling_block|commandblock_minecart|boat|minecart|chest_minecart|furnace_minecart|tnt_minecart|hopper_minecart|spawner_minecart|elder_guardian|wither_skeleton|stray|husk|zombie_villager|evocation_illager|vex|vindication_illager|illusion_illager|creeper|skeleton|spider|giant|zombie|slime|ghast|zombie_pigman|enderman|cave_spider|silverfish|blaze|magma_cube|ender_dragon|wither|witch|endermite|guardian|shulker|skeleton_horse|zombie_horse|donkey|mule|bat|pig|sheep|cow|chicken|squid|wolf|mooshroom|snowman|ocelot|villager_golem|horse|rabbit|polar_bear|llama|parrot|villager|player|lightning_bolt"),
		"comment" :  re.compile('^\s*#.*$'),
		"command" : re.compile('\s*(/?)([a-z]+)')
	}

	def __init__(self, view):
		self.current = 0
		self.token_id = 0
		self.view = view

	# start is inclusive while end is exclusive, like string slices
	# Updates token_id
	def add_region(self, start, end, scope):
		new_region = sublime.Region(self.region.begin() + start, self.region.begin() + end)
		self.view.add_regions("token" + str(self.token_id), [new_region], scope, flags=self.add_regions_flags)
		self.token_id += 1
		return end

	def highlight(self, command_tree, line_region, current):
		self.current = current
		if ("redirect" in command_tree):
			redirect_command = command_tree["redirect"][0]
			if redirect_command == "root":
				new_command_tree = COMMAND_TREE
			else:
				new_command_tree = COMMAND_TREE["children"][redirect_command]
			print("Redirecting to: " + redirect_command + ", " + str(self.current))
			return self.highlight(new_command_tree, line_region, self.current)
		elif not "children" in command_tree or self.current >= line_region.size():
			if not "executable" in command_tree or not command_tree["executable"]:
				self.current = self.add_region(0,  line_region.size(), "invalid.illegal")
			return self.token_id

		self.string = self.view.substr(line_region)
		self.region = line_region
		if self.regex["comment"].match(self.string):
			self.add_region(0,  line_region.size(), "mcccomment")
			return self.token_id
		elif command_tree["type"] == "root":
			command_match = self.regex["command"].search(self.string, self.current)
			if not command_match:
				return self.token_id
			command = command_match.group(2)
			#print("command: " + command)
			if command in command_tree["children"]:
				self.add_region(command_match.start(1), command_match.end(1), "invalid.illegal")
				self.current = self.add_region(command_match.start(2), command_match.end(2), "mcccommand")
				return self.highlight(command_tree["children"][command], line_region, command_match.end())
			else:
				self.add_region(0,  line_region.size(), "invalid.illegal")
				return self.token_id
		else:
			while (self.current < len(self.string) and self.string[self.current] in " \t\n"):
				self.current += 1

			if (self.current >= len(self.string)):
				self.add_region(0,  line_region.size(), "invalid.illegal")
				return self.token_id

			command_tree = command_tree["children"]
			#print(command_tree)
			for key, properties in command_tree.items():
				#print("Key: " + key)
				if properties["type"] == "literal" and self.current + len(key) <= len(self.string) and self.string[self.current:self.current + len(key)] == key:
					#print("String segment: " + self.string[self.current:self.current + len(key)])
					self.current = self.add_region(self.current, self.current + len(key), "mccliteral")
					return self.highlight(properties, line_region, self.current)
				elif properties["type"] == "argument":
					parser_name = properties["parser"]
					parse_function = self.parsers[parser_name]
					old_current = self.current
					if "properties" in properties:
						#print("using properties for " + parser_name)
						self.current = parse_function(self, properties["properties"])
					else:
						self.current = parse_function(self)

					if old_current != self.current:
						return self.highlight(properties, line_region, self.current)

			print("Went thrugh all options ")
			#self.add_region(0,  line_region.size(), "invalid.illegal")
			return self.token_id

	# Returns True if the end of the string is reached, else False and will advacne self.current to the next non-whitespace character
	# this will error highlight the section from err_start until the end of the string
	def skip_whitespace(self, err_start):
		if self.current >= len(self.string):
			self.current = self.add_region(err_start, self.current, "invalid.illegal")
			return True
		while self.string[self.current] in " \n\t":
			self.current += 1
			if self.current >= len(self.string):
				print("Adding error region: " + self.string[err_start:self.current])
				self.current = self.add_region(err_start, self.current, "invalid.illegal")
				return True
		return False

	def namespace_parser(self, properties={}): #all parsers return (token_id, newStart)
		namespace_match = self.regex["namespace"].match(self.string, current)
		if namespace_match:
			self.add_region(namespace_match.start(1), namespace_match.end(1), "mccstring")
			self.current = add_region(namespace_match.start(2), namespace_match.end(2), "mccliteral")
			if namespace_match.start(3) > -1:
				return self.add_region(namespace_match.start(3), namespace_match.end(3), "invalid.illegal",token_id)
		return self.current

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
	def entity_parser(self, properties={}):
		if self.string[self.current] == "*" and "has_wildcard" in properties and properties["has_wildcard"]:
			return self.add_region(self.current, self.current+1, "mccentity")

		if self.string[self.current] != "@" or (self.current + 1 < len(self.string) and not self.string[self.current+1] in "pears"): #Checks to see if it's a valid entity selector
			return self.current

		self.current = self.add_region(self.current, self.current + 2, "mccentity")
		if (self.current < len(self.string) and self.string[self.current] == "["):
			self.current = self.add_region(self.current, self.current + 1, "mccentity")
			bracket_start = self.current

			while (self.string[self.current] != "]"):
				reached_end = self.skip_whitespace(bracket_start)
				if reached_end:
					return self.current
				
				start_of_key = self.current
				key_match = self.regex["entity_tag_key"].match(self.string, self.current)
				if not key_match:
					return self.current

				key = key_match.group(1)
				self.current = self.add_region(key_match.start(2), key_match.end(2), "mcccommand") #the command scope is used here because that's the legacy highlghting of '='
				self.add_region(key_match.start(1), key_match.end(1), "mccstring")
				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if key == "level":
					int_range_match = self.regex["integer_range"].match(self.string, self.current)
					if not int_range_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.add_region(int_range_match.start(1), int_range_match.end(1), "mccconstant")
					self.add_region(int_range_match.start(2), int_range_match.end(2), "mcccommand")
					self.current = self.add_region(int_range_match.start(3), int_range_match.end(3), "mccconstant")

				elif key in ["x", "y", "z", "x_rotation", "y_rotation", "distance", "dx", "dy", "dz"]:
					float_range_match = self.regex["float_range"].match(self.string, self.current)
					if not float_range_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.add_region(float_range_match.start(1), float_range_match.end(1), "mccconstant")
					self.add_region(float_range_match.start(2), float_range_match.end(2), "mcccommand")
					self.current = self.add_region(float_range_match.start(3), float_range_match.end(3), "mccconstant")

				elif key == "tag":
					if self.string[self.current] == "!":
						self.add_region(self.current, self.current + 1, "mcccommand") #Similar deal to the '=' earlier
						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current


					tag_value_match = self.regex["entity_tag"].match(self.string, self.current)
					if not tag_value_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.current = self.add_region(tag_value_match.start(), tag_value_match.end(), "mccstring")

				elif key == "gamemode":
					if self.string[self.current] == "!":
						self.current = self.add_region(self.current, self.current+1, "mcccommand") #Similar deal to the '=' earlier
						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

					gamemode_match = self.regex["gamemode"].match(self.string, self.current)
					if not gamemode_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.current = self.add_region(gamemode_match.start(), gamemode_match.end(), "mccliteral")

				elif key == "sort":
					sort_match = self.regex["sort"].match(self.string, self.current)
					if not sort_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.current = self.add_region(sort_match.start(), entity_match.end(), "mccliteral")

				elif key == "type":
					if self.string[self.current] == "!":
						self.current = self.add_region(self.current, self.current + 1, "mcccommand") #Similar deal to the '=' earlier
						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

					entity_match = self.regex["entity"].match(self.string, self.current)
					if not entity_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.current = self.add_region(entity_match.start(), entity_match.end(), "mccliteral")

				elif key == "team":
					if self.string[self.current] == "!":
						self.current = self.add_region(self.current, self.current + 1, "mcccommand") #Similar deal to the '=' earlier
						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

					team_match = self.regex["username"].match(self.string, self.current)
					if team_match:
						self.current = self.add_region(team_match.start(), team_match.end(), "mccstring")

				elif key == "name":
					if self.string[self.current] == "!":
						self.current = self.add_region(self.current, self.current + 1, "mcccommand") #Similar deal to the '=' earlier
						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

					tag_value_match = self.regex["string"].match(self.string, self.current)

					if not tag_value_match:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.current = self.add_region(tag_value_match.start(), tag_value_match.end(), "mccstring")

				elif key == "scores":
					if self.string[self.current] != "{":
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					score_bracket_start = self.current
					self.current += 1

					while self.string[self.current] != "}":
						reached_end = self.skip_whitespace(score_bracket_start)
						if reached_end:
							return self.current
						start_of_score = self.current

						score_match = self.regex["entity_tag_key"].match(self.string, self.current)
						if not score_match:
							return self.current

						self.add_region(score_match.start(2), score_match.end(2), "mcccommand")
						self.add_region(score_match.start(1), score_match.end(1), "mccstring")
						self.current = score_match.end()

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

						int_range_match = self.regex["integer_range"].match(self.string, self.current)
						if not int_range_match:
							return self.add_region(start_of_score, self.current, "invalid.illegal")
						self.add_region(int_range_match.start(1), int_range_match.end(1), "mccconstant")
						self.add_region(int_range_match.start(2), int_range_match.end(2), "mcccommand")
						self.current = self.add_region(int_range_match.start(3), int_range_match.end(3), "mccconstant")

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

						if self.string[self.current] == ",":
							self.current += 1
						elif self.string[self.current] != "}":
							return self.add_region(self.current, self.current + 1, "invalid.illegal")

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

					self.current += 1

				elif key == "advancements":
					self.current = self.advancement_tag_parser(self.string)
					if self.string[self.current - 1] != "}": #Make sure the parse was good
						return self.current

				else:
					return self.add_region(start_of_key, self.current, "invalid.illegal")

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if self.string[self.current] == ",":
					self.current += 1
				elif self.string[self.current] != "]":
					return self.add_region(self.current, self.current + 1, "invalid.illegal")

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

			return self.add_region(self.current, self.current + 1, "mccentity")

		return self.current

	def advancement_tag_parser(self, do_nested=True):
		if self.string[self.current] != "{":
			return self.add_region(start_of_key, self.current, "invalid.illegal")
		bracket_start = self.current
		self.current += 1

		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(bracket_start)
			if reached_end:
				return self.current

			start_of_advancement = self.current
			advancement_match = self.regex["entity_tag_advancement_key"].match(self.string, self.current)
			if not advancement_match:
				return self.current

			elif not do_nested and advancement_match.group(1): # if theres a nested advancement thing in a nested advancement thing that's not good
				return self.add_region(self.current, advancement_match.end(), "invalid.illegal")

			self.add_region(advancement_match.start(3), advancement_match.end(3), "mcccommand")
			self.add_region(advancement_match.start(2), advancement_match.end(2), "mccstring")
			self.current = advancement_match.end()

			reached_end = self.skip_whitespace(start_of_advancement)
			if reached_end:
				return self.current

			if advancement_match.group(1) != None:
				self.add_region(advancement_match.start(1), advancement_match.end(1), "mccliteral")
				self.current = self.advancement_tag_parser(do_nested=False)
				if self.string[self.current - 1] != "}": #This tests to see if the parse was successful
					return self.current
			else:
				new_current = self.boolean_parser(self.string)
				if new_current == self.current:
					return self.add_region(start_of_advancement, self.current, "invalid.illegal")
				self.current = new_current

			reached_end = self.skip_whitespace(start_of_advancement)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")

			reached_end = self.skip_whitespace(start_of_advancement)
			if reached_end:
				return self.current

		self.current += 1
		return self.current

	# Word means "up to the next space", phrase is "an unquoted word or quoted string", and greedy is "everything from this point to the end of input".
	# strict means only a regular quote enclosed string will work
	def string_parser(self, properties={}):
		if string[self.current] != "\"":
			return self.current
		string_match = self.regex["string"].match(self.string, self.current);
		if not string_match:
			return self.add_region(self.current, string_match.end(), "mccstring")
		return self.current

	def username_parser(self, properties={}):
		username_match = self.regex["username"].match(self.string, self.current)
		if username_match:
			return self.add_region(self.current, username_match.end(), "mccstring")
		return self.current

	# Todo: add entity highlighting
	def message_parser(self, properties={}):
		newline_index = self.string.find("\n", self.current)
		if newline_index < 0:
			return self.add_region(self.current, len(self.string), "mccstring")
		else:
			return self.add_region(self.current, newline_index, "mccstring")

	def position_parser(self, properties={}):
		if (self.string[self.current:self.current+8] == "position"):
			return self.add_region(self.current, self.current + 8, "mccliteral")
		return self.current

	def nbt_parser(self, properties={}):
		if (self.string[self.current] != "{"):
			return self.current
		elif not "escape_depth" in properties:
			properties["escape_depth"] = 0

		braces_start = self.current
		self.current += 1

		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(braces_start)
			if reached_end:
				return self.current

			start_of_key = self.current

			key_match = self.regex["nbt_key"].match(self.string, self.current)
			if not key_match:
				return self.add_region(braces_start, self.current, "invalid.illegal")

			key = key_match.group(1)
			self.add_region(key_match.start(1), key_match.end(1), "mccstring")
			self.current = key_match.end()
			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current


			if key in NBT_STRING_LIST_TAGS:
				self.current = self.nbt_list_parser(self.regex["string"], "mccstring", "")
				if (self.string[self.current - 1] != ']'):
					return self.current

			elif key in NBT_INTEGER_LIST_TAGS:
				self.current = self.nbt_list_parser(self.regex["integer"], "mccconstant", "")
				if (self.string[self.current - 1] != "]"):
					return self.current

			elif key in NBT_DOUBLE_TAGS:
				new_current = self.nbt_value_parser(self.regex["float"], "mccconstant", "d")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current= new_current

			elif key in NBT_FLOAT_LIST_TAGS:
				self.current = self.nbt_list_parser(self.regex["float"], "mccconstant", "f")
				if (self.string[self.current-1] != "]"):
					return self.current

			elif key in NBT_FLOAT_TAGS:
				new_current = self.nbt_value_parser(self.regex["float"], "mccconstant", "f")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_LONG_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "L")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_SHORT_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "s")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_STRING_TAGS:
				new_current = self.nbt_value_parser(self.regex["string"], "mccstring", "")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_COMPOUND_TAGS:
				self.current= self.nbt_parser(self.string)
				if self.string[self.current-1] != "}":
					return self.current

			elif key in NBT_BYTE_TAGS:
				new_current = self.nbt_value_parser(self.regex["nbt_boolean"], "mccconstant", "b")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_INTEGER_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "")
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			else:
				return self.add_region(start_of_key, self.current, "invalid.illegal")

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")
		self.current += 1
		return self.current

	def nbt_list_parser(self, item_regex, item_scope, item_suffix):
		if self.string[self.current] != "[":
			return self.current
		start_of_list = self.current
		self.current += 1

		while self.string[self.current] != "]":

			reached_end = self.skip_whitespace(start_of_list)
			if reached_end:
				return self.current
			
			start_of_value = self.current

			new_current = self.nbt_value_parser(item_regex, item_scope, item_suffix)
			if new_current == self.current:
				return self.add_region(start_of_list, self.current, "invalid.illegal")
			self.current = new_current

			reached_end = self.skip_whitespace(start_of_value)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "]":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")

		self.current += 1
		return self.current


	def nbt_value_parser(self, value_regex, scope, suffix):
		value_match = value_regex.match(self.string, self.current)
		if value_match:
			end = value_match.end()
			if end + len(suffix) <= len(self.string) and self.string[end : end + len(suffix)] == suffix:
				end += len(suffix)
			elif end < len(self.string) and not self.string[end:end+1] in " \t,]}":
				return self.current
			return self.add_region(value_match.start(), end, scope)
		return self.current

	def item_parser(self, properties={}):
		if (self.string[self.current:self.current+4] == "item"):
			return self.add_region(self.current, self.current+4, "mccstring")
		return self.current

	def integer_parser(self, properties={}):
		integer_match = self.regex["integer"].match(self.string, self.current)
		if integer_match:
			value = int(integer_match.group(1))
			if "min" in properties and value < properties["min"] or "max" in properties and value > properties["max"]:
				return self.add_region(integer_match.start(1), integer_match.end(1), "invalid.illegal")
			return self.add_region(integer_match.start(1), integer_match.end(1), "mccconstant")
		return self.current

	def block_parser(self, properties={}):
		if (self.string[self.current:self.current+5] == "block"):
			return self.add_region(self.current, self.current + 5, "mccstring")
		return self.current

	def nbt_path_parser(self, properties={}):
		if (self.string[self.current:self.current+7] == "nbtpath"):
			return self.add_region(self.current, self.current + 7, "mccstring")
		return self.current

	def float_parser(self, properties={}):
		float_match = self.regex["float"].match(self.string, self.current)
		if float_match:
			value = float(float_match.group(1))
			if ("min" in properties and value < properties["min"]) or ("max" in properties and value > properties["max"]):
				return self.add_region(float_match.start(1), float_match.end(1), "invalid.illegal")
			return self.add_region(float_match.start(1), float_match.end(1), "mccconstant")
		return self.current

	def boolean_parser(self, properties={}):
		if (self.current + 4 < len(self.string) and self.string[self.current:self.current+4] == "true"):
			return self.add_region(self.current, self.current + 4, "mccconstant")

		elif (self.current + 5 < len(self.string) and self.string[self.current:self.current + 5] == "false"):
			return self.add_region(self.current, self.current + 5, "mccconstant")

		return self.current

	def axes_parser(self, properties={}):
		axes = set("xyz")
		axes_match = self.regex["axes"].match(self.string, self.current)
		if axes_match and len(set(axes_match.group(1))) == len(axes_match.group(1)) and axes.issuperset(axes_match.group(1)):
			return self.add_region(self.current, axes_match.end(1), "mccconstant")
		return self.current

	def scoreHolder_parser(self, properties={}):
		new_current = self.username_parser(properties)
		if new_current != self.current:
			return new_current
		return self.entity_parser(properties)

	def objective_parser(self, properties={}):
		return self.username_parser(properties)

	def vector_3d_parser(self, properties={}):
		vec3d_match = self.regex["vec3d"].match(self.string, self.current)
		if vec3d_match:
			self.add_region(vec3d_match.start(1), vec3d_match.end(1), "mccconstant")
			self.add_region(vec3d_match.start(2), vec3d_match.end(2), "mccconstant")
			return self.add_region(vec3d_match.start(3), vec3d_match.end(3), "mccconstant")
		return self.current

	def vector_2d_parser(self, properties={}):
		vec2d_match = self.regex["vec2d"].match(self.string, self.current)
		if vec2d_match:
			self.add_region(vec2d_match.start(1), vec2d_match.end(1), "mccconstant")
			return self.add_region(vec2d_match.start(2), vec2d_match.end(2), "mccconstant")
		return self.current

	def particle_parser(self, properties={}):
		particle_match = self.regex["entity_tag"].match(self.string, self.current)
		if particle_match and particle.group() in PARTICLES:
			return self.add_region(self.current, particle_match.end(), "mccliteral")
		return self.current

	def item_slot_parser(self, properties={}):
		item_slot_match = self.regex["item_slot"].match(self.string, self.current)
		if item_slot_match:
			return self.add_region(item_slot_match.start(), item_slot_match.end(), "mccstring")
		return self.current

	def scoreboard_slot_parser(self, properties={}):
		slot_match = self.regex["scoreboard_slot"]
		if slot_match:
			return self.add_region(slot_match.start(), slot_match.end(), "mccstring")
		return self.current

	def team_parser(self, properties={}):
		return self.username_parser(properties)

	def color_parser(self, properties={}):
		color_match = self.regex["color"].match(self.string, self.current)
		if color_match:
			return self.add_region(color_match.start(), color_match.end(), "mccconstant")
		return self.current

	def rotation_parser(self, properties={}):
		if (self.string[self.current:self.current+8] == "rotation"):
			return self.add_region(self.current, self.current + 8, "mccconstant")
		return self.current

	# https://www.json.org/
	def json_parser(self, properties={}):
		if not "escape_depth" in properties:
			properties[escape_depth] = 0

		if self.string[self.current] == "[":
			return self.json_array_parser(properties)
		elif self.string[self.current]  == "{":
			return self.json_object_parser(properties)

		return self.current

	def json_object_parser(self, properties={}):# The '{}' one
		if self.string[self.current] != "{":
			return self.current
		quote = generate_quote(properties["escape_depth"])
		start_of_object = self.current
		self.current += 1


		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				return self.add_region(start_of_object, self.current, "invalid.illegal")

			# " \" \\\" \\\\\\\" ...
			# 1 2  4    8        ...
			key = string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_json)
			if reached_end:
				return self.current

			if not self.string[self.current] in ",:":
				return self.add_region(self.current, self.current + 1, "invalid.illega")

			elif self.string[self.current] == ":":
				self.current += 1
				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if key in JSON_STRING_KEYS:
					start_of_value = self.current
					self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
					if start_of_key == self.current:
						return self.add_region(start_of_value, self.current, "invalid.illegal")

				elif key in JSON_ENTITY_KEYS:
					start_of_string = self.current
					if not self.current + len(quote) < len(self.string) or not self.string[self.current : self.current + len(quote)] == quote:
						return self.current
					self.current = self.add_region(self.current, self.current + len(quote), "mccstring")
				
					new_current = self.entity_parser(properties)
					if new_current == self.current:
						return self.add_region(start_of_string, self.current, "invalid.illegal")
					self.current = new_current

					if not self.current + len(quote) < len(self.string) or not self.string[self.current : self.current + len(quote)] == quote:
						return self.add_region(start_of_string, self.current, "invalid.illegal")
					self.current = self.add_region(self.current, self.current + len(quote), "mccstring")

				elif key in JSON_BOOLEAN_KEYS:
					new_current = boolean_parser(properties)
					if self.current == new_current:
						return self.add_region(start_of_key, self.current, "invalid.illegal")
					self.currrent = new_current

				elif key in JSON_NESTED_KEYS:
					self.current = self.json_parser(properties)
					if not self.string[self.current - 1] in "}]":
						return self.current

				elif key == "color":
					start_of_string = self.current
					if not self.current + len(quote) < len(self.string) or not self.string[self.current : self.current + len(quote)] == quote:
						return self.current
					self.current = self.add_region(self.current, self.current + len(quote), "mccstring")
				
					new_current = self.color_parser(properties)
					if new_current == self.current:
						return self.add_region(start_of_string, self.current, "invalid.illegal")
					self.current = new_current

					if not self.current + len(quote) < len(self.string) or not self.string[self.current : self.current + len(quote)] == quote:
						return self.add_region(start_of_string, self.current, "invalid.illegal")
					self.current = self.add_region(self.current, self.current + len(quote), "mccstring")

				elif key == "hoverEvent":
					self.current = self.json_hover_event_parser(properties)
					if not self.string[self.current - 1] in "}":
						return self.current

				elif key == "clickEvent":
					self.current = self.json_click_event_parser(properties)
					if not self.string[self.current - 1] in "}":
						return self.current

				elif key == "score":
					self.current = self.json_score_parser(properties)
					if not self.string[self.current - 1] in "}":
						return self.current

				else:
					return self.add_region(start_of_key, self.current, "invalid.illegal")

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1

			elif self.string[self.current] != "}":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")
		self.current += 1
		return self.current

	def json_array_parser(self, properties={}): # The '[]' one
		start_of_list = self.current
		self.current += 1

		while self.string[self.current] != "]":
			reached_end = self.skip_whitespace(start_of_array)
			if reached_end:
				return self.current

			start_of_value = self.current

			match_made = False
			new_current = self.string_parser(properties={"type":"strict", "escape_depth":properties["escape_depth"]})
			if new_current != self.current:
				match_made = True
				self.current = new_current

			new_current = self.float_parser(properties)
			if not match_made and new_current != self.current:
				match_made = True
				self.current = new_current

			new_current = self.json_parser(properties)
			if not match_made and new_current != self.current:
				match_made = True
				self.current = new_current

			new_current = self.boolean_parser(properties)
			if not match_made and new_current != self.current:
				match_made = True
				self.current = new_current

			if self.current + 4 < len(self.string) and self.string[self.current : self.current + 4] == "null":
				match_made = True
				self.current = self.add_region(self.current, self.current + 4, "mccconstant")

			if not match_made:
				return self.current

			reached_end = self.skip_whitespace(start_of_value)
			if reached_end:
				return self.current
			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "]":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")

		self.current += 1
		return self.current

	def json_hover_event_parser(self, properties={}):
		if self.string[self.current] != "{": #Can't be [] since its an object
			return self.current
		current += 1
		quote = generate_quote(properties["escape_depth"])

		start_of_object = self.current
		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				return self.add_region(start_of_object, self.current, "invalid.illegal")

			key = string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")
			self.current += 1

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if key == "action":

			elif key == "value":

			else:
				return self.add_region(start_of_key, self.current, "invalid.illegal")


		return self.current

	def json_click_event_parser(self, properties={}):
		return self.current

	def json_score_parser(self, properties={}):
		return self.current

	@staticmethod
	def generate_quote(escape_depth):
		if escape_depth == 0:
			return "\""
		else:
			quote = "\""
		for i in range(0, escape_depth):
			quote += "\\"
		return quote + generate_quote(escape_depth - 1)

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