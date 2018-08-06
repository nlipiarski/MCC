import sublime, re
from .Blocks import BLOCKS
from .Items import ITEMS
from .Data import *
from .CommandTree import COMMAND_TREE

class Parser:
	add_regions_flags = sublime.DRAW_NO_OUTLINE
	regex = {
		"axes" : re.compile("[xyz]+"),
		"click_event_action": re.compile("(?:run|suggest)_command|open_url|change_page"),
		"color" : re.compile("none|black|dark_blue|dark_green|dark_aqua|dark_red|dark_purple|gold|gray|dark_gray|blue|green|aqua|red|light_purple|yellow|white"),
		"command" : re.compile('[\t ]*(/?)([a-z]+)'),
		"comment" :  re.compile('^[\t ]*#.*$'),
		"entity_anchor" : re.compile("feet|eyes"),
		"entity_tag_advancement_key" : re.compile("([a-z_\-1-9]+:)?(\w+)[\t ]*(=)"),
		"entity_tag_key" : re.compile("(\w+)[\t ]*(=)"),
		"float" : re.compile("-?(\d+(\.\d+)?|\.\d+)"),
		"gamemode" : re.compile("survival|creative|adventure|spectator"),
		"greedy_string" : re.compile(".*$"),
		"hex4" : re.compile("[0-9a-fA-F]{4}"),
		"hover_event_action" : re.compile("show_(?:text|item|entity|achievement)"),
		"integer" : re.compile("-?\d+"),
		"item_block_id" : re.compile("(#?[a-z_]+:)?([a-z_]+)"),
		"item_slot" : re.compile("slot\.(?:container\.\d+|weapon\.(?:main|off)hand|\.(?:enderchest|inventory)\.(?:2[0-6]|1?[0-9])|hotbar.[0-8]|horse\.(?:saddle|chest|armor|1[0-4]|[0-9])|villager\.[0-7])"),
		"namespace" : re.compile("(#?[a-z_\-1-9\.]+:)([a-z_\-1-9\.]+(?:\/[a-z_\-1-9\.]+)*)(\/?)"),
		"nbt_key" : re.compile("(\w+)[\t ]*:"),
		"operation" : re.compile("[+\-\*\%\/]?=|>?<|>"),
		"position-2" : re.compile("(~?-?\d*\.?\d+|~)[\t ]+(~?-?\d*\.?\d+|~)"),
		"position-3" : re.compile("([~\^]?-?\d*\.?\d+|[~\^])[\t ]+([~\^]?-?\d*\.?\d+|[~\^])[\t ]+([~\^]?-?\d*\.?\d+|[~\^])"),
		"resource_location" : re.compile("([\w\.]+:)?([\w\.]+)"),
		"scoreboard_slot" : re.compile("belowName|list|sidebar(?:.team.(?:black|dark_blue|dark_green|dark_aqua|dark_red|dark_purple|gold|gray|dark_gray|blue|green|aqua|red|light_purple|yellow|white))?"),
		"sort" : re.compile("nearest|furthest|random|arbitrary"),
		"username" : re.compile("[\w\(\)\.\<\>_\-]+"),
		"vec4" : re.compile("((?:\d*\.)?\d+)[\t ]+((?:\d*\.)?\d+)[\t ]+((?:\d*\.)?\d+)[\t ]+((?:\d*\.)?\d+)"),
		"word_string" : re.compile("\w+"),
		"white_space" : re.compile("^\s+$")
	}

	def __init__(self, view):

		self.current = 0
		self.view = view
		self.mcccomment = []
		self.mcccommand = []
		self.mccconstant = []
		self.mccstring = []
		self.mccentity = []
		self.mccliteral = []
		self.invalid = []

		#The order of this list corresponds to the ordering of nbt_tag_lists.
		# The tuples are ordered like this
		# (isList, parser,  item suffix scope, item suffix)
		self.nbt_value_parsers = [ 
			(True, self.string_parser, None, ""),
			(True, self.float_parser, self.mccconstant, "d"),
			(True, self.integer_parser, None, ""),
			(False, self.float_parser, self.mccconstant, "d"),
			(True, self.nbt_parser, None, ""),
			(True, self.float_parser, self.mccconstant, "f"),
			(False, self.float_parser, self.mccconstant, "f"),
			(False, self.integer_parser, self.mccconstant, "L"),
			(False, self.integer_parser, self.mccconstant, "s"),
			(False, self.string_parser, None, ""),
			(False, self.nbt_parser, None, ""),
			(False, self.nbt_byte_parser, None, ""),
			(False, self.integer_parser, None, ""),
			(False, self.json_in_nbt_parser, None, ""),
			(True, self.json_in_nbt_parser, None, ""),
			(False, self.nbt_tags_parser, None, "")
		]

		def score_parser(properties):
			properties["decimals"] = False
			return self.nested_entity_tag_parser(self.brigadier_range_parser, do_nested=False, properties=properties)

		def advancement_parser(properties):
			return self.nested_entity_tag_parser(self.boolean_parser, do_nested=True)

		def name_or_string_parser(properties):
			start = self.current
			self.current = self.username_parser(properties)
			if start != self.current:
				return self.current
			old_string_type = properties["type"]
			properties["type"] = "strict"
			self.current = self.string_parser(properties)
			properties["type"] = old_string_type
			return self.current

		# Data for target selector parsing
		# order for tuple:
		# (isNegatable, isRange, parser)
		self.target_selector_value_parsers = [
			(False, True, self.integer_parser),
			(False, False, self.integer_parser),
			(False, True, self.float_parser),
			(True, False, name_or_string_parser),
			(True, False, self.gamemode_parser),
			(True, False, self.sort_parser),
			(True, False, self.entity_location_parser),
			(False, False, score_parser),
			(False, False, advancement_parser),
			(False, False, self.nbt_parser)
		]


	def add_regions(self):
		self.view.add_regions("mcccomment", self.mcccomment, "mcccomment", flags=self.add_regions_flags)
		self.view.add_regions("mcccommand", self.mcccommand, "mcccommand", flags=self.add_regions_flags)
		self.view.add_regions("mccconstant", self.mccconstant, "mccconstant", flags=self.add_regions_flags)
		self.view.add_regions("mccstring", self.mccstring, "mccstring", flags=self.add_regions_flags)
		self.view.add_regions("mccentity", self.mccentity, "mccentity", flags=self.add_regions_flags)
		self.view.add_regions("mccliteral", self.mccliteral, "mccliteral", flags=self.add_regions_flags)
		self.view.add_regions("invalid", self.invalid, "invalid.illegal", flags=self.add_regions_flags)

	def append_region(self, region_list, start, end):
		region_list.append(sublime.Region(self.region_begin + start, self.region_begin + end))

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
				self.append_region(self.invalid, 0, line_region.size())
				self.current = self.region.size()
				return False
			else:
				while (self.current < len(self.string) and self.string[self.current] in " \t"):
					self.current += 1

				if self.current < line_region.size():
					self.append_region(self.invalid, self.current, line_region.size())
					self.current = line_region.size()
					return False

				return True

		self.string = self.view.substr(line_region)
		if self.regex["white_space"].match(self.string):
			return True

		self.region = line_region
		self.region_begin = self.region.begin()

		comment_match = self.regex["comment"].match(self.string, self.current)
		if comment_match:
			self.append_region(self.mcccomment, comment_match.start(), comment_match.end())
			self.current = comment_match.end()
			return True

		elif command_tree["type"] == "root":
			command_match = self.regex["command"].match(self.string, self.current)
			if not command_match:
				self.append_region(self.invalid, 0, line_region.size())
				return False

			command = command_match.group(2)
			#print("command: " + command)
			if command in command_tree["children"]:
				self.append_region(self.invalid, command_match.start(1), command_match.end(1))

				self.current = command_match.end(2)
				if self.highlight(command_tree["children"][command], line_region, command_match.end()):
					self.append_region(self.mcccommand, command_match.start(2), command_match.end(2))
					return True
				else:
					self.append_region(self.invalid, command_match.start(2), command_match.end(2))
					return False

			else:
				self.append_region(self.invalid, 0, line_region.size())
				return False
		else:
			was_space = False
			while (self.current < len(self.string) and self.string[self.current] in " \t"):
				self.current += 1
				was_space = True

			if self.current >= len(self.string):
				if not "executable" in command_tree or not command_tree["executable"]:
					return False
				else:
					return True

			elif not was_space:
				return False	

			start = self.current
			for key, properties in command_tree["children"].items():
				if properties["type"] == "literal" and self.string.startswith(key, self.current):
					self.append_region(self.mccliteral, self.current, self.current + len(key))
					self.current += len(key)
					success = self.highlight(properties, line_region, self.current)
					if success:
						return True
					else:
						self.current = start
						self.mccliteral.pop()

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
						success = self.highlight(properties, line_region, self.current)
						if success:
							return True
						else:
							self.invalid.pop()
							self.current = start

			while (self.current < len(self.string) and self.string[self.current] in " \t"):
				self.current += 1

			if self.current < line_region.size():
				self.append_region(self.invalid, self.current, line_region.size())
				self.current = line_region.size()

			if not "executable" in properties or not properties["executable"]:
				return False
			else:
				return True
			
	# Returns True if the end of the string is reached, else False and will advacne self.current to the next non-whitespace character
	# this will error highlight the section from err_start until the end of the string
	def skip_whitespace(self, err_start):
		start = self.current
		if self.current >= len(self.string):
			return True
		while self.string[self.current] in " \t":
			self.current += 1
			if self.current >= len(self.string):
				self.current = start
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
		if "min" in properties:
			properties.pop("min")

		if self.current >= len(self.string):
			return self.current
		if self.string[self.current] == "*" and "amount" in properties and properties["amount"] == "multiple":
			self.append_region(self.mccentity, self.current, self.current + 1)
			return self.current + 1

		if self.string[self.current] != "@" or self.current + 1 >= len(self.string) or not self.string[self.current+1] in "pears": #Checks to see if it's a valid entity selector
			return self.current

		self.append_region(self.mccentity, self.current, self.current + 2)
		self.current += 2

		if (self.current < len(self.string) and self.string[self.current] == "["):
			self.append_region(self.mccentity, self.current, self.current + 1)
			self.current += 1
			continue_parsing = True

			while continue_parsing:
				reached_end = self.skip_whitespace(self.current)
				if reached_end:
					return self.current
				
				start_of_key = self.current
				key_match = self.regex["entity_tag_key"].match(self.string, self.current)
				if not key_match:
					return self.current

				key = key_match.group(1)
				self.append_region(self.mcccommand, key_match.start(2), key_match.end(2))
				self.append_region(self.mccstring, key_match.start(1), key_match.end(1))
				self.current = key_match.end(2)

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					self.mcccommand.pop()
					self.mccstring.pop()
					return start_of_key

				#properties["min"] = 0
				matched = False
				for i in range(len(TARGET_KEY_LISTS)):
					if key in TARGET_KEY_LISTS[i]:
						isNegatable, isRange, parser = self.target_selector_value_parsers[i]
						if isNegatable and self.string[self.current] == "!":
							self.append_region(self.mcccommand, self.current, self.current + 1)
							self.current += 1

							reached_end = self.skip_whitespace(start_of_key)
							if reached_end:
								return start_of_key

						old_current = self.current
						if isRange:
							self.current = self.range_parser(parser, {})
						else:
							self.current = parser(properties)

						if old_current != self.current:
							matched = True
							break

				if not matched:
					self.append_region(self.invalid, start_of_key, self.current)
					return self.current + 1

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if self.string[self.current] == ",":
					self.current += 1
				elif self.string[self.current] == "]":
					continue_parsing = False
				else:
					self.append_region(self.invalid, self.current, self.current + 1)
					return self.current + 1

			self.append_region(self.mccentity, self.current, self.current + 1)
			return self.current + 1

		return self.current

	def brigadier_range_parser(self, properties={}):
		if properties["decimals"]:
			return self.range_parser(self.float_parser, properties)
		else:
			return self.range_parser(self.integer_parser, properties)

	def range_parser(self, parse_function, properties={}):
		matched = False
		start = self.current
		self.current = parse_function(properties)
		if start != self.current:
			matched = True

		if self.current + 2 <= len(self.string) and self.string[self.current:self.current + 2] == "..":
			self.append_region(self.mcccommand, self.current, self.current + 2)
			self.current += 2

		start = self.current
		self.current = parse_function(properties)
		if start != self.current:
			matched = True

		if not matched:
			return start

		return self.current

	def nested_entity_tag_parser(self, parser, do_nested=False, properties={}): # scores= and advancements=
		if self.string[self.current] != "{":
			return self.current
		bracket_start = self.current
		self.current += 1
		continue_parsing = True

		while continue_parsing:
			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			start_of_key = self.current
			key_match = self.regex["entity_tag_advancement_key"].match(self.string, self.current)
			if not key_match:
				return self.current

			elif not do_nested and key_match.group(1): # If theres a nested tag where there shouldn't be
				self.append_region(self.invalid, self.current, key_match.end())
				self.current = key_match.end()
				return self.current

			self.append_region(self.mccstring, key_match.start(2), key_match.end(2))
			self.append_region(self.mcccommand, key_match.start(3), key_match.end(3))
			self.current = key_match.end()

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if key_match.group(1) != None:
				self.append_region(self.mccliteral, key_match.start(1), key_match.end(1))
				self.current = self.nested_entity_tag_parser(parser, do_nested=False, properties=properties)
				if self.string[self.current - 1] != "}": #This tests to see if the parse was successful
					return self.current
			else:
				old_current = self.current
				self.current = parser(properties)
				if old_current == self.current:
					self.mccstring.pop()
					self.mcccommand.pop()
					return self.current

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1
			else:
				continue_parsing = False

		self.current += 1
		return self.current

	# Word means "up to the next space", phrase is "an unquoted word or quoted string", and greedy is "everything from this point to the end of input".
	# strict means only a regular quote enclosed string will work
	def string_parser(self, properties={}):
		if self.current >= len(self.string):
			return self.current

		if not "escape_depth" in properties:
			escape_depth = 0
		else:
			escape_depth = properties["escape_depth"]

		if properties["type"] == "word":
			old_current = self.current
			self.current = self.regex_parser(self.regex["word_string"], [self.mccstring])
			if old_current != self.current:
				return self.current

		if properties["type"] == "greedy":
			old_current = self.current
			self.current = self.regex_parser(self.regex["greedy_string"], [self.mccstring])

		elif properties["type"] in {"strict", "word"}:
			quote = self.generate_quote(escape_depth)
			escape = self.generate_quote(escape_depth + 1)[:-1] # Gets the needed backslashes to escape

			string_start = self.current
			start = self.current

			if not self.string.startswith(quote, self.current):
				return self.current

			self.current += len(quote)
			continue_parsing = True
			while continue_parsing:
				if self.current >= len(self.string):
					self.append_region(self.invalid, self.current - 1, self.current)
					return self.current

				elif self.string.startswith(quote, self.current):
					self.append_region(self.mccstring, start, self.current + len(quote))
					self.current += len(quote)
					continue_parsing = False

				elif self.string.startswith(escape, self.current) and self.current + len(escape) < len(self.string):
					escape_char = self.string[self.current + len(escape)]
					if escape_char in "\"\\/bfnrt":
						if self.current - start > 0:
							self.append_region(self.mccstring, start, self.current)

						self.append_region(self.mccconstant, self.current, self.current + len(escape) + 1)
						self.current += len(escape) + 1
						start = self.current
					elif escape_char == "u":
						if self.current - start > 0:
							self.append_region(self.mccstring, start, self.current)
						
						hex_match = self.regex["hex4"].match(self.string, self.current + len(escape) + 1)
						if not hex_match:
							self.append_region(self.invalid, self.current, self.current + len(escape) + 1)
							return self.current + len(escape) + 1

						self.append_region(self.mccconstant, self.current, self.current + len(escape) + 5)
						self.current += len(escape) + 5
						start = self.current

					else:
						self.append_region(self.invalid, self.current, self.current + 1)
						return self.current + 1

				elif self.string[self.current] in "\"\\":
					self.append_region(self.invalid, self.current, self.current + 1)
					return self.current + 1
				else:
					self.current += 1

		return self.current

	# Todo: add entity highlighting
	def message_parser(self, properties={}):
		self.append_region(self.mccstring, self.current, self.region.size())
		return len(self.string)

	def nbt_parser(self, properties={}):
		if self.current >= len(self.string) or self.string[self.current] != "{":
			return self.current
		elif not "escape_depth" in properties:
			properties["escape_depth"] = 0

		braces_start = self.current
		self.current += 1
		nbt_value_parsers = self.nbt_value_parsers

		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(braces_start)
			if reached_end:
				return self.current

			start_of_key = self.current

			key_match = self.regex["nbt_key"].match(self.string, self.current)
			if not key_match:
				if self.current < len(self.string):
					self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			key = key_match.group(1)
			self.append_region(self.mccstring, key_match.start(1), key_match.end(1))
			self.current = key_match.end()

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			old_type = None
			if "type" in properties:
				old_type = properties["type"]
			properties["type"] = "word"

			matched = False
			for i in range(len(NBT_KEY_LISTS)):
				keys = NBT_KEY_LISTS[i]
				if key in keys:
					is_list, value_parser, suffix_scope, suffix = nbt_value_parsers[i]
					old_current = self.current
					if is_list:
						self.current = self.nbt_list_parser(value_parser, suffix_scope, suffix, properties)
					else:
						self.current = self.nbt_value_parser(value_parser, suffix_scope, suffix, properties)

					if old_current != self.current:
						matched = True
						break

			if old_type != None:
				properties["type"] = old_type

			if not matched:
				old_current = self.current
				self.current = self.nbt_value_parser(self.nbt_byte_parser, None, "", properties)
				if old_current == self.current:
					self.append_region(self.invalid, self.current, self.current + 1)
					return self.current + 1

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1

			elif self.string[self.current] != "}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1
		
		self.current += 1
		return self.current

	def nbt_tags_parser(self, properties={}):
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
					self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			self.append_region(self.mccstring, key_match.start(1), key_match.end(1))
			self.current = key_match.end()

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			start = self.current
			self.current = self.nbt_value_parser(self.nbt_byte_parser, None, "", properties)

			if start == self.current:
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1

			elif self.string[self.current] != "}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1
		
		self.current += 1
		return self.current

	def nbt_list_parser(self, item_parser, suffix_scope, item_suffix, properties={}):
		if self.string[self.current] != "[":
			return self.current
		start_of_list = self.current
		self.current += 1

		continue_parsing = True
		while continue_parsing:

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
			else:
				continue_parsing = False

		self.current += 1
		return self.current


	def nbt_value_parser(self, parser, suffix_scope, suffix, properties={}):
		start = self.current
		self.current = parser(properties)
		if start != self.current:
			if (len(suffix) > 0 and
					self.current + len(suffix) <= len(self.string) and 
					self.string[self.current:self.current + len(suffix)] == suffix):
				self.append_region(suffix_scope, self.current, self.current + len(suffix))
			return self.current + len(suffix)

		return start

	def nbt_byte_parser(self, properties={}):
		start = self.current
		self.current = self.integer_parser(properties)
		if start != self.current:
			if self.current < len(self.string) and self.string[self.current] == "b":
				self.append_region(self.mccconstant, self.current, self.current + 1)
				return self.current + 1
			else: 
				return start
		return self.boolean_parser(properties)

	def integer_parser(self, properties={}):
		integer_match = self.regex["integer"].match(self.string, self.current)
		if integer_match:
			value = int(integer_match.group())
			if "min" in properties and value < properties["min"] or "max" in properties and value > properties["max"]:
				print("min: " + str(properties["min"]) + " Val: " + str(value))
				self.append_region(self.invalid, integer_match.start(), integer_match.end())
			else:
				self.append_region(self.mccconstant, integer_match.start(), integer_match.end())
			return integer_match.end()
		return self.current

	def block_parser(self, properties={}):
		start = self.current
		lenient = False
		if self.current < len(self.string) and self.string[self.current] ==  "#":
			lenient=True
			self.current += 1

		block_match = self.regex["item_block_id"].match(self.string, self.current)
		if block_match:
			if block_match.group(1) != None:
				self.append_region(self.mccliteral, start, block_match.end(1))
			elif self.string[start] == "#":
				self.append_region(self.invalid, start, start+1)

			self.append_region(self.mccstring, block_match.start(2), block_match.end(2))
			self.current = block_match.end()

			if block_match.start(1) == block_match.end(1):
				block_name = "minecraft:" + block_match.group(2)
			else:
				block_name = block_match.group(0)

			if block_name in BLOCKS and "properties" in BLOCKS[block_name]:
				properties = BLOCKS[block_name]["properties"]
			else:
				properties = {}

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
					self.append_region(self.invalid, self.current, self.current + 1)
					return self.current + 1

				key = key_match.group(1)
				if lenient or key in properties:
					self.append_region(self.mccstring, key_match.start(1), key_match.end(1))
				else:
					self.append_region(self.invalid, key_match.start(1), key_match.end(1))
				self.append_region(self.mcccommand, key_match.start(2), key_match.end(2))
				self.current = key_match.end()

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				value_match = self.regex["word_string"].match(self.string, self.current)
				if not value_match:
					self.append_region(self.invalid, self.current, self.current + 1)
					return self.current + 1

				if lenient or (key in properties and value_match.group() in properties[key]):
					self.append_region(self.mccstring, value_match.start(), value_match.end())
				else: 
					self.append_region(self.invalid, value_match.start(), value_match.end())
				self.current = value_match.end()

				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				if self.string[self.current] == ",":
					self.current += 1
				elif self.string[self.current] != "]":
					self.append_region(self.invalid, self.current, self.current + 1)
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
				self.append_region(self.mccstring, start, self.current)
				if start_of_segment == self.current and self.string[self.current - 1] == ".":
					self.append_region(self.invalid, self,ccurrent - 1, self.current)
				
				return self.current

		return start

	def float_parser(self, properties={}):
		float_match = self.regex["float"].match(self.string, self.current)
		if float_match:
			value = float(float_match.group())
			if ("min" in properties and value < properties["min"]) or ("max" in properties and value > properties["max"]):
				self.append_region(self.invalid, float_match.start(), float_match.end())
			else:
				self.append_region(self.mccconstant, float_match.start(), float_match.end())
			return float_match.end()
		return self.current

	def boolean_parser(self, properties={}):
		if self.current + 4 <= len(self.string) and self.string[self.current:self.current+4] == "true":
			self.append_region(self.mccconstant, self.current, self.current + 4)
			return self.current + 4

		elif self.current + 5 <= len(self.string) and self.string[self.current:self.current + 5] == "false":
			self.append_region(self.mccconstant, self.current, self.current + 5)
			return self.current + 5

		return self.current

	def axes_parser(self, properties={}):
		axes = set("xyz")
		axes_match = self.regex["axes"].match(self.string, self.current)
		if axes_match and len(set(axes_match.group())) == len(axes_match.group()) and axes.issuperset(axes_match.group()):
			self.append_region(self.mccconstant, self.current, axes_match.end())
			return axes_match.end()
		return self.current

	def score_holder_parser(self, properties={}):
		start = self.current
		if self.string[self.current] == "#":
			self.current = self.current + 1

		username_parser = self.parsers["minecraft:game_profile"]
		username_start = self.current
		self.current = username_parser(self, properties)
		if username_start != self.current:
			self.append_region(self.mccstring, start, start + 1)
			return self.current
		return self.entity_parser(properties)

	def particle_parser(self, properties={}):
		particle_match = self.regex["item_block_id"].match(self.string, self.current)
		if particle_match and particle_match.group(2) in PARTICLES and particle_match.group(1) in [None, "minecraft:"]:
			self.append_region(self.mccliteral, particle_match.start(1), particle_match.end(1))
			self.append_region(self.mccstring, particle_match.start(2), particle_match.end(2))
			self.current = particle_match.end(2)

			if particle_match.group(2) == "block" or particle_match.group(2) == "falling_dust":
				self.skip_whitespace(self.current)
				return self.block_parser(self.current)

			elif particle_match.group(2) == "item":
				self.skip_whitespace(self.current)
				return self.item_parser(self.current)

			elif particle_match.group(2) == "dust":
				self.skip_whitespace(self.current)
				return self.regex_parser(self.regex["vec4"], [self.mccconstant, self.mccconstant, self.mccconstant, self.mccconstant])

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
		finished_parsing = False

		while not finished_parsing:
			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if not self.string[self.current] in ",:}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			elif self.string[self.current] == ":":
				self.current += 1
				reached_end = self.skip_whitespace(start_of_key)
				if reached_end:
					return self.current

				matched = False
				if key in JSON_STRING_KEYS:
					start_of_value = self.current
					self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
					if start_of_value != self.current:
						matched = True

				if not matched and key in JSON_ENTITY_KEYS:
					start_of_value = self.current
					self.current = self.quoted_parser(self.entity_parser, properties)
					if start_of_value != self.current:
						matched = True

				if not matched and key in JSON_BOOLEAN_KEYS:
					start_of_value = self.current
					self.current = self.boolean_parser(properties)
					if start_of_value != self.current:
						matched = True

				if not matched and key in JSON_NESTED_KEYS:
					self.current = self.json_parser(properties)
					if not self.string[self.current - 1] in "}]":
						return self.current
					matched = True

				if not matched and key == "color":
					start_of_value = self.current
					self.current = self.quoted_parser(self.color_parser, properties)
					if start_of_value != self.current:
						matched = True

				if not matched and key == "clickEvent":
					self.current = self.json_event_parser(regex["click_event_action"], properties)
					if not self.string[self.current - 1] in "}":
						return self.current
					matched = True

				if not matched and key == "hoverEvent":
					self.current = self.json_event_parser(regex["hover_event_action"], properties)
					if not self.string[self.current - 1] in "}":
						return self.current
					matched = True

				if not matched and key == "score":
					self.current = self.json_score_parser(properties)
					if not self.string[self.current - 1] in "}":
						return self.current
					matched = True

				if not matched:
					self.mccstring.pop()
					self.append_region(self.invalid, start_of_key, self.current)
					return self.current

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1

			elif self.string[self.current] != "}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			else:
				finished_parsing = True

		return self.current + 1

	def json_array_parser(self, properties={}): # The '[]' one
		if self.string[self.current] != "[":
			return self.current
		start_of_list = self.current
		self.current += 1

		def null_parser(properties={}):
			if self.current + 4 < len(self.string) and self.string[self.current : self.current + 4] == "null":
				self.append_region(self.mccconstant, self.current, self.current + 4)
				self.current += 4
			return self.current

		possible_parsers = [
			null_parser,
			self.string_parser,
			self.float_parser,
			self.json_parser,
			self.boolean_parser
		]

		old_type = None
		if "type" in properties:
			old_type = properties["type"]
		properties["type"] = "strict"

		continue_parsing = True
		while continue_parsing:
			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				if old_type != None:
					properties["type"] = old_type
				return self.current

			start_of_value = self.current

			for parser in possible_parsers:
				old_current = self.current
				self.current = parser(properties)
				if old_current != self.current:
					break

			if old_type != None:
				properties["type"] = old_type

			if start_of_value == self.current:
				if self.current < len(self.string):
					self.append_region(self.invalid, self.current, self.current + 1)
				if old_type != None:
					properties["type"] = old_type
				return self.current

			reached_end = self.skip_whitespace(start_of_value)
			if reached_end:
				if old_type != None:
					properties["type"] = old_type
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "]":
				if old_type != None:
					properties["type"] = old_type
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1
			else:
				continue_parsing = False

		if old_type != None:
			properties["type"] = old_type
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
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current+1

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1
			self.current += 1

			reached_end = self.skip_whitespace(start_of_key)
			if reached_end:
				return self.current

			success = False
			if key == "action":
				def action_parser(properties={}):
					return self.regex_parser(action_regex, [self.mccstring])

				start_of_value = self.current
				self.current = self.quoted_parser(action_parser)
				if start_of_value != self.current:
					success = True

			if key == "value":
				start_of_value = self.current
				self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
				if start_of_value == self.current:
					success = True

			if not success:
				self.mccstring.pop()
				self.append_region(self.invalid, start_of_key, self.current)
				return self.current

			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

		return self.current + 1

	def json_score_parser(self, properties={}):
		if self.string[self.current] != "{": #Can't be [] since its an object
			return self.current
		self.current += 1
		quote = self.generate_quote(properties["escape_depth"])

		start_of_object = self.current
		while self.string[self.current] != "}":
			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			start_of_key = self.current
			self.current = self.string_parser(properties={"type":"strict","escape_depth":properties["escape_depth"]})
			if start_of_key == self.current:
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

			key = self.string[start_of_key + len(quote) : self.current - len(quote)]
			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			if self.string[self.current] != ":":
				self.mccstring.pop()
				self.append_region(self.invalid, start_of_key, self.current)
				return self.current + 1
			self.current += 1

			reached_end = self.skip_whitespace(start_of_object)
			if reached_end:
				return self.current

			success = False
			if key == "name":
				start_of_value = self.current
				self.current = self.quoted_parser(self.score_holder_parser, properties)
				if start_of_value != self.current:
					success = True

			elif key == "objective":
				start_of_value = self.current
				self.current = self.quoted_parser(self.username_parser, properties)
				if start_of_value != self.current:
					success = True

			elif key == "value":
				start_of_value = self.current
				self.current = self.integer_parser(properties)
				if start_of_value == self.current:
					success = True

			if not success:
				self.mccstring.pop()
				self.append_region(self.invalid, start_of_key, self.current)
				return self.current

			reached_end = self.skip_whitespace(self.current)
			if reached_end:
				return self.current

			if self.string[self.current] == ",":
				self.current += 1
			elif self.string[self.current] != "}":
				self.append_region(self.invalid, self.current, self.current + 1)
				return self.current + 1

		self.current += 1
		return self.current

	def objective_criteria_parser(self, properties={}):
		criteria_match = self.regex["resource_location"].match(self.string, self.current)
		if criteria_match:
			criteria = criteria_match.group()
			namespace = criteria_match.group(1)
			if criteria_match.group(2).startswith("minecraft."):
				location = criteria_match.group(2)[10:]
			else:
				location = criteria_match.group(2)

			if (criteria in OBJECTIVE_CRITERIA or 
			   (namespace in CRITERIA_BLOCKS and location in BLOCKS) or
			   (namespace in CRITERIA_ITEMS and location in ITEMS) or
			   (namespace in CRITERIA_ENTITIES and location in ENTITIES)):
				if namespace != None:
					self.append_region(self.mccliteral, criteria_match.start(1), criteria_match.end(1))

				self.append_region(self.mccstring, criteria_match.start(2), criteria_match.end(2))
				self.current = criteria_match.end()

		return self.current

	def entity_location_parser(self, properties={}):
		return self.location_from_list_parser(self.regex["item_block_id"], ENTITIES)

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
		return self.location_from_list_parser(self.regex["item_block_id"], POTIONS)

	def sound_parser(self, properties={}):
		return self.location_from_list_parser(self.regex["resource_location"], SOUNDS)

	def gamemode_parser(self, properties={}):
		return self.regex_parser(self.regex["gamemode"], [self.mccstring])

	def sort_parser(self, properties={}):
		return self.regex_parser(self.regex["sort"], [self.mccliteral])

	def item_parser(self, properties={}):
		old_current = self.current
		self.current = self.location_from_list_parser(self.regex["item_block_id"], ITEMS)
		if self.current != old_current:
			return self.nbt_parser(properties)
		return self.current

	def location_from_list_parser(self, regex, possibilities):
		match = regex.match(self.string, self.current)
		if match and match.group(1) != None and match.group(1)[0] == "#" or (
		   match and match.group(2) in possibilities and match.group(1) in [None, "minecraft:"]):
			self.append_region(self.mccliteral, match.start(1), match.end(1))
			self.append_region(self.mccstring, match.start(2), match.end(2))
			self.current = match.end()

		return self.current

	# properties["type"] must equal "word".  This should be done already.
	def json_in_nbt_parser(self, properties):
		if not "escape_depth" in properties:
			escape_depth = 0
		else:
			escape_depth = properties["escape_depth"]

		quote = self.generate_quote(escape_depth)
		if not self.string.startswith(quote, self.current):
			return self.string_parser(properties)

		start = self.current
		self.append_region(self.mccstring, self.current, self.current + len(quote))
		self.current += len(quote)

		old_current = self.current
		properties["escape_depth"] = escape_depth + 1
		self.current = self.json_parser(properties)
		if old_current == self.current:
			self.mccstring.pop()
			properties["escape_depth"] = escape_depth
			self.current = start
			return self.string_parser(properties)

		if not self.string.startswith(quote, self.current):
			if self.current < len(self.string):
				delta = 1
			else:
				delta = -1
			self.append_region(self.invalid, self.current, self.current + delta)
			return self.current + max(0, delta)

		self.append_region(self.mccstring, self.current, self.current + len(quote))
		self.current += len(quote)
		return self.current

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
		if not self.string.startswith(quote, self.current):
			return self.current

		self.append_region(self.mccstring, self.current, self.current + len(quote))
		self.current += len(quote)

		old_current = self.current
		self.current = parser(properties)
		if old_current == self.current:
			self.mccstring.pop()
			return self.current

		if not self.string.startswith(quote, self.current):
			self.mccstring.pop()
			return start
		self.append_region(self.mccstring, self.current, self.current + len(quote))
		return self.current + len(quote)

	def generate_quote(self, escape_depth):
		quotes = ["\"", "\\\"", "\\\\\\\"", "\\\\\\\\\\\\\\\"", "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\""]
		if escape_depth <= 4:
			return quotes[escape_depth]
		
		for i in range(0, escape_depth):
			quote += "\\"
		return quote + self.generate_quote(escape_depth - 1)

	parsers = { # Master list of what function the parser name in commands.json corresponds to
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
		"brigadier:float"            : float_parser,
		"brigadier:double"           : float_parser,
		"brigadier:bool"             : boolean_parser,
		"minecraft:swizzle"          : axes_parser, # any cobination of x, y, and z e.g. x, xy, xz. AKA swizzle
		"minecraft:score_holder"     : score_holder_parser, #Has options to include wildcard or not
		"minecraft:objective"        : username_parser,
		"minecraft:vec3"             : vec3d_parser,
		"minecraft:vec2"             : vec2d_parser,
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
		"minecraft:mob_effect"       : mob_effect_parser,
		"minecraft:sound"            : sound_parser,
		"minecraft:objective_criteria":objective_criteria_parser,
		"minecraft:entity_location": entity_location_parser
	}