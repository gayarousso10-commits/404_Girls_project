import socket
from datetime import datetime

class NetworkServer:

    def __init__(self, ip="127.0.0.1", port=8000):

        self.__ip = ip
        self.__port = port

        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__server.bind((self.__ip, self.__port))
        self.__server.listen(1)
        print(f"server is up at {ip}:{port}")

    def start(self) -> None:
        client_socket, address = self.__server.accept()
        print(f"client connected at {address}")
        try:
            self.__handle_client(client_socket, address)
        finally:
            client_socket.close()
            self.__server.close()
            print("Server say bye")




    def __handle_client(self, client_socket, address) -> None:
        try:
            client_message = client_socket.recv(1024).decode("utf-8")

            while client_message != "EXIT" and client_message != "":
                print(f"client say: {client_message}")

                response = self.__process(client_message)
                client_socket.send(response.encode("utf-8"))

                client_message = client_socket.recv(1024).decode("utf-8")

            client_socket.send("BYE".encode("utf-8"))

        except ConnectionAbortedError:
            pass


    def __process(self, msg: str) -> str:
        parts = msg.split(" ", 1)
        command = parts[0].upper()
        data = parts[1] if len(parts) > 1 else ""

        if command == "TIME":
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        elif command == "ECHO":
            return data

        elif command == "PING":
            return "PONG"

        elif command == "EXIT":
            return "BYE"

        else:
            return "ERROR"


if __name__ == "__main__":
    server = NetworkServer("192.168.11.77", 8000)
    server.start()