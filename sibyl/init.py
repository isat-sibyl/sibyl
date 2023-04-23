import os
import shutil

if __name__ == "__main__":
    base_folder = os.path.dirname(__file__)
    folders = ["layouts", "locales", "pages", "static"]
    files = ["settings.yaml", "Pipfile", "requirements.txt"]
    for folder in folders:
        shutil.copytree(os.path.join(base_folder, folder), folder)
    os.makedirs("components", exist_ok=True)

    for file in files:
        shutil.copy(os.path.join(base_folder, file), file)

    with open(".gitignore", "w") as file:
        file.write("dist")
    with open("runtime.txt", "w") as file:
        file.write("3.7")

    print("Project initialized successfully.")
    print("To start the development server, run 'sibyl dev' or 'python -m sibyl.dev'")
    print("To build the project, run 'sibyl build' or 'python -m sibyl.build'")
