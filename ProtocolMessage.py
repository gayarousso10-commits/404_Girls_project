from Protocol import ProtocolError

class ProtocolMessage:
    SEPARATOR = "|"
    ENCODING = "utf-8"
    VALID_COMMANDS = {"TIME", "ECHO", "PING", "EXIT"}

    def __init__(self, command: str, data: str = ""):
        # בדיקת טיפוסים
        if not isinstance(command, str):
            raise ProtocolError("Command must be a string")

        if not isinstance(data, str):
            raise ProtocolError("Data must be a string")

        # פקודה לאותיות גדולות
        normalized_command = command.upper()

        # בדיקת תקינות הפקודה
        if normalized_command not in ProtocolMessage.VALID_COMMANDS:
            raise ProtocolError(f"Invalid command: '{normalized_command}'")

        # בדיקת התו המפריד
        if ProtocolMessage.SEPARATOR in data:
            raise ProtocolError(
                "Data cannot contain the separator character"
            )

        self.__command = normalized_command
        self.__data = data

    @property
    def command(self) -> str:
        return self.__command

    @property
    def data(self) -> str:
        return self.__data

    def to_bytes(self) -> bytes:
        message_str = (
            f"{self.__command}"
            f"{ProtocolMessage.SEPARATOR}"
            f"{self.__data}"
        )

        return message_str.encode(ProtocolMessage.ENCODING)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ProtocolMessage":
        if not isinstance(raw, bytes):
            raise ProtocolError("Message must be provided as bytes")

        try:
            decoded_str = raw.decode(cls.ENCODING)
        except UnicodeDecodeError:
            raise ProtocolError("Failed to decode bytes using UTF-8")

        parts = decoded_str.split(cls.SEPARATOR, 1)

        # בדיקה שהפקודה קיימת
        if not parts[0]:
            raise ProtocolError(
                "Invalid message format: missing command"
            )

        command = parts[0]
        data = parts[1] if len(parts) > 1 else ""

        try:
            return cls(command, data)
        except ProtocolError as e:
            raise ProtocolError(f"Error while parsing message: {e}") from e

    @classmethod
    def from_user_input(cls, line: str) -> "ProtocolMessage":
        if not isinstance(line, str):
            raise ProtocolError("User input must be a string")

        line = line.strip()

        if not line:
            raise ProtocolError("User input cannot be empty")

        parts = line.split(maxsplit=1)

        command = parts[0]
        data = parts[1] if len(parts) > 1 else ""

        return cls(command, data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProtocolMessage):
            return False

        return (
            self.__command == other.command
            and self.__data == other.data
        )

    def __repr__(self) -> str:
        return (
            f"ProtocolMessage("
            f"command='{self.__command}', "
            f"data='{self.__data}')"
        )

    def __str__(self) -> str:
        return f"[{self.__command}] {self.__data}"
