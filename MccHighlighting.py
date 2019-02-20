import sublime
import sublime_plugin
from .CommandTree import COMMAND_TREE
from .Parser import Parser
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

		full_region = sublime.Region(0, view.size())
		file_lines = view.lines(full_region)
		allow_custom_tags = sublime.load_settings("Preferences.sublime-settings").get("mcc_custom_tags", False)
		parser = Parser(view, allow_custom_tags)
		
		i = 0
		for line in file_lines:
			if not line.empty():
				parser.highlight(COMMAND_TREE, line, 0)
				parser.add_regions(line_num=i)
				i += 1

def plugin_loaded():
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