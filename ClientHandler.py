import socket
import threading
import datetime

# ייבוא המחלקות ששלחת
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage


class ClientHandler(threading.Thread):
    def __init__(self, client_socket: socket.socket, address: tuple, server):
        """אתחול מחלקת האב ושמירת הפניות."""
        super().__init__()
        self.__sock = client_socket
        self.__address = address
        self.__server = server
        self.name = f"ClientHandler-{address[0]}:{address[1]}"
        self.__is_running = True

    def run(self):
        """כניסה ל-Thread; ניקוי משאבים והסרה ב-finally."""
        try:
            print(f"[{self.name}] Started handling client.")
            self.__serve()
        except Exception as e:
            print(f"[{self.name}] Unexpected error in run: {e}")
        finally:
            # מופעל תמיד: ניקוי משאבים והסרה מבוקרת מרשימת השרת
            self.__close_resources()
            print(f"[{self.name}] Connection closed and handler resources cleaned up.")

    def __serve(self):
        """לולאת קבלה, עיבוד ושליחת תגובות עד EXIT/ניתוק."""
        while self.__is_running:
            try:
                # קבלת הודעה מפורקת דרך הפרוטוקול
                msg = Protocol.receive(self.__sock)

                # אם חזר None - הלקוח התנתק בצורה נקייה
                if msg is None:
                    print(f"[{self.name}] Client closed connection.")
                    break

                print(f"[{self.name}] Received: command='{msg.command}', data='{msg.data}'")

                # הפקת תשובה לפי פקודה
                response_msg = self.__process(msg)

                # שליחת התגובה
                success = self.__reply(response_msg)
                if not success:
                    break

                # אם הפקודה הייתה EXIT, מנתקים לאחר שליחת התגובה (BYE)
                if msg.command == "EXIT":
                    print(f"[{self.name}] Client sent EXIT. Stopping loop.")
                    break

            except ProtocolError as pe:
                # טיפול בשגיאות פרוטוקול - שליחת הודעת ERROR ללקוח
                print(f"[{self.name}] Protocol error encountered: {pe}")
                err_reply = ProtocolMessage("ERROR", str(pe))
                self.__reply(err_reply)
            except (OSError, socket.error) as se:
                # טיפול בסגירת השקע בזמן חסימה על recv
                print(f"[{self.name}] Socket interrupted: {se}")
                break
            except Exception as e:
                print(f"[{self.name}] General error in serve loop: {e}")
                break

    def __process(self, msg: ProtocolMessage) -> ProtocolMessage:
        """הפקת תשובה ל-PING/ECHO/TIME/EXIT/CLIENTS ופקודה לא מוכרת."""
        cmd = msg.command

        if cmd == "PING":
            return ProtocolMessage("PONG", "")

        elif cmd == "ECHO":
            return ProtocolMessage("ECHO", msg.data)

        elif cmd == "TIME":
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return ProtocolMessage("TIME", now_str)

        elif cmd == "CLIENTS":
            # פנייה לשרת לקבלת מספר המטפלים המחוברים
            count = self.__server.client_count()
            return ProtocolMessage("CLIENTS", str(count))

        elif cmd == "EXIT":
            return ProtocolMessage("BYE", "Goodbye")

        else:
            return ProtocolMessage("ERROR", f"Unknown command: {cmd}")

    def __reply(self, message: ProtocolMessage) -> bool:
        """שליחת תגובה והחזרת סטטוס הצלחה."""
        try:
            Protocol.send(self.__sock, message)
            return True
        except Exception as e:
            print(f"[{self.name}] Failed to send reply: {e}")
            return False

    def stop(self):
        """שחרור recv חסום באמצעות shutdown, וטיפול ב-OSError."""
        self.__is_running = False
        try:
            # shutdown גורם לקריאת ה-recv החסומה להשתחרר/להיכשל מיד
            self.__sock.shutdown(socket.SHUT_RDWR)
        except (OSError, socket.error):
            pass  # מתעלמים אם השקע כבר סגור או לא מחובר

    def __close_resources(self):
        """מתודת עזר פנימית לסגירת השקע והסרה מהשרת."""
        try:
            self.__sock.close()
        except (OSError, socket.error):
            pass

        # הסרה בטוחה של המטפל מרשימת השרת
        try:
            self.__server.remove_handler(self)
        except Exception as e:
            print(f"[{self.name}] Error removing handler from server: {e}")