import socket
from threading import Lock
from ClientHandler import ClientHandler


class NetworkServer:
    """שרת TCP מרובה תהליכונים המנהל חיבורי לקוחות ומקצה מטפל לכל לקוח."""

    def __init__(self, ip="127.0.0.1", port=8000):
        """אתחול שקע ההאזנה הראשי, רשימת המטפלים ומנעול הסנכרון."""
        self.__ip = ip
        self.__port = port
        self.__running = False
        self.__shutdown_done = False

        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.__server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__server.bind((self.__ip, self.__port))
            self.__server.listen(5)
            self.__server.settimeout(1.0)
        except OSError:
            self.__server.close()
            raise

        self.__handlers: list[ClientHandler] = []
        self.__lock: Lock = Lock()

        print(f"Server is up at {ip}:{port}")

    def start(self):
        """הפעלת השרת בלולאת accept לקבלת חיבורים מרובים במקביל."""
        self.__running = True
        try:
            while self.__running:
                try:
                    client_socket, address = self.__server.accept()
                except socket.timeout:
                    continue

                print(f"Client connected at {address}")

                with self.__lock:
                    if not self.__running:
                        client_socket.close()
                        break

                    handler = ClientHandler(client_socket, address, self)
                    self.__handlers.append(handler)
                    handler.start()

        except KeyboardInterrupt:
            print("\nServer shutting down...")
        except OSError as e:
            if self.__running:
                print(f"\nServer socket error: {e}")
        finally:
            self.shutdown()

    def remove_handler(self, handler: ClientHandler):
        """הסרה בטוחה של מטפל שהסתיים מתוך רשימת הפעילים תחת מנעול."""
        with self.__lock:
            if handler in self.__handlers:
                self.__handlers.remove(handler)

    def client_count(self) -> int:
        """החזרת מספר המטפלים הרשומים בזמן הקריאה בצורה מסונכרנת."""
        with self.__lock:
            return len(self.__handlers)

    def shutdown(self):
        """סגירת שקע השרת, עצירת כל המטפלים הפעילים והמתנה לסיומם."""
        with self.__lock:
            self.__running = False
            if self.__shutdown_done:
                return
            self.__shutdown_done = True
            handlers_copy = list(self.__handlers)

        try:
            self.__server.close()
        except OSError:
            pass

        for handler in handlers_copy:
            handler.stop()

        for handler in handlers_copy:
            handler.join(timeout=3.0)

        print("Server says bye")


if __name__ == "__main__":
    server = NetworkServer("127.0.0.1", 8000)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        server.shutdown()