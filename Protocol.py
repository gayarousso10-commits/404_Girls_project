import socket
from protocol_error import ProtocolError
from protocol_message import ProtocolMessage

class Protocol:
    HEADER_SIZE = 4
    BYTE_ORDER = "big"
    MAX_LENGTH = 1024 * 1024  # הגבלת אורך הגיונית לתוכן (1MB) כפי שמופיע בתרשימים

    @staticmethod
    def _recv_exact(sock, n):
        """פעולה סטטית פרטית: קבלת בדיוק n בתים מה-Socket."""
        data = bytearray()

        while len(data) < n:
            chunk = sock.recv(n - len(data))

            if not chunk:
                return None

            data.extend(chunk)

        return bytes(data)

    @staticmethod
    def send(sock, message):
        """פעולה סטטית: שליחת הודעה עם כותרת המציינת את אורך ההודעה."""
        if not isinstance(message, ProtocolMessage):
            raise TypeError("ההודעה חייבת להיות מסוג ProtocolMessage")

        raw_body = message.to_bytes()

        if len(raw_body) > Protocol.MAX_LENGTH:
            raise ProtocolError("The message body is too large to be sent")

        # שימוש בשיטה המובנית שלך להמרת מספר לבייטים
        header = len(raw_body).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER)

        sock.sendall(header + raw_body)

    @staticmethod
    def receive(sock):
        """פעולה סטטית: קבלת הודעה מלאה מה-Socket והחזרת אובייקט ProtocolMessage."""
        header = Protocol._recv_exact(sock, Protocol.HEADER_SIZE)

        if header is None:
            return None

        length = int.from_bytes(header, Protocol.BYTE_ORDER)

        if length < 0 or length > Protocol.MAX_LENGTH:
            raise ProtocolError(f"Invalid message length received in header: {length}")

        raw_body = Protocol._recv_exact(sock, length)

        if raw_body is None:
            return None

        try:
            return ProtocolMessage.from_bytes(raw_body)
        except ProtocolError as e:
            raise ProtocolError(f"Failed to parse incoming message protocol: {e}")