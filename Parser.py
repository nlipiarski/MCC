import sublime, re
from .Blocks import BLOCKS
from .Data import *
from .CommandTree import COMMAND_TREE

class Parser:
	add_regions_flags = sublime.DRAW_NO_OUTLINE
	regex = {
		"position-2" : re.compile("(~?-?\d*\.?\d+|~)[\t ]+(~?-?\d*\.?\d+|~)"),
		"float" : re.compile("-?\d+(?:\.\d+)?"),
		"integer" : re.compile("-?\d+"),
		"namespace" : re.compile("([a-z_\-1-9]+:)([a-z_\-1-9]+(?:\/[a-z_\-1-9]+)*)(\/?)"),
		"word_string" : re.compile("\w+|\"(?:[^\\\\\"]|(\\\\.))*\""),
		"username" : re.compile("[\w-]{,16}"),
		"axes" : re.compile("[xyz]+"),
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
		"entity_anchor" : re.compile("feet|eyes"),
		"resource_location" : re.compile("([\w]+:)?([\w\.]+)"),
		"potions" : re.compile("(minecraft:)?(water|mundane|thick|awkward|night_vision|long_night_vision|invisibility|long_invisibility|leaping|strong_leaping|long_leaping|fire_resistance|long_fire_resistance|swiftness|strong_swiftness|long_swiftness|slowness|long_slowness|water_breathing|long_water_breathing|healing|strong_healing|strong_harming|poison|strong_poison|long_poison|regeneration|strong_regeneration|long_regeneration|strength|strong_strength|long_strength|weakness|long_weakness|luck|turtle_master|strong_turtle_master|long_turtle_master)")
	}

	def __init__(self, view):
		self.current = 0
		self.token_id = 0
		self.view = view
		self.mcccomment = []
		self.mcccommand = []
		self.mccconstant = []
		self.mccstring = []
		self.mccentity = []
		self.mccliteral = []
		self.invalid = []

	# start is inclusive while end is exclusive, like string slices
	# Updates token_id
	def add_regions(self):
		self.view.add_regions("mcccomment", self.mcccomment, "mcccomment", flags=self.add_regions_flags)
		self.view.add_regions("mcccommand", self.mcccommand, "mcccommand", flags=self.add_regions_flags)
		self.view.add_regions("mccconstant", self.mccconstant, "mccconstant", flags=self.add_regions_flags)
		self.view.add_regions("mccstring", self.mccstring, "mccstring", flags=self.add_regions_flags)
		self.view.add_regions("mccentity", self.mccentity, "mccentity", flags=self.add_regions_flags)
		self.view.add_regions("mccliteral", self.mccliteral, "mccliteral", flags=self.add_regions_flags)
		self.view.add_regions("invalid", self.invalid, "invalid", flags=self.add_regions_flags)

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
				self.invalid.append(sublime.Region(self.region_begin, line_region.end()))
				self.current = self.region.size()
				return (self.token_id, False)
			else:
				while (self.current < len(self.string) and self.string[self.current] in " \t"):
					self.current += 1
				newline_index = self.string.find("\n", self.current)
				if newline_index > self.current:
					self.invalid.append(sublime.Region(self.region_begin, newline_index))
					self.current = newline_index
					return (self.token_id, True)
				elif self.current < line_region.size():
					self.invalid.append(sublime.Region(self.region_begin, line_region.end()))
					self.current = line_region.size()
					return (self.token_id, True)
				return (self.token_id, True)

		self.string = self.view.substr(line_region)
		self.region = line_region
		self.region_begin = self.region.begin()
		if self.regex["comment"].match(self.string):
			self.mcccomment.append(sublime.Region(self.region_begin, line_region.end()))
			return (self.token_id, True)
		elif command_tree["type"] == "root":
			command_match = self.regex["command"].search(self.string, self.current)
			if not command_match:
				return (self.token_id, False)
			command = command_match.group(2)
			#print("command: " + command)
			if command in command_tree["children"]:
				self.invalid.append(sublime.Region(self.region_begin + command_match.start(1), 
	                                               self.region_begin + command_match.end(1)))

				self.mcccommand.append(sublime.Region(self.region_begin + command_match.start(2), 
	                                               self.region_begin + command_match.end(2)))
				self.current = command_match.end(2)
				return self.highlight(command_tree["children"][command], line_region, command_match.end())
			else:
				print("Invalid command")
				self.invalid.append(sublime.Region(self.region_begin, line_region.end()))
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
					self.mccliteral.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + len(key)))
					self.current += len(key)
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

			while (self.current < len(self.string) and self.string[self.current] in " \t"):
				self.current += 1

			self.invalid.append(sublime.Region(self.region_begin + self.current, line_region.end()))
			self.current = line_region.size()
			if not "executable" in properties or not properties["executable"]:
				return (self.token_id, False)
			else:
				return (self.token_id, True)
			
	# Returns True if the end of the string is reached, else False and will advacne self.current to the next non-whitespace character
	# this will error highlight the section from err_start until the end of the string
	def skip_whitespace(self, err_start):
		if self.current >= len(self.string):
			self.invalid.append(sublime.Region(self.region_begin + err_start, self.region_begin + self.current))
			return True
		while self.string[self.current] in " \n\t":
			self.current += 1
			if self.current >= len(self.string):
				self.invalid.append(sublime.Region(self.region_begin + err_start, self.region_begin + self.current))
				return True
		return False

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
		if self.current >= len(self.string):
			return self.current
		if self.string[self.current] == "*" and "amount" in properties and properties["amount"] == "multiple":
			self.mccentity.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
			return self.current + 1

		if self.string[self.current] != "@" or self.current + 1 > len(self.string) or not self.string[self.current+1] in "pears": #Checks to see if it's a valid entity selector
			return self.current

		self.mccentity.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 2))
		self.current += 2
		if (self.current < len(self.string) and self.string[self.current] == "["):
			self.mccentity.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
			self.current += 1
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
				self.mcccommand.append(sublime.Region(self.region_begin + key_match.start(2), self.region_begin + key_match.end(2)))
				self.mccstring.append(sublime.Region(self.region_begin + key_match.start(1), self.region_begin + key_match.end(1)))
				self.current = key_match.end(2)

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					self.mcccommand.pop()
					self.mccstring.pop()
					return start_of_key

				if key == "level":
					old_current = self.current
					self.current = self.range_parser(self.integer_parser)
					if old_current == self.current:
						return self.current

				elif key == "limit":
					old_current = self.current
					self.current = self.integer_parser(properties={"min":0})
					if old_current == self.current:
						return self.current

				elif key in ["x", "y", "z", "x_rotation", "y_rotation", "distance", "dx", "dy", "dz"]:
					old_current = self.current
					self.current = self.range_parser(self.float_parser)
					if old_current == self.current:
						return self.current

				elif key == "tag":
					if self.string[self.current] == "!":
						self.mcccommand.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
						self.current += 1

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return start_of_key

					old_current = self.current
					self.current = self.regex_parser(self.regex["entity_tag"], [self.mccstring])
					if old_current == self.current:
						return self.current

				elif key == "gamemode":
					if self.string[self.current] == "!":
						self.mcccommand.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
						self.current += 1

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return start_of_key

					old_current = self.current
					self.current = self.regex_parser(self.regex["gamemode"], [self.mccliteral])
					if old_current == self.current:
						return self.current

				elif key == "sort":
					old_current = self.current
					self.current = self.regex_parser(self.regex["sort"], [self.mccliteral])
					if old_current == self.current:
						return self.current

				elif key == "type":
					if self.string[self.current] == "!":
						self.mcccommand.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
						self.current += 1

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return start_of_key

					old_current = self.current
					self.current = self.regex_parser(self.regex["entity"], [self.mccliteral])
					if old_current == self.current:
						return self.current

				elif key == "team":
					if self.string[self.current] == "!":
						self.mcccommand.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
						self.current += 1

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return start_of_key

					self.current = self.regex_parser(self.regex["username"], [self.mccstring])

				elif key == "name":
					if self.string[self.current] == "!":
						self.mcccommand.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
						self.current += 1

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return start_of_key

					if not "escape_depth" in properties:
						properties["escape_depth"] = 0
					old_current = self.current
					self.current = self.string_parser(properties={"type":"word","escape_depth":properties["escape_depth"]})
					if old_current == self.current:
						return self.current

				elif key == "scores":
					if self.string[self.current] != "{":
						return self.current
					score_bracket_start = self.current
					self.current += 1

					while self.string[self.current] != "}":
						reached_end = self.skip_whitespace(score_bracket_start)
						if reached_end:
							return self.current

						start_of_score = self.current
						self.current = self.regex_parser(self.regex["entity_tag_key"], [self.mccstring, self.mcccommand])
						if start_of_score == self.current:
							return self.current

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

						self.current = self.range_parser(self.integer_parser)

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

						if self.string[self.current] == ",":
							self.current += 1
						elif self.string[self.current] != "}":
							self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
							return self.current + 1

						reached_end = self.skip_whitespace(start_of_key)
						if reached_end:
							return self.current

					self.current += 1

				elif key == "advancements":
					self.current = self.advancement_tag_parser(self.string)
					if self.string[self.current - 1] != "}": #Make sure the parse was good
						return self.current

				elif key == "nbt":
					old_current = self.current
					self.current = self.nbt_parser(properties)
					if old_current == self.current:
						return self.current

				else:
					self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
					return self.current + 1

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if self.string[self.current] == ",":
					self.current += 1
				elif self.string[self.current] != "]":
					self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
					return self.current + 1

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

			self.mccentity.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
			return self.current + 1

		return self.current

	def brigadier_range_parser(self, properties={}):
		if properties["decimals"]:
			return self.range_parser(self.float_parser, self.current, properties)
		else:
			return self.range_parser(self.integer_parser, self.current, properties)

	def range_parser(self, parse_function, properties={}):
		matched = False
		start = self.current
		self.current = parse_function(properties)
		if start != self.current:
			matched = True

		if self.current + 2 <= len(self.string) and self.string[self.current:self.current + 2] == "..":
			self.mcccommand.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 2))
			self.current += 2

		start = self.current
		self.current = parse_function(properties)
		if start != self.current:
			matched = True

		if not matched:
			return start

		return self.current

	def advancement_tag_parser(self, do_nested=True):
		if self.string[self.current] != "{":
			return self.current
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
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + advancement_match.end()))
				self.current = advancement_match.end
				return self.current

			self.mccstring.append(sublime.Region(self.region_begin + advancement_match.start(2), 
				                                 self.region_begin + advancement_match.end(2)))

			self.mcccommand.append(sublime.Region(self.region_begin + advancement_match.start(3), 
				                                  self.region_begin + advancement_match.end(3)))
			self.current = advancement_match.end()

			reached_end = self.skip_whitespace(start_of_advancement)
			if reached_end:
				return self.current

			if advancement_match.group(1) != None:
				self.mccliteral.append(sublime.Region(self.region_begin + advancement_match.start(1), 
				                                  self.region_begin + advancement_match.end(1)))
				self.current = self.advancement_tag_parser(do_nested=False)
				if self.string[self.current - 1] != "}": #This tests to see if the parse was successful
					return self.current
			else:
				new_current = self.boolean_parser(self.string)
				if new_current == self.current:
					return self.current
				self.current = new_current

			reached_end = self.skip_whitespace(start_of_advancement)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				return self.current

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
			self.mccstring.append(sublime.Region(self.region_begin + self.current, 
				                                  self.region_begin + string_match.end()))
			return string_match.end()
		return self.current

	# Todo: add entity highlighting
	def message_parser(self, properties={}):
		newline_index = self.string.find("\n", self.current)
		if newline_index < 0:
			self.mccstring.append(sublime.Region(self.region_begin + self.current, self.region.end()))
			return len(self.string)
		else:
			self.mccstring.append(sublime.Region(self.region_begin + self.current, self.region_begin + newline_index))
			return newline_index

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
				if self.current < len(self.string):
					self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

			key = key_match.group(1)
			self.mccstring.append(sublime.Region(self.region_begin + key_match.start(1), self.region_begin + key_match.end(1)))
			self.current = key_match.end()

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			matched = False
			if not matched and key in NBT_STRING_LIST_TAGS:
				properties["type"] = "word"
				old_current = self.current
				self.current = self.nbt_list_parser(self.string_parser, self.mccstring, "", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_INTEGER_LIST_TAGS:
				old_current = self.current
				self.current = self.nbt_list_parser(self.integer_parser, self.mccconstant, "", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_DOUBLE_TAGS:
				old_current = self.current
				self.current = self.nbt_value_parser(self.float_parser, self.mccconstant, "d", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_FLOAT_LIST_TAGS:
				old_current = self.current
				self.current = self.nbt_list_parser(self.float_parser, self.mccconstant, "f", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_FLOAT_TAGS:
				old_current = self.current
				self.current = self.nbt_value_parser(self.float_parser, self.mccconstant, "f", properties)
				if old_current != self.current:
					matched= True

			if not matched and key in NBT_LONG_TAGS:
				old_current = self.current
				self.current = self.nbt_value_parser(self.integer_parser, self.mccconstant, "L", properties)
				if old_current != self.current:
					macthed = True

			if not matched and key in NBT_SHORT_TAGS:
				old_current = self.current
				self.current = self.nbt_value_parser(self.integer_parser, self.mccconstant, "s", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_STRING_TAGS:
				old_current = self.current
				properties["type"] = "word"
				self.current = self.nbt_value_parser(self.string_parser, self.mccstring, "", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_COMPOUND_TAGS:
				old_current = self.current
				self.current= self.nbt_parser(properties)
				if self.string[self.current-1] != "}":
					self.current = old_current
				else:
					matched = True

			if not matched and key in NBT_BYTE_TAGS:
				old_current = self.current
				self.current = self.nbt_value_parser(self.nbt_byte_parser, None, "", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_INTEGER_TAGS:
				old_current = self.current
				self.current = self.nbt_value_parser(self.integer_parser, None, "", properties)
				if old_current != self.current:
					matched = True

			if not matched and key in NBT_COMPOUNT_LIST_TAGS:
				old_current = self.current
				self.current = self.nbt_list_parser(self.nbt_parser, None, "", properties)
				if self.string[self.current-1] =="]": #special because nbt is hard
					matched = True

			if not matched:
				self.mccstring.pop()
				self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
				return self.current

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1
		
		self.current += 1
		return self.current

	def nbt_list_parser(self, item_parser, suffix_scope, item_suffix, properties={}):
		if self.string[self.current] != "[":
			return self.current
		start_of_list = self.current
		self.current += 1

		while self.string[self.current] != "]":

			reached_end = self.skip_whitespace(start_of_list)
			if reached_end:
				return start_of_list
			
			start_of_value = self.current
			self.current = self.nbt_value_parser(item_parser, suffix_scope, item_suffix, properties)

			if start_of_value == self.current:
				return start_of_list

			reached_end = self.skip_whitespace(start_of_value)
			if reached_end:
				return start_of_list

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "]":
				return start_of_list

		self.current += 1
		return self.current


	def nbt_value_parser(self, parser, suffix_scope, suffix, properties={}):
		start = self.current
		self.current = parser(properties)
		if start != self.current:
			if self.current + len(suffix) <= len(self.string) and self.string[self.current : self.current + len(suffix)] == suffix:
				if len(suffix) > 0:
					suffix_scope.append(sublime.Region(self.region_begin + self.current,
															self.region_begin + self.current + len(suffix)))
				return self.current + len(suffix)
			else:
				return start
		return start

	def nbt_byte_parser(self, properties={}):
		start = self.current
		self.current = self.integer_parser(properties)
		if start != self.current:
			if self.current < len(self.string) and self.string[self.current] == "b":
				self.mccconstant.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1
			else: 
				return start
		return self.boolean_parser(properties)

	def item_parser(self, properties={}):
		item_match = self.regex["item_block_id"].match(self.string, self.current)
		start = self.current
		self.current = self.regex_parser(self.regex["item_block_id"], [self.mccliteral, self.mccstring])
		if self.current != start:
			return self.nbt_parser(properties)
		return start

	def integer_parser(self, properties={}):
		integer_match = self.regex["integer"].match(self.string, self.current)
		if integer_match:
			value = int(integer_match.group())
			if "min" in properties and value < properties["min"] or "max" in properties and value > properties["max"]:
				self.invalid.append(sublime.Region(self.region_begin + integer_match.start(), self.region_begin + integer_match.end()))
			else:
				self.mccconstant.append(sublime.Region(self.region_begin + integer_match.start(), self.region_begin + integer_match.end()))
			return integer_match.end()
		return self.current

	def block_parser(self, properties={}):
		start = self.current
		if self.current < len(self.string) and self.string[self.current] ==  "#":
			self.current += 1

		block_match = self.regex["item_block_id"].match(self.string, self.current)
		if block_match:
			self.mccliteral.append(sublime.Region(self.region_begin + start, self.region_begin + block_match.end(1)))
			self.mccstring.append(sublime.Region(self.region_begin + block_match.start(2), self.region_begin + block_match.end(2)))
			self.current =block_match.end()

			if block_match.start(1) == block_match.end(1):
				block_name = "minecraft:" + block_match.group(2)
			else:
				block_name = block_match.group(0)

			if block_name in BLOCKS:
				states = BLOCKS[block_name]
			else:
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
					self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
					return self.current + 1

				key = key_match.group(1)
				if key in states:
					self.mccstring.append(sublime.Region(self.region_begin + key_match.start(1), self.region_begin + key_match.end(1)))
				else:
					self.invalid.append(sublime.Region(self.region_begin + key_match.start(1), self.region_begin + key_match.end(1)))
				self.mcccommand.append(sublime.Region(self.region_begin + key_match.start(2), self.region_begin + key_match.end(2)))

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				value_match = self.regex["entity_tag"].match(self.string, self.current)
				if not value_match:
					self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
					return self.current + 1

				if key in states and value_match.group(0) in states[key]:
					self.mccstring.append(self.region_begin + value_match.start(), self.region_begin + value_match.end())
				else: 
					self.invalid.append(self.region_begin + value_match.start(), self.region_begin + value_match.end())
				self.current = value_match.end()

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if self.string[self.current] == ",":
					self.current += 1
				elif self.string[self.current] != "]":
					self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
					return self.current + 1

			self.current += 1
			return self.nbt_parser(properties)

		return start

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
				self.mccstring.append(sublime.Region(self.region_begin + start, self.region_begin + self.current))
				if start_of_segment == self.current and self.string[self.current - 1] == ".":
					self.invalid.append(sublime.Region(self.region_begin + self.current - 1, self.region_begin + self.current))
				
				return self.current

		return start

	def float_parser(self, properties={}):
		float_match = self.regex["float"].match(self.string, self.current)
		if float_match:
			value = float(float_match.group())
			if ("min" in properties and value < properties["min"]) or ("max" in properties and value > properties["max"]):
				self.invalid.append(sublime.Region(self.region_begin + float_match.start(), self.region_begin + float_match.end()))
			else:
				self.mccconstant.append(sublime.Region(self.region_begin + float_match.start(), self.region_begin + float_match.end()))
			return float_match.end()
		return self.current

	def boolean_parser(self, properties={}):
		if self.current + 4 <= len(self.string) and self.string[self.current:self.current+4] == "true":
			self.mccconstant.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 4))
			return self.current + 4

		elif self.current + 5 <= len(self.string) and self.string[self.current:self.current + 5] == "false":
			self.mccconstant.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 5))
			return self.current + 5

		return self.current

	def axes_parser(self, properties={}):
		axes = set("xyz")
		axes_match = self.regex["axes"].match(self.string, self.current)
		if axes_match and len(set(axes_match.group())) == len(axes_match.group()) and axes.issuperset(axes_match.group()):
			self.mccconstant.append(sublime.Region(self.region_begin + self.current, self.region_begin + axes_match.end()))
			return axes_match.end()
		return self.current

	def score_holder_parser(self, properties={}):
		username_parser = self.parsers["minecraft:game_profile"]
		start = self.current
		self.current = username_parser(self, properties)
		if start != self.current:
			return self.current
		return self.entity_parser(properties)

	def particle_parser(self, properties={}):
		particle_match = self.regex["item_block_id"].match(self.string, self.current)
		if particle_match and particle_match.group(2) in PARTICLES and particle_match.group(1) in [None, "minecraft:"]:
			self.mccliteral.append(sublime.Region(self.region_begin + particle_match.start(1), self.region_begin + particle_match.end(1)))
			self.mccstring.append(sublime.Region(self.region_begin + particle_match.start(2), self.region_begin + particle_match.end(2)))
			self.current = particle_match.end(2)
			if particle_match.group(2) == "block":
				self.skip_whitespace(self.current)
				return self.block_parser(self.current)

		return self.current

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
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

			# " \" \\\" \\\\\\\" ...
			# 1 2  4    8        ...
			key = self.string[start_of_key + len(quote) : self.current - len(quote)]
			#print("Json key: " + key)

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if not self.string[self.current] in ",:}":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

			elif self.string[self.current] == ":":
				self.current += 1
				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if key in JSON_STRING_KEYS:
					start_of_value = self.current
					self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
					if start_of_value == self.current:
						self.mccstring.pop()
						self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
						return self.current

				elif key in JSON_ENTITY_KEYS:
					start_of_value = self.current
					self.current = self.quoted_parser(self.entity_parser, properties)
					if start_of_value == self.current:
						self.mccstring.pop()
						self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
						return self.current

				elif key in JSON_BOOLEAN_KEYS:
					start_of_value == self.current
					self.current = boolean_parser(properties)
					if self.current == start_of_value:
						self.mccstring.pop()
						self.invalid.appen(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
						return self.current

				elif key in JSON_NESTED_KEYS:
					self.current = self.json_parser(properties)
					if not self.string[self.current - 1] in "}]":
						return self.current

				elif key == "color":
					start_of_value = self.current
					self.current = self.quoted_parser(self.color_parser, properties)
					if start_of_value == self.current:
						self.mccstring.pop()
						self.invalid.append(sublie.Region(self.region_begin + start_of_key, self.region_begin + self.current))
						return self.current

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
					self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
					return self.current

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1

			elif self.string[self.current] != "}":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

		return self.current + 1

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
				self.mccconstant.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 4))
				self.current += 4

			if not match_made:
				return self.current

			reached_end = self.skip_whitespace(start_of_value)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "]":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

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
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current+1

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1
			self.current += 1

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if key == "action":
				def action_parser(properties={}):
					return self.regex_parser(action_regex, [self.mccstring])

				start_of_value = self.current
				self.current = self.quoted_parser(action_parser)
				if start_of_value == self.current:
					self.mccstring.pop()
					self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
					return self.current

			elif key == "value":
				start_of_value = self.current
				self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
				if start_of_value == self.current:
					self.mccstring.pop()
					self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
					return self.current

			else:
				self.mccstring.pop()
				self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
				return self.current

			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

		return self.current + 1

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
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				self.mccstring.pop()
				self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
				return self.current + 1
			self.current += 1

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if key == "name":
					start_of_value = self.current
					self.current = self.quoted_parser(self.score_holder_parser, properties)
					if start_of_value == self.current:
						self.mccstring.pop()
						self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
						return self.current

			elif key == "objective":
				start_of_value = self.current
				self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
				if start_of_value == self.current:
					self.mccstring.pop()
					self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
					return self.current

			elif key == "value":
				start_of_value = self.current
				self.current = self.integer_parser(properties)
				if start_of_value == self.current:
					self.mccstring.pop()
					self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
					return self.current

			else:
				self.mccstring.pop()
				self.invalid.append(sublime.Region(self.region_begin + start_of_key, self.region_begin + self.current))
				return self.current

			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				self.invalid.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + 1))
				return self.current + 1
			
		self.current += 1
		return self.current

	def objective_criteria_parser(self, properties={}):
		return self.string_parser({"type":"word"})

	def resource_location_parser(self, properties={}):
		return self.regex_parser(self.regex["resource_location"], [self.mccliteral, self.mccstring])

	def function_parser(self, properties={}):
		return self.regex_parser(self.regex["namespace"], [self.mccstring, self.mccliteral, self.invalid])

	def username_parser(self, properties={}):
		return self.regex_parser(self.regex["username"], [self.mccstring])

	def vec3d_parser(self, properties={}):
		return self.regex_parser(self.regex["position-3"], [self.mccconstant, self.mccconstant, self.mccconstant])

	def vec2d_parser(self, properties={}):
		return self.regex_parser(self.regex["position-2"], [self.mccconstant, self.mccconstant])

	def item_slot_parser(self, properties={}):
		return self.regex_parser(self.regex["item_slot"], [self.mccstring])

	def scoreboard_slot_parser(self, properties={}):
		return self.regex_parser(self.regex["scoreboard_slot"], [self.mccstring])

	def color_parser(self, properties={}):
		return self.regex_parser(self.regex["color"], [self.mccconstant])

	def entity_anchor_parser(self, properties={}):
		return self.regex_parser(self.regex["entity_anchor"], [self.mccstring])

	def scoreboard_operation_parser(self, properties={}):
		return self.regex_parser(self.regex["operation"], [self.mcccommand])

	def mob_effect_parser(self, proeprties={}):
		return self.regex_parser(self.regex["potions"], [self.mccliteral, self.mccstring])

	def regex_parser(self, pattern, scopes, properties={}):
		pattern_match = pattern.match(self.string, self.current)
		if pattern_match:
			if len(scopes) == 1:
				scopes[0].append(sublime.Region(self.region_begin + pattern_match.start(), self.region_begin + pattern_match.end()))
				
			else:
				for i in range(len(scopes)):
					scopes[i].append(sublime.Region(self.region_begin + pattern_match.start(i + 1), 
													self.region_begin + pattern_match.end(i + 1)))
			self.current = pattern_match.end()
		return self.current

	def quoted_parser(self, parser, properties={}):
		if not "escape_depth" in properties:
			escape_depth = 0
		else:
			escape_depth = properties["escape_depth"]
		start = self.current
		quote = self.generate_quote(escape_depth)
		if self.current + len(quote) > len(self.string) or self.string[self.current:self.current + len(quote)] != quote:
			return self.current

		self.mccstring.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + len(quote)))
		self.current += len(quote)
		old_current = self.current
		self.current = parser(properties)
		if old_current == self.current:
			self.mccstring.pop()
			return self.current

		if self.current + len(quote) > len(self.string) or self.string[self.current:self.current + len(quote)] != quote:
			self.mccstring.pop()
			return start
		self.mccstring.append(sublime.Region(self.region_begin + self.current, self.region_begin + self.current + len(quote)))
		return self.current + len(quote)

	def generate_quote(self, escape_depth):
		quotes = ["\"", "\\\"", "\\\\\\\"", "\\\\\\\\\\\\\\\"", "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\""]
		if escape_depth <= 4:
			return quotes[escape_depth]
		
		for i in range(0, escape_depth):
			quote += "\\"
		return quote + self.generate_quote(escape_depth - 1)

	parsers = { #need to include the properties tag
		"minecraft:resource_location": resource_location_parser,
		"minecraft:function"         : function_parser,
		"minecraft:entity"           : entity_parser,
		"brigadier:string"           : string_parser, #type  = word and type= greedy
		"minecraft:game_profile"     : username_parser,
		"minecraft:message"          : message_parser,
		"minecraft:block_pos"        : vec3d_parser,
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
		"minecraft:objective"        : username_parser,
		"minecraft:vec3"             : vec3d_parser, #Assuming this doesn't include relative coords?
		"minecraft:vec2"             : vec2d_parser, #Pretty sure these don't
		"minecraft:particle"         : particle_parser,
		"minecraft:item_slot"        : item_slot_parser, #Check the wiki on this one I guess
		"minecraft:scoreboard_slot"  : scoreboard_slot_parser,
		"minecraft:team"             : username_parser,
		"minecraft:color"            : color_parser,
		"minecraft:rotation"         : vec2d_parser, # [yaw, pitch], includes relative changes
		"minecraft:component"        : json_parser,
		"minecraft:entity_anchor"    : entity_anchor_parser,
		"minecraft:operation"        : scoreboard_operation_parser, # +=, = , <>, etc
		"minecraft:range"            : brigadier_range_parser,
		"minecraft:objective_criteria":objective_criteria_parser,
		"minecraft:mob_effect"       : mob_effect_parser
	}