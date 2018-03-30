import sublime, re
from .Blocks import BLOCKS
from .Data import *
from .CommandTree import COMMAND_TREE

class Parser:
	add_regions_flags = sublime.DRAW_NO_OUTLINE
	regex = {
		"position-2" : re.compile("(~?-?\d*\.?\d+|~)[\t ]+(~?-?\d*\.?\d+|~)"),
		"float" : re.compile("(-?\d+(?:\.\d+)?)"),
		"integer" : re.compile("(-?\d+)"),
		"namespace" : re.compile("([a-z_\-1-9]+:)([a-z_\-1-9]+(?:\/[a-z_\-1-9]+)*)(\/?)"),
		"word_string" : re.compile("\w+|\"(?:[^\\\\\"]|(\\\\.))*\""),
		"username" : re.compile("\w{3,16}"),
		"axes" : re.compile("([xyz]+)"),
		"entity_tag" : re.compile("\w+"),
		"entity_tag_key" : re.compile("(\w+)[\t ]*(=)"),
		"entity_tag_advancement_key" : re.compile("([a-z_\-1-9]+:)?([a-z]+)[\t ]*(=)"),
		"nbt_key" : re.compile("(\w+)[\t ]*:"),
		"nbt_boolean" : re.compile("[01]"),
		"color" : re.compile("none|black|dark_blue|dark_green|dark_aqua|dark_red|dark_purple|gold|gray|dark_gray|blue|green|aqua|red|light_purple|yellow|white"),
		"scoreboard_slot" : re.compile("belowName|list|sidebar(?:.team.(?:black|dark_blue|dark_green|dark_aqua|dark_red|dark_purple|gold|gray|dark_gray|blue|green|aqua|red|light_purple|yellow|white))?"),
		"item_slot" : re.compile("slot\.(?:container\.\d+|weapon\.(?:main|off)hand|\.(?:enderchest|inventory)\.(?:2[0-6]|1?[0-9])|hotbar.[0-8]|horse\.(?:saddle|chest|armor|1[0-4]|[0-9])|villager\.[0-7])"),
		"gamemode" : re.compile("survival|creative|adventure|spectator"),
		"sort" : re.compile("nearest|furthest|random|arbitrary"),
		"entity" : re.compile("(minecraft:)?(item|xp_orb|area_effect_cloud|leash_knot|painting|item_frame|armor_stand|evocation_fangs|ender_crystal|egg|arrow|snowball|fireball|small_fireball|ender_pearl|eye_of_ender_signal|potion|xp_bottle|wither_skull|fireworks_rocket|spectral_arrow|shulker_bullet|dragon_fireball|llama_spit|tnt|falling_block|commandblock_minecart|boat|minecart|chest_minecart|furnace_minecart|tnt_minecart|hopper_minecart|spawner_minecart|elder_guardian|wither_skeleton|stray|husk|zombie_villager|evocation_illager|vex|vindication_illager|illusion_illager|creeper|skeleton|spider|giant|zombie|slime|ghast|zombie_pigman|enderman|cave_spider|silverfish|blaze|magma_cube|ender_dragon|wither|witch|endermite|guardian|shulker|skeleton_horse|zombie_horse|donkey|mule|bat|pig|sheep|cow|chicken|squid|wolf|mooshroom|snowman|ocelot|villager_golem|horse|rabbit|polar_bear|llama|parrot|villager|player|lightning_bolt)"),
		"comment" :  re.compile('^[\t ]*#.*$'),
		"command" : re.compile('[\t ]*(/?)([a-z]+)'),
		"hover_event_action" : re.compile("show_(?:text|item|entity|achievement)"),
		"click_event_action": re.compile("(?:run|suggest)_command|open_url|change_page"),
		"item_block_id" : re.compile("([a-z_]+:)?([a-z_]+)"),
		"position-3" : re.compile("([~\^]?-?\d*\.?\d+|[~\^])[\t ]+([~\^]?-?\d*\.?\d+|[~\^])[\t ]+([~\^]?-?\d*\.?\d+|[~\^])"),
		"strict_string" : re.compile("\"(?:[^\\\\\"]|(\\\\.))*\""),
		"greedy_string" : re.compile("[^\n]*"),
		"operation" : re.compile("[+\-\*\%\/]?=|>?<|>"),
		"entity_anchor" : re.compile("feet|eyes")
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
			#print("Redirecting to: " + redirect_command + ", " + str(self.current))
			return self.highlight(new_command_tree, line_region, self.current)
		elif not "children" in command_tree or self.current >= line_region.size():
			if not "executable" in command_tree or not command_tree["executable"]:
				#print("command not exectuable")
				self.current = self.add_region(0,  line_region.size(), "invalid.illegal")
				return (self.token_id, False)
			else:
				while (self.current < len(self.string) and self.string[self.current] in " \t"):
					self.current += 1
				newline_index = self.string.find("\n", self.current)
				if newline_index > self.current:
					self.current = self.add_region(self.current, newline_index, "invalid.illegal")
					return (self.token_id, False)
				elif self.current < len(self.string):
					self.current = self.add_region(self.current, line_region.size(), "invalid.illegal")
					return (self.token_id, False)
				return (self.token_id, True)

		self.string = self.view.substr(line_region)
		self.region = line_region
		if self.regex["comment"].match(self.string):
			self.add_region(0,  line_region.size(), "mcccomment")
			return (self.token_id, True)
		elif command_tree["type"] == "root":
			command_match = self.regex["command"].search(self.string, self.current)
			if not command_match:
				return (self.token_id, False)
			command = command_match.group(2)
			#print("command: " + command)
			if command in command_tree["children"]:
				self.add_region(command_match.start(1), command_match.end(1), "invalid.illegal")
				self.current = self.add_region(command_match.start(2), command_match.end(2), "mcccommand")
				return self.highlight(command_tree["children"][command], line_region, command_match.end())
			else:				
				self.add_region(self.current,  line_region.size(), "invalid.illegal")
				return (self.token_id, False)
		else:
			while (self.current < len(self.string) and self.string[self.current] in " \t\n"):
				self.current += 1

			if self.current >= len(self.string):
				if not "executable" in command_tree or not command_tree["executable"]:
					return (self.token_id, False)
				else:
					return (self.token_id, True)				

			#print(command_tree)
			start = self.current
			old_token_id = self.token_id
			for key, properties in command_tree["children"].items():
				#print("Key: " + key)
				if properties["type"] == "literal" and self.current + len(key) <= len(self.string) and self.string[self.current:self.current + len(key)] == key:
					#print("String segment: " + self.string[self.current:self.current + len(key)])
					self.current = self.add_region(self.current, self.current + len(key), "mccliteral")
					self.token_id, success = self.highlight(properties, line_region, self.current)
					if success:
						return (self.token_id, True)
					else:
						self.current = start
						self.token_id = old_token_id
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
						self.token_id, success = self.highlight(properties, line_region, self.current)
						if success:
							return (self.token_id, True)
						else:
							self.current = start
							self.token_id = old_token_id

			self.add_region(self.current,  line_region.size(), "invalid.illegal")
			return (self.token_id, False)
			
	# Returns True if the end of the string is reached, else False and will advacne self.current to the next non-whitespace character
	# this will error highlight the section from err_start until the end of the string
	def skip_whitespace(self, err_start):
		if self.current >= len(self.string):
			self.current = self.add_region(err_start, self.current, "invalid.illegal")
			return True
		while self.string[self.current] in " \n\t":
			self.current += 1
			if self.current >= len(self.string):
				self.current = self.add_region(err_start, self.current, "invalid.illegal")
				return True
		return False

	def namespace_parser(self, properties={}): #all parsers return (token_id, newStart)
		namespace_match = self.regex["namespace"].match(self.string, self.current)
		if namespace_match:
			self.add_region(namespace_match.start(1), namespace_match.end(1), "mccstring")
			self.current = self.add_region(namespace_match.start(2), namespace_match.end(2), "mccliteral")
			if namespace_match.start(3) > -1:
				return self.add_region(namespace_match.start(3), namespace_match.end(3), "invalid.illegal")
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
		if self.current > len(self.string):
			return self.current
		if self.string[self.current] == "*" and "amount" in properties and properties["amount"] == "multiple":
			return self.add_region(self.current, self.current+1, "mccentity")

		if self.string[self.current] != "@" or (self.current + 1 < len(self.string) and not self.string[self.current+1] in "pears"): #Checks to see if it's a valid entity selector
			return self.current

		self.current = self.add_region(self.current, self.current + 2, "mccentity")
		if (self.current < len(self.string) and self.string[self.current] == "["):
			self.current = self.add_region(self.current, self.current + 1, "mccentity")
			bracket_start = self.current

			while self.current < len(self.string) and self.string[self.current] != "]":
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
					self.current = self.range_parser(self.integer_parser, start_of_key)

				elif key == "limit":
					old_current = self.current
					self.current = self.integer_parser(properties={"min":0})
					if old_current == self.current:
						return self.current

				elif key in ["x", "y", "z", "x_rotation", "y_rotation", "distance", "dx", "dy", "dz"]:
					self.current = self.range_parser(self.float_parser, start_of_key)

				elif key == "tag":
					if self.string[self.current] == "!":
						self.current = self.add_region(self.current, self.current + 1, "mcccommand") #Similar deal to the '=' earlier
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
					self.current = self.add_region(sort_match.start(), sort_match.end(), "mccliteral")

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

					tag_value_match = self.regex["word_string"].match(self.string, self.current)

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

						self.current = self.range_parser(self.integer_parser, start_of_score)

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

	def brigadier_range_parser(self, properties={}):
		if properties["decimals"]:
			return self.range_parser(self.float_parser, self.current, properties)
		else:
			return self.range_parser(self.integer_parser, self.current, properties)

	def range_parser(self, parse_function, key_start, properties={}):
		matched = False
		old_current = self.current
		self.current = parse_function(properties)
		if old_current != self.current:
			matched = True

		if self.current + 2 <= len(self.string) and self.string[self.current:self.current + 2] == "..":
			self.current = self.add_region(self.current, self.current + 2, "mcccommand")

		old_current = self.current
		self.current = parse_function(properties)
		if old_current != self.current:
			matched = True

		if not matched:
			return self.add_region(key_start, self.current, "invalid.illegal")
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
		if properties["type"] == "word":
			string_match = self.regex["word_string"].match(self.string, self.current)
		elif properties["type"] == "greedy":
			string_match = self.regex["greedy_string"].match(self.string, self.current)
		elif properties["type"] == "strict":
			string_match = self.regex["strict_string"].match(self.string, self.current)

		if string_match:
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
		position_match = self.regex["position-3"].match(self.string, self.current)
		if position_match:
			self.add_region(position_match.start(1), position_match.end(1), "mccconstant")
			self.add_region(position_match.start(2), position_match.end(2), "mccconstant")
			return self.add_region(position_match.start(3), position_match.end(3), "mccconstant")
		return self.current

	def nbt_parser(self, properties={}):
		if self.current >= len(self.string) or self.string[self.current] != "{":
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
				self.current = self.nbt_list_parser(self.regex["word_string"], "mccstring", "", properties)
				if (self.string[self.current - 1] != ']'):
					return self.current

			elif key in NBT_INTEGER_LIST_TAGS:
				self.current = self.nbt_list_parser(self.regex["integer"], "mccconstant", "", properties)
				if (self.string[self.current - 1] != "]"):
					return self.current

			elif key in NBT_DOUBLE_TAGS:
				new_current = self.nbt_value_parser(self.regex["float"], "mccconstant", "d", properties)
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current= new_current

			elif key in NBT_FLOAT_LIST_TAGS:
				self.current = self.nbt_list_parser(self.regex["float"], "mccconstant", "f", properties)
				if (self.string[self.current-1] != "]"):
					return self.current

			elif key in NBT_FLOAT_TAGS:
				new_current = self.nbt_value_parser(self.regex["float"], "mccconstant", "f", properties)
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_LONG_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "L", properties)
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_SHORT_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "s", properties)
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_STRING_TAGS:
				new_current = self.nbt_value_parser(self.regex["word_string"], "mccstring", "", properties)
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_COMPOUND_TAGS:
				self.current= self.nbt_parser(properties)
				if self.string[self.current-1] != "}":
					return self.current

			elif key in NBT_BYTE_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "b", properties)
				if new_current == self.current:
					return self.add_region(start_of_key, new_current, "invalid.illegal")
				self.current = new_current

			elif key in NBT_INTEGER_TAGS:
				new_current = self.nbt_value_parser(self.regex["integer"], "mccconstant", "", properties)
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

	def nbt_list_parser(self, item_regex, item_scope, item_suffix, properties={}):
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


	def nbt_value_parser(self, value_regex, scope, suffix, properties={}):
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
		item_match = self.regex["item_block_id"].match(self.string, self.current)
		if item_match:
			self.add_region(item_match.start(1), item_match.end(1), "mccliteral")
			self.current = self.add_region(item_match.start(2), item_match.end(2), "mccstring")
			return self.nbt_parser(properties)
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
		block_match = self.regex["item_block_id"].match(self.string, self.current)
		if block_match:
			self.add_region(block_match.start(1), block_match.end(1), "mccliteral")
			self.current = self.add_region(block_match.start(2), block_match.end(2), "mccstring")

			if block_match.start(1) == block_match.end(1):
				block_name = "minecraft:" + block_match.group(2)
			else:
				block_name = block_match.group(0)

			if block_name in BLOCKS:
				states = BLOCKS[block_name]
			else:
				self.current = self.add_region(block_match.start(), block_match.end(), "invalid.illegal")
				states = {}

			if self.current >= len(self.string) or self.string[self.current] != "[":
				return self.nbt_parser(properties)
			start_of_bracket = self.current
			self.current += 1
			
			while self.string[self.current] != "]":
				reached_end = self.skip_whitespace(self.current)
				if reached_end:
					return self.current

				start_of_key = self.current
				key_match = self.regex["entity_tag_key"].match(self.string, self.current)
				if not key_match:
					return self.add_region(self.current, self.current + 1, "invalid.illegal")

				key = key_match.group(1)
				if key in states:
					self.add_region(key_match.start(1), key_match.end(1), "mccstring")
				else:
					self.add_region(key_match.start(1), key_match.end(1), "invalid.illegal")
				self.current = self.add_region(key_match.start(2), key_match.end(2), "mcccommand")

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				value_match = self.regex["entity_tag"].match(self.string, self.current)
				if not value_match:
					return self.add_region(self.current, self.current + 1, "invalid.illegal")

				if key in states and value_match.group(0) in states[key]:
					self.add_region(value_match.start(), value_match.end(), "mccstring")
				else: 
					self.add_region(value_match.start(), value_match.end(), "invalid.illegal")

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if self.string[self.current] == ",":
					self.current += 1
				elif self.string[self.current] != "]":
					return self.add_region(self.current, self.current + 1, "invalid.illegal")

			self.current += 1
			return self.nbt_parser(properties)

		return self.current

	def nbt_path_parser(self, properties={}):
		start = self.current

		while self.current < len(self.string):
			start_of_segment = self.current
			old_current = self.current
			self.current = self.string_parser({"type":"word"})
			if self.current < len(self.string) and self.string[self.current] == "[":
				self.current += 1
				old_current = self.current
				self.current = self.integer_parser({"min":0})
				if old_current == self.current or (self.current < len(self.string) and self.string[self.current] != "]"):
					return start
				else:
					self.current += 1
			
			if self.current < len(self.string) and self.string[self.current] == "." and start_of_segment != self.current:
				self.current += 1
			else:
				self.current = self.add_region(start, self.current, "mccstring")
				if start_of_segment == self.current and self.string[self.current - 1] == ".":
					return self.add_region(self.current - 1, self.current, "invalid.illeal")
				else:
					return self.current

		return start

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

	def score_holder_parser(self, properties={}):
		new_current = self.username_parser(properties)
		if new_current != self.current:
			return new_current
		return self.entity_parser(properties)

	def objective_parser(self, properties={}):
		return self.username_parser(properties)

	def vector_3d_parser(self, properties={}):
		return self.position_parser(properties)

	def vector_2d_parser(self, properties={}):
		vec2d_match = self.regex["position-2"].match(self.string, self.current)
		if vec2d_match:
			self.add_region(vec2d_match.start(1), vec2d_match.end(1), "mccconstant")
			return self.add_region(vec2d_match.start(2), vec2d_match.end(2), "mccconstant")
		return self.current

	def particle_parser(self, properties={}):
		particle_match = self.regex["entity_tag"].match(self.string, self.current)
		if particle_match and particle_match.group(0) in PARTICLES:
			old_current = self.current
			self.current = self.add_region(self.current, particle_match.end(), "mccliteral")
			if self.string[old_current:self.current] == "block":
				self.skip_whitespace(self.current)
				return self.block_parser(self.current)

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
		return self.vector_2d_parser(properties)

	# https://www.json.org/
	def json_parser(self, properties={}):
		if not "escape_depth" in properties:
			properties["escape_depth"] = 0

		if self.string[self.current] == "[":
			return self.json_array_parser(properties)
		elif self.string[self.current]  == "{":
			return self.json_object_parser(properties)

		return self.current

	def json_object_parser(self, properties={}):# The '{}' one
		if self.string[self.current] != "{":
			return self.current
		quote = self.generate_quote(properties["escape_depth"])
		start_of_object = self.current
		self.current += 1

		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				return self.add_region(start_of_object, self.current, "invalid.illegal")

			# " \" \\\" \\\\\\\" ...
			# 1 2  4    8        ...
			key = self.string[start_of_key + len(quote) : self.current - len(quote)]
			#print("Json key: " + key)

			reached_end = self.skip_whitespace(start_of_key)
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
					if start_of_value == self.current:
						return self.add_region(start_of_key, self.current, "invalid.illegal")

				elif key in JSON_ENTITY_KEYS:
					start_of_string = self.current
					if self.current + len(quote) > len(self.string) or self.string[self.current : self.current + len(quote)] != quote:
						return self.add_regeion(start_of_key, self.current, "invalid.illegal")
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

				elif key == "clickEvent":
					self.current = self.json_event_parser(regex["click_event_action"], properties)
					if not self.string[self.current - 1] in "}":
						return self.current

				elif key == "hoverEvent":
					self.current = self.json_event_parser(regex["hover_event_action"], properties)
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
		if self.string[self.current] != "[":
			return self.current
		start_of_list = self.current
		self.current += 1

		while self.string[self.current] != "]":
			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			start_of_value = self.current

			match_made = False
			old_current = self.current
			self.current = self.string_parser(properties={"type":"strict", "escape_depth":properties["escape_depth"]})
			if old_current != self.current:
				match_made = True

			old_current = self.current
			self.current = self.float_parser(properties)
			if not match_made and old_current != self.current:
				match_made = True

			old_current = self.current
			self.current = self.json_parser(properties)
			if not match_made and old_current != self.current:
				match_made = True

			old_current = self.current
			self.current = self.boolean_parser(properties)
			if not match_made and old_current != self.current:
				match_made = True

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

	def json_event_parser(self, action_regex, properties={}):
		if self.string[self.current] != "{": #Can't be [] since it's an object
			return self.current
		current += 1
		quote = self.generate_quote(properties["escape_depth"])

		start_of_object = self.current
		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				return self.add_region(self.current, self.current+1, "invalid.illegal")

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")
			self.current += 1

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if key == "action":
				start_of_string= self.current
				if self.current + len(quote) > len(self.string) or self.string[self.current : self.current + len(quote)]  != quote:
					return self.add_region(start_of_key, self.current, "invalid.illegal")
				self.current += len(quote)

				action_match = action_regex.match(self.string, self.current)
				if not action_match:
					return self.add_region(start_of_key, self.current, "invalid.illegal")
				self.current = action_match.end()

				if self.current + len(quote) > len(self.string) or self.string[self.current : self.current + len(quote)] != quote:
					return self.add_region(start_of_string, self.current, "invalid.illegal")

				self.current = self.add_region(start_of_string, self.current + len(quote), "mccstring")

			elif key == "value":
				start_of_value = self.current
				self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
				if start_of_value == self.current:
					return self.add_region(start_of_key, self.current, "invalid.illegal")

			else:
				return self.add_region(start_of_key, self.current, "invalid.illegal")

			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")

		self.current += 1
		return self.current

	def json_score_parser(self, properties={}):
		if self.string[self.current] != "{": #Can't be [] since its an object
			return self.current
		current += 1
		quote = self.generate_quote(properties["escape_depth"])

		start_of_object = self.current
		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				return self.add_region(start_of_object, self.current, "invalid.illegal")

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")
			self.current += 1

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if key == "name":
					start_of_string = self.current
					if self.current + len(quote) > len(self.string) or self.string[self.current : self.current + len(quote)] != quote:
						return self.add_regeion(start_of_key, self.current, "invalid.illegal")
					self.current = self.add_region(self.current, self.current + len(quote), "mccstring")
				
					new_current = self.score_holder_parser(properties)
					if new_current == self.current:
						return self.add_region(start_of_string, self.current, "invalid.illegal")
					self.current = new_current

					if not self.current + len(quote) < len(self.string) or not self.string[self.current : self.current + len(quote)] == quote:
						return self.add_region(start_of_string, self.current, "invalid.illegal")
					self.current = self.add_region(self.current, self.current + len(quote), "mccstring")

			elif key == "objective":
				start_of_value = self.current
				self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
				if start_of_value == self.current:
					return self.add_region(start_of_key, self.current, "invalid.illegal")

			elif key == "value":
				start_of_value = self.current
				self.current = self.integer_parser(properties)
				if start_of_value == self.current:
					return self.add_region(start_of_key, self.current, "invalid.illegal")

			else:
				return self.add_region(start_of_key, self.current, "invalid.illegal")

			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				return self.add_region(self.current, self.current + 1, "invalid.illegal")
			
		self.current += 1
		return self.current

	def operation_parser(self, properties={}):
		operation_match = self.regex["operation"].match(self.string, self.current)
		if operation_match:
			return self.add_region(operation_match.start(), operation_match.end(), "mcccommand")
		return self.current

	def resource_location_parser(self, properties={}):
		entity_match = self.regex["entity"].match(self.string, self.current)
		if entity_match:
			self.add_region(entity_match.start(1), entity_match.end(1), "mccliteral")
			return self.add_region(entity_match.start(2), entity_match.end(2), "mccstring")
		return self.current

	def entity_acnhor_parser(self, properties={}):
		anchor_match = self.regex["entity_anchor"].match(self.string, self.current)
		if anchor_match:
			return self.add_region(anchor_match.start(), anchor_match.end(), "mccstring")
		return self.current

	def objective_criteria_parser(self, properties={}):
		return self.string_parser({"type":"word"})

	def generate_quote(self, escape_depth):
		quotes = ["\"", "\\\"", "\\\\\\\"", "\\\\\\\\\\\\\\\"", "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\""]
		if escape_depth <= 4:
			return quotes[escape_depth]
		
		for i in range(0, escape_depth):
			quote += "\\"
		return quote + self.generate_quote(escape_depth - 1)

	parsers = { #need to include the properties tag
		"minecraft:resource_location": resource_location_parser,
		"minecraft:function"         : namespace_parser,
		"minecraft:entity"           : entity_parser,
		"brigadier:string"           : string_parser, #type  = word and type= greedy
		"minecraft:game_profile"     : username_parser,
		"minecraft:message"          : message_parser,
		"minecraft:block_pos"        : position_parser,
		"minecraft:nbt"              : nbt_parser,
		"minecraft:item_stack"       : item_parser,
		"minecraft:item_predicate"   : item_parser,
		"brigadier:integer"          : integer_parser, #Properties has min and max
		"minecraft:block_state"      : block_parser,
		"minecraft:block_predicate"  : block_parser,
		"minecraft:nbt_path"         : nbt_path_parser,
		"brigadier:float"            : float_parser, #Properties has min and max
		"brigadier:double"           : float_parser, #Properties has min and max
		"brigadier:bool"             : boolean_parser,
		"minecraft:swizzle"          : axes_parser, # any cobination of x, y, and z e.g. x, xy, xz. AKA swizzle
		"minecraft:score_holder"     : score_holder_parser, #Has options to include wildcard or not
		"minecraft:objective"        : objective_parser,
		"minecraft:vec3"             : vector_3d_parser, #Assuming this doesn't include relative coords?
		"minecraft:vec2"             : vector_2d_parser, #Pretty sure these don't
		"minecraft:particle"         : particle_parser,
		"minecraft:item_slot"        : item_slot_parser, #Check the wiki on this one I guess
		"minecraft:scoreboard_slot"  : scoreboard_slot_parser,
		"minecraft:team"             : team_parser,
		"minecraft:color"            : color_parser,
		"minecraft:rotation"         : rotation_parser, # [yaw, pitch], includes relative changes
		"minecraft:component"        : json_parser,
		"minecraft:entity_anchor"    : entity_acnhor_parser,
		"minecraft:operation"        : operation_parser, # +=, = , <>, etc
		"minecraft:range"            : brigadier_range_parser,
		"minecraft:objective_criteria":objective_criteria_parser
	}