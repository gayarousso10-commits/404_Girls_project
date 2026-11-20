import socket
from threading import Lock
from ClientHandler import ClientHandler


class NetworkServer:
    """שרת TCP מרובה תהליכונים המנהל חיבורי לקוחות ומקצה מטפל לכל לקוח."""

    def __init__(self, ip="127.0.0.1", port=8000):
        """אתחול שקע ההאזנה הראשי, רשימת המטפלים ומנעול הסנכרון."""
        self.__ip = ip
        self.__port = port
        # דגל שמסמן האם השרת פעיל (מונע קבלת לקוחות חדשים בזמן סגירה)
        self.__running = False

        # אתחול שקע ההאזנה הראשי עם SO_REUSEADDR (לשחרור מהיר של הפורט), bind ו-listen
        self.__server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        try:
            self.__server.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )
            self.__server.bind((self.__ip, self.__port))
            self.__server.listen(5)

            # הגדרת timeout כדי ש-accept() לא יחסום לנצח ויאפשר תגובה מהירה לעצירה
            self.__server.settimeout(1.0)

        except OSError:
            # סגירת השקע במקרה שהפורט תפוס או שההגדרה נכשלה
            self.__server.close()
            raise

        # רשימת המטפלים הרשומים ומנעול (Lock) למניעת התנגשויות בין תהליכונים
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
                    # חזרה לבדיקת תנאי הלולאה self.__running (מאפשר עצירה מהירה)
                    continue

                print(f"Client connected at {address}")

                # נעילת המנעול לפני גישה לרשימת הלקוחות ובדיקת מצב הריצה
                with self.__lock:
                    # בדיקה שהשרת לא התחיל להיסגר בזמן שהחיבור התקבל
                    if not self.__running:
                        client_socket.close()
                        break

                    # יצירת מטפל ייעודי והעברת self כדי שיוכל להסיר את עצמו בסיום
                    handler = ClientHandler(client_socket, address, self)
                    self.__handlers.append(handler)
                    # הפעלת התהליכון (Thread) של הלקוח במקביל לשרת
                    handler.start()

        except KeyboardInterrupt:
            # תפיסת עצירה יזומה (Ctrl+C)
            print("\nServer shutting down...")
        except OSError as e:
            # אם השרת עדיין אמור לרוץ, מדובר בתקלת שקע אמיתית ולא בסגירה יזומה
            if self.__running:
                print(f"\nServer socket error: {e}")
        finally:
            # מובטח שיופעל תמיד כדי לסגור את כל המשאבים בצורה נקייה
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
        # 1. עדכון דגל הריצה והעתקת הרשימה תחת מנעול (לפני סגירת השקע ועצירת המטפלים)
        with self.__lock:
            self.__running = False
            handlers_copy = list(self.__handlers)

        # 2. הפסקת קבלת חיבורים חדשים ע"י סגירת שקע השרת הראשי
        try:
            self.__server.close()
        except OSError:
            pass

        # 3. שליחת הוראת עצירה לכל המטפלים במקביל (מחוץ למנעול למניעת Deadlock)
        for handler in handlers_copy:
            handler.stop()

        # 4. המתנה לסיום כל ה-threads לאחר שכולם קיבלו הוראת עצירה
        for handler in handlers_copy:
            handler.join()

        print("Server says bye")

if __name__ == "__main__":
    server = NetworkServer("127.0.0.1", 8000)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        server.shutdown()