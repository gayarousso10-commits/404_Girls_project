import socket
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage


def test_commands_encoding_decoding():
    """בדיקת פקודות תקינות וקידוד/פענוח (PING, ECHO, TIME, EXIT)"""
    commands_to_test = [
        ProtocolMessage("PING"),
        ProtocolMessage("ECHO", "Hello CyberVault!"),
        ProtocolMessage("TIME"),
        ProtocolMessage("EXIT")
    ]

    for msg in commands_to_test:
        raw_data = msg.to_bytes()
        decoded_msg = ProtocolMessage.from_bytes(raw_data)
        assert msg == decoded_msg


def test_user_input_parsing():
    """בדיקת קלט משתמש"""
    user_msg = ProtocolMessage.from_user_input("  echo   בדיקת מערכת מאובטחת  ")
    assert user_msg.command == "ECHO"
    assert user_msg.data == "בדיקת מערכת מאובטחת"


def test_error_handling_unknown_command():
    """בדיקת תפיסת פקודה לא חוקית"""
    try:
        ProtocolMessage("UNKNOWN_CMD")
        assert False, "צפויה להיות שגיאה עבור פקודה לא חוקית"
    except ProtocolError:
        pass


def test_error_handling_invalid_separator():
    """בדיקת תפיסת תו מפריד אסור"""
    try:
        ProtocolMessage("ECHO", "data|with|pipe")
        assert False, "צפויה להיות שגיאה עבור תו מפריד בנתונים"
    except ProtocolError:
        pass


def test_error_handling_missing_separator():
    """בדיקת תפיסת בתים חסרי מפריד לפענוח"""
    try:
        ProtocolMessage.from_bytes(b"INVALID_WITHOUT_PIPE")
        assert False, "צפויה להיות שגיאה עבור בתים ללא מפריד"
    except ProtocolError:
        pass


def test_socketpair_communication():
    """בדיקת שליחה וקבלה באמצעות socketpair"""
    client_sock, server_sock = socket.socketpair()
    try:
        original_msg = ProtocolMessage("PING", "test payload")
        Protocol.send(client_sock, original_msg)
        received_msg = Protocol.receive(server_sock)

        assert original_msg == received_msg
    finally:
        client_sock.close()
        server_sock.close()