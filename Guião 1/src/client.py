"""CD Chat client program"""
import logging
import socket
import selectors
import sys
import fcntl
import os

from .protocol import CDProto, CDProtoBadFormat

logging.basicConfig(filename=f"{sys.argv[0]}.log", level=logging.DEBUG)

class Client:
    """Chat Client process."""

    def __init__(self, name: str = "Foo"):
        """Initializes chat client."""
        self.client_name = name
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   

        self.client_selector = selectors.DefaultSelector()
        self.client_selector.register(self.client_socket, selectors.EVENT_READ, self.read)

        self.channel = None
    
    def connect(self):
        """Connect to chat server and setup stdin flags."""
        self.client_socket.connect(('localhost',50000))                           #conectar a scoket ao servidor 

        mensagem_registo = CDProto.register(self.client_name)
        CDProto.send_msg(self.client_socket, mensagem_registo)

    def read(self, conn, mask):
        if not mask & selectors.EVENT_READ:
            return 

        try:
            
            mensagem_enviada = CDProto.recv_msg(self.client_socket) 
            logging.debug(f'Received: "{mensagem_enviada}"')

            if mensagem_enviada.command == "message":
                print("\r< " + mensagem_enviada.message) 

            elif mensagem_enviada.command == "join":
                print("\rJoined channel: " + mensagem_enviada.channel)

            else:
                 print("\rRegistered on the server with the name:  " + mensagem_enviada.user)

        except Exception as e:
            logging.error(f"Error reading message: {e}")
            self.cleanup_connection(conn)

    def client_input_read(self,stdin,mask):
        if not mask & selectors.EVENT_READ:
            return 

        
        frase = stdin.readline().strip()

        if frase.startswith("/join "):
  
            channel_name = frase[6:]
            mensagem = CDProto.join(channel_name)
            CDProto.send_msg(self.client_socket, mensagem)
            self.channel = channel_name

        elif frase == "exit":

            self.client_socket.close() 
            sys.exit("Exiting...")  

        else:
            mensagem = CDProto.message(frase, self.channel)
            CDProto.send_msg(self.client_socket, mensagem)     
        


    def loop(self):
        """Loop indefinetely."""
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

        self.client_selector.register(sys.stdin, selectors.EVENT_READ, self.client_input_read)
        while True:
            sys.stdout.write('> ')
            sys.stdout.flush()

            for k, mask in self.client_selector.select():
                callback = k.data
                callback(k.fileobj,mask)


    def cleanup_connection(self, conn):
        try:
            self.selector.unregister(conn)
        except Exception as e:
            logging.error(f"Failed to unregister {conn}: {e}")
        self.connections.pop(conn, None)
        conn.close()