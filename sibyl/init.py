import os
import shutil

if __name__ == "__main__":
    base_folder = os.path.dirname(__file__)
    folders = ["layouts", "locales", "pages", "static"]
    files = ["settings.yaml", "Pipfile", "requirements.txt"]
    for folder in folders:
        shutil.copytree(os.path.join(base_folder, folder), folder, dirs_exist_ok=True)
    os.makedirs("components", exist_ok=True)

    for file in files:
        shutil.copy(os.path.join(base_folder, file), file)

    print("Project initialized successfully.")
    print("To start the development server, run 'sibyl dev' or 'python -m sibyl.dev'")
    print("To build the project, run 'sibyl build' or 'python -m sibyl.build'")
