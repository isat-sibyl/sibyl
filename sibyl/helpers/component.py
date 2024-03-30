import os
import sys
import bs4
from .requirement import Requirement, RequirementType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
from . import settings

from typing import Dict


class Component:
    """A reusable html component. It has a name, a template, style, script and python, which is code that is executed when the component is loaded."""

    name: str
    file: str
    soup: bs4.BeautifulSoup
    template: bs4.Tag
    style: bs4.Tag
    script: bs4.Tag
    pythons: bs4.Tag

    # unused since it had weird interactions with bs4
    cache: Dict[str, Self] = {}

    def __init__(self, file):
        """Load the component from a file."""
        # load the component from a file. the name is the file name without the extension
        self.file = file
        with open(file, "r+", encoding="utf-8") as file:
            self.name = os.path.splitext(os.path.basename(file.name))[0]
            self.soup = bs4.BeautifulSoup(file.read(), "html.parser")

        self.template = self.soup.find("template")
        if not self.template:
            raise ValueError("Component must have a template tag")
        self.style = self.soup.find("style")
        self.script = self.soup.find("script")
        self.pythons = self.soup.find_all("python")

    @staticmethod
    def build(file: str, no_cache=False) -> Self:
        """Build a component from a file. If the component is already loaded, return the loaded component."""
        component = Component(file)
        return component

    @staticmethod
    def resolve_component(name: str, settings: settings.Settings) -> str:
        """Resolve the path of a component by searching the components_paths."""
        for path in settings.components_paths:
            component_path = os.path.join(path, name + ".html")
            if os.path.exists(component_path):
                return component_path
        raise ValueError("Component " + name + " not found")

    @staticmethod
    def resolve_layout(name: str, settings: settings.Settings) -> str:
        """Resolve the path of a layout by searching the layouts_paths."""
        for path in settings.layouts_paths:
            layout_path = os.path.join(path, name + ".html")
            if os.path.exists(layout_path):
                return layout_path
        raise ValueError("Layout " + name + " not found")

    def __str__(self):
        """Return the name of the component."""
        return self.name

    def requirement_name(self):
        """Return the name of the requirement."""
        return "component" + self.name

    def build_requirement(self, file, settings: settings.Settings):
        output_path = os.path.join(settings.build_path, file)
        if (
            os.path.exists(output_path)
            or output_path.startswith("http://")
            or output_path.startswith("https://")
        ):
            return
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w+", encoding="utf-8") as file:
            if output_path.endswith(".css"):
                file.write(self.style.text)
            elif output_path.endswith(".js"):
                file.write(self.script.text)

    def get_self_requirements(self, settings: settings.Settings):
        result = []
        base_req_file = self.file.replace(
            os.environ["SIBYL_PATH"], settings.cdn_url
        ).replace("\\", "/")

        if self.style:
            style_req_file = base_req_file.replace(".html", ".css")
            result.append(
                Requirement(
                    self.requirement_name() + "Styles",
                    RequirementType.STYLE,
                    style_req_file,
                )
            )
            style_build_file = self.file.replace(".html", ".css")
            self.build_requirement(style_build_file, settings)

        if self.script:
            script_req_file = base_req_file.replace(".html", ".js")
            result.append(
                Requirement(
                    self.requirement_name() + "Script",
                    RequirementType.SCRIPT,
                    script_req_file,
                )
            )
            script_build_file = self.file.replace(".html", ".js")
            self.build_requirement(script_build_file, settings)

        return result

    def get_imported_requirements(self):
        result = []
        imported_requirements = self.soup.find_all("requirement")
        for imported_requirement in imported_requirements:
            req_type = None
            if imported_requirement["type"] == "script":
                req_type = RequirementType.SCRIPT
            elif imported_requirement["type"] == "style":
                req_type = RequirementType.STYLE
            else:
                raise ValueError(
                    "Unknown requirement type: " + imported_requirement["type"]
                )
            result.append(
                Requirement(
                    imported_requirement["name"],
                    req_type,
                    imported_requirement["src"].replace("\\", "/"),
                )
            )
        return result

    def get_requirements(self, settings: settings.Settings):
        return self.get_self_requirements(settings) + self.get_imported_requirements()

    def run_python(self, python, context: dict):
        """Run the python code of the component."""
        b = compile(python, self.requirement_name(), "exec")
        exec(b, context)

    def run_python_phase(self, context: dict, phase: str):
        """Run the python code of the component if it has the given phase."""
        for python in self.pythons:
            # if phase matches or pyhton has no attributes and phase is defualt
            if python.has_attr(phase) or (
                not python.has_attr("cleanup") and phase == "default"
            ):
                self.run_python(python.text, context)

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name
