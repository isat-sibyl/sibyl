import os
import shutil

if __name__ == '__main__':
	folders = ['layouts', 'locales', 'pages', 'static']
	files = ['settings.yaml', 'requirements.txt', 'dev.bat', 'build.bat']
	for folder in folders:
		shutil.copytree("sibyl/" + folder, folder, dirs_exist_ok=True)
	os.makedirs("components", exist_ok=True)
		
	for file in files:
		shutil.copy("sibyl/" + file, file)
	
	print("Init successful, you must now install dependencies.")