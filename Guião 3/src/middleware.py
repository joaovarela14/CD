from collections.abc import Callable
from enum import Enum
import json
import pickle
import socket
import xml.etree.ElementTree as ET
from typing import Any, Tuple


class MiddlewareType(Enum):
    """Middleware Type."""
    CONSUMER = 1
    PRODUCER = 2


class Queue:
    """Representation of Queue interface for both Consumers and Producers."""

    def __init__(self, topic: str, _type: MiddlewareType = MiddlewareType.CONSUMER):
        """Create Queue."""
        self.topic = topic
        self.type = _type
        self.sock = self._create_socket()
        self._initialize_connection()

        if self.type == MiddlewareType.CONSUMER:
            self.subscribe(self.topic)

    def _create_socket(self) -> socket.socket:
        """Create and connect a socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Add this line to allow address reuse
        sock.connect(('localhost', 9000))
        return sock

    def _initialize_connection(self):
        """Initialize the connection by sending the serialization type."""
        serialization_type = self.__class__.__name__
        header = self._create_header(len(serialization_type), 2)
        self.sock.send(header.encode('utf-8'))
        self.sock.send(serialization_type.encode('utf-8'))

    @staticmethod
    def _create_header(message_size: int, header_size: int) -> str:
        """Create a header of a fixed size."""
        message_size_str = str(message_size)
        size_header = len(message_size_str)
        return 'f' * (header_size - size_header) + message_size_str

    def push(self, value: Any):
        """Send data to broker."""
        self.send("PUBLISH", self.topic, value)

    def pull(self) -> Tuple[str, Any]:
        """Waits for (topic, data) from broker."""
        header = self.sock.recv(4).decode('utf-8').replace('f', '')
        data = self.sock.recv(int(header))
        operation, topic, message = self.decode(data)

        if operation == "LIST_TOPICS":
            print("Available topics:")
            for topic in message:
                print(f"  - {topic}")
        elif operation == "MESSAGE":
            print(f"[{topic}]] --> {message}")

        return topic, message

    def list_topics(self, callback: Callable):
        """Lists all topics available in the broker."""
        self.send("LIST_TOPICS", "", "")
        header = self.sock.recv(4).decode('utf-8').replace('f', '')
        data = self.sock.recv(int(header))
        operation, _, message = self.decode(data)
        callback(message)

    def cancel(self, topic: str):
        """Cancel subscription."""
        self.send("UNSUBSCRIBE", topic, "")

    def subscribe(self, topic: str):
        """Subscribe to a topic."""
        self.send("SUBSCRIBE", topic, "")

    def send(self, operation: str, topic: str, data: Any):
        """Send encoded message to the broker."""
        serialized_data = self.encode(operation, topic, data)
        header = str(len(serialized_data))
        size_header = len(header)
        full_header = 'f' * (4 - size_header) + header
        self.sock.send(full_header.encode('utf-8'))
        self.sock.send(serialized_data)

    def encode(self, operation: str, topic: str, data: Any) -> bytes:
        """Serialize data (to be implemented by subclasses)."""
        raise NotImplementedError

    def decode(self, data: bytes) -> Tuple[str, str, Any]:
        """Unserialize data (to be implemented by subclasses)."""
        raise NotImplementedError


class JSONQueue(Queue):
    """Queue implementation with JSON based serialization."""

    def encode(self, operation: str, topic: str, data: Any):
        message = {'operation': operation, 'topic': topic, 'data': data}
        return json.dumps(message).encode('utf-8')

    def decode(self, data: bytes) -> Tuple[str, str, Any]:
        data = json.loads(data.decode('utf-8'))
        return data['operation'], data['topic'], data['data']


class XMLQueue(Queue):
    """Queue implementation with XML based serialization."""

    def encode(self, operation: str, topic: str, data: Any):
        root = ET.Element('root')
        ET.SubElement(root, 'operation').set("value", operation)
        ET.SubElement(root, 'topic').set("value", topic)
        ET.SubElement(root, 'data').set("value", str(data))
        return ET.tostring(root)

    def decode(self, data: bytes) -> Tuple[str, str, Any]:
        xml_tree = ET.fromstring(data.decode('utf-8'))
        operation = xml_tree.find('operation').attrib['value']
        topic = xml_tree.find('topic').attrib['value']
        message = xml_tree.find('data').attrib['value']
        return operation, topic, message


class PickleQueue(Queue):
    """Queue implementation with Pickle based serialization."""

    def encode(self, operation: str, topic: str, data: Any) -> bytes:
        pickle_dict = {'operation': operation, 'topic': topic, 'data': data}
        return pickle.dumps(pickle_dict)

    def decode(self, data: bytes) -> Tuple[str, str, Any]:
        data = pickle.loads(data)
        return data['operation'], data['topic'], data['data']
