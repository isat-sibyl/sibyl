# Sibyl

Sibyl is a static site builder written in Python. It allows you to easily create, develop, and build static websites with a Single Page Application (SPA) feel. With its simple-to-use commands, hot reloading capabilities, and partial page loading, Sibyl makes your web development process seamless and efficient.

## Features

* Blazing fast websites
* Ready for deployment to Cloudflare Pages
* Hot reloading on the development server
* Navigation between pages like a SPA with partial page loading

## Installation

Ensure that you have Python 3.7 or higher installed. You can download the latest version of Python from [https://www.python.org/downloads/](https://www.python.org/downloads/).

To install Sibyl, run the following command:

```
pip install git+ssh://git@github.com/isat-sibyl/sibyl.git
```

## Usage

### Initializing a new project

To create a new project, navigate to the desired directory and run the following command:

```
sibyl init
```

This will generate a new project structure with the necessary files.

### Starting a development server

To start a development server with hot reloading, navigate to your project directory and run:

```
sibyl dev
```

Once the server is up and running, you can view your website at [http://localhost:8000](http://localhost:8000).

### Building for production

To build your website for production, navigate to your project directory and run:

```
sibyl build
```

This command will generate a `dist` folder containing the production-ready static files.