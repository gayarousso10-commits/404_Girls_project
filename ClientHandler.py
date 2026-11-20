import socket
import threading
import datetime

from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage


class ClientHandler(threading.Thread):

    def __init__(self, client_socket: socket.socket, address: tuple, server):
        """אתחול מחלקת האב ושמירת הפניות."""
        super().__init__(name=f"ClientHandler-{address[0]}:{address[1]}")

        self.__sock = client_socket
        self.__address = address
        self.__server = server
        self.__is_running = True

    def run(self):
        """כניסה ל-Thread, ניקוי משאבים והסרה מהשרת."""
        try:
            print(f"[{self.name}] Started handling client.")
            self.__serve()

        except Exception as e:
            print(f"[{self.name}] Unexpected error in run: {e}")

        finally:
            self.__close_resources()
            print(f"[{self.name}] Connection closed and handler resources cleaned up.")

    def __serve(self):
        """קבלת הודעות, עיבודן ושליחת תגובות עד EXIT או ניתוק."""

        while self.__is_running:
            try:
                # קבלת הודעה דרך הפרוטוקול
                msg = Protocol.receive(self.__sock)

                # בדיקה האם התקבלה הוראת עצירה מהשרת
                if not self.__is_running:
                    break

                # בדיקה האם הלקוח התנתק
                if msg is None:
                    print(f"[{self.name}] Client closed connection.")
                    break

                print(
                    f"[{self.name}] Received: "
                    f"command='{msg.command}', data='{msg.data}'"
                )

                # עיבוד הפקודה והפקת תשובה
                response_msg = self.__process(msg)

                # שליחת התשובה ללקוח
                success = self.__reply(response_msg)

                if not success:
                    break

                # ניתוק הלקוח לאחר שליחת תשובת BYE
                if msg.command == "EXIT":
                    print(f"[{self.name}] Client sent EXIT. Stopping loop.")
                    break

            except ProtocolError as pe:
                # טיפול בשגיאת פרוטוקול ושליחת הודעת ERROR
                print(f"[{self.name}] Protocol error encountered: {pe}")

                err_reply = ProtocolMessage("ERROR", str(pe))

                if not self.__reply(err_reply):
                    break

            except OSError as se:
                # טיפול בשגיאת socket או בניתוק יזום
                print(f"[{self.name}] Socket interrupted: {se}")
                break

            except Exception as e:
                print(f"[{self.name}] General error in serve loop: {e}")
                break

    def __process(self, msg: ProtocolMessage) -> ProtocolMessage:
        """הפקת תשובה בהתאם לפקודה שהתקבלה."""

        cmd = msg.command

        if cmd == "PING":
            return ProtocolMessage("PONG", "")

        elif cmd == "ECHO":
            return ProtocolMessage("ECHO", msg.data)

        elif cmd == "TIME":
            now_str = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            return ProtocolMessage("TIME", now_str)

        elif cmd == "CLIENTS":
            # קבלת מספר המטפלים הרשומים בשרת
            count = self.__server.client_count()
            return ProtocolMessage("CLIENTS", str(count))

        elif cmd == "EXIT":
            return ProtocolMessage("BYE", "Goodbye")

        else:
            return ProtocolMessage("ERROR", f"Unknown command: {cmd}")

    def __reply(self, message: ProtocolMessage) -> bool:
        """שליחת הודעה והחזרת הצלחת הפעולה."""

        try:
            Protocol.send(self.__sock, message)
            return True

        except OSError as e:
            print(f"[{self.name}] Socket error while sending reply: {e}")
            return False

        except Exception as e:
            print(f"[{self.name}] Unexpected error while sending reply: {e}")
            return False

    def stop(self):
        """עצירת ה-Thread ושחרור recv חסום."""

        self.__is_running = False

        try:
            # שחרור recv אם הוא ממתין לקבלת נתונים
            self.__sock.shutdown(socket.SHUT_RDWR)

        except OSError:
            pass

    def __close_resources(self):
        """סגירת socket והסרת המטפל מרשימת השרת."""

        try:
            self.__sock.close()

        except OSError:
            pass

        try:
            self.__server.remove_handler(self)

        except Exception as e:
            print(f"[{self.name}] Error removing handler from server: {e}")