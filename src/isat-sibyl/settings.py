"""Build settings"""

ROOT = '/'
DEFAULT_LOCALE = 'en'

MAX_COMPONENT_NESTING = 100

COMPONENTS_PATH = ['components', 'sibyl/components']
LAYOUT_PATH = ['layouts', 'sibyl/layouts']
PAGES_PATH = 'pages'
BUILD_PATH = 'dist'
LOCALES_PATH = 'locales'
STATIC_PATH = 'static'

DEV_PORT = 8080
WEBSOCKETS_PORT = 8091
OPEN_BROWSER = False
HOT_RELOAD_SCRIPT = "sibyl/hot_reload.html"