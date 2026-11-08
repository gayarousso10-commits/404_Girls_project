
import socket
from datetime import datetime

from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage


class NetworkServer:

    def __init__(self, ip="127.0.0.1", port=8000):
        self.__ip = ip
        self.__port = port

        self.__server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.__server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.__server.bind((self.__ip, self.__port))
        self.__server.listen(1)

        print(f"Server is up at {ip}:{port}")

    def start(self):
        client_socket, address = self.__server.accept()

        print(f"Client connected at {address}")

        try:
            self.__handle_client(client_socket)

        finally:
            client_socket.close()
            self.__server.close()
            print("Server say bye")

    def __handle_client(self, client_socket):

        try:
            while True:

                # קבלת הודעה באמצעות הפרוטוקול
                client_message = Protocol.receive(client_socket)

                if client_message is None:
                    break

                print("Client:", client_message)

                # עיבוד ההודעה
                response_data = self.__process(client_message)

                # יצירת הודעת תשובה
                response = ProtocolMessage(
                    "ECHO" if client_message.command != "EXIT"
                    else "EXIT",
                    response_data
                )

                # שליחת התשובה
                Protocol.send(client_socket, response)

                if client_message.command == "EXIT":
                    break

        except (ProtocolError, ConnectionError) as e:
            print("Communication error:", e)

    def __process(self, message):

        command = message.command
        data = message.data

        if command == "TIME":
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        elif command == "ECHO":
            return data

        elif command == "PING":
            return "PONG"

        elif command == "EXIT":
            return "BYE"


if __name__ == "__main__":
    server = NetworkServer("127.0.0.1", 8000)
    server.start()
