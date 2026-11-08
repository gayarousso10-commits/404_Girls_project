
import socket
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage


class NetworkClient:

    def __init__(self, ip="127.0.0.1", port=8000):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.__sock.connect((ip, port))
            print("Connected to server!")

        except OSError:
            self.__sock.close()
            print("Server is not available.")
            raise

    def run(self):
        try:
            while True:
                user_input = input(
                    "Enter command (TIME, ECHO, PING, EXIT): "
                )

                try:
                    message = ProtocolMessage.from_user_input(user_input)

                    # שליחת הודעה לפי הפרוטוקול
                    Protocol.send(self.__sock, message)

                    # קבלת תשובה לפי הפרוטוקול
                    response = Protocol.receive(self.__sock)

                    if response is None:
                        print("Server disconnected.")
                        break

                    print("Server:", response.data)

                    if message.command == "EXIT":
                        break

                except ProtocolError as e:
                    print("Protocol error:", e)

        finally:
            self.__sock.close()
            print("Client say bye")


if __name__ == "__main__":
    client = NetworkClient()
    client.run()
