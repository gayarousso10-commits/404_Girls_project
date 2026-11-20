import socket
# תוספת: ייבוא threading עבור ניהול מנעול (Lock) לבקשות במקביל
import threading
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage


class NetworkClient:
    # תוספת: הגדרת זמני המתנה להתחברות ולקבלת תשובה לפי דרישות שלב 5
    CONNECT_TIMEOUT = 5
    REPLY_TIMEOUT = 10

    def __init__(self, ip="127.0.0.1", port=8000):
        # תוספת: שמירת כתובת השרת, יצירת מנעול ואתחול דגל מצב החיבור
        self.__address = (ip, port)
        self.__lock = threading.Lock()
        self.__connected = False
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # שינוי: הגדרת timeout להתחברות, התחברות לכתובת השמורה, ושינוי ל-timeout תשובה
            self.__sock.settimeout(self.CONNECT_TIMEOUT)
            self.__sock.connect(self.__address)
            self.__sock.settimeout(self.REPLY_TIMEOUT)
            self.__connected = True
            print("Connected to server!")

        except OSError:
            # שינוי: סגירה מסודרת דרך מתודת close() החדשה
            self.close()
            print("Server is not available.")
            raise

    # תוספת: חשיפת מצב החיבור לקריאה בלבד עבור ממשק המשתמש
    @property
    def connected(self) -> bool:
        return self.__connected

    # תוספת: שליחת בקשה בודדת וקבלת תשובה תחת מנעול, עם טיפול ב-timeout וניתוקים (לשימוש Gradio והמסוף)
    def request(self, message: ProtocolMessage) -> ProtocolMessage:
        with self.__lock:
            if not self.__connected:
                raise ConnectionError("Client is not connected to server")

            try:
                Protocol.send(self.__sock, message)
                response = Protocol.receive(self.__sock)

                if response is None:
                    self.close()
                    raise ConnectionError("Server closed the connection")

                return response

            except (socket.timeout, OSError, ProtocolError):
                self.close()
                raise

    # תוספת: סגירת השקע בבטחה ועדכון מצב החיבור ל-False
    def close(self):
        self.__connected = False
        try:
            self.__sock.close()
        except OSError:
            pass

    def run(self):
        try:
            while self.connected:
                try:
                    user_input = input(
                        "Enter command (PING, ECHO, TIME, CLIENTS, EXIT): "
                    )
                except KeyboardInterrupt:
                    print("\nInterrupted by user.")
                    break

                try:
                    message = ProtocolMessage.from_user_input(user_input)
                    response = self.request(message)
                    print("Server:", response.data)

                    if message.command == "EXIT":
                        break

                except ProtocolError as e:
                    print("Protocol error:", e)
                except (socket.timeout, OSError) as e:
                    print("Connection error:", e)
                    break

        finally:
            self.close()
            print("Client say bye")


if __name__ == "__main__":
    try:
        client = NetworkClient()
        client.run()
    except OSError:
        pass