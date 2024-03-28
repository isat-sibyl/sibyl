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
from .helpers import settings as settings_module
import socketserver
import websockets
from websockets.server import serve
import signal
import re
from urllib.parse import unquote

connected = set()
settings = settings_module.Settings()

logging.basicConfig(level=logging.INFO)


def try_build():
    """Try to build the site, and log any errors."""
    try:
        build.Build(True)
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
        if (
            event.src_path != "."
            and not event.src_path.startswith(".\\" + settings.build_path)
            and not event.src_path.startswith(".\\Lib")
            and not event.src_path.startswith(".\\Script")
            and not event.src_path.startswith(".\\.git")
        ):
            logging.info("File " + event.src_path + " has been modified, rebuilding...")
            try_build()
            asyncio.run(send_reload_signal())


class RequestHandler(SimpleHTTPRequestHandler):
    """A request handler that adds cache-control headers to all responses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=settings.build_path, **kwargs)

    def end_headers(self):
        self.send_my_headers()
        SimpleHTTPRequestHandler.end_headers(self)

    def send_my_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def do_GET(self):
        if re.search("^/[a-zA-z]+:\/", self.path) and (
            not self.path.lower().startswith("http://")
            and not self.path.lower().startswith("https://")
        ):
            # remove leading slash and serve the file from the absolute path specified
            self.path = unquote(self.path[1:])
            with open(self.path, "rb") as f:
                self.send_response(200)
                ctype = self.guess_type(self.path)
                fs = os.fstat(f.fileno())
                self.send_header("Content-type", ctype)
                self.send_header("Content-Length", str(fs[6]))
                self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                self.end_headers()
                self.copyfile(f, self.wfile)
            return
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/" + settings.default_locale + "/")
            self.end_headers()
            return
        SimpleHTTPRequestHandler.do_GET(self)


async def handler(websocket: websockets.WebSocketServerProtocol):
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


async def run_ws_server(stop_event: asyncio.Event, stopped: asyncio.Event):
    """Run the websocket server."""
    server = await serve(handler, "localhost", settings.websockets_port)
    await stop_event.wait()
    server.close()
    await server.wait_closed()
    stopped.set()


async def main(terminate: asyncio.Event):
    """Start the web server, file watcher, and websocket server."""
    stop_event = asyncio.Event()
    stopped = asyncio.Event()
    ws_server = asyncio.create_task(run_ws_server(stop_event, stopped))
    logging.info(
        "Serving websocket server at port " + str(settings.websockets_port) + "..."
    )

    observer = Observer()
    observer.schedule(Handler(), ".", recursive=True)  # watch the local directory
    observer.start()
    logging.info("Watching for file changes...")
    try_build()

    httpd = socketserver.ThreadingTCPServer(("", settings.dev_port), RequestHandler)
    logging.info("Serving files at port " + str(settings.dev_port) + "...")
    if settings.open_browser:
        logging.info("Opening browser...")
        webbrowser.open("http://localhost:" + str(settings.dev_port) + "/")
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
    await stopped.wait()
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
