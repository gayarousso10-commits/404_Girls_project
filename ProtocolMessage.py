from protocol_error import ProtocolError


class ProtocolMessage:
    SEPARATOR = "|"
    ENCODING = "utf-8"
    VALID_COMMANDS = {"TIME", "ECHO", "PING", "EXIT"}

    def __init__(self, command: str, data: str = ""):
        normalized_command = command.upper()

        if normalized_command not in ProtocolMessage.VALID_COMMANDS:
            raise ProtocolError(f"Invalid command: '{normalized_command}'")

        if ProtocolMessage.SEPARATOR in normalized_command:
            raise ProtocolError("Command cannot contain the separator character")
        if ProtocolMessage.SEPARATOR in data:
            raise ProtocolError("Data cannot contain the separator character")

        self.__command = normalized_command
        self.__data = data

    @property
    def command(self) -> str:
        return self.__command

    @property
    def data(self) -> str:
        return self.__data

    def to_bytes(self) -> bytes:
        message_str = f"{self.__command}{ProtocolMessage.SEPARATOR}{self.__data}"
        return message_str.encode(ProtocolMessage.ENCODING)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ProtocolMessage":
        try:
            decoded_str = raw.decode(cls.ENCODING)
        except UnicodeDecodeError:
            raise ProtocolError("Failed to decode bytes using UTF-8")

        parts = decoded_str.split(cls.SEPARATOR, 1)

        if len(parts) < 1 or not parts[0]:
            raise ProtocolError("Invalid message format: missing components")

        # תיקון: גישה לאינדקסים הנכונים ברשימה
        command = parts[0]
        data = parts[1] if len(parts) > 1 else ""

        try:
            return cls(command, data)
        except ProtocolError as e:
            raise ProtocolError(f"Error while parsing message: {e}")

    @classmethod
    def from_user_input(cls, line: str) -> "ProtocolMessage":
        line = line.strip()
        if not line:
            raise ProtocolError("User input cannot be empty")

        parts = line.split(maxsplit=1)

        # תיקון: גישה לאינדקסים הנכונים ברשימה
        command = parts[0]
        data = parts[1] if len(parts) > 1 else ""

        return cls(command, data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProtocolMessage):
            return False
        return self.__command == other.command and self.__data == other.data

    def __repr__(self) -> str:
        return f"ProtocolMessage(command='{self.__command}', data='{self.__data}')"

    def __str__(self) -> str:
        return f"[{self.__command}] {self.__data}"