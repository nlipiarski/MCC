import sublime, sublime_plugin
import re
import json
import os

smeltJsonRegions = []
codeRegions = []
codeType = []

class UpdateGutterCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		if(self.view.file_name().find("mcc")>0):
			self.view.add_regions("smeltJson", [], "source")
			for blockType in ["impulse", "repeating", "chain", "impulse-chain", "repeating-chain"]:
				self.view.add_regions(blockType, [], "source")
				self.view.add_regions(blockType + "-conditional", [], "source")

			smeltJsonRegions = self.view.find_all(">\{.*\}")
			self.view.add_regions("smeltJson",smeltJsonRegions)
			codeRegions = []
			codeType = []
			lastType = "impulse"
			lastConditional = ""
			for i in range(len(smeltJsonRegions)):
				if (i<(len(smeltJsonRegions)-1)):
					codeRegions.append(sublime.Region(smeltJsonRegions[i].end()+1, smeltJsonRegions[i+1].begin()-1))
				elif (smeltJsonRegions[i].end()+1<self.view.size()):
					codeRegions.append(sublime.Region(smeltJsonRegions[i].end()+1, self.view.size()))

				jsonString = self.view.substr(smeltJsonRegions[i])
				jsonString = jsonString[jsonString.find("{"):]
				smeltJson = json.loads(jsonString)
				newType = ""
				newConditional = ""
				try: 
					conditional = smeltJson["conditional"]
					if (conditional):
						newConditional = "-conditional"
					else:
						newConditional = ""
				except KeyError:
					newConditional = lastConditional

				try:
					if (smeltJson["type"] in ["impulse", "repeating", "chain", "impulse-chain", "repeating-chain"]):
						newType = smeltJson["type"]
					else:
						newType = lastType
				except KeyError:
					newType = lastType

				codeType.append(newType+newConditional)
				for line in self.view.lines(codeRegions[-1]):
					if(re.search(r"^\s*\/",self.view.substr(line))):
						regions = []
						if (self.view.get_regions(newType+newConditional)!=None and len(self.view.get_regions(newType+newConditional)) > 0):
							regions.extend(self.view.get_regions(newType+newConditional))
							regions.append(line)
						else:
							regions = [line]
						
						icon = self.get_icon(newType + newConditional)
						self.view.add_regions(newType+newConditional, regions, "source",  icon, sublime.PERSISTENT | sublime.HIDDEN)

					elif (re.search(r"^\s*\#",self.view.substr(line))):
						newType = "impulse"
						newConditional = ""
						lastType = "impulse"
						lastConditional = ""

				lastType = newType
				lastConditional = newConditional

	def get_icon(self, icon):
		if int(sublime.version())<3014:
			path = "../MinecraftCommandCode"
			extension = ""
		else:
			path = os.path.realpath(__file__)
			root = os.path.split(os.path.dirname(path))[1]
			path = "Packages/" + os.path.splitext(root)[0]
			extension = ".png"
		return path + "/icons/" + icon + extension

class UpdateGutter(sublime_plugin.EventListener):
	def on_load(self, view):
		if (view.file_name().endswith(".mcc")):
			view.run_command("update_gutter")

	def on_modified(self, view):
		if (view.file_name().endswith(".mcc")):
			view.run_command("update_gutter")

	def on_activate(self, view):
		if (view.file_name().endswith(".mcc")):
			view.run_command("update_gutter")

	def on_new(self, view):
		if (view.file_name().endswith(".mcc")):
			view.run_command("update_gutter")