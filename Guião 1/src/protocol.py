"""Protocol for chat server - Computação Distribuida Assignment 1."""
import json
from datetime import datetime
from socket import socket


class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command

    def __str__(self):
        return f'{{"command": "{self.command}"'

    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self, command, channel):
        super().__init__(command)
        self.channel = channel

    def __str__(self):

        base_str = super().__str__()

        full_message = f'{base_str}, "channel": "{self.channel}"}}'
        
        return full_message


class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, command, user):
        super().__init__(command)
        self.user = user

    def __str__(self):
        base_str = super().__str__()

        user_part = f'"user": "{self.user}"'
        
        full_message = f'{base_str}, {user_part}}}'
        
        return full_message


    
class TextMessage(Message):
    """Message to chat with other clients."""
    def __init__(self, command, message, channel=None):
        super().__init__(command)
        self.message = message
        self.channel = channel

    def __str__(self):
        base_str = super().__str__()
        timestamp = int(datetime.now().timestamp())

        message_parts = [f'"message": "{self.message}"', f'"ts": {timestamp}']


        if self.channel is not None:
            message_parts.insert(0, f'"channel": "{self.channel}"')

        full_message = f'{base_str}, {", ".join(message_parts)}}}'

        return full_message


class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        return RegisterMessage("register",username)

    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        return JoinMessage("join", channel)

    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        return TextMessage("message", message, channel)

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""

        #Construir a msg em formato json
        if isinstance(msg, RegisterMessage):
            json_message = json.dumps({"command": msg.command, "user": msg.user}).encode('utf-8')
        elif isinstance(msg, JoinMessage):
            json_message = json.dumps({"command": msg.command, "channel": msg.channel}).encode('utf-8')
        elif isinstance(msg, TextMessage):
            if(msg.channel==None):
                json_message = json.dumps({"command": msg.command, "message": msg.message, "ts": int(datetime.now().timestamp())}).encode('utf-8')
            else:
                json_message = json.dumps({"command": msg.command, "channel": msg.channel, "message": msg.message, "ts": int(datetime.now().timestamp())}).encode('utf-8')


        header = len(json_message).to_bytes(2, byteorder="big")  
        connection.sendall(header + json_message)    


    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        """Receives a message object through a connection."""
        header = connection.recv(2)
        if not header:
            raise ConnectionError("Failed to receive message header.")


        message_length = int.from_bytes(header, "big")


        message_data = connection.recv(message_length).decode('utf-8')

        try:
            message_json = json.loads(message_data)
        except json.JSONDecodeError as e:
            raise CDProtoBadFormat("Received message is not valid JSON.") from e


        command = message_json.get("command")


        if command == "message":

            message_content = message_json.get("message")
            channel = message_json.get("channel", None)  
            return CDProto.message(message_content, channel)

        elif command == "join":
            channel = message_json.get("channel")
            return CDProto.join(channel)

        elif command == "register":
            user_name = message_json.get("user")
            return CDProto.register(user_name)

        else:
            raise CDProtoBadFormat(f"Unknown command: {command}")                            #caso alguma chave nao exista em json.loads(msg) chamar CDProtoBadFormat                 


class CDProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")