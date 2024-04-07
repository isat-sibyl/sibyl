import copy
import glob
import json
import logging
import os
import shutil
import time
from sibyl.helpers import (
    settings as settings_module,
    component,
    requirement,
    version,
    shutil_compat,
)
import bs4
from typing import List, Set

no_var_attributes = ["for-each", "render-if", "render-elif", "render-else"]
passable_component_attributes = [
    "id",
    "class",
    "style",
    "onclick",
    "onmouseover",
    "onmouseout",
]


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Build:
    """A class to build the site."""

    settings: settings_module.Settings
    context: dict
    locales: List[str]
    exec_path = os.path.dirname(__file__)
    build_files_path: str
    debug_path: List[str]
    debug_line: int = -1
    requirements: Set[requirement.Requirement]
    page_count: int
    locale_count: int

    def evaluate(self, condition: str, ignore_errors=False):
        """Evaluates the given condition and returns its value"""
        try:
            # convert every dict in context to a dotdict
            for key, value in self.context.items():
                if isinstance(value, dict) and not isinstance(value, dotdict):
                    self.context[key] = dotdict(value)
            return eval(condition, self.context)
        except:
            if not ignore_errors:
                logging.error(
                    f"Error evaluating '{condition}' at or near line {self.debug_line}: {' -> '.join(self.debug_path)}"
                )
                logging.debug(f"Context: {self.context}")
            raise

    def format(self, string: str):
        """Formats the given string, evaluating all text inside {{}}"""
        result = ""
        if string is None:
            return result
        while True:
            start = string.find("{{")
            if start == -1:
                result += string
                break
            if start > 0 and string[start - 1] == "\\":
                result += string[: start - 1] + "{{"
                string = string[start + 2 :]
                continue
            end = string.find("}}", start)
            if end == -1:
                raise ValueError("Missing }}")
            result += string[:start]
            try:
                result += str(self.evaluate(string[start + 2 : end]))
            except (NameError, AttributeError):
                logging.warning(
                    f"Variable '{string[start + 2:end]}' not found at or near line {self.debug_line}: {' -> '.join(self.debug_path)}"
                )
                logging.debug(f"Context: {self.context}")
                if self.settings.treat_warnings_as_errors:
                    raise NameError(
                        f"Variable '{string[start + 2:end]}' not found at or near line {self.debug_line}: {' -> '.join(self.debug_path)}"
                    )
                result += string[start : end + 2]
            string = string[end + 2 :]
        return result

    @staticmethod
    def kebab_to_camel(string: str):
        """Converts a kebab-case string to camelCase."""
        components = string.split("-")
        return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def is_else_tag(tag: bs4.Tag):
        """Returns true if the given tag is a render-else tag."""
        return (
            tag is not None
            and isinstance(tag, bs4.Tag)
            and ("render-else" in tag.attrs or "render-elif" in tag.attrs)
        )

    def replace_condition(self, tag: bs4.Tag):
        condition = None
        if "render-if" in tag.attrs:
            condition = tag.attrs["render-if"]
            attr_name = "render-if"
        elif "render-elif" in tag.attrs:
            condition = tag.attrs["render-elif"]
            attr_name = "render-elif"
        elif "render-else" in tag.attrs:
            del tag["render-else"]
            return True

        self.debug_line = tag.sourceline

        if condition is None:
            raise ValueError("Missing condition")
        # if the condition is true, remove the attribute and continue
        try:
            result = self.evaluate(condition, True)
        except NameError:
            result = False
        if result:
            del tag[attr_name]
            next_tag = tag.find_next_sibling()
            while Build.is_else_tag(next_tag):
                next_next_tag = next_tag.find_next_sibling()
                next_tag.__visited = True
                next_tag.extract()
                next_tag = next_next_tag
            return True

        next_tag = tag.find_next_sibling()
        # delete the tag and all its children
        tag.extract()
        tag.__visited = True

        if Build.is_else_tag(next_tag):
            self.replace_condition(next_tag)

        return False

    def expand_for(self, tag: bs4.Tag):  # NOSONAR
        """Expands the for-each tag."""
        self.debug_line = tag.sourceline
        # get the for-each attribute
        for_each = tag["for-each"]
        # get the name of the variable
        (var_name, list_name) = for_each.split(" in ")
        # get the list
        try:
            iterable = self.evaluate(list_name)
        except NameError:
            iterable = []
            logging.warning(
                f"Variable '{list_name}' not found at or near line {self.debug_line}: {' -> '.join(self.debug_path)}"
            )
            if self.settings.treat_warnings_as_errors:
                raise
        old_value = self.context.get(var_name)

        del tag["for-each"]

        for item in iterable:
            new_tag = copy.copy(tag)
            is_tuple = False
            if isinstance(item, tuple):
                is_tuple = True
                item = list(item)

            if isinstance(item, dict):
                item = dotdict(item)
            elif isinstance(item, list):
                for i in range(len(item)):
                    if isinstance(item[i], dict):
                        item[i] = dotdict(item[i])

            if is_tuple:
                item = tuple(item)
            self.context[var_name] = item
            tag.insert_before(new_tag)
            self.perform_replacements(new_tag)

        tag.extract()

        self.context[var_name] = old_value

    def expand_variables(self, template: bs4.Tag):
        """Expands the variables in the given template. A variable is inside {{}} and can be inside an attribute except the attributes in no_var_attributes."""
        for attr in template.attrs:
            if attr not in no_var_attributes:
                # if the attribute is a list
                if isinstance(template[attr], list):
                    template[attr] = [self.format(value) for value in template[attr]]
                else:
                    template[attr] = self.format(template[attr])
        for tag in template.contents:
            if isinstance(tag, bs4.Comment):
                tag.extract()
            elif isinstance(tag, bs4.NavigableString) and not isinstance(
                tag, bs4.Doctype
            ):
                tag.replace_with(self.format(str(tag)))

    def replace_slots(self, tag: bs4.Tag, template: bs4.Tag):
        """Replaces the slots in the given template."""
        slots = template.find_all("slot")

        # replace slots
        for slot in slots:  # Replace slots
            if slot.get("name") is None or slot["name"] == "default":
                replacement = tag
            else:
                replacement = tag.find(slot["name"].lower())
            if replacement is not None:
                replacement = replacement.contents
            if (
                not replacement
            ):  # if the page doesn't override the slot, use the slot's contents
                replacement = slot.contents

            slot.insert_after(*replacement)  # replace slot with contents
            slot.extract()

    def pass_attributes(self, source: bs4.Tag, dest: bs4.Tag):  # NOSONAR
        """Passes the attributes from the source tag to the destination tag."""
        for attr in source.attrs:
            if attr in no_var_attributes:
                continue
            if attr not in passable_component_attributes:
                self.context[Build.kebab_to_camel(attr)] = self.format(source[attr])
                continue
            for child in dest.find_all(recursive=False):
                if attr == "class":
                    child["class"] = child.get("class", [])
                    child["class"].extend(self.format(x) for x in source["class"])
                elif attr == "style":
                    old_style = child.get("style", "")
                    if old_style and not old_style.endswith(";"):
                        old_style += ";"
                    child["style"] = old_style + self.format(source[attr])
                else:
                    child[attr] = self.format(source[attr])

    def replace_component(self, tag: bs4.Tag):
        """Replaces the component tag with the component's template."""
        self.debug_line = tag.sourceline
        self.debug_path.append(tag["name"] + " (Component)")

        # get the component's name
        component_name = tag["name"]
        if component_name.startswith("{{") and component_name.endswith("}}"):
            component_name = self.format(component_name)
        # get the component's path
        component_path = component.Component.resolve_component(
            component_name, self.settings
        )
        # get the component
        component_soup = component.Component.build(component_path)

        # get a copy of the component's template
        template = component_soup.template

        old_context = {**self.context}
        self.context["__SIBYL_COMPONENT_TAG__"] = tag

        # add the component's attributes to the template
        self.pass_attributes(tag, template)

        component_soup.run_python_phase(self.context, "default")

        self.replace_slots(tag, template)

        if "__SIBYL_HALT__" not in self.context:
            for child in template.find_all(recursive=False):
                self.perform_replacements(child)
        else:
            print("Halted")
            del self.context["__SIBYL_HALT__"]

        self.requirements.update(component_soup.get_requirements(self.settings))

        tag.replace_with(*template.contents)

        component_soup.run_python_phase(self.context, "cleanup")

        self.context = old_context
        self.debug_path.pop()

    def perform_replacements(
        self, template: bs4.Tag
    ):  # TODO: Tail recursion optimization
        """Performs replacements in the given template and recursively in all its children."""
        self.debug_line = template.sourceline
        if template.__visited or not isinstance(template, bs4.Tag):
            return

        template.__visited = True

        if "render-if" in template.attrs and not self.replace_condition(template):
            return

        if "for-each" in template.attrs:
            self.expand_for(template)
            return

        if (
            template.name == "component"
            and "__SIBYL_HALT_COMPONENTS__" not in self.context
        ):
            self.replace_component(template)
            return

        self.expand_variables(template)

        for tag in template.find_all(recursive=False):
            self.perform_replacements(tag)

    def create_redirects_file(self):
        """Create a redirects file."""
        redirects = open(
            os.path.join(self.settings.build_path, "_redirects"), "a", encoding="utf-8"
        )
        redirects.write(f"/ /{self.settings.default_locale}\n")

    def build_page(self, page_path: str, hot_reloading=False):  # NOSONAR
        """Builds the page in the given page_path. The page_path is inside .build_files"""
        self.debug_path.append(os.path.basename(page_path))

        relative_page_path = page_path[len(self.build_files_path) + 1 :]

        # remove the .html extension
        relative_page_path = relative_page_path[:-5]

        # if the name is index.html, remove the index.html
        if relative_page_path.endswith("index"):
            relative_page_path = relative_page_path[:-5]

        self.context["SIBYL_PAGE"] = os.path.join(
            *(relative_page_path.split(os.path.sep)[1:])
        ).replace("\\", "/")

        # Step 1: Create the directory at the build directory
        build_page_path = os.path.join(self.settings.build_path, relative_page_path)
        os.makedirs(os.path.dirname(build_page_path), exist_ok=True)

        # Step 2: Load the page
        page = component.Component.build(page_path, True)
        self.requirements = set()
        self.requirements.update(
            page.get_imported_requirements()
        )  # self requirements are dealt with by partials

        old_context = {**self.context}
        page.run_python_phase(self.context, "default")

        # remove all requirement tags
        self.perform_replacements(page.template)

        for tag in page.template.find_all("requirement"):
            tag.extract()

        # Step 4: Build the partial for this page
        partial_path = os.path.join(
            self.settings.build_path, relative_page_path, "partial.html"
        )
        os.makedirs(os.path.dirname(partial_path), exist_ok=True)
        with open(partial_path, "w", encoding="utf-8") as partial_file:
            if self.settings.debug:
                partial_file.write(page.template.prettify())
                if page.script:
                    partial_file.write(page.script.prettify())
                if page.style:
                    partial_file.write(page.style.prettify())
            else:
                partial_file.write(str(page.template))
                if page.script:
                    partial_file.write(str(page.script))
                if page.style:
                    partial_file.write(str(page.style))

        # Step 5: Build the requirements for this page
        requirements_path = os.path.join(
            self.settings.build_path, relative_page_path, "partial.requirements.json"
        )
        os.makedirs(os.path.dirname(requirements_path), exist_ok=True)
        with open(requirements_path, "w") as requirements_file:
            requirements = {
                Build.kebab_to_camel(x.name): x.to_dict() for x in self.requirements
            }
            requirements["locale"] = self.context["SIBYL_LOCALE"]
            requirements["layout"] = page.template["layout"]
            requirements_file.write(json.dumps(requirements))

        # Step 6: Inject page into layout (found in the layout attribute of the template)

        # resolve the layout and copy it
        if "layout" not in page.template.attrs:
            raise ValueError("No layout specified for page " + relative_page_path)
        layout_path = component.Component.resolve_layout(
            page.template["layout"], self.settings
        )

        # load the layout
        with open(layout_path, "r+", encoding="utf-8") as file:
            layout_soup = bs4.BeautifulSoup(file.read(), "html.parser")

            self.perform_replacements(layout_soup)

            # inject the page into the layout
            template_slot = layout_soup.find("slot", {"name": "template"})
            if template_slot is None:
                raise ValueError("No template slot found in layout " + layout_path)
            template_slot.replace_with(*page.template.contents)
            title_slot = layout_soup.find("slot", {"name": "title"})
            if title_slot is None:
                raise ValueError("No title slot found in layout " + layout_path)
            title = page.template.get("title", None)
            if title is not None:
                title_slot.replace_with(page.template.get("title", ""))
            else:
                logging.warning("No title found for page " + relative_page_path)
                if self.settings.treat_warnings_as_errors:
                    raise ValueError("No title found for page " + relative_page_path)
                title_slot.replace_with(*title_slot.contents)

            if page.script:
                layout_soup.body.append(page.script)
            if page.style:
                page.style.attrs["id"] = "sibyl-page-style"
                layout_soup.head.append(page.style)

            # inject all the requirements
            for req in self.requirements:
                if req.type == requirement.RequirementType.SCRIPT:
                    layout_soup.body.append(req.to_tag())
                elif req.type == requirement.RequirementType.STYLE:
                    layout_soup.head.append(req.to_tag())
        if hot_reloading:
            hot_reload_soup = bs4.BeautifulSoup(
                open(
                    os.path.join(os.path.dirname(__file__), "hot-reload.html"),
                    encoding="utf-8",
                ),
                "html.parser",
            )
            # convert soup to string
            hot_reload_soup = str(hot_reload_soup)
            # replace localhost:8090 with localhost:port
            hot_reload_soup = bs4.BeautifulSoup(
                hot_reload_soup.replace(
                    "localhost:8090", f"localhost:{self.settings.websockets_port}"
                ),
                "html.parser",
            )
            layout_soup.find("body").append(hot_reload_soup)

        output_path = os.path.join(
            self.settings.build_path, relative_page_path, "index.html"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            if self.settings.debug:
                file.write(layout_soup.prettify())
            else:
                file.write(str(layout_soup))

        # Step 7: Clean up
        page.run_python_phase(self.context, "cleanup")
        self.context = old_context
        self.debug_path.pop()

    def build_dir(self, dir_path: str, hot_reloading=False):
        """Build the site for a given directory."""
        self.debug_path.append(os.path.basename(dir_path))

        for page in os.listdir(dir_path):
            page_path = os.path.join(dir_path, page)
            if os.path.isdir(page_path):
                self.build_dir(page_path, hot_reloading)
            else:
                self.page_count += 1
                self.build_page(page_path, hot_reloading)

        self.debug_path.pop()

    def __init__(self, hot_reloading=False):  # NOSONAR
        self.context = {}
        self.locales = []
        self.debug_path = []
        self.debug_line = -1
        self.requirements = set()
        self.page_count = 0
        self.locale_count = 0
        start = time.time()

        # Step 1: Load settings
        self.settings = settings_module.Settings()

        # Step 2: Delete build directory and re-create it
        if os.path.exists(self.settings.build_path):
            shutil.rmtree(self.settings.build_path)
        os.mkdir(self.settings.build_path)

        # Step 3: Copy everything from sibyl-static to the build directory
        shutil_compat.copytree(
            os.path.join(self.exec_path, "sibyl-static"),
            self.settings.build_path,
            dirs_exist_ok=True,
        )

        # Step 4: Copy everything from static to the build directory.
        shutil_compat.copytree(
            self.settings.static_path, self.settings.build_path, dirs_exist_ok=True
        )

        # Step 5: For every folder in root-folders, move its' contents to the build directory and delete the folder
        for folder in self.settings.root_folders:
            shutil_compat.copytree(
                os.path.join(self.settings.build_path, folder),
                self.settings.build_path,
                dirs_exist_ok=True,
            )
            shutil.rmtree(os.path.join(self.settings.build_path, folder))

        # Step 6: Load all the locales from settings.locales_path
        for locale in os.listdir(self.settings.locales_path):
            if locale == "global.json":
                continue
            if not locale.endswith(".json"):
                raise ValueError(f"Invalid locale file '{locale}'")
            locale = locale[:-5]
            self.locales.append(locale)

        # Step 7: Create a folder called .build_files and create a folder for each locale there. Then, copy the contents of the pages folder to each locale's folder
        self.build_files_path = os.path.join(self.settings.build_path, ".build_files")
        if os.path.exists(self.build_files_path):
            raise ValueError(
                "The .build_files folder already exists. Please delete it and try again."
            )
        os.mkdir(self.build_files_path)
        for locale in self.locales:
            if locale != "global":
                locale_path = os.path.join(self.build_files_path, locale)
                shutil_compat.copytree(
                    self.settings.pages_path, locale_path, dirs_exist_ok=True
                )

        # Step 8: Add locales to context
        self.context["SIBYL_LOCALES"] = self.locales
        self.context["SIBYL_VERSION"] = version.version
        # add everything from global.json to the context, if it exists
        global_path = os.path.join(self.settings.locales_path, "global.json")

        if os.path.exists(global_path):
            with open(global_path, "r", encoding="utf-8") as file:
                self.context.update(json.load(file))

        base_context = self.context
        # Step 9: For each locale, build the website
        for locale in self.locales:
            self.context = base_context.copy()

            # inside the locale's context
            locale_path = os.path.join(self.settings.locales_path, locale + ".json")
            with open(locale_path, "r", encoding="utf-8") as file:
                self.context.update(json.load(file))

            self.context["SIBYL_LOCALE"] = locale
            self.context["SIBYL_OTHER_LOCALES"] = [
                l for l in self.locales if l != locale
            ]
            self.context["SIBYL_ROOT"] = "/" + locale + "/"

            self.debug_path = []
            try:
                self.locale_count += 1
                self.build_dir(
                    os.path.join(self.build_files_path, locale), hot_reloading
                )
            except Exception as e:
                logging.error(f"Error while building {locale}: {e}")
                logging.error(f"Debug path: {' -> '.join(self.debug_path)}")
                raise e

            self.context = base_context

        # Step 10: Delete the .build_files folder
        shutil.rmtree(self.build_files_path)

        if not self.settings.debug:
            # move all files at */404/index.html to */404.html
            for path in glob.glob(
                f"{self.settings.build_path}/**/404/index.html", recursive=True
            ):
                shutil.move(
                    path,
                    path.replace("\\index.html", ".html").replace(
                        "/index.html", ".html"
                    ),
                )
                # remove empty directories
                shutil.rmtree(os.path.dirname(path), ignore_errors=True)

        self.create_redirects_file()

        logging.info(
            f"Built {self.page_count} pages in {self.locale_count} locales in {time.time() - start} seconds."
        )


if __name__ == "__main__":
    Build()
