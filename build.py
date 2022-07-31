from copy import copy
import json
import re
from xml.etree.ElementTree import ParseError
import settings
import os
import shutil

from bs4 import BeautifulSoup, Tag

var_pattern = re.compile(r"{{\s*(\S+)\s*}}")

class Parser:
	def get_var(self, string):
		split = string.split(".", 1)
		result = self.context
		while True:
			result = result.get(split[0], None)
			if result is None:
				return "{{ " + string + " }}"
			elif len(split) == 1: 
				return result
			split = split[1].split(".", 1)

	def var_replacement(self, string):			
		return re.sub(r"{{\s*(\S+?)\s*}}", lambda match : str(self.get_var(match.group(1))), string)

	def replace_components(self, tag : Tag):
		component_soup = BeautifulSoup(open(settings.COMPONENTS_PATH + "/" + tag["name"] + ".html"), 'html.parser')
		required_styles = set()
		required_scripts = set()

		for component in component_soup.find_all("component"):
			if component["name"] == tag["name"]:
				raise ParseError("Recursive component " + tag["name"] + " detected, aborting build.")
			(styles, scripts) = self.replace_components(component)
			required_styles.update(styles)
			required_scripts.update(scripts)
		
		tag.insert_after(*component_soup.find("template").contents)
		tag.extract()

		if os.path.exists(settings.BUILD_PATH + "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".css"):
			required_styles.add(Tag(name="link", attrs={"rel": "stylesheet", "href": "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".css"}, can_be_empty_element=True))
		if os.path.exists(settings.BUILD_PATH + "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".js"):
			required_scripts.add(Tag(name="script", attrs={"src": "/" + settings.COMPONENTS_PATH + "/" + tag["name"] + ".js"}))
		
		return (required_styles, required_scripts)

	def replace_repeat(self, tag : Tag):
		[x, each] = tag.get("each", "x in []").split(" in ")
		if not each:
			raise ParseError("Invalid syntax in for tag, no each specified")
		old_context = self.context
		self.context = {**self.context}
		if (each.startswith("[") and each.endswith("]")): # allow passing arrays
			var = json.loads(each)
		else:
			var = self.get_var(each)

		template = "\n".join([str(x) for x in tag.contents]) # turn the contents of the tag into a string
		to_add = []
		for item in var:
			self.context[x] = item
			
			new_tag = BeautifulSoup(self.var_replacement(template), 'html.parser')
			match = new_tag.find("for")
			while match is not None:
				self.replace_repeat(match)
				match = new_tag.find("for")
			to_add.append(new_tag)

		to_add.reverse()
		tag.insert_after(*to_add)
		tag.extract()

		self.context = old_context

	def template_replacement(self, build_path):
		page_soup = BeautifulSoup(open(build_path + "index.html.temp"), 'html.parser')
		page_settings = page_soup.find("settings")
		if page_settings is None:
			raise ParseError("No Settings tag found in " + build_path)
		shutil.copyfile(f"{settings.LAYOUT_PATH}/{page_settings['layout']}.html", build_path + "index.html")
		with open(build_path + "index.html", "r+") as file:
			soup = BeautifulSoup(file, 'html.parser')

			for tag in soup.find_all("slot"): # Replace slots
				replacement = page_soup.find(tag["name"].lower())
				if replacement:
					replacement = replacement.contents
				if not replacement: # if the page doesn't override the slot, use the slot's contents
					replacement = tag.contents
				tag.insert_after(*replacement) # replace slot with contents
				tag.extract()
			
			required_styles = set()
			required_scripts = set()
			
			for component in soup.find_all("component"): # Replace components
				(styles, scripts) = self.replace_components(component)
				required_styles.update(styles)
				required_scripts.update(scripts)
			
			soup.find("head").extend(required_styles) # Add stylesheets to end of head
			soup.find("body").extend(required_scripts) # Add scripts to end of body

			match = soup.find("for")
			while match is not None:
				self.replace_repeat(match)
				match = soup.find("for")

			file.seek(0) # move to the beginning of the file
			file.truncate(0) # clear file
			file.write(self.var_replacement(soup.prettify())) # write the result with replaced variables and pretiffied
		os.remove(build_path + "index.html.temp") # clean temp file

	def build_page(self, path):
		for page in os.listdir(settings.PAGES_PATH + path):
			# Recursively build pages
			if os.path.isdir(page):
				self.build_page(path + page)
			else:
				build_path = settings.BUILD_PATH + "/"

				if self.base_path:
					build_path += self.base_path + "/"

				# If the page isn't index, make it a directory
				if page != "index.html":
					build_path += page.split(".")[0] + "/"

				os.makedirs(os.path.dirname(build_path), exist_ok=True) # Prepare directories
				shutil.copyfile(f"{settings.PAGES_PATH}/{page}", build_path + "index.html.temp") # Copy to a temp file
				self.template_replacement(build_path)

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

	def build(self): #NOSONAR
		shutil.rmtree(settings.BUILD_PATH + "/", ignore_errors=True)
		shutil.copytree(settings.STATIC_PATH, settings.BUILD_PATH + "/")
		os.makedirs(os.path.dirname(f"{settings.BUILD_PATH}/{settings.COMPONENTS_PATH}/"), exist_ok=True)

		self.build_components(settings.COMPONENTS_PATH)
		self.global_context = json.load(open(f"{settings.LOCALES_PATH}/.global.json"))
				
		for locale_file in os.listdir(settings.LOCALES_PATH):
			[self.locale, extension] = locale_file.split(".", 1)
			
			if self.locale != "" and extension == "json":
				self.base_path = "" if self.locale == settings.DEFAULT_LOCALE else self.locale
				self.context = {**self.global_context, **json.load(open(f"{settings.LOCALES_PATH}/{locale_file}"))}
				self.context["LOCALE"] = self.locale
				if "BASE_URL" not in self . context:
					self.context["BASE_URL"] = "/" + self.base_path
				if "LOCALES" not in self . context:
					self.context["LOCALES"] = [x.split(".")[0] for x in os.listdir(settings.LOCALES_PATH)]
					try:
						self.context["LOCALES"].remove("")
					except ValueError:
						pass
				self.build_page("/")

if __name__ == '__main__':
	Parser().build()