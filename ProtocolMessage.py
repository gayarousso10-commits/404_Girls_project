from Protocol import Protocol, ProtocolError


class ProtocolMessage:
    """מחלקת המייצגת הודעה בפרוטוקול התקשורת של CyberVault.
    אחראית על ולידציה, קידוד ופענוח של מבנה ההודעה (COMMAND|data).
    """

    SEPARATOR = "|"
    ENCODING = "utf-8"
    VALID_COMMANDS = set(Protocol.COMMANDS)

    def __init__(self, command, data=""):
        if not isinstance(command, str):
            raise ProtocolError("Command must be a string")
        if not isinstance(data, str):
            raise ProtocolError("Data must be a string")

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
    def command(self):
        return self.__command

    @property
    def data(self):
        return self.__data

    def to_bytes(self):
        message_str = (
            f"{self.__command}"
            f"{ProtocolMessage.SEPARATOR}"
            f"{self.__data}"
        )
        return message_str.encode(ProtocolMessage.ENCODING)

    @classmethod
    def from_bytes(cls, raw):
        if not isinstance(raw, bytes):
            raise ProtocolError("Message must be provided as bytes")

        try:
            decoded_str = raw.decode(cls.ENCODING)
        except UnicodeDecodeError:
            raise ProtocolError("Failed to decode bytes using UTF-8")

        parts = decoded_str.split(cls.SEPARATOR, 1)

        if not parts[0]:
            raise ProtocolError("Invalid message format: missing command")

        command = parts[0]
        data = parts[1] if len(parts) > 1 else ""

        try:
            return cls(command, data)
        except ProtocolError as e:
            raise ProtocolError(f"Error while parsing message: {e}") from e

    @classmethod
    def from_user_input(cls, line):
        if not isinstance(line, str):
            raise ProtocolError("User input must be a string")

        line = line.strip()

        if not line:
            raise ProtocolError("User input cannot be empty")

        parts = line.split(maxsplit=1)

        command = parts[0]
        data = parts[1] if len(parts) > 1 else ""

        upper_cmd = command.upper()

        # בדיקה 1: אם הפקודה דורשת נתונים (כמו ECHO), אבל data ריק -> שגיאה!
        if upper_cmd in Protocol.COMMANDS_WITH_DATA and not data:
            raise ProtocolError(f"Command '{upper_cmd}' requires data")

        # בדיקה 2: אם הפקודה לא דורשת נתונים (כמו PING), אבל המשתמש כן כתב משהו -> שגיאה!
        if upper_cmd not in Protocol.COMMANDS_WITH_DATA and data:
            raise ProtocolError(f"Command '{upper_cmd}' does not accept data")

        return cls(command, data)

    def __eq__(self, other):
        if not isinstance(other, ProtocolMessage):
            return False

        return (
            self.__command == other.command
            and self.__data == other.data
        )

    def __repr__(self):
        return (
            f"ProtocolMessage("
            f"command='{self.__command}', "
            f"data='{self.__data}')"
        )

    def __str__(self):
        return f"[{self.__command}] {self.__data}"