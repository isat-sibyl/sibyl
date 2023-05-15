# Sibyl

Sibyl is a static site builder written in Python. It allows you to easily create, develop, and build static websites with a Single Page Application (SPA) feel. With its simple-to-use commands, hot reloading capabilities, and partial page loading, Sibyl makes your web development process seamless and efficient.

## Features

* Blazing fast websites
* Ready for deployment to Cloudflare Pages
* Hot reloading on the development server
* Navigation between pages like a SPA with partial page loading

## Installation

Ensure that you have Python 3.7 or higher installed. You can download the latest version of Python from [https://www.python.org/downloads/](https://www.python.org/downloads/).

To install Sibyl, make sure you have access to this GitHub repo from your shell (see adding ssh keys below) and run the following command:

```
pip install git+ssh://git@github.com/isat-sibyl/sibyl.git#egg=sibyl[dev]
```

## Adding ssh keys to your shell (if needed)

If you do not have access to this GitHub repo from your shell, you will need to add your ssh keys to your shell. To do this, follow the instructions below:

1. Generate a new ssh key by running the following command (replace the email with your own):

```
ssh-keygen -t ed25519 -C "your_email@example.com"
```

2. Manually clone any repo via ssh before proceeding to the next step. For example, to clone this repo, run:

```
git clone git@github.com:isat-sibyl/sibyl.git
```

You will be prompted to trust the host. Verify that the fingerprint matches GitHub's fingerprint and type `yes` to continue.

3. Follow the steps in [GitHub's documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) to add your ssh key to your GitHub account.

## Usage

### Initializing a new project

To create a new project, navigate to the desired directory and run the following command:

```
sibyl init
```

or

```
python -m sibyl.init
```

This will generate a new project structure with the necessary files.

### Starting a development server

To start a development server with hot reloading, navigate to your project directory and run:

```
sibyl dev
```

Once the server is up and running, you can view your website at [http://localhost:8080](http://localhost:8080).

### Building for production

To build your website for production, navigate to your project directory and run:

```
sibyl build
```

This command will generate a `dist` folder containing the production-ready static files.

# Project structure

A project is divided by folders:

 - pages - Folder in which every html file represents a page
 - locales - All the locales with locale specific translations
 - static - All files that will be accessible at the root of the website
   - favicon - Favicon files folder
   - variables.css - Styling variables for the website
 - components - Callable components (for reusing code)
 - layouts - General layout of a page, for reusing for multiple pages
 - dist - Folder in which the result website is placed
 - settings.yaml - The settings file
