import json, sublime, sublime_plugin, os
from .CommandTree import COMMAND_TREE

class CompletionsBuilderCommand(sublime_plugin.TextCommand):

	def run(self, args):
		completions_file_path = sublime.packages_path() + "/MCC/MCC.sublime-completions"
		if os.path.exists(completions_file_path):
			os.remove(completions_file_path)

		gamerule_data = COMMAND_TREE["children"]["gamerule"]
		completions = ["gamerule"]

		for rule in gamerule_data["children"].keys():
			gamerule_type = gamerule_data["children"][rule]["children"]["value"]["parser"][10:]
			completion = {
				"trigger": "gamerule " + rule,
				"contents": "gamerule " + rule + " ${1:[" + gamerule_type + "]}"
			}
			completions.append(completion)

		completions_file = open(completions_file_path, "w")
		completions_data = {
			"scope": "source.mcc",
			"completions": completions
		}
		json.dump(completions_data, completions_file, indent="\t")
		completions_file.close()
