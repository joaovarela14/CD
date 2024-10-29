import argparse
import socket
import json
import threading
from sudoku import Sudoku
import itertools
from http.server import BaseHTTPRequestHandler, HTTPServer


class SudokuServerHandler(BaseHTTPRequestHandler):
    anchor_address = ('localhost', 7000)
    def __init__(self, worker_node, *args, **kwargs):
        self.worker_node = worker_node
        super().__init__(*args, **kwargs)

        
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
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            print(f"Received POST data: {post_data}")
            data = json.loads(post_data.decode('utf-8'))
            print(f"Decoded JSON data: {data}")

            anchor_response = self.send_to_anchor(data, 'solve')
            print(f"Received response from anchor: {anchor_response}")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(anchor_response)
        except json.JSONDecodeError as e:
            self.send_error(400, f"Bad Request: Unable to decode JSON. Error: {e}")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")
            print(f"Exception: {e}")

    def forward_to_anchor(self, endpoint):
        try:
            response = self.send_to_anchor({}, endpoint)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")
            print(f"Exception: {e}")

    def send_to_anchor(self, data, endpoint):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(self.anchor_address)
                s.sendall(json.dumps({"type": endpoint, "data": data}).encode('utf-8'))
                return self.receive_full_response(s)
        except Exception as e:
            print(f"Error communicating with anchor: {e}")
            raise

    def receive_full_response(self, sock):
        buffer_size = 4096
        response = b""
        while True:
            part = sock.recv(buffer_size)
            response += part
            if len(part) < buffer_size:
                break
        return response


