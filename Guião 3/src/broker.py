import enum
import json
import pickle
import socket
import selectors
import xml.etree.ElementTree as ET
from typing import List, Tuple , Any


class Serializer(enum.Enum):
    """Possible message serializers."""
    JSON = 0
    XML = 1
    PICKLE = 2


class Broker:
    """Implementation of a PubSub Message Broker."""

    def __init__(self, host="localhost", port=9000):
        """Initialize broker."""
        self.canceled = False
        self._host = host
        self._port = port
        self.broker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.broker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broker.bind((self._host, self._port))
        self.broker.listen()
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.broker, selectors.EVENT_READ, self.accept)

        self.topic_subscribers = {}
        self.topic_message = {}
        self.consumers_info = {}
        self.producer_topics = []

    def accept(self, broker, mask):
        """Accept a connection and register the handler."""
        conn, addr = broker.accept()
        header = conn.recv(2).decode('utf-8')
        header_size = int(header.replace('f', ''))
        serialization_type = conn.recv(header_size).decode('utf-8')

        if serialization_type == "JSONQueue":
            self.consumers_info[conn] = Serializer.JSON
        elif serialization_type == "XMLQueue":
            self.consumers_info[conn] = Serializer.XML
        elif serialization_type == "PickleQueue":
            self.consumers_info[conn] = Serializer.PICKLE
        else:
            raise ValueError(f"Unsupported serialization type: {serialization_type}")


        self.sel.register(conn, selectors.EVENT_READ, self.handle)

    def handle(self, conn, mask):
        """Handle operations according to the message received by the Queue."""
        serialization_type = self.consumers_info[conn]
        header = conn.recv(4)

        if header:
            header = int(header.decode('utf-8').replace('f', ''))
            data = conn.recv(header)

            if serialization_type == Serializer.JSON:
                operation, topic, message = self.decode_json(data)
            elif serialization_type == Serializer.XML:
                operation, topic, message = self.decode_xml(data)
            elif serialization_type == Serializer.PICKLE:
                operation, topic, message = self.decode_pickle(data)
            else:
                raise ValueError(f"Unsupported serialization type: {serialization_type}")

            if operation == "PUBLISH":
                self.put_topic(topic, message)
            elif operation == "LIST_TOPICS":
                topic_list = self.list_topics()
                self.send(conn, "LIST_TOPICS", topic_list)
            elif operation == "SUBSCRIBE":
                self.subscribe(topic, conn, serialization_type)
            elif operation == "UNSUBSCRIBE":
                self.unsubscribe(topic, conn)
            else:
                raise ValueError(f"Unsupported operation: {operation}")
        else:
            self.unsubscribe("", conn)
            self.sel.unregister(conn)
            conn.close()

        


    def send(self, conn, operation: str, data, topic=""):
        """Send message to the consumer."""
        try:
            serialization_type = self.consumers_info[conn]

            if serialization_type == Serializer.JSON:
                encoded_msg = self.encode_json(operation, topic, data)
            elif serialization_type == Serializer.XML:
                encoded_msg = self.encode_xml(operation, topic, data)
            elif serialization_type == Serializer.PICKLE:
                encoded_msg = self.encode_pickle(operation, topic, data)
            else:
                raise ValueError(f"Unsupported serialization type: {serialization_type}")

            header = str(len(encoded_msg))
            size_header = len(header)
            newheader = 'f' * (4 - size_header) + header

            conn.send(newheader.encode('utf-8'))
            conn.send(encoded_msg)

        except KeyError:
            print(f"Connection {conn} not found in consumers_info")
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error occurred: {e}")


    def list_topics(self) -> List[str]:
        """Returns a list of strings containing all topics."""
        return self.producer_topics

    def get_topic(self, topic):
        """Returns the currently stored value in topic."""
        return self.topic_message.get(topic, None)

    def put_topic(self, topic, value):
        """Store the value in the topic and notify subscribers."""
        try:
            self.topic_message[topic] = value

            if topic not in self.producer_topics:
                self.producer_topics.append(topic)

            if topic not in self.topic_subscribers:
                self.topic_subscribers[topic] = []
                self._migrate_subscribers_from_parent_topics(topic)

            self._notify_subscribers(topic, value)

        except KeyError as e:
            print(f"Key error: {e}")
        except Exception as e:
            print(f"Unexpected error occurred: {e}")

    def _migrate_subscribers_from_parent_topics(self, topic: str):
        """Migrate subscribers from parent topics to the new topic."""
        subscribers_to_migrate = [
            consumer
            for parent_topic in self.topic_subscribers.keys()
            if topic.startswith(parent_topic)
            for consumer in self.list_subscriptions(parent_topic)
            if consumer not in self.list_subscriptions(topic)
        ]
        
        self.topic_subscribers[topic].extend(subscribers_to_migrate)

    def _notify_subscribers(self, topic: str, value):
        """Notify all subscribers of the topic with the new value."""
        for consumer in self.list_subscriptions(topic):
            self.send(consumer[0], "MESSAGE", value, topic)

    def list_subscriptions(self, topic: str) -> List[socket.socket]:
        """Provide list of subscribers to a given topic."""
        return self.topic_subscribers.get(topic, [])

    def subscribe(self, topic: str, address: socket.socket, _format: Serializer = None):
        """Subscribe to topic by client at the given address."""
        try:
            consumer_info = (address, _format)
            
            if address not in self.consumers_info:
                self.consumers_info[address] = _format
            
            if topic not in self.topic_subscribers:
                self.topic_subscribers[topic] = []
                self._migrate_subscribers_from_parent_topics(topic)
            
            if consumer_info not in self.topic_subscribers[topic]:
                self.topic_subscribers[topic].append(consumer_info)

            self._add_consumer_to_subtopics(topic, consumer_info)
            
            if topic in self.topic_message:
                self.send(address, "MESSAGE", self.get_topic(topic), topic)
        
        except KeyError as e:
            print(f"Key error: {e}")
        except Exception as e:
            print(f"Unexpected error occurred: {e}")

    def _add_consumer_to_subtopics(self, topic: str, consumer_info: Tuple[socket.socket, Serializer]):
        """Add consumer to all subtopics that start with the given topic."""
        for subtopic in self.topic_subscribers.keys():
            if subtopic.startswith(topic) and consumer_info not in self.topic_subscribers[subtopic]:
                self.topic_subscribers[subtopic].append(consumer_info)

    def unsubscribe(self, topic, address):
        """Unsubscribe to topic by client at the given address."""
        try:
            serialization_type = self.consumers_info[address]
            consumer_info = (address, serialization_type)
            
            if topic:
                # Remove the consumer from the specific topic and its subtopics
                self._remove_consumer_from_topics(topic, consumer_info)
            else:
                # Remove the consumer from all topics
                self._remove_consumer_from_all_topics(consumer_info)
        
        except KeyError as e:
            print(f"Key error: {e}")
        except Exception as e:
            print(f"Unexpected error occurred: {e}")

    def _remove_consumer_from_topics(self, topic: str, consumer_info: Tuple[socket.socket, Serializer]):
        """Remove consumer from the specific topic and its subtopics."""
        for t in list(self.topic_subscribers.keys()):
            if t.startswith(topic) and consumer_info in self.topic_subscribers[t]:
                self.topic_subscribers[t].remove(consumer_info)
    
    def _remove_consumer_from_all_topics(self, consumer_info: Tuple[socket.socket, Serializer]):
        """Remove consumer from all topics."""
        for t in list(self.topic_subscribers.keys()):
            if consumer_info in self.topic_subscribers[t]:
                self.topic_subscribers[t].remove(consumer_info)

    def encode_json(self, operation, topic, data):
        """Encode data using JSON."""
        message = {'operation': operation, 'topic': topic, 'data': data}
        return json.dumps(message).encode('utf-8')

    def decode_json(self, data):
        """Decode data using JSON."""
        decoded_data = json.loads(data.decode('utf-8'))
        return decoded_data['operation'], decoded_data['topic'], decoded_data['data']

    def encode_xml(self, operation, topic, data):
        """Encode data using XML."""
        root = ET.Element('root')
        ET.SubElement(root, 'operation').set("value", operation)
        ET.SubElement(root, 'topic').set("value", topic)
        ET.SubElement(root, 'data').set("value", str(data))
        return ET.tostring(root)

    def decode_xml(self, data):
        """Decode data using XML."""
        xml_tree = ET.fromstring(data.decode('utf-8'))
        operation = xml_tree.find('operation').attrib['value']
        topic = xml_tree.find('topic').attrib['value']
        message = xml_tree.find('data').attrib['value']
        return operation, topic, message

    def encode_pickle(self, operation, topic, data):
        """Encode data using Pickle."""
        pickle_dict = {'operation': operation, 'topic': topic, 'data': data}
        return pickle.dumps(pickle_dict)

    def decode_pickle(self, data):
        """Decode data using Pickle."""
        decoded_data = pickle.loads(data)
        return decoded_data['operation'], decoded_data['topic'], decoded_data['data']

    def run(self):
        """Run until canceled."""
        try:
            while not self.canceled:
                events = self.sel.select(timeout=1)
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj, mask)
        except Exception as e:
            print(f"Unexpected error occurred: {e}")

