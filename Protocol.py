import socket


class ProtocolError(Exception):
    """מחלקת חריגה ייעודית לפרוטוקול התקשורת."""
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
                if not data:
                    return None
                raise ProtocolError(
                    "Connection closed before receiving all bytes"
                )
            data.extend(chunk)
        return bytes(data)

    @staticmethod
    def send(sock, message):
        """Sends a message with a 4-byte length header."""
        from ProtocolMessage import ProtocolMessage  # ייבוא מקומי למניעת מעגל

        if not isinstance(message, ProtocolMessage):
            raise TypeError("The message must be of type ProtocolMessage")

        raw_body = message.to_bytes()
        if len(raw_body) > Protocol.MAX_LENGTH:
            raise ProtocolError("The message body is too large to be sent")

        header = len(raw_body).to_bytes(
            Protocol.HEADER_SIZE,
            Protocol.BYTE_ORDER
        )
        sock.sendall(header + raw_body)

    @staticmethod
    def receive(sock):
        """Receives a complete message from the socket."""
        from ProtocolMessage import ProtocolMessage  # ייבוא מקומי למניעת מעגל

        header = Protocol._recv_exact(sock, Protocol.HEADER_SIZE)
        if header is None:
            return None

        length = int.from_bytes(header, Protocol.BYTE_ORDER)
        if length > Protocol.MAX_LENGTH:
            raise ProtocolError(
                f"Invalid message length received in header: {length}"
            )

        raw_body = Protocol._recv_exact(sock, length)
        if raw_body is None:
            raise ProtocolError(
                "Connection closed before receiving the message body"
            )

        try:
            return ProtocolMessage.from_bytes(raw_body)
        except ProtocolError as e:
            raise ProtocolError(
                f"Failed to parse incoming message protocol: {e}"
            ) from e