import shutil

if __name__ == '__main__':
	copy = ['components', 'layouts', 'locales', 'pages', 'static', 'settings.py', 'requirements.txt', 'dev.bat', 'build.bat']
	for to_copy in copy:
		shutil.copytree("/sibyl/" + to_copy, "/" + copy)
