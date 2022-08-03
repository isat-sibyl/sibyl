from datetime import date
import sys
from css_html_js_minify import minify

import json
import re
import time
from xml.etree.ElementTree import ParseError
import settings
import os
import shutil

from bs4 import BeautifulSoup, PageElement, Tag

var_pattern = re.compile(r"{{\s*([^\s{}]+)\s*(\|\s*(\S+)\s*)?}}")

class Parser:
	def get_debug_location(self):
		result = self.context.get('PATH', 'PATH NOT FOUND') + " " + str(self.context["LOCATION"])
		return result
		
	def resolve_var(self, string):
		split = string.split(".", 1)
		result = self.context
		while True:
			result = result.get(split[0], None)
			if result is None:
				return None
			elif len(split) == 1: 
				return result
			elif isinstance(result, str):
				print(result)
				raise ParseError(string + " resolved to string and cannot have further nested variables. At " + self.get_debug_location())
			split = split[1].split(".", 1)
	
	def get_var(self, match):
		result = self.resolve_var(match.group(1))
		if result is None:
			result = match.group(3)
		if result is None:
			return "{{" + match.group(1) + "}}"
		return str(result)

	def replace_var(self, string):
		while re.search(var_pattern, string) is not None: # TODO: Find a better way to recursively replace variables
			new_string = re.sub(var_pattern, self.get_var, string)
			if new_string == string:
				break
			string = new_string
		return string
	
	def vars_replacement(self, element):
		variables = element.find_all(text = var_pattern)
		for variable in variables:
			variable.replace_with(self.replace_var(variable.string))

	def from_kebab_to_camel(self, kebab_str):
		components = kebab_str.split('-')
		return components[0] + ''.join(x.title() for x in components[1:])
	
	def components_replacement(self, tag : Tag): #NOSONAR
		self.context["LOCATION"].append(tag["name"])

		component_soup = BeautifulSoup(open(settings.COMPONENTS_PATH + "/" + tag["name"] + ".html"), 'html.parser')
		first_child = component_soup.find("template").find()

		required_styles = set()
		required_scripts = set()

		old_context = self.context
		self.context = {**self.context}

		if self.component_depth > settings.MAX_COMPONENT_NESTING:
			raise ParseError("Component " + tag["name"] + " is too deeply nested, aborting build.")
		self.component_depth += 1

		for key, value in tag.attrs.items():
			if key == "name":
				continue
			elif key == "style":
				old_style = first_child.get('style', "")
				if old_style and not old_style.endswith(";"):
					old_style += ";"
				first_child['style'] = old_style + value
			elif key == "id":
				first_child['id'] = value
			elif key == "class":
				old_class = first_child.get('class', [])
				first_child['class'] = old_class + value
			elif value.startswith == "{{" and value.endswith == "}}":
				self.context[self.from_kebab_to_camel(key)] = var_pattern.match(value).group(1)
			else:
				self.context[self.from_kebab_to_camel(key)] = value
		
		for component in component_soup.find_all("component"):
			(styles, scripts) = self.components_replacement(component)
			required_styles.update(styles)
			required_scripts.update(scripts)
		
		template = component_soup.find("template")
		self.vars_replacement(template)
		
		tag.insert_after(*template.contents)
		tag.extract()

		self.context = old_context
		self.component_depth -= 1

		if os.path.exists(settings.BUILD_PATH + "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".css"):
			required_styles.add(Tag(name="link", attrs={"rel": "stylesheet", "href": "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".css"}, can_be_empty_element=True))
		if os.path.exists(settings.BUILD_PATH + "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".js"):
			required_scripts.add(Tag(name="script", attrs={"src": "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".js"}))
		
		self.context["LOCATION"].pop()

		return (required_styles, required_scripts)
	
	def slots_replacement(self, template_soup, page_soup):
		for slot in template_soup.find_all("slot"): # Replace slots
			self.context["LOCATION"].append(slot["name"])

			replacement = page_soup.find(slot["name"].lower())
			if replacement:
				replacement = replacement.contents
			if not replacement: # if the page doesn't override the slot, use the slot's contents
				replacement = slot.contents
			slot.insert_after(*replacement) # replace slot with contents
			slot.extract()
			
			self.context["LOCATION"].pop()
	
	def repeat_replacement(self, tag : Tag):
		self.context["LOCATION"].append("For " + tag["each"])
		[each, of] = tag.get("each", "x in []").split(" in ")
		if not of:
			raise ParseError("Invalid syntax in for tag, no each specified")
		old_context = self.context
		self.context = {**self.context}
		if (of.startswith("[") and of.endswith("]")): # allow passing arrays
			var = json.loads(of)
		else:
			var = self.resolve_var(of)

		if var is not None:
			template = "\n".join([str(x) for x in tag.contents]) # turn the contents of the tag into a string

			to_add = []
			for item in var:
				self.context[each] = item
				
				new_tag = BeautifulSoup(self.replace_var(template), 'html.parser')
				match = new_tag.find("for")
				while match is not None:
					self.repeat_replacement(match)
					match = new_tag.find("for")
				to_add.append(new_tag)
			prev = tag
			for item in to_add:
				last = item.contents[-1]
				prev.insert_after(*item.contents)
				prev = last
		tag.extract()

		self.context = old_context
		self.context["LOCATION"].pop()
	
	def template_replacement(self, build_path):
		page_soup = BeautifulSoup(open(build_path + "index.html.temp"), 'html.parser')
		page_settings = page_soup.find("settings")
		if page_settings is None:
			raise ParseError("No Settings tag found in " + build_path)
		shutil.copyfile(f"{settings.LAYOUT_PATH}/{page_settings['layout']}.html", build_path + "index.html") # copy the layout and use it as a base
		with open(build_path + "index.html", "r+") as file:
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

			file.seek(0) # move to the beginning of the file
			file.truncate(0) # clear file
			file.write(self.replace_var(soup.prettify())) # write the result with replaced variables and pretiffied
		os.remove(build_path + "index.html.temp") # clean temp file
	
	def build_pages(self, path):
		for page in os.listdir(settings.PAGES_PATH + path):
			self.context["LOCATION"].append(page)
			self.context["PAGE"] = page.split(".")[0] if page != "index.html" else ""
			# Recursively build pages
			if os.path.isdir(page):
				self.build_pages(path + page)
			else:
				build_path = settings.BUILD_PATH + "/"

				if self.base_path: # if not home page
					build_path += self.base_path + "/"

				# If the page isn't index, make it a directory
				if page != "index.html":
					build_path += self.context["PAGE"] + "/"
				
				self.context["PATH"] = "/" + build_path.replace(settings.BUILD_PATH + "/", "")

				os.makedirs(os.path.dirname(build_path), exist_ok=True) # Prepare directories
				shutil.copyfile(f"{settings.PAGES_PATH}/{page}", build_path + "index.html.temp") # Copy to a temp file
				self.template_replacement(build_path) # parse the page
			self.context["LOCATION"].pop()
	
	def build_components(self, path):
		for component in os.listdir(path):
			# Recursively build components
			if os.path.isdir(component):
				self.build_components(path + component)
			if component.endswith(".html"):
				soup = BeautifulSoup(open(f"{settings.COMPONENTS_PATH}/{component}"), 'html.parser')

				# Ensure component has a template
				template = soup.find("template")
				if template is None:
					raise ParseError(f"No template tag found in {component}")

				# Build style
				style = soup.find("style")
				if style is not None:
					file = open(f"{settings.BUILD_PATH}/{settings.COMPONENTS_PATH}/{component.split('.')[0]}.css", "w")
					file.write(style.text)

				# Build script
				script = soup.find("script")
				if script is not None:
					file = open(f"{settings.BUILD_PATH}/{settings.COMPONENTS_PATH}/{component.split('.')[0]}.js", "w")
					file.write(script.text)

	def build(self):
		start_time = time.time()

		# Prepare build directory
		shutil.rmtree(settings.BUILD_PATH + "/", ignore_errors=True)
		shutil.copytree(settings.STATIC_PATH, settings.BUILD_PATH + "/")
		os.makedirs(os.path.dirname(f"{settings.BUILD_PATH}/{settings.COMPONENTS_PATH}/"), exist_ok=True)

		self.build_components(settings.COMPONENTS_PATH)
		global_context = json.load(open(f"{settings.LOCALES_PATH}/.global.json"))
		global_context["YEAR"] = date.today().year
		
		locale_files = os.listdir(settings.LOCALES_PATH)
		try:
			locale_files.remove(".global.json")
		except ValueError:
			pass
		
		print(f"[INFO] Building pages for {len(locale_files)} locales...")

		for locale_file in locale_files:
			self.locale = locale_file.split(".", 1)[0]
			
			self.base_path = "" if self.locale == settings.DEFAULT_LOCALE else self.locale
			
			# Prepare context
			self.context = {**global_context, **json.load(open(f"{settings.LOCALES_PATH}/{locale_file}"))}
			self.context["LOCALE"] = self.locale
			self.context["LOCATION"] = [self.locale]

			self.component_depth = 0
			if "ROOT" not in self.context:
				self.context["ROOT"] = "/" + self.base_path
				if self.base_path:
					self.context["ROOT"] += "/"
			if "LOCALES" not in self.context:
				other_locales = []
				for locale in os.listdir(settings.LOCALES_PATH):
					if locale != locale_file and locale != ".global.json":
						name = locale.split(".", 1)[0]
						other_locales.append({"name": name, "path": f"/{name}/" if name != settings.DEFAULT_LOCALE else "/"})
				self.context["OTHER_LOCALES"] = other_locales
			self.build_pages("/")
		
		print("[INFO] Build complete in " + "{:.3f}".format(time.time() - start_time) + " seconds")

if __name__ == '__main__':
	Parser().build()
	sys._argv = sys.argv[:]
	sys.argv=['', '--quiet', '--overwrite', 'dist/']
	minify.main()
	sys.argv = sys._argv