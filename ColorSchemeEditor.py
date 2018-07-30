import colorsys
import json
import os
import os.path
import plistlib
import re
import sublime
import sublime_plugin

class ColorSchemeEditor:
	CSS_COLORS = {"aliceblue":"#f0f8ff","antiquewhite":"#faebd7","aqua":"#00ffff","aquamarine":"#7fffd4","azure":"#f0ffff","beige":"#f5f5dc","bisque":"#ffe4c4","black":"#000000","blanchedalmond":"#ffebcd","blue":"#0000ff","blueviolet":"#8a2be2","brown":"#a52a2a","burlywood":"#deb887","cadetblue":"#5f9ea0","chartreuse":"#7fff00","chocolate":"#d2691e","coral":"#ff7f50","cornflowerblue":"#6495ed","cornsilk":"#fff8dc","crimson":"#dc143c","cyan":"#00ffff","darkblue":"#00008b","darkcyan":"#008b8b","darkgoldenrod":"#b8860b","darkgray":"#a9a9a9","darkgreen":"#006400","darkgrey":"#a9a9a9","darkkhaki":"#bdb76b","darkmagenta":"#8b008b","darkolivegreen":"#556b2f","darkorange":"#ff8c00","darkorchid":"#9932cc","darkred":"#8b0000","darksalmon":"#e9967a","darkseagreen":"#8fbc8f","darkslateblue":"#483d8b","darkslategray":"#2f4f4f","darkslategrey":"#2f4f4f","darkturquoise":"#00ced1","darkviolet":"#9400d3","deeppink":"#ff1493","deepskyblue":"#00bfff","dimgray":"#696969","dimgrey":"#696969","dodgerblue":"#1e90ff","firebrick":"#b22222","floralwhite":"#fffaf0","forestgreen":"#228b22","fuchsia":"#ff00ff","gainsboro":"#dcdcdc","ghostwhite":"#f8f8ff","gold":"#ffd700","goldenrod":"#daa520","gray":"#808080","green":"#008000","greenyellow":"#adff2f","grey":"#808080","honeydew":"#f0fff0","hotpink":"#ff69b4","indianred":"#cd5c5c","indigo":"#4b0082","ivory":"#fffff0","khaki":"#f0e68c","lavender":"#e6e6fa","lavenderblush":"#fff0f5","lawngreen":"#7cfc00","lemonchiffon":"#fffacd","lightblue":"#add8e6","lightcoral":"#f08080","lightcyan":"#e0ffff","lightgoldenrodyellow":"#fafad2","lightgray":"#d3d3d3","lightgreen":"#90ee90","lightgrey":"#d3d3d3","lightpink":"#ffb6c1","lightsalmon":"#ffa07a","lightseagreen":"#20b2aa","lightskyblue":"#87cefa","lightslategray":"#778899","lightslategrey":"#778899","lightsteelblue":"#b0c4de","lightyellow":"#ffffe0","lime":"#00ff00","limegreen":"#32cd32","linen":"#faf0e6","magenta":"#ff00ff","maroon":"#800000","mediumaquamarine":"#66cdaa","mediumblue":"#0000cd","mediumorchid":"#ba55d3","mediumpurple":"#9370db","mediumseagreen":"#3cb371","mediumslateblue":"#7b68ee","mediumspringgreen":"#00fa9a","mediumturquoise":"#48d1cc","mediumvioletred":"#c71585","midnightblue":"#191970","mintcream":"#f5fffa","mistyrose":"#ffe4e1","moccasin":"#ffe4b5","navajowhite":"#ffdead","navy":"#000080","oldlace":"#fdf5e6","olive":"#808000","olivedrab":"#6b8e23","orange":"#ffa500","orangered":"#ff4500","orchid":"#da70d6","palegoldenrod":"#eee8aa","palegreen":"#98fb98","paleturquoise":"#afeeee","palevioletred":"#db7093","papayawhip":"#ffefd5","peachpuff":"#ffdab9","peru":"#cd853f","pink":"#ffc0cb","plum":"#dda0dd","powderblue":"#b0e0e6","purple":"#800080","rebeccapurple":"#663399","red":"#ff0000","rosybrown":"#bc8f8f","royalblue":"#4169e1","saddlebrown":"#8b4513","salmon":"#fa8072","sandybrown":"#f4a460","seagreen":"#2e8b57","seashell":"#fff5ee","sienna":"#a0522d","silver":"#c0c0c0","skyblue":"#87ceeb","slateblue":"#6a5acd","slategray":"#708090","slategrey":"#708090","snow":"#fffafa","springgreen":"#00ff7f","steelblue":"#4682b4","tan":"#d2b48c","teal":"#008080","thistle":"#d8bfd8","tomato":"#ff6347","turquoise":"#40e0d0","violet":"#ee82ee","wheat":"#f5deb3","white":"#ffffff","whitesmoke":"#f5f5f5","yellow":"#ffff00","yellowgreen":"#9acd32"}

	COLOR_SCHEME_COLORS ={ 
		"mcccomment"	   : ["comment"],
		"mcccommand"	   : ["keyword.control", "source"],
		"mccentity"		: ["entity.name.function", "entity", "source"],
		"mccliteral"	   : ["support.type", "support", "support.constant", "support.function.builtin", "support.class", "source"],
		"mccstring"		: ["string"],
		"mccconstant"	  : ["constant.numeric", "constant", "source"]
	}

	@staticmethod
	def edit_color_scheme():
		original_color_scheme = sublime.load_settings("Preferences.sublime-settings").get('color_scheme')
		if original_color_scheme.find("(MCC)") > -1:
			return
		elif original_color_scheme.endswith("sublime-color-scheme"):
			ColorSchemeEditor.edit_json_color_scheme(original_color_scheme)
		else:
			ColorSchemeEditor.edit_plist_color_scheme(original_color_scheme)

	@staticmethod
	def edit_json_color_scheme(original_color_scheme):
		file_contents = sublime.load_resource(original_color_scheme)
		contents_comments_removed = re.sub("//[^\n]+\n", "\n", file_contents)
		sanitized_input = re.sub(",\s*([\}\]])", r"\1", contents_comments_removed, flags=re.MULTILINE)
		try:
			scheme_data = json.loads(sanitized_input)
		except Exception as e:
			if len(sanitized_input) > 0:
				print("Error loading color scheme")
				print("Scheme: " + original_color_scheme)
				print("sanitized contents: " + sanitized_input)
			return

		if os.path.exists(sublime.packages_path() + "/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".sublime-color-scheme"):
			sublime.load_settings("Preferences.sublime-settings").set("color_scheme", "Packages/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".sublime-color-scheme")
			sublime.save_settings("Preferences.sublime-settings")
			return
		elif scheme_data["name"].find("(MCC)") > -1:
			return

		try:
			if "background" in  scheme_data["globals"]:
				background_color = ColorSchemeEditor.get_rgb_color(scheme_data["globals"]["background"], scheme_data)
				new_background_rgb = ColorSchemeEditor.change_color_by_one(background_color)
			else:
				new_background_rgb = "#000000"

			scheme_data = ColorSchemeEditor.add_mcc_scopes(scheme_data, True, new_background_rgb)

			if not os.path.exists(sublime.packages_path() + "/MCC/ModifiedColorSchemes/"):
				os.makedirs(sublime.packages_path() + "/MCC/ModifiedColorSchemes/")

			new_file_name = "/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".sublime-color-scheme"
			scheme_data["name"] = scheme_data["name"] + " (MCC)"
			scheme_file = open(sublime.packages_path() + new_file_name, "w")
			scheme_file.write(json.dumps(scheme_data))

			sublime.load_settings("Preferences.sublime-settings").set("color_scheme", "Packages" + new_file_name)
			sublime.save_settings("Preferences.sublime-settings")
		except Exception as e:
			print("Error on JSON theme conversion")
			print(e)
			sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

	@staticmethod
	def edit_plist_color_scheme(original_color_scheme):
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
				new_background_rgb = ColorSchemeEditor.change_color_by_one(scheme_data["settings"][0]["settings"]["background"])
			
			scheme_data = ColorSchemeEditor.add_mcc_scopes(scheme_data, False, new_background_rgb)

			if not os.path.exists(sublime.packages_path() + "/MCC/ModifiedColorSchemes/"):
				os.makedirs(sublime.packages_path() + "/MCC/ModifiedColorSchemes/")

			new_file_name = "/MCC/ModifiedColorSchemes/" + scheme_data["name"] + ".tmTheme"
			scheme_data["name"] = scheme_data["name"] + " (MCC)"
			plistlib.writePlist(scheme_data, sublime.packages_path() + new_file_name)

			sublime.load_settings("Preferences.sublime-settings").set("color_scheme", "Packages" + new_file_name)
			sublime.save_settings("Preferences.sublime-settings")
		except Exception as e:
			# sublime.error_message("MCC couldn't convert your current color scheme")
			print("Error on tmTheme conversion")
			print(e)
			sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

	@staticmethod
	def add_mcc_scopes(scheme_data, is_json, new_background_rgb):
		if is_json:
			scope_rules_key = "rules"
		else:
			scope_rules_key = "settings"

		found = {}
		for scheme_item in scheme_data[scope_rules_key]:
			if "scope" in scheme_item:
				scheme_scope = SchemeScope(scheme_item["scope"])

				for mcc_scope, possible_real_scopes in ColorSchemeEditor.COLOR_SCHEME_COLORS.items():

					if not mcc_scope in found:
						for possible_scope in possible_real_scopes:
							if scheme_scope.matches(possible_scope):
								if is_json:
									new_rule = {
										"scope": mcc_scope,
										"foreground": scheme_item["foreground"],
										"background": new_background_rgb
									}
									if "font_style" in scheme_item:
										new_rule["font_style"] = scheme_item["font_style"]
								else:
									new_rule = {
										"scope": mcc_scope,
										"settings": {
											"foreground": scheme_item["settings"]["foreground"],
											"background": new_background_rgb
										}}

								scheme_data[scope_rules_key].append(new_rule)
								found[mcc_scope] = True
								break
		
		#checks if all are found
		for mcc_scope, _ in ColorSchemeEditor.COLOR_SCHEME_COLORS.items():
			if not mcc_scope in found:
				sublime.error_message("MCC couldn't find a matching scope for " + mcc_scope)

		return scheme_data

	# Color should be a hex rgba vaue includding the leading '#'
	@staticmethod
	def change_color_by_one(color):
		rgba = ColorSchemeEditor.full_hex_chars(color)

		if len(rgba) == 9:
			rgb = rgba[1:-2]
			alpha = rgba[-2:]
		else:
			rgb = rgba[1:]
			alpha = ""

		original_color_decimal = int(rgb, 16)
		if original_color_decimal == 0:
			new_color_decimal = 1

		elif original_color_decimal % 65536 == 0: # For when green and blue are 0 e.g. #340000
			new_color_decimal = original_color_decimal - 65536

		elif original_color_decimal % 256 == 0: # For when blue is 0 e.g. #090300
			new_color_decimal = original_color_decimal - 256

		else: # Just the normal deal like #0903C5
			new_color_decimal = original_color_decimal - 1

		return "#{0:0>6X}{1}".format(new_color_decimal, alpha)

	@staticmethod
	def get_rgb_color(scope_defined_color_raw, scheme):
		scope_defined_color = scope_defined_color_raw.strip()
		if scope_defined_color.startswith("#"):
			return ColorSchemeEditor.full_hex_chars(scope_defined_color.strip())
		elif scope_defined_color.startswith("var("): 
			return ColorSchemeEditor.get_rgb_color(scheme["variables"][scope_defined_color[4:-1]], scheme)

		elif scope_defined_color.startswith("rgb("): #rgb(255, 0, 0)
			rgb_match = re.match("rgb\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)", scope_defined_color)
			red = int(rgb_match.group(1))
			green = int(rgb_match.group(2))
			blue = int(rgb_match.group(3))
			return "#{0:0>2X}{1:0>2X}{2:0>2X}00".format(red, green, blue)

		elif scope_defined_color.startswith("rgba("): #rgba(255, 0, 0, 0.5)
			rgba_match = re.match("rgb\(\s*(\d+),\s*(\d+),\s*(\d+)\s*,\s*(1(\.0+)?|0(\.\d+)?)\s*\)", scope_defined_color)
			red = int(rgba_match.group(1))
			green = int(rgba_match.group(2))
			blue = int(rgba_match.group(3))
			alpha = int(float(rgba_match.group(4)) * 255)
			return "#{0:0>2X}{1:0>2X}{2:0>2X}{3:0>2X}".format(red, green, blue, alpha)

		elif scope_defined_color.startswith("hsl("): #hsl(0, 100%, 100%)
			hsl_match = re.match("hsl\(\s*(\d+),\s*(\d+)%,\s*(\d+)%\s*\)", scope_defined_color)
			hue = float(hsl_match.group(1)) / 360
			saturation = float(hsl_match.group(2)) / 100
			lightness = float(hsl_match.group(3)) / 100
			red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
			return "#{0:0>2X}{1:0>2X}{2:0>2X}00".format(int(red * 255), int(green * 255), int(blue * 255))

		elif scope_defined_color.startswith("hsla("): #hsla(0, 100%, 100%, 0.5)
			hsla_match = re.match("hsl\(\s*(\d+),\s*(\d+)%,\s*(\d+)%,\s*(1(\.0+)?|0(\.\d+)?)\s*\)", scope_defined_color)
			hue = float(hsla_match.group(1)) / 360
			saturation = float(hsla_match.group(2)) / 100
			lightness = float(hsla_match.group(3)) / 100
			alpha = int(float(hsla_match.group(4)) * 255)
			red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
			return "#{0:0>2X}{1:0>2X}{2:0>2X}{3:0>2X}".format(int(red * 255), int(green * 255), int(blue * 255), alpha)

		elif scope_defined_color.startswith("color("): # can have all of the above plus blend, blenda, alpha, a.  Blend percent is percent of first color
			contents, modifier = ColorSchemeEditor.get_color_prefix(scope_defined_color[6:-1])
			color = ColorSchemeEditor.get_rgb_color(contents, scheme)

			if len(modifier) == 0:
				return color
			else:
				return ColorSchemeEditor.modify_color(ColorSchemeEditor.full_hex_chars(color), modifier, scheme)
		else:
			return CSS_COLORS[scope_defined_color]

	@staticmethod
	def modify_color(rgb1, modifier, scheme):
		if modifier.startswith("alpha") or modifier.startswith("a"):
			alpha_match = re.match("(?:a|alpha)\(\s*(1(\.0+)?|0(\.\d+)?)\s*\)", modifier)
			if len(rgb1) == 9:
				color = rgb1[0:7]
			else:
				color = rgb1

			alpha = int(float(alpha_match.group(1)) * 255)
			return "{0}{1:0>2x}".format(color, alpha)

		elif modifier.startswith("blend("):
			content = modifier[6:-1].strip()
			color2, data = ColorSchemeEditor.get_color_prefix(content)
			rgb2 = ColorSchemeEditor.get_rgb_color(color2, scheme)
			percent, method = data.split("%")
			if len(rgb2) == 9:
				alpha = rgb2[-2:]
				rgb2 = rgb2[:-2]
			else:
				alpha = ""

			if len(method.strip()) == 0 or method.strip() == "rgb":
				blend = ColorSchemeEditor.rgb_blend(rgb1[1:7], rgb2[1:7], float(percent) / 100)
			else:
				blend = ColorSchemeEditor.hsl_blend(rgb1[1:7], rgb2[1:7], float(percent) / 100)

			return "#{0}{1}".format(blend, alpha)

		elif modifier.startswith("blenda("):
			content = modifier[7:-1].strip()

			color2, data = ColorSchemeEditor.get_color_prefix(content)
			rgb2 = ColorSchemeEditor.get_rgb_color(color2, scheme)

			if len(rgb1) < 8:
				alpha1 = 0
			else:
				alpha1 = int(rgb1[-2:], 16)

			if len(rgb2) < 8:
				alpha2 = 0
			else:
				alpha2 = int(rgb2[-2:], 16)

			alpha = (alpha1 + alpha2) / 2

			percent, method = data.split("%")

			if len(method.strip()) == 0 or method.strip() == "rgb":
				blend = ColorSchemeEditor.rgb_blend(rgb1[:7], rgb2[:7], float(percent) / 100)
			else:
				blend = ColorSchemeEditor.hsl_blend(rgb1[:7], rgb2[:7], float(percent) / 100)

			return "{0}{1:0>2x}".format(blend, alpha)

	@staticmethod
	def rgb_blend(rgb1, rgb2, percent):
		red1, green1, blue1 = ColorSchemeEditor.split_rgb(rgb1)
		red2, green2, blue2 = ColorSchemeEditor.split_rgb(rgb2)

		red = percent * float(red1) + (1 - percent) * float(red2)
		green = percent * float(green1) + (1 - percent) * float(green2)
		blue = percent * float(blue1) + (1 - percent) * float(blue2)

		return "#{0:0>2x}{1:0>2x}{2:0>2x}".format(int(red), int(green), int(blue))

	@staticmethod
	def hsl_blend(rgb1, rgb2, percent):
		red1, green1, blue1 = ColorSchemeEditor.split_rgb(rgb1)
		red2, green2, blue2 = ColorSchemeEditor.split_rgb(rgb2)

		h1, l1, s1 = colorsys.rgb_to_hls(float(red1) / 255, float(green1) / 255, float(blue1) / 255)
		h2, l2, s2 = colorsys.rgb_to_hls(float(red2) / 255, float(green2) / 255, float(blue2) / 255)

		if h2 - h1 > 0.5:
			h1 = h1 + 1
		elif h1 - h2 > 0.5:
			h2 = h2 + 1

		h = (percent * h2 + (1 - percent) * h1) % 1
		s = percent * s1 + (1 - percent) * s2
		l = percent * l1 + (1 - percent) * l2
		l = (1 - percent) * l1 + percent * l2

		red, green, blue = colorsys.hls_to_rgb(h, l, s)

		return "#{0:0>2x}{1:0>2x}{2:0>2x}".format(int(red * 255), int(green * 255), int(blue * 255))

	@staticmethod
	def get_color_prefix(string):
		color_function_match = re.match("\w+\([^\)]+\)", string)
		if color_function_match:
			color = color_function_match.group()
			extras = string[color_function_match.end():].strip()
		else:
			space_index = string.find(" ")
			if space_index >= 0:
				color = string[:space_index]
				extras = string[space_index:].strip()
			else:
				color = string
				extras = ""

		return (color.strip(), extras.strip())

	@staticmethod #Pads out a hex code to 6 or 8 characters.  Must have '#'
	def full_hex_chars(color):
		if len(color) <= 5:
			rgb = "#"
			for char in color[1:]:
				rgb = rgb + char + char
		else:
			rgb = color[:7]
		return rgb

	@staticmethod
	def split_rgb(rgb): #Ignores alpha, returns (red, green, blue)
		return (int(rgb[1:3], 16), int(rgb[3:5], 16), int(rgb[5:7], 16))

class SchemeScope:

	def __init__(self, scope_pattern):
		self.top_node = self.parse_scope(scope_pattern)

	def parse_scope(self, scope_pattern):
		scopes = scope_pattern.split(",")
		scope_nodes = []

		for scope in scopes:
			tokens = self.tokenizeScope(scope)
			operators = []
			output = []

			for token in tokens:
				if token in "&|-":
					while (len(operators) > 0 and self.isGreaterPrecedence(operators[-1], token) and operators[-1] != "("):
						output.append(operators.pop())
					operators.append(token)
				elif token == "(":
					operators.append(token)
				elif token == ")":
					while operators[-1] != "(":
						output.append(operators.pop())
					operators.pop()
				else:
					output.append(token)
				
			while len(operators) > 0:
				output.append(operators.pop())

			scope_nodes.append(self.create_node(output[::-1]))

		if len(scope_nodes) > 1:
			return SchemeScopeNode(SchemeScopeNode.LIST, scope_nodes)
		else:
			return scope_nodes[0]

	def create_node(self, reverse_polish):
		stack = []

		while len(reverse_polish) > 0:
			token = reverse_polish.pop()
			if token in "&|-":
				right = stack.pop()
				left = stack.pop()
				new_node = SchemeScopeNode(SchemeScopeNode.getType(token), [left, right])
				stack.append(new_node)
			else:
				stack.append(SchemeScopeNode(SchemeScopeNode.TERMINAL, [token]))

		return stack.pop()

	def isGreaterPrecedence(self, operator1, operator2):
		return "-|&".find(operator1) >= "-|&".find(operator2)

	def tokenizeScope(self, scope_pattern):
		tokens = []
		token_start = 0

		for i in range(0, len(scope_pattern)):
			if scope_pattern[i] in "()&|-":
				last_token = scope_pattern[token_start:i].strip()
				if len(last_token) > 0:
					tokens.append(last_token)

				tokens.append(scope_pattern[i])
				token_start = i + 1

		final_token = scope_pattern[token_start:].strip()
		if len(final_token) > 0:
			tokens.append(final_token)

		return tokens

	def matches(self, scope):
		return self.top_node.matches(scope)

class SchemeScopeNode:
	# Precedence of operators is & | -
	INTERSECTION = 0
	UNION = 1
	DIFFERENCE = 2
	LIST = 3
	TERMINAL = 4

	def __init__(self, node_type, children):
		self.type = node_type
		self.children = children

	@staticmethod
	def getType(operator):
		return "&|-".find(operator)

	def matches(self, scope):
		if self.type == self.INTERSECTION:
			return self.children[0].matches(scope) and self.children[1].matches(scope)

		elif self.type == self.UNION:
			return self.children[0].matches(scope) or self.children[1].matches(scope)

		elif self.type == self.DIFFERENCE:
			return self.children[0].matches(scope) and not self.children[1].matches(scope)

		elif self.type == self.LIST:
			for child in self.children:
				if child.matches(scope):
					return True
			return False

		else:
			return scope.startswith(self.children[0])

