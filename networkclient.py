import socket

class NetworkClient:
    def __init__(self, ip: str = "127.0.0.1", port: int = 8000):
        # תכונה פרטית המחזיקה את אובייקט ה-socket
        self.__sock = socket.socket()
        # התחברות לשרת לפי ה-IP וה-Port שהתקבלו
        self.__sock.connect((ip, port))

    def run(self) -> None:
        user_message = input("enter your command (TIME, ECHO, PING, EXIT): ")

        # הלולאה ממשיכה כל עוד הלקוח לא מקליד Exit
        while user_message.strip().upper() != "EXIT":
            # שליחת ההודעה מקודדת לשרת
            self.__sock.send(user_message.encode())

            # מקבלת תגובה מהשרת
            server_message = self.__sock.recv(1024)

            # אם החיבור נסגר מהצד של השרת
            if not server_message:
                print("Server disconnected.")
                break

            print(f"server say {server_message.decode()}")


            # קלט נוסף מהמשתמש
            user_message = input("enter your command (TIME, ECHO, PING, EXIT): ")

        # סגירת ה-socket בסיום
        self.__sock.close()
        print("client say bye")


# דוגמה להרצת המחלקה:
if __name__ == "__main__":
    client = NetworkClient(ip="192.168.11.77", port=8000)
    client.run()