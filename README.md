# Sibyl

Sibyl is a static site builder written in Python. It allows you to easily create, develop, and build static websites with a Single Page Application (SPA) feel. With its simple-to-use commands, hot reloading capabilities, and partial page loading, Sibyl makes your web development process seamless and efficient.

That was the marketing part. Now for the real part, Sibyl is something I wrote in a Sunday and wrote some words I call documentation in a morning. This was never meant to be public or used in anything real, yet here we are.

Most documentation is actually in my mind. Considering all of that, if you still want to use Sibyl, feel free to. If you want to contribute, even better, just create a PR.

## Features

* Blazing fast websites
* Ready for deployment to Cloudflare Pages
* Hot reloading on the development server
* Navigation between pages like a SPA with partial page loading

## Installation

Ensure that you have Python 3.7 or higher installed. You can download the latest version of Python from [https://www.python.org/downloads/](https://www.python.org/downloads/).

To install Sibyl run the following command:

```
pip install isat-sibyl
```

## Docs

Available at https://docs.sibyl.dev.
Contribute at https://github.com/isat-sibyl/sibyl-docs.

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
