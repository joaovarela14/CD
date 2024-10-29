"""CD Chat server program."""
import logging
import socket
import selectors

from .protocol import CDProto
logging.basicConfig(filename="server.log", level=logging.DEBUG)

class Server:
    """Chat Server process."""
    adress = ('localhost', 50000)

    def __init__(self):
        # Initialize server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind(self.adress)
        self.server_socket.listen(25)

        self.server_selector = selectors.DefaultSelector()
        self.server_selector.register(self.server_socket, selectors.EVENT_READ, self.accept)
        
        self.connections = {}

    def accept(self, sock, mask):
        if not mask & selectors.EVENT_READ:
            return


        conn, client_adress = sock.accept()  # Establish a new connection with the client
        print('Accepted', conn, 'from', client_adress)  # Print a message indicating the new connection
        conn.setblocking(False)  

        self.server_selector.register(conn, selectors.EVENT_READ, self.read)

        self.connections[conn] = [None] 


    def read(self,conn, mask):
        try:
            if not mask & selectors.EVENT_READ:
                return
            # Receive a message from the connection
            mensagem_recebida = CDProto.recv_msg(conn)

            logging.debug('Received: "%s"', mensagem_recebida)
            print('Echoing', str(mensagem_recebida), 'to', conn)

            if mensagem_recebida.command == "join":
                if(None in self.connections[conn]):               
                    self.connections[conn].remove(None) 
                if(mensagem_recebida.channel not in self.connections[conn]):   
                    self.connections[conn].append(mensagem_recebida.channel)

                CDProto.send_msg(conn, mensagem_recebida) 


            elif mensagem_recebida.command == "message":
             
                self.connections[conn] = self.connections.get(conn, set())

                for connection in self.connections:
                    if mensagem_recebida.channel in self.connections[connection]:
                        CDProto.send_msg(connection, mensagem_recebida)

            elif mensagem_recebida.command == "register":
                
                CDProto.send_msg(conn, mensagem_recebida)

        except ConnectionError:
            # Handle connection errors
            print('Closing...', conn)
            self.cleanup_connection(conn)                                  




    def loop(self):
        """Loop indefinitely to process incoming events."""
        while True:
            events = self.server_selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)



    def cleanup_connection(self, conn):
        try:
            self.server_selector.unregister(conn)

        except Exception as e:
            logging.error(f"Failed to unregister {conn}: {e}")
            
        self.connections.pop(conn, None)
        conn.close()