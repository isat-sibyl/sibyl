
import yaml
import os
	
class Settings:
	"""A class to hold the settings from settings.yaml."""

	root : str = "/"
	default_locale : str = "en"
	open_browser : bool = True
	debug: bool = True

	max_component_nesting : int = 100
	components_paths : list[str] = ["components", "{$SIBYL_PATH}/components"]
	layouts_paths : list[str] = ["layouts", "{$SIBYL_PATH}/layouts"]
	root_folders : list[str] = ["favicon"]

	pages_path : str = "pages"
	build_path : str = "build"
	locales_path : str = "locales"
	static_path : str = "static"

	cdn_url : str = "https://sibyl.dev"

	treat_warnings_as_errors : bool = False

	dev_port : int = 8080
	websockets_port : int = 8081

	def __init__(self):
		"""Load the settings from settings.yaml."""
		# set env var SIBYL_PATH as os.path.dirname(__file__)
		with open("settings.yaml", "r", encoding="utf-8") as file:
			result = yaml.safe_load(file)
			os.environ["SIBYL_PATH"] = os.path.dirname(os.path.dirname(__file__))
			result = Settings.replace_env_vars(result)
		
		# validate the settings. They must have the correct key and either not exist or be of the correct type
		for key, value in result.items():
			if value is None:
				continue
			if not hasattr(self, key):
				raise ValueError(f"Invalid setting '{key}'")
			if not isinstance(value, type(getattr(self, key))):
				raise ValueError(f"Invalid type for setting '{key}'. Expected {type(getattr(self, key))} but got {type(value)}")
			setattr(self, key, value)
	
	@staticmethod
	def replace_env_vars(var):
		"""Replace all instances of $ENV_VAR with the value of the environment variable."""
		if isinstance(var, str):
			return os.path.expandvars(var)
		elif isinstance(var, dict):
			for key, value in var.items():
				var[key] = Settings.replace_env_vars(value)
			return var
		elif isinstance(var, list):
			for i in range(len(var)):
				var[i] = Settings.replace_env_vars(var[i])
			return var
						