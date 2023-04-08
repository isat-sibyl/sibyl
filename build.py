from datetime import date
import glob

import json
import re
import time
from xml.etree.ElementTree import ParseError
import os
import shutil
import logging

from bs4 import BeautifulSoup, Tag
import yaml

var_pattern = re.compile(r"{{\s*([^\s{}]+)\s*(\|\s*(\S+)\s*)?}}")

class Parser:
	def get_debug_location(self):
		result = self.context.get('PATH', 'PATH NOT FOUND') + " " + str(self.context["LOCATION"])
		return result
		
	def resolve_var(self, string):
		"""Resolve a variable from the context. Resolves all nested variables.
		Returns None if the variable is not found.
		Raises ParseError if the variable is a string and cannot have further nested variables."""
		split = string.split(".", 1)
		result = self.context
		while True:
			result = result.get(split[0], None)
			if result is None:
				return None
			elif len(split) == 1:
				return result
			elif isinstance(result, str):
				raise ParseError(string + " resolved to string and cannot have further nested variables. At " + self.get_debug_location())
			split = split[1].split(".", 1)
	
	def get_var(self, match):
		"""Get a variable from the context. Returns the variable if found, otherwise returns the original string."""
		result = self.resolve_var(match.group(1))
		if result is None:
			result = match.group(3)
		if result is None:
			return "{{" + match.group(1) + "}}"
		return str(result)

	def replace_var(self, string):
		"""Replace all variables in a string with their values from the context."""
		while re.search(var_pattern, string) is not None: # This might have performance issues since it's treating the whole page as a single string
			new_string = re.sub(var_pattern, self.get_var, string)
			if new_string == string:
				break
			string = new_string
		return string
	
	def find_by_attribute(self, value):
		"""Check if a value is a string or list that contains a variable."""
		try:
			return re.match(var_pattern, value)
		except TypeError: # is list
			for v in value:
				return re.match(var_pattern, v)
	
	def vars_replacement(self, element):
		"""
			Replace all variables in an element and its descendants.
			Variables are replaced in the following places:
			- text contents
			- attribute values
		"""
		# replace all text contents
		variables = element.find_all(text = var_pattern)
		for variable in variables:
			variable.replace_with(self.replace_var(variable.string))
		
		# replace all attribute values for all descendants
		variables = element.find_all(lambda x: any(self.find_by_attribute(value) for value in x.attrs.values()))
		for variable in variables:
			# replace all attribute values
			for key, value in variable.attrs.items():
				try:
					variable[key] = self.replace_var(value)
				except TypeError: # is list
					variable[key] = [self.replace_var(v) for v in value]


	def from_kebab_to_camel(self, kebab_str):
		"""Convert a kebab-case string to camelCase."""
		components = kebab_str.split('-')
		return components[0] + ''.join(x.title() for x in components[1:])

	def get_component_path(self, name):
		# ensure that the component exists
		for path in self.settings["COMPONENTS_PATH"]:
			if os.path.isfile(path + "/" + name + ".html"):
				return path
		raise ParseError("Component " + name + " not found. At " + self.get_debug_location())
	
	def process_attrs(self, tag : Tag, first_child : Tag):
		"""Process the attributes of a component tag."""
		for key, value in tag.attrs.items():
			if key == "name":
				continue
			elif key == "style":
				# append to existing style
				old_style = first_child.get('style', "")
				if old_style and not old_style.endswith(";"):
					old_style += ";"
				first_child['style'] = old_style + value
			elif key == "id":
				# replace existing id
				first_child['id'] = value
			elif key == "class":
				# append to existing class
				old_class = first_child.get('class', [])
				first_child['class'] = old_class + value
			elif value.startswith == "{{" and value.endswith == "}}":
				# add variable to component's context
				self.context[self.from_kebab_to_camel(key)] = var_pattern.match(value).group(1)
			else:
				# add literal to component's context
				self.context[self.from_kebab_to_camel(key)] = value
	    
	def components_replacement(self, tag : Tag):
		"""Replace a component tag with the component's HTML. Returns the used styles and scripts."""
		self.context["LOCATION"].append(tag["name"])
		
		path = self.get_component_path(tag["name"])
		
		component_soup = BeautifulSoup(open(path + "/" + tag["name"] + ".html", encoding = 'utf-8'), 'html.parser')
		first_child = component_soup.find("template").find()

		required_styles = set()
		required_scripts = set()

		old_context = self.context
		self.context = {**self.context}

		if self.component_depth > self.settings["MAX_COMPONENT_NESTING"]:
			raise ParseError("Component " + tag["name"] + " is too deeply nested, aborting build.")
		self.component_depth += 1

		self.process_attrs(tag, first_child)
		
		for component in component_soup.find_all("component"):
			(styles, scripts) = self.components_replacement(component)
			required_styles.update(styles)
			required_scripts.update(scripts)
		
		template = component_soup.find("template")

		# replace all for loops
		match = template.find("for")
		while match is not None:
			self.repeat_replacement(match)
			match = template.find("for")
		
		self.slots_replacement(component_soup, tag, component=True)
		self.vars_replacement(template)
		
		tag.insert_after(*template.contents)
		tag.extract()

		self.context = old_context
		self.component_depth -= 1

		if os.path.exists(os.path.join(self.settings["BUILD_PATH"], path, tag["name"] + ".css")):
			required_styles.add(Tag(name="link", attrs={"rel": "stylesheet", "href": "/" + path + "/" + tag["name"] + ".css"}, can_be_empty_element=True))
		if os.path.exists(os.path.join(self.settings["BUILD_PATH"], path, tag["name"] + ".js")):
			required_scripts.add(Tag(name="script", attrs={"src": "/" + path + "/" + tag["name"] + ".js", "defer" : True}))
		
		self.context["LOCATION"].pop()

		return (required_styles, required_scripts)
	
	def slots_replacement(self, template_soup, page_soup, component=False):
		"""Replace all slots in a template with the passed contents, if available."""
		for slot in template_soup.find_all("slot"): # Replace slots
			if slot.get("name") is None:
				slot['name'] = "default"
			self.context["LOCATION"].append(slot["name"])

			if component and slot["name"] == "default":
				replacement = page_soup
			else:
				replacement = page_soup.find(slot["name"].lower())
			if replacement is not None:
				replacement = replacement.contents
			if not replacement: # if the page doesn't override the slot, use the slot's contents
				replacement = slot.contents
			
			slot.insert_after(*replacement) # replace slot with contents
			slot.extract()
			
			self.context["LOCATION"].pop()
	
	def repeat_replacement(self, tag : Tag):
		"""Replace a for loop with the contents repeated."""
		self.context["LOCATION"].append("For " + tag["each"])
		[each, of] = tag.get("each", "x in []").split(" in ")
		if not of:
			raise ParseError("Invalid syntax in for tag, no each specified")
		old_context = self.context
		self.context = {**self.context}
		if of.startswith("[") and of.endswith("]"): # allow passing arrays
			var = json.loads(of)
		else:
			var = self.resolve_var(of)
		if isinstance(var, str) and var.isdigit():
			var = [*range(int(var))]

		if var is not None:
			template = "\n".join([str(x) for x in tag.contents]) # turn the contents of the tag into a string
			index = 0
			to_add = []
			for item in var:
				self.context[each] = item
				self.context["INDEX"] = index
				
				new_tag = BeautifulSoup(self.replace_var(template), 'html.parser')
				match = new_tag.find("for")
				while match is not None:
					self.repeat_replacement(match)
					match = new_tag.find("for")
				to_add.append(new_tag)
				index += 1
			prev = tag
			for item in to_add:
				last = item.contents[-1]
				prev.insert_after(*item.contents)
				prev = last
		tag.extract()

		self.context = old_context
		self.context["LOCATION"].pop()
	
	def template_replacement(self, build_path, debug=False):
		"""Replace all variables and components in a template."""
		page_soup = BeautifulSoup(open(build_path + "index.html.temp", encoding = 'utf-8'), 'html.parser')
		page_settings = page_soup.find("settings")
		if page_settings is None:
			raise ParseError("No Settings tag found in " + build_path)

		for path in self.settings["LAYOUT_PATH"]:
			if os.path.exists(path + "/" + page_settings['layout'] + ".html"):
				break
		else:
			raise ParseError("Layout " + page_settings['layout'] + " not found")
		
		shutil.copyfile(f"{path}/{page_settings['layout']}.html", build_path + "index.html") # copy the layout and use it as a base
		with open(build_path + "index.html", "r+", encoding = 'utf-8') as file:
			soup = BeautifulSoup(file, 'html.parser')

			self.slots_replacement(soup, page_soup)
			
			required_styles = set()
			required_scripts = set()
			
			for component in soup.find_all("component"): # Replace components
				(styles, scripts) = self.components_replacement(component)
				required_styles.update(styles)
				required_scripts.update(scripts)
			
			soup.find("head").extend(required_styles) # Add stylesheets to end of head
			soup.find("body").extend(required_scripts) # Add scripts to end of body

			match = soup.find("for")
			while match is not None:
				self.repeat_replacement(match)
				match = soup.find("for")
			
			style = page_soup.find("style")
			if style is not None:
				soup.find("head").append(style)
			
			script = page_soup.find("script")
			if script is not None:
				soup.find("body").append(script)
			
			if debug:
				hot_reload_soup = BeautifulSoup(open(os.path.join(os.path.dirname(__file__), "hot-reload.html"), encoding = 'utf-8'), 'html.parser')
				# convert soup to string
				hot_reload_soup = str(hot_reload_soup)
				# replace localhost:8090 with localhost:port
				hot_reload_soup = BeautifulSoup(hot_reload_soup.replace("localhost:8090", f"localhost:{self.settings['WEBSOCKETS_PORT']}"), 'html.parser')
				soup.find("body").append(hot_reload_soup)

			file.seek(0) # move to the beginning of the file
			file.truncate(0) # clear file
			file.write(self.replace_var(str(soup))) # write the result with replaced variables and pretiffied
		os.remove(build_path + "index.html.temp") # clean temp file
	
	def build_pages(self, path, debug=False):
		"""Build all pages in a directory."""
		for page in os.listdir(self.settings["PAGES_PATH"] + path):
			self.context["LOCATION"].append(page)
			self.context["PAGE"] = page.split(".")[0] if page != "index.html" else ""
			# Recursively build pages
			if os.path.isdir(page):
				self.build_pages(path + page)
			else:
				build_path = self.settings["BUILD_PATH"] + "/"

				if self.base_path: # if not home page
					build_path += self.base_path + "/"

				# If the page isn't index, make it a directory
				if page != "index.html":
					build_path += self.context["PAGE"] + "/"
				
				self.context["PATH"] = "/" + build_path.replace(self.settings["BUILD_PATH"] + "/", "")

				os.makedirs(os.path.dirname(build_path), exist_ok=True) # Prepare directories
				shutil.copyfile(f"{self.settings['PAGES_PATH']}/{page}", build_path + "index.html.temp") # Copy to a temp file
				self.template_replacement(build_path, debug) # parse the page
			self.context["LOCATION"].pop()
	
	def build_components(self, path):
		"""Build all components in a directory."""
		if not os.path.exists(path):
			return
		for component in os.listdir(path):
			# Recursively build components
			if os.path.isdir(component):
				self.build_components(path + component)
			if component.endswith(".html"):
				soup = BeautifulSoup(open(f"{path}/{component}", encoding = 'utf-8'), 'html.parser')

				# Ensure component has a template
				template = soup.find("template")
				if template is None:
					raise ParseError(f"No template tag found in {component}")

				# Build style
				style = soup.find("style")
				if style is not None:
					style_file = open(f"{self.settings['BUILD_PATH']}/{path}/{component.split('.')[0]}.css", "w", encoding = 'utf-8')
					style_file.write(style.text)

				# Build script
				script = soup.find("script")
				if script is not None:
					js_file = open(f"{self.settings['BUILD_PATH']}/{path}/{component.split('.')[0]}.js", "w", encoding = 'utf-8')
					js_file.write(script.text)
	
	def add_global_context_values(self, global_context):
		"""Add global context values to the context."""
		global_context["YEAR"] = date.today().year
	
	def get_other_locales(self, locale_file):
		"""Get a list of other locales."""
		other_locales = []
		for locale in os.listdir(self.settings["LOCALES_PATH"]):
			if locale != locale_file and locale != ".global.json":
				name = locale.split(".", 1)[0]
				other_locales.append({"name": name, "path": f"/{name}/" if name != self.settings["DEFAULT_LOCALE"] else "/"})
		return other_locales
	
	def initialize_locale_context(self, locale_file, global_context):
		"""Initialize the locale context."""
		self.locale = locale_file.split(".", 1)[0]
		self.base_path = "" if self.locale == self.settings["DEFAULT_LOCALE"] else self.locale
		self.context = {**global_context, **json.load(open(f"{self.settings['LOCALES_PATH']}/{locale_file}", encoding = 'utf-8'))}
		self.context["LOCALE"] = self.locale
		self.context["LOCATION"] = [self.locale]

		self.component_depth = 0
		if "ROOT" not in self.context:
			self.context["ROOT"] = "/" + self.base_path
			if self.base_path:
				self.context["ROOT"] += "/"
		if "LOCALES" not in self.context:
			self.context["OTHER_LOCALES"] = self.get_other_locales(locale_file)

	def build(self, debug=False):
		"""Build the website."""
		start_time = time.time()

		# load settings from cwd self.settings["yaml
		yaml_string = open("settings.yaml", encoding = 'utf-8').read()
		self.settings = yaml.load(yaml_string, Loader=yaml.Loader)

		# Prepare build directory
		shutil.rmtree(self.settings["BUILD_PATH"] + "/", ignore_errors=True)
		shutil.copytree(self.settings["STATIC_PATH"], self.settings["BUILD_PATH"] + "/")

		for path in self.settings["COMPONENTS_PATH"]:
			os.makedirs(os.path.dirname(f"{self.settings['BUILD_PATH']}/{path}/"), exist_ok=True)
			self.build_components(path)

		global_context = json.load(open(f"{self.settings['LOCALES_PATH']}/.global.json", encoding = 'utf-8'))
		self.add_global_context_values(global_context)
		
		locale_files = os.listdir(self.settings['LOCALES_PATH'])
		try:
			locale_files.remove(".global.json")
		except ValueError:
			pass
		
		logging.info(f"Building pages for {len(locale_files)} locales...")

		for locale_file in locale_files:
			self.initialize_locale_context(locale_file, global_context)
			self.build_pages("/", debug)
		
		if not debug:
			# move all files at */404/index.html to */404.html
			for path in glob.glob(f"{self.settings['BUILD_PATH']}/**/404/index.html", recursive=True):
				shutil.move(path, path.replace("\\index.html", ".html").replace("/index.html", ".html"))
				# remove empty directories
				shutil.rmtree(os.path.dirname(path), ignore_errors=True)
		
		logging.info("Build complete in " + "{:.3f}".format(time.time() - start_time) + " seconds")

if __name__ == '__main__':
	Parser().build()