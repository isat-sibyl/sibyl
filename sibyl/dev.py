import asyncio
import os
import traceback
import logging
import webbrowser
from http.server import SimpleHTTPRequestHandler
from threading import Thread
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from . import build
import socketserver
import websockets
from websockets.server import serve
import signal

connected = set()
settings = build.load_settings()

logging.basicConfig(level=logging.INFO)

def try_build():
	"""Try to build the site, and log any errors."""
	try:
		build.Parser().build(True)
	except Exception as e:
		logging.error("Failed to rebuild")
		logging.error(e)
		traceback.print_exc()
	else:
		logging.info("Successfully rebuilt")

async def send_reload_signal():
	"""Send a reload signal to all connected clients."""
	for client in connected:
		await client.send("reload")

class Handler(FileSystemEventHandler):
	"""A watchdog event handler that rebuilds the site on file changes."""
	def on_modified(self, event):
		if event.src_path != "." and not event.src_path.startswith(".\\" + settings['BUILD_PATH']) and not event.src_path.startswith(".\\Lib") and not event.src_path.startswith(".\\Script"):
			logging.info("File " + event.src_path + " has been modified, rebuilding...")
			try_build()
			asyncio.run(send_reload_signal())

class RequestHandler(SimpleHTTPRequestHandler):
	"""A request handler that adds cache-control headers to all responses."""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory=settings['BUILD_PATH'], **kwargs)

	def end_headers(self):
		self.send_my_headers()
		SimpleHTTPRequestHandler.end_headers(self)

	def send_my_headers(self):
		self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
		self.send_header("Pragma", "no-cache")
		self.send_header("Expires", "0")
	
	def do_GET(self):
		if self.path == "/":
			self.send_response(302)
			self.send_header("Location", "/" + settings["DEFAULT_LOCALE"] + "/")
			self.end_headers()
		else:
			SimpleHTTPRequestHandler.do_GET(self)

async def handler(websocket : websockets.WebSocketServerProtocol):
	"""A websocket handler that sends a reload signal to all connected clients when a reload signal is received."""
	connected.add(websocket)
	
	while True:
		try:
			message = await websocket.recv()
			if message != "reload":
				logging.error("Received invalid message: " + message)
				continue
		except websockets.exceptions.ConnectionClosed:
			connected.remove(websocket)
			break
		else:
			logging.info("Reload signal received, reloading all clients...")
			# send a reload signal to all connected clients
			for client in connected:
				await client.send("reload") 

async def run_ws_server(stop_event : asyncio.Event, stopped : asyncio.Event):
	"""Run the websocket server."""
	server = await serve(handler, "localhost", settings['WEBSOCKETS_PORT'])
	await stop_event.wait()
	server.close()
	await server.wait_closed()
	stopped.set()

async def main(terminate : asyncio.Event):
	"""Start the web server, file watcher, and websocket server."""
	stop_event = asyncio.Event()
	stopped = asyncio.Event()
	ws_server = asyncio.create_task(run_ws_server(stop_event, stopped))
	logging.info("Serving websocket server at port " + str(settings['WEBSOCKETS_PORT']) + "...")

	observer = Observer()
	observer.schedule(Handler(), ".", recursive=True) # watch the local directory
	observer.start()
	logging.info("Watching for file changes...")
	try_build()

	httpd = socketserver.ThreadingTCPServer(("", settings['DEV_PORT']), RequestHandler) 
	logging.info("Serving files at port " + str(settings['DEV_PORT']) + "...")
	if settings['OPEN_BROWSER']:
		logging.info("Opening browser...")
		webbrowser.open("http://localhost:" + str(settings['DEV_PORT']) + "/")
	static_server = Thread(target=httpd.serve_forever)
	static_server.start()

	await terminate.wait()
	
	logging.info("Shutting down web server...")
	httpd.shutdown()
	
	logging.info("Shutting down observer...")
	observer.stop()
	
	logging.info("Shutting down websocket server...")
	stop_event.set()
	static_server.join()
	observer.join()
	await	stopped.wait()
	ws_server.cancel()
	logging.info("All servers shut down.")
	
	loop = asyncio.get_event_loop()
	loop.call_soon_threadsafe(loop.stop)
	
if __name__ == "__main__":
	terminate = asyncio.Event()
	for sig in (signal.SIGINT, signal.SIGTERM):
		signal.signal(sig, lambda x, y: terminate.set())
	asyncio.run(main(terminate))
	os._exit(0) 