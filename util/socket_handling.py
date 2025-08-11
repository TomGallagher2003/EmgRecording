""" Functions for handling TCP socket connections and data transfer """
import socket
import time


class SocketHandler:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = None

    def connect(self, retries=5, retry_delay=2):
        """ Establish a socket connection """
        for i in range(retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.socket.connect((self.ip, self.port))
                print("Connected to Socket!")
                self.socket.settimeout(20)
                return True
            except socket.error as msg:
                print(msg)
                time.sleep(retry_delay)
        raise ConnectionError("Failed to connect to socket after multiple retries")

    def close(self):
        """ Shut down and close the socket connection """
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            print("Socket Closed!")
            return True
        except socket.error as msg:
            print(msg)
            return False

    def send(self, data):
        """ Send data over the socket """
        try:
            sent = self.socket.sendall(data)
            self.socket.settimeout(20)
            return sent
        except socket.error as msg:
            print(msg)
            return None

    def receive(self, size):
        """ Receive data over the socket """
        try:
            data = self.socket.recv(size)
            return data
        except socket.error as msg:
            print(msg)
            return None

    def flush(self):
        """Flush any residual data in the buffer"""
        while True:
            data = self.socket.recv(4096)
            if not data:
                break
