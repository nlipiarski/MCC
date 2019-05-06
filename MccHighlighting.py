import sublime
import sublime_plugin
from .CommandTree import COMMAND_TREE
from .Parser import *
from .ColorSchemeEditor import ColorSchemeEditor

class MccHighlightCommand(sublime_plugin.EventListener):

	def on_load(self, view):
		self.run(view)

	def on_modified(self, view):
		self.run(view)

	def on_activated(self, view):
		self.run(view)

	def run(self, view):
		file_name = view.file_name()
		if file_name == None or not file_name.endswith(".mcfunction"):
			return

		full_region_string = view.substr(sublime.Region(0, view.size()))
		file_lines = full_region_string.split("\n")
		allow_custom_tags = sublime.load_settings("Preferences.sublime-settings").get("mcc_custom_tags", False)

		PARSER.reset(view, allow_custom_tags)
		region_start = 0;

		i = 0
		for line in file_lines:
			if len(line) > 0:
				PARSER.highlight(COMMAND_TREE, line, 0, region_start)
				PARSER.add_regions(line_num=i)
				i += 1
			region_start += len(line) + 1

def plugin_loaded():
	parser = Parser()
	settings = sublime.load_settings("Preferences.sublime-settings")
	settings.add_on_change('color_scheme',ColorSchemeEditor.edit_color_scheme)
	ColorSchemeEditor.edit_color_scheme()

	allowed_autocomplete = settings.get("auto_complete_selector", "")
	if not "text.plain" in allowed_autocomplete:
		if len(allowed_autocomplete) > 0:
			allowed_autocomplete += ", "
		allowed_autocomplete += "text.plain"
		print(allowed_autocomplete)
		settings.set("auto_complete_selector", allowed_autocomplete)