import sublime
import sublime_plugin
from .MccHighlighting import MccHighlightCommand

class ToggleCustomNbtCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		settings = sublime.load_settings("Preferences.sublime-settings")
		allow_custom = settings.get("mcc_custom_tags", False)
		allow_custom = settings.set("mcc_custom_tags", not allow_custom)
		view = sublime.active_window().active_view()
		MccHighlightCommand().run(view)
		return None

	def is_enabled(self):
		return True

	def description(self):
		settings = sublime.load_settings("Preferences.sublime-settings")
		allow_custom = settings.get("mcc_custom_tags", False)

		if allow_custom:
			return "Disable custom NBT tags"
		else:
			return "Allow custom NBT tags"

	def input(self, args):
		return None