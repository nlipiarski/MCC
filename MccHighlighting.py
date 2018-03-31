import sublime
import sublime_plugin
import os
import os.path
import plistlib
import re
from .CommandTree import COMMAND_TREE
from .Parser import Parser

color_scheme_colors ={ 
	"mcccomment"       : ["comment"],
	"mcccommand"       : ["keyword"],
	"mccentity"        : ["entity.name"],
	"mccliteral"       : ["support.type", "support.constant"],
	"mccstring"        : ["string"],
	"mccconstant"      : ["constant.numeric"]
}
max_token_ids = {}

class MccHighlightCommand(sublime_plugin.EventListener):

	def on_load(self, view):
		self.run(view)

	def on_modified(self, view):
		self.run(view)

	def on_activated(self, view):
		self.run(view)

	def run(self, view):
		file_name = view.file_name()
		if file_name == None or len(file_name) < 6 or file_name[-6:] != ".mcc13":
			return
		self.edit_color_scheme()
		full_region = sublime.Region(0, view.size())
		file_lines = view.lines(full_region)
		token_id = 0
		parser = Parser(view)

		for line in file_lines:
			token_id, _ = parser.highlight(COMMAND_TREE, line, 0)

		viewId = view.id() # If token_ids aren't overwritten already, remove them from the equation
		if viewId in max_token_ids and max_token_ids[viewId] > token_id:
			for i in range(token_id, max_token_ids[viewId]):
				view.add_regions("token" + str(i), [])
		max_token_ids[viewId] = token_id

	@staticmethod
	def edit_color_scheme():
		original_color_scheme = sublime.load_settings("Preferences.sublime-settings").get('color_scheme')
		if original_color_scheme.find("(MCC)") > -1:
			return

		scheme_data = plistlib.readPlistFromBytes(sublime.load_binary_resource(original_color_scheme))
		if os.path.exists(sublime.packages_path() + "/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".tmTheme"):
			sublime.load_settings("Preferences.sublime-settings").set("color_scheme", "Packages/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".tmTheme")
			sublime.save_settings("Preferences.sublime-settings")
			return
		elif scheme_data["name"].find("(MCC)") > -1:
			return
		try:
			new_background_rgb = "#000000"
			if "background" in scheme_data["settings"][0]["settings"]:
				original_bg = scheme_data["settings"][0]["settings"]["background"]
				background_rgb = max(1, int(original_bg[1:], 16))
				new_background_rgb = "#{0:0>6x}".format(background_rgb - 1)
			
			for mcc_scope, copy_scopes in color_scheme_colors.items():
				for copy_scope in copy_scopes:
					found = False
					for item in scheme_data["settings"]:
						if "scope" in item:
							comma_index = item["scope"].find(",")
							space_index = item["scope"].find(" ")
							if comma_index < 0 and space_index < 0:
								scope_from_scheme = item["scope"]
							else: 
								if comma_index < 0 or space_index < 0:
									scope_from_scheme = item["scope"][:max(comma_index, space_index)]
								else:
									scope_from_scheme = item["scope"][:min(comma_index, space_index)]
							if copy_scope == scope_from_scheme:
								scheme_data["settings"].append({
									"scope": mcc_scope,
									"settings": {
										"foreground": item["settings"]["foreground"],
										"background": new_background_rgb
									}})
								found = True
								break
					if found:
						break
				else:
					sublime.error_message("MCC couldn't find a matching scope for " + copy_scope)
			if not os.path.exists(sublime.packages_path() + "/MCC/ModifiedColorSchemes/"):
				os.makedirs(sublime.packages_path() + "/MCC/ModifiedColorSchemes/")

			new_file_name = "/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".tmTheme"
			scheme_data["name"] = scheme_data["name"] + " (MCC)"
			plistlib.writePlist(scheme_data, sublime.packages_path() + new_file_name)

			sublime.load_settings("Preferences.sublime-settings").set("color_scheme", "Packages" + new_file_name)
			sublime.save_settings("Preferences.sublime-settings")
		except Exception as e:
			# sublime.error_message("MCC couldn't convert your current color scheme")
			print(e)
			sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

def plugin_loaded():
	sublime.load_settings("Preferences.sublime-settings").add_on_change('color_scheme',MccHighlightCommand.edit_color_scheme)