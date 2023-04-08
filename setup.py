import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='sibyl',
    version='0.0.22',
    author='Pedro Cavalheiro',
    author_email='pedro.cavalheiro@isat.pt',
    description='Sibyl static site generator',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/isat-sibyl/sibyl',
    project_urls = {
        "Bug Tracker": "https://github.com/isat-sibyl/sibyl/issues"
    },
    license='All rights reserved',
    packages=['sibyl'],
    package_data={'sibyl': ['components/*', 'layouts/*', 'locales/*', 'locales/.global.json', 'pages/*', 'static/*', 'settings.yaml', 'hot-reload.html', 'dev.bat', 'build.bat']},
    include_package_data=True,
    install_requires=[
			'beautifulsoup4==4.12.2',
			'PyYAML==6.0',
			'soupsieve==2.4',
			'watchdog==3.0.0',
			'websockets==11.0.1'
		],
)