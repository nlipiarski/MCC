import sublime
import sublime_plugin
import cProfile, pstats, io
from .CommandTree import COMMAND_TREE
from .Parser import *
from .ColorSchemeEditor import ColorSchemeEditor

class MccProfileCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		profiler = cProfile.Profile()
		profiler.enable()
		view = self.view
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
				i += 1
			region_start += len(line) + 1

		PARSER.add_regions(line_num=i)
		profiler.disable()
		s = io.StringIO()
		profile_stats = pstats.Stats(profiler, stream=s)
		profile_stats.print_stats()

		stat_file = open(sublime.packages_path() + "/MCC/MCCStats.txt", "w")
		stat_file.write(s.getvalue())
		stat_file.close()