class WorkerNode:
    def __init__(self, http_port, p2p_port, handicap, anchor=None):
        self.http_port = http_port
        self.p2p_port = p2p_port
        self.handicap = handicap / 1000  # Converte para segundos
        self.anchor = anchor
        self.nodes = {f"{self.get_local_ip()}:{self.p2p_port}": []}
        self.lock = threading.Lock()
        self.solved_count = 0
        self.validation_counts = {f"{self.get_local_ip()}:{self.p2p_port}": 0}

    def get_local_ip(self):
        return socket.gethostbyname(socket.gethostname())
    
    def start(self):
        p2p_thread = threading.Thread(target=self.run_p2p_server)
        p2p_thread.start()
        http_thread = threading.Thread(target=self.run_http_server)
        http_thread.start()

    def run_http_server(self):
        server_address = ('', self.http_port)
        httpd = HTTPServer(server_address, lambda *args, **kwargs: SudokuServerHandler(self, *args, **kwargs))
        print(f'HTTP server running on port {self.http_port}...')
        httpd.serve_forever()

    def run_p2p_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.p2p_port))  # Escuta em todas as interfaces
        server_socket.listen(5)
        print(f"P2P server running on port {self.p2p_port}...")

        if self.anchor:
            self.join_network(self.anchor)

        while True:
            client_socket, addr = server_socket.accept()
            client_handler = threading.Thread(
                target=self.handle_p2p_client,
                args=(client_socket,)
            )
            client_handler.start()


    def join_network(self, anchor):
        try:
            anchor_host, anchor_port = anchor.split(':')
            anchor_address = (anchor_host, int(anchor_port))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(anchor_address)
                print(self.get_ip_address())
                s.sendall(json.dumps({"type": "join", "address": f"{self.get_ip_address()}:{self.p2p_port}"}).encode('utf-8'))
                response = json.loads(self.receive_full_response(s).decode('utf-8'))
                with self.lock:
                    self.nodes = response['nodes']
        except Exception as e:
            print(f"Error joining network: {e}")


    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except Exception as e:
            ip_address = "127.0.0.1" 
        return ip_address

    def handle_p2p_client(self, client_socket):
        try:
            data = self.receive_full_response(client_socket)
            message = json.loads(data.decode('utf-8'))
            
            match message['type']:
                case 'join':
                    with self.lock:
                        new_node_address = message['address']
                        local_address = f"{self.get_local_ip()}:{self.p2p_port}"
                        
                        if local_address not in self.nodes:
                            self.nodes[local_address] = []
                        self.nodes[local_address].append(new_node_address)
                        
                        if new_node_address not in self.nodes:
                            self.nodes[new_node_address] = [local_address]
                        else:
                            self.nodes[new_node_address].append(local_address)
                        
                        client_socket.sendall(json.dumps({"nodes": self.nodes}).encode('utf-8'))
                        print(f"Node joined: {message['address']}")

                case 'solve':
                    data = message['data']
                    sudoku_grid = data.get('sudoku')
                    if sudoku_grid:
                        self.solve_sudoku(sudoku_grid, client_socket)

                case 'solve_part':
                    part = message['part']
                    solutions = self.solve_part(part)
                    client_socket.sendall(json.dumps({"solutions": solutions}).encode('utf-8'))

                case 'stats':
                    stats = self.get_stats()
                    self.send_stats_to_client(client_socket, stats)

                case 'network':
                    self.send_network_info(client_socket)

                case _:
                    print(f"Tipo de mensagem desconhecido: {message['type']}")


        except Exception as e:
            print(f"Error handling P2P client: {e}")
        finally:
            client_socket.close()


    def get_stats(self):
        if self.is_anchor_node():  # Verificar se este nó é o âncora
            return self.collect_stats_from_nodes()
        else:
            return self.get_local_stats()


    def is_anchor_node(self):
        return self.anchor is None


    def collect_stats_from_nodes(self):
        stats = {
            "all": {
                "solved": 0,
                "validations": 0
            },
            "nodes": []
        }
        node_validation_counts = {}
        
        with self.lock:
            nodes_copy = list(self.nodes.keys())

        for node in nodes_copy:
            if node != self.get_node_key():
                node_stats = self.get_node_stats(node)
                if node_stats:
                    stats["all"]["solved"] += node_stats["solved"]
                    node_validations = node_stats["validations"]
                    stats["all"]["validations"] += node_validations
                    node_validation_counts[node] = node_validations

        with self.lock:
            current_node_validations = self.validation_counts.get(self.get_node_key(), 0)
            stats["all"]["solved"] += self.solved_count
            stats["all"]["validations"] += current_node_validations
            node_validation_counts[self.get_node_key()] = current_node_validations

        for address, validations in node_validation_counts.items():
            stats["nodes"].append({"address": address, "validations": validations})

        return stats


    def get_local_stats(self):
        node_key = self.get_node_key()
        with self.lock:
            stats = {
                "solved": self.solved_count,
                "validations": self.validation_counts.get(node_key, 0)
            }
        return stats


    def get_node_key(self):
        return f"{socket.gethostbyname(socket.gethostname())}:{self.p2p_port}"


    def get_node_stats(self, node):
        node_host, node_port = node.split(':')
        node_address = (node_host, int(node_port))
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(node_address)
                s.sendall(json.dumps({"type": "stats"}).encode('utf-8'))
                response = json.loads(self.receive_full_response(s).decode('utf-8'))
                return {
                    "solved": response.get("solved", 0),
                    "validations": response.get("validations", 0)
                }
        except Exception as e:
            print(f"Error retrieving stats from node {node}: {e}")
            return None


    def send_stats_to_client(self, client_socket, stats):
        client_socket.sendall(json.dumps(stats).encode('utf-8'))

    
    #NETWORK
    def send_network_info(self, client_socket):
        network_info = self.fetch_network_info()
        self.send_data(client_socket, network_info)


    def fetch_network_info(self):
        with self.lock:
            network_info = self.nodes.copy() 
        return network_info


    def send_data(self, client_socket, data):
        json_data = json.dumps(data).encode('utf-8')
        client_socket.sendall(json_data)

    #SUDOKU SOLVE


    def solve_sudoku(self, sudoku_grid, client_socket):
        while True:
            num_workers = len(self.nodes)
            print(f"Number of workers: {num_workers}")
            
            parts = self.split_sudoku(sudoku_grid, num_workers)
            all_solutions = self.distribute_and_collect(parts)

            if all_solutions and all(part is not None for part in all_solutions):
                combined_solution = self.combine_solutions(all_solutions)
                response = {
                    "message": "Sudoku solved successfully!" if combined_solution else "Failed to find a valid Sudoku solution.",
                    "sudoku": combined_solution if combined_solution else sudoku_grid
                }
                if combined_solution:
                    self.solved_count += 1

                client_socket.sendall(json.dumps(response).encode('utf-8'))
                break
            else:
                print("Retrying with fewer workers due to non-responsive nodes...")

    def split_sudoku(self, sudoku, num_workers):
        order = [0] * num_workers
        current_worker = 0
        
        index = 0
        while index < len(sudoku):
            order[current_worker] += 1
            current_worker = (current_worker + 1) % num_workers
            index += 1

        print(f"Order of distribution: {order}")

        parts = []
        current_line = 0
        worker_index = 0

        while worker_index < len(order):
            lines_per_worker = order[worker_index]
            parts.append(sudoku[current_line:current_line + lines_per_worker])
            current_line += lines_per_worker
            worker_index += 1

        return parts


    def distribute_and_collect(self, parts):
        results = [None] * len(parts)
        threads = []
        with self.lock:
            nodes_copy = list(self.nodes.keys())

        for i, part in enumerate(parts):
            if i >= len(nodes_copy):
                break
        
            worker_address = nodes_copy[i]
            thread = threading.Thread(
                target=self.send_to_worker,
                args=(i, part, results, worker_address)
            )
            threads.append(thread)
            thread.start()


        [thread.join() for thread in threads]

        with self.lock:
            for i, result in enumerate(results):
                if result is None and nodes_copy[i % len(nodes_copy)] in self.nodes:
                    worker_address = nodes_copy[i % len(nodes_copy)]
                    print(f"Removing non-responsive worker: {worker_address}")
                    del self.nodes[worker_address]

        return results

    def send_to_worker(self, part_index, part, results, worker_address):
        try:
            worker_host, worker_port = worker_address.split(':')
            worker_address = (worker_host, int(worker_port))
            local_address = socket.gethostbyname(socket.gethostname())
            
            message = self.create_message(part_index, part, local_address)
            
            with socket.create_connection(worker_address) as sock:
                self.send_message(sock, message)
                response = self.receive_full_response(sock)
                results[part_index] = self.process_response(response)
                
        except socket.error as e:
            print(f"Socket error with worker {worker_address}: {e}")
            results[part_index] = None
        except json.JSONDecodeError as e:
            print(f"JSON error while decoding response: {e}")
            results[part_index] = None
        except Exception as e:
            print(f"Unexpected error with worker {worker_address}: {e}")
            results[part_index] = None

    def create_message(self, part_index, part, local_address):
        return json.dumps({
            'type': 'solve_part',
            'part_index': part_index,
            'part': part,
            'address': f"{local_address}:{self.p2p_port}"
        }).encode('utf-8')

    def send_message(self, sock, message):
        try:
            sock.sendall(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            raise

    def process_response(self, response):
        try:
            return json.loads(response.decode('utf-8')).get('solutions')
        except Exception as e:
            print(f"Error processing response: {e}")
            return None


    def receive_full_response(self, sock):
        buffer_size = 4096
        response = b""
        while True:
            part = sock.recv(buffer_size)
            response += part
            if len(part) < buffer_size:
                break
        return response

    def combine_solutions(self, parts):
        print("Combining solutions")
        if any(part is None for part in parts):
            print("One or more parts are None")
            return None

        all_combinations = list(itertools.product(*parts))
        for combination in all_combinations:
            combined_sudoku = [item for part in combination for item in part if isinstance(part, list)]
            print(f"Combining part: {combined_sudoku}")
            sudoku = Sudoku(combined_sudoku)

            if sudoku.check():
                return combined_sudoku
        return None

    def solve_part(self, part):
        print(f"Solving part: {part}")
        sudoku = Sudoku(part)
        solutions, validations = sudoku.solve(part)
        print(f"Solutions: {solutions}, Validations: {validations}")
        with self.lock:
            self.validation_counts[f"{socket.gethostbyname(socket.gethostname())}:{self.p2p_port}"] += validations
        return solutions


def parse_args():
    parser = argparse.ArgumentParser(description="Sudoku Solver Node")
    parser.add_argument('-p', '--http-port', type=int, required=True, help="Port for HTTP server")
    parser.add_argument('-s', '--p2p-port', type=int, required=True, help="Port for P2P server")
    parser.add_argument('-c', '--handicap', type=int, default=0, help="Handicap in ms for validation")
    parser.add_argument('-a', '--anchor', type=str, help="Anchor node address (e.g., 127.0.0.1:7000)")

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    worker_node = WorkerNode(args.http_port, args.p2p_port, args.handicap, args.anchor)
    worker_node.start()