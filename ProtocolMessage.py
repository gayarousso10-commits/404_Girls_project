HEADER_SIZE = 4    # MAX_LENGTH = 2 ** (8 * HEADER_SIZE) - 1    # largest length COMMANDS = ["TIME", "ECHO", "PING", "EXIT"]

class ProtocolMessage:
    def send(sock, message):
        return 1
