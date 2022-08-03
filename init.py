import shutil

if __name__ == '__main__':
	folders = ['components', 'layouts', 'locales', 'pages', 'static']
	files = ['settings.py', 'requirements.txt', 'dev.bat', 'build.bat']
	for folder in folders:
		shutil.copytree("sibyl/" + folder, folder, dirs_exist_ok=True)
		
	for file in files:
		shutil.copy("sibyl/" + file, file)
	
	print("Init successful, you must now install dependencies.")