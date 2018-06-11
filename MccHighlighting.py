import sublime
import sublime_plugin
import os
import os.path
import re
from .CommandTree import COMMAND_TREE
from .Parser import Parser
from .ColorSchemeEditor import ColorSchemeEditor

class MccHighlightCommand(sublime_plugin.EventListener): #dd

	def on_load(self, view):
		self.run(view)

	def on_modified(self, view):
		self.run(view)

	def on_activated(self, view):
		self.run(view)

	def run(self, view):
		file_name = view.file_name()
		if file_name == None or not (file_name.endswith(".mcc13") or file_name.endswith(".mcfunction")):
			return

		full_region = sublime.Region(0, view.size())
		file_lines = view.lines(full_region)
		parser = Parser(view)

		if file_name.endswith(".mcfunction"):
			first_line_string = view.substr(file_lines[0])
			if not re.match("(?i)[ \t]*#[ \t]*use[ \t]*1\.13[ \t]*parsing[ \t]*$", first_line_string):
				parser.add_regions()
				if os.path.exists(sublime.installed_packages_path() + "/Marshal Command Code.sublime-package"):
					view.settings().set("syntax", "Packages/Marshal Command Code/Minecraft Function.tmLanguage")
				elif os.path.exists(sublime.installed_packages_path() + "/MinecraftCommandCode.sublime-package"):
					view.settings().set("syntax", "Packages/MinecraftCommandCode/Minecraft Function.tmLanguage")
				print("MCC not found")
				return
			else:
				view.settings().set("syntax", "Packages/Text/Plain text.tmLanguage")

		
		for line in file_lines:
			if not line.empty():
				parser.highlight(COMMAND_TREE, line, 0)

		parser.add_regions()

def plugin_loaded():
	sublime.load_settings("Preferences.sublime-settings").add_on_change('color_scheme',ColorSchemeEditor.edit_color_scheme)
	ColorSchemeEditor.edit_color_scheme()