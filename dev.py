from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import settings
import build

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

def try_build():
	try:
		build.Parser().build()
	except Exception as e:
		print(bcolors.WARNING +"[ERROR] Failed to rebuild", file=sys.stderr)
		print(str(e) + bcolors.ENDC, file=sys.stderr)
	else:
		print("[INFO] Successfully rebuilt")

class Handler(FileSystemEventHandler):
	def on_modified(self, event):
		if event.src_path != "." and not event.src_path.startswith(".\\" + settings.BUILD_PATH) and not event.src_path.startswith(".\\Lib") and not event.src_path.startswith(".\\Script"):
			print("[INFO] File " + event.src_path + " has been modified, rebuilding...")
			try_build()

class RequestHandler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory=settings.BUILD_PATH, **kwargs)

	def end_headers(self):
		self.send_my_headers()
		SimpleHTTPRequestHandler.end_headers(self)

	def send_my_headers(self):
		self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
		self.send_header("Pragma", "no-cache")
		self.send_header("Expires", "0")
	
if __name__ == '__main__':
	print("[INFO] Server started on port " + str(settings.DEV_PORT))
	server = HTTPServer(('localhost', settings.DEV_PORT), RequestHandler)
	observer = Observer()
	observer.schedule(Handler(), ".", recursive=True) # watch the local directory
	observer.start()
	try_build()
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		print("Shutting down...")
		server.shutdown()
		observer.stop()
		observer.join()