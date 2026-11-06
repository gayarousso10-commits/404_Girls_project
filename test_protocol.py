import socket
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage

def run_tests():
    print("--- מתחיל בדיקות פרוטוקול מקיפות לשלב ג' ---\n")

    # 1. בדיקת פקודות תקינות וקידוד/פענוח (PING, ECHO, TIME, EXIT)
    commands_to_test = [
        ProtocolMessage("PING"),
        ProtocolMessage("ECHO", "Hello CyberVault!"),
        ProtocolMessage("TIME"),
        ProtocolMessage("EXIT")
    ]

    for msg in commands_to_test:
        print(f"בודק הודעה מקורית: {msg!r}")
        raw_data = msg.to_bytes()
        decoded_msg = ProtocolMessage.from_bytes(raw_data)
        assert msg == decoded_msg, "שגיאה: ההודעה המפוענחת שונה מהמקורית!"
        print("[V] קידוד ופענוח עברו בהצלחה!\n")

    # 2. בדיקת קלט משתמש (from_user_input)
    print("בודק קלט משתמש...")
    user_msg = ProtocolMessage.from_user_input("  echo   בדיקת מערכת מאובטחת  ")
    assert user_msg.command == "ECHO"
    assert user_msg.data == "בדיקת מערכת מאובטחת"
    print(f"[V] קלט משתמש פוענח בהצלחה: {user_msg}\n")

    # 3. בדיקת שגיאות ווולידציות (פקודה לא מוכרת, תו מפריד אסור)
    print("בודק תפיסת שגיאות...")
    try:
        ProtocolMessage("UNKNOWN_CMD")
    except ProtocolError as e:
        print(f"[V] תפס בהצלחה פקודה לא חוקית: {e}")

    try:
        ProtocolMessage("ECHO", "data|with|pipe")
    except ProtocolError as e:
        print(f"[V] תפס בהצלחה תו מפריד אסור בנתונים: {e}")

    try:
        ProtocolMessage.from_bytes(b"INVALID_WITHOUT_PIPE")
    except ProtocolError as e:
        print(f"[V] תפס בהצלחה פענוח בתים חסר מפריד: {e}\n")

    # 4. בדיקת תקשורת פרוטוקול (שליחה וקבלה באמצעות socketpair)
    print("בודק שליחה וקבלה בשכבת הפרוטוקול...")
    client_sock, server_sock = socket.socketpair()
    try:
        original_msg = ProtocolMessage("PING", "test payload")
        Protocol.send(client_sock, original_msg)
        received_msg = Protocol.receive(server_sock)

        assert original_msg == received_msg
        print(f"[V] ההודעה נשלחה והתקבלה בהצלחה דרך הפרוטוקול: {received_msg}")
    finally:
        client_sock.close()
        server_sock.close()

    print("\n--- כל הבדיקות לשלב ג' הסתיימו בהצלחה מלאה! ---")

if __name__ == "__main__":
    run_tests()