import sublime
import sublime_plugin
import re
import json
import os
from .Parsers import parsers as argument_parsers
from .Parsers import add_regions_flags
from .CommandTree import COMMAND_TREE

comment_regex = re.compile('^\s*#.*$')
command_regex = re.compile('(\s*)([a-z]+)')
colorSchemeColors ={ 
	"mcccomment" : "comment",
	"mcccommand" : "keyword",
	"mccentity"  : "entity.name",
	"mccliteral" : "support.type", #Italic too
	"mccstring"  : "string",
	"mccconstant": "constant.numeric"
}
max_token_ids = {}

class MccHighlightCommand(sublime_plugin.TextCommand):

	def run(self, edit):

		full_region = sublime.Region(0, self.view.size())
		file_lines = self.view.lines(full_region)
		token_id = 0
		for line in file_lines:
			token_id = self.highlight(COMMAND_TREE, line, 0, token_id)

		viewId = self.view.id() # If token_ids aren't overwritten already, remove them from the equation
		if viewId in max_token_ids and max_token_ids[viewId] > token_id:
			for i in range(token_id, max_token_ids[viewId]):
				self.view.add_regions("token" + str(i), [])
		max_token_ids[viewId] = token_id

		print("done")

	def highlight(self, command_tree, line_region, current, token_id):
		if ("redirect" in command_tree):
			redirect_command = command_tree["redirect"][0]
			if redirect_command == "root":
				new_command_tree = COMMAND_TREE
			else:
				new_command_tree = COMMAND_TREE["children"][redirect_command]
			print("Redirecting to: " + redirect_command + ", " + str(current))
			return self.highlight(new_command_tree, line_region, current, token_id)
		elif not "children" in command_tree or current >= line_region.size():
			if not "executable" in command_tree or not command_tree["executable"]:
				self.view.add_regions("token" + str(token_id), [line_region], "invalid.illegal", flags=add_regions_flags)
				return token_id + 1
			return token_id

		line_string = self.view.substr(line_region)
		if re.match(comment_regex, line_string):
			self.view.add_regions("token" + str(token_id), [line_region], "mcccomment", flags=add_regions_flags)
			return token_id + 1
		elif command_tree["type"] == "root":
			command_match = command_regex.search(line_string, current)
			if not command_match:
				return token_id
			command = command_match.group(2)
			if command in command_tree["children"]:
				new_region = sublime.Region(line_region.begin() + command_match.start(2), line_region.begin() + command_match.end(2))
				self.view.add_regions("token" + str(token_id), [new_region], "mcccommand", flags=add_regions_flags)
				return self.highlight(command_tree["children"][command], line_region, command_match.end(), token_id + 1)
			else:
				self.view.add_regions("token" + str(token_id), [line_region], "invalid.illegal", flags=add_regions_flags)
				return token_id + 1
		else:
			while (current < len(line_string) and line_string[current] in " \t\n"):
				current+=1

			if (current >= len(line_string)):
				return token_id

			command_tree = command_tree["children"]
			for key, properties in command_tree.items():
				if properties["type"] == "literal" and current + len(key) <= len(line_string) and line_string[current:current+len(key)] == key:
					literal_region = sublime.Region(line_region.begin() + current, line_region.begin() + current + len(key))
					self.view.add_regions("token" + str(token_id), [literal_region], "mccliteral", flags=add_regions_flags)
					return self.highlight(properties, line_region, current+len(key), token_id + 1)
				elif properties["type"] == "argument":
					parser_name = properties["parser"]
					parse_function = argument_parsers[parser_name]
					if "properties" in properties:
						#print("using properties for " + parser_name)
						new_token_id, new_start = parse_function(self.view, line_region, line_string, current, token_id, properties["properties"])
					else:
						new_token_id, new_start = parse_function(self.view, line_region, line_string, current, token_id)
					if new_token_id > token_id:
						return self.highlight(properties, line_region, new_start, new_token_id)

			error_region = sublime.Region(line_region.begin() + current, line_region.end())
			self.view.add_regions("token" + str(token_id), [error_region], "invalid.illegal", flags=add_regions_flags)

			return token_id + 1
