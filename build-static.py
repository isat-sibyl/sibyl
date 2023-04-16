import os
import shutil
import time
from sibyl.helpers import settings as settings_module, component
import sibyl.build
from sibyl.helpers.version import version


class BuildComponents(sibyl.build.Build):
    def __init__(self, version: str):
        start = time.time()

        # Step 1: Load settings
        self.settings = settings_module.Settings("settings.yaml")
        self.settings.build_path = os.path.join(self.settings.build_path, version)
        self.settings.components_paths = ["components"]

        # Step 2: Skip if the build already exists
        if os.path.exists(self.settings.build_path):
            print(f"Skipping build of {version} because it already exists.")
            return
        os.makedirs(self.settings.build_path)

        # Step 3: Copy everything from sibyl-static to the build directory
        shutil.copytree("sibyl-static", self.settings.build_path, dirs_exist_ok=True)

        # Step 4: Create a folder called .build_files and build
        self.build_files_path = os.path.join(self.settings.build_path, ".build_files")
        if os.path.exists(self.build_files_path):
            raise ValueError(
                "The .build_files folder already exists. Please delete it and try again."
            )
        os.mkdir(self.build_files_path)

        components: set[component.Component] = set()
        # scan every component in the components folder and add it to the requirements
        for component_path in self.settings.components_paths:
            for component_file in os.listdir(component_path):
                component_name = os.path.splitext(component_file)[0]
                component_path = component.Component.resolve_component(
                    component_name, self.settings
                )
                if component_path is None:
                    raise ValueError(f"Component {component_name} not found.")
                components.add(component.Component(component_path))

        for component_file in components:
            component_file.get_self_requirements(self.settings)

        # Step 5: Delete the .build_files folder
        shutil.rmtree(self.build_files_path)

        print(f"Built {len(components)} components in {time.time() - start} seconds.")


if __name__ == "__main__":
    os.chdir("sibyl")
    BuildComponents(version)
