
# Protocol class
import socket
from ProtocolMessage import ProtocolMessage


class ProtocolError(Exception):
    pass


class Protocol:
    HEADER_SIZE = 4
    BYTE_ORDER = "big"
    MAX_LENGTH = 1024 * 1024  # 1MB

    @staticmethod
    def _recv_exact(sock, n):
        """Receives exactly n bytes from the socket."""

        if not isinstance(n, int) or n < 0:
            raise ValueError("n must be a non-negative integer")

        data = bytearray()

        while len(data) < n:
            chunk = sock.recv(n - len(data))

            if not chunk:
                # החיבור נסגר לפני שהתקבל מידע כלשהו
                if not data:
                    return None

                # החיבור נסגר לאחר קבלת מידע חלקי
                raise ProtocolError(
                    "Connection closed before receiving all bytes"
                )

            data.extend(chunk)

        return bytes(data)

    @staticmethod
    def send(sock, message):
        """Sends a message with a 4-byte length header."""

        if not isinstance(message, ProtocolMessage):
            raise TypeError(
                "The message must be of type ProtocolMessage"
            )

        raw_body = message.to_bytes()

        if len(raw_body) > Protocol.MAX_LENGTH:
            raise ProtocolError(
                "The message body is too large to be sent"
            )

        # יצירת כותרת בת 4 בתים המציינת את אורך ההודעה
        header = len(raw_body).to_bytes(
            Protocol.HEADER_SIZE,
            Protocol.BYTE_ORDER
        )

        # שליחת הכותרת וגוף ההודעה
        sock.sendall(header + raw_body)

    @staticmethod
    def receive(sock):
        """Receives a complete message from the socket."""

        # קריאת הכותרת
        header = Protocol._recv_exact(
            sock,
            Protocol.HEADER_SIZE
        )

        # None מציין שהחיבור נסגר לפני שהתקבלה כותרת
        if header is None:
            return None

        length = int.from_bytes(
            header,
            Protocol.BYTE_ORDER
        )

        # בדיקת אורך ההודעה
        if length > Protocol.MAX_LENGTH:
            raise ProtocolError(
                f"Invalid message length received in header: {length}"
            )

        # קריאת גוף ההודעה
        raw_body = Protocol._recv_exact(sock, length)

        if raw_body is None:
            # הכותרת התקבלה, אך החיבור נסגר לפני שהתקבל הגוף
            raise ProtocolError(
                "Connection closed before receiving the message body"
            )

        # פענוח גוף ההודעה
        try:
            return ProtocolMessage.from_bytes(raw_body)

        except ProtocolError as e:
            raise ProtocolError(
                f"Failed to parse incoming message protocol: {e}"
            ) from e
