import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from queue import Queue, Empty

from boxsdk import OAuth2, Client
from box.box_config import get_box_settings, store_tokens_callback, load_tokens, BoxSettings
from pathlib import Path


# ─── LOCAL HTTP SERVER FOR CALLBACK ────────────────────────────────────────────
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """
    Simple handler that:
     - Parses 'code' from the GET request query
     - Puts it onto a queue
     - Returns a 200 OK with a small HTML page
     - Shuts down the HTTP server after handling
    """

    server_version = "BoxOAuthCallback/1.0"

    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)
        if "code" in params:
            code = params["code"][0]
            # Send the code back to the main thread
            self.server.queue.put(code)
            # Respond to browser
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            try:
                html_path = f"{Path(__file__).parent}/auth_success.html"
                with open(html_path, "rb") as file:
                    html_content = file.read()
                    self.wfile.write(html_content)

            except FileNotFoundError:
                # Fallback to the original message if the file is not found
                self.wfile.write(
                    b"<html><body><h2>Authentication successful!</h2>"
                    b"You can close this window.</body></html>"
                )
            # Shutdown server
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(400, "Missing 'code' parameter in query")


class ThreadedHTTPServer(HTTPServer):
    """
    Extends HTTPServer by attaching a queue for passing the OAuth code back.
    """

    def __init__(self, server_address, RequestHandlerClass, queue):
        super().__init__(server_address, RequestHandlerClass)
        self.queue = queue


def get_authorization_code(auth_url: str, queue: Queue, timeout: int = 120) -> str:
    # Start HTTP server in background
    settings = get_box_settings()
    server = ThreadedHTTPServer(
        (settings.REDIRECT_HOST, settings.REDIRECT_PORT), OAuthCallbackHandler, queue
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Open the browser to let user authenticate
    print(f"Opening browser to:\n{auth_url}\n")
    webbrowser.open(auth_url, new=1, autoraise=True)

    try:
        # Wait up to x seconds for the code
        code = queue.get(timeout=timeout)
    except Empty:
        raise TimeoutError("Did not receive OAuth callback in time.")
    finally:
        server.server_close()

    return code


# ─── OAUTH2 AUTHENTICATION ─────────────────────────────────────────────────────
def authenticate_oauth(settings: BoxSettings) -> Client:
    access_token, refresh_token = load_tokens()
    oauth2 = OAuth2(
        client_id=settings.BOX_CLIENT_ID,
        client_secret=settings.BOX_CLIENT_SECRET,
        access_token=access_token,
        refresh_token=refresh_token,
        store_tokens=store_tokens_callback,
    )

    if not access_token:
        REDIRECT_URI = f"http://{settings.REDIRECT_HOST}:{settings.REDIRECT_PORT}/"
        # print(vars(oauth2))
        # print(REDIRECT_URI)
        auth_url, _csrf_token = oauth2.get_authorization_url(REDIRECT_URI)
        # queue for passing the code from HTTP handler to this thread
        code_queue = Queue()
        auth_code = get_authorization_code(auth_url, code_queue)
        oauth2.authenticate(auth_code)

    return Client(oauth2)


def main():
    """
    run this script independently to generate the box-tokens in a browser friendly environment

    from src/ directory run 'python -m box.box_auth'
    """
    settings = get_box_settings()
    authenticate_oauth(settings)


if __name__ == "__main__":
    main()
