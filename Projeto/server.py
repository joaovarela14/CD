from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import socket

class SudokuServerHandler(BaseHTTPRequestHandler):
    anchor_server_address = ('localhost', 7000)  # Address of the anchor server

    def do_POST(self):
        if self.path == '/solve':
            self.process_solve_request()
        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self):
        if self.path in ['/stats', '/network']:
            self.process_get_request()
        else:
            self.send_error(404, "Endpoint not found")

    def process_solve_request(self):
        """Process POST request for solving Sudoku."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            print(f"Received POST data: {post_data}")
            sudoku_data = self.decode_json(post_data)
            print(f"Decoded JSON data: {sudoku_data}")

            anchor_response = self.send_request_to_anchor(sudoku_data, 'solve')
            print(f"Received response from anchor: {anchor_response}")

            self.send_response_with_json(anchor_response)
        except json.JSONDecodeError as e:
            self.handle_error(400, f"Bad Request: Unable to decode JSON. Error: {e}")
        except Exception as e:
            self.handle_error(500, f"Internal Server Error: {e}")
            print(f"Exception: {e}")

    def process_get_request(self):
        """Process GET request for stats or network information."""
        endpoint = self.path.strip("/")
        try:
            response = self.send_request_to_anchor({}, endpoint)
            self.send_response_with_json(response)
        except Exception as e:
            self.handle_error(500, f"Internal Server Error: {e}")
            print(f"Exception: {e}")

    def send_request_to_anchor(self, data, endpoint):
        """Send request to the anchor server and get response."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(self.anchor_server_address)
                request_payload = self.create_request_payload(data, endpoint)
                sock.sendall(request_payload)
                return self.read_full_response(sock)
        except Exception as e:
            print(f"Error communicating with anchor: {e}")
            raise

    def decode_json(self, raw_data):
        """Decode raw JSON data."""
        return json.loads(raw_data.decode('utf-8'))

    def create_request_payload(self, data, endpoint):
        """Create JSON payload to send to the anchor server."""
        return json.dumps({"type": endpoint, "data": data}).encode('utf-8')

    def read_full_response(self, sock):
        """Read full response from the anchor server."""
        buffer_size = 4096
        response = b""
        while True:
            part = sock.recv(buffer_size)
            if not part:
                break
            response += part
        return response

    def send_response_with_json(self, response_data):
        """Send JSON response to the client."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(response_data)

    def handle_error(self, code, message):
        """Handle HTTP errors with appropriate response."""
        self.send_error(code, message)

def start_server(server_class=HTTPServer, handler_class=SudokuServerHandler, port=8001):
    """Start the HTTP server."""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Server running on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    start_server()
