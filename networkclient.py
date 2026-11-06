import socket

class NetworkClient:

    def __init__(self, ip: str = "127.0.0.1", port: int = 8000):
        self.__sock = socket.socket()

        try:
            self.__sock.connect((ip, port))
            print("Connected to server!")

        except ConnectionRefusedError:
            print("Server is not available.")
            self.__sock.close()
            raise

    def run(self) -> None:
        try:
            while True:
                user_message = input("enter your command (TIME, ECHO, PING, EXIT): ")

                # שליחת הפקודה לשרת
                self.__sock.sendall((user_message + "\n").encode("utf-8"))
                # קבלת תשובה מהשרת
                server_message = b""

                while b"\n" not in server_message:
                    chunk = self.__sock.recv(1024)

                    if not chunk:
                        break

                    server_message += chunk

                server_message = server_message.split(b"\n", 1)[0]

                if not server_message:
                    print("Server disconnected.")
                    break

                print(f"server say {server_message.decode('utf-8')}")

                # יציאה לאחר קבלת תשובת השרת
                if user_message.strip().upper() == "EXIT":
                    break

        finally:
            self.__sock.close()
            print("client say bye")


# דוגמה להרצת המחלקה:
if __name__ == "__main__":
    client = NetworkClient(ip="127.0.0.1", port=8000)
    client.run()