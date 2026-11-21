import socket
import threading
import time
from types import SimpleNamespace
import pytest

from networkserver import NetworkServer
from networkclient import NetworkClient
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage
from GradioClientUI import GradioClientUI

IP = "127.0.0.1"
PORT = 8055


def _call_gradio_method(ui, name_base, *args):
    """תמיכה הן בשם פרטי (_GradioClientUI__name) והן בשם מוגן (_name) לפי ה-UML."""
    mangled = f"_GradioClientUI__{name_base}"
    protected = f"_{name_base}"
    if hasattr(ui, mangled):
        return getattr(ui, mangled)(*args)
    if hasattr(ui, protected):
        return getattr(ui, protected)(*args)
    raise AttributeError(f"Method {protected} / {mangled} not found on GradioClientUI")


@pytest.fixture(scope="module")
def server():
    srv = NetworkServer(IP, PORT)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.3)
    yield srv
    srv.shutdown()


# ==============================================================================
# בדיקות קבלה 01 - 15 (לפי דף עבודה 2)
# ==============================================================================

def test_01_three_clients_ping(server):
    """01. שלושה לקוחות מסוף מתחברים ושולחים PING -> שלוש תשובות PONG."""
    clients = []
    try:
        for _ in range(3):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((IP, PORT))
            clients.append(s)

        for s in clients:
            Protocol.send(s, ProtocolMessage("PING"))
            res = Protocol.receive(s)
            assert res is not None
            assert res.command == "PONG"
    finally:
        for s in clients:
            s.close()
        time.sleep(0.2)


def test_02_parallel_echo_and_time(server):
    """02. שני לקוחות שולחים ECHO/TIME במקביל -> תגובות מתאימות."""
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s1.connect((IP, PORT))
        s2.connect((IP, PORT))

        results = {}

        def run_echo():
            Protocol.send(s1, ProtocolMessage("ECHO", "שלום CyberVault"))
            results["echo"] = Protocol.receive(s1)

        def run_time():
            Protocol.send(s2, ProtocolMessage("TIME"))
            results["time"] = Protocol.receive(s2)

        t1 = threading.Thread(target=run_echo)
        t2 = threading.Thread(target=run_time)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["echo"].command == "ECHO"
        assert results["echo"].data == "שלום CyberVault"
        assert results["time"].command == "TIME"
        assert len(results["time"].data) > 0
    finally:
        s1.close()
        s2.close()
        time.sleep(0.2)


def test_03_clients_count_three(server):
    """03. CLIENTS בשלושה חיבורים -> מחזיר 3."""
    clients = []
    try:
        for _ in range(3):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((IP, PORT))
            clients.append(s)
        time.sleep(0.15)

        Protocol.send(clients[0], ProtocolMessage("CLIENTS"))
        res = Protocol.receive(clients[0])
        assert res is not None
        assert res.command == "CLIENTS"
        assert res.data == "3"
    finally:
        for s in clients:
            s.close()
        time.sleep(0.2)


def test_04_exit_single_client_others_continue(server):
    """04. EXIT של לקוח יחיד -> BYE והאחרים ממשיכים."""
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s1.connect((IP, PORT))
        s2.connect((IP, PORT))

        Protocol.send(s1, ProtocolMessage("EXIT"))
        res1 = Protocol.receive(s1)
        assert res1 is not None
        assert res1.command == "BYE"
        s1.close()

        Protocol.send(s2, ProtocolMessage("PING"))
        res2 = Protocol.receive(s2)
        assert res2 is not None
        assert res2.command == "PONG"
    finally:
        s1.close()
        s2.close()
        time.sleep(0.2)


def test_05_clients_after_handler_removed(server):
    """05. CLIENTS לאחר הסרת handler -> מספר קטן באחד."""
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s1.connect((IP, PORT))
        s2.connect((IP, PORT))
        time.sleep(0.15)

        Protocol.send(s2, ProtocolMessage("EXIT"))
        Protocol.receive(s2)
        s2.close()
        time.sleep(0.2)

        Protocol.send(s1, ProtocolMessage("CLIENTS"))
        res = Protocol.receive(s1)
        assert res is not None
        assert res.command == "CLIENTS"
        assert res.data == "1"
    finally:
        s1.close()
        s2.close()
        time.sleep(0.2)


def test_06_sudden_disconnect(server):
    """06. ניתוק פתאומי של לקוח -> אין קריסת שרת והאחרים ממשיכים."""
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s1.connect((IP, PORT))
        s2.connect((IP, PORT))
        time.sleep(0.15)

        s2.close()
        time.sleep(0.2)

        Protocol.send(s1, ProtocolMessage("PING"))
        res = Protocol.receive(s1)
        assert res is not None
        assert res.command == "PONG"
    finally:
        s1.close()
        s2.close()
        time.sleep(0.2)


def test_07_unknown_command_returns_error(server):
    """07. פקודה לא מוכרת -> ERROR לפי הפרוטוקול."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((IP, PORT))

        payload = b"UNKNOWN|"
        header = len(payload).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER)
        s.sendall(header + payload)

        res = Protocol.receive(s)
        assert res is not None
        assert res.command == "ERROR"
    finally:
        s.close()
        time.sleep(0.2)


def test_08_split_tcp_message(server):
    """08. הודעה מפוצלת ב-TCP (בייט אחרי בייט) -> פענוח תקין."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((IP, PORT))

        raw = ProtocolMessage("ECHO", "SplitMessage בעברית").to_bytes()
        header = len(raw).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER)
        packet = header + raw

        for byte in packet:
            s.sendall(bytes([byte]))
            time.sleep(0.005)

        res = Protocol.receive(s)
        assert res is not None
        assert res.command == "ECHO"
        assert res.data == "SplitMessage בעברית"
    finally:
        s.close()
        time.sleep(0.2)


def test_09_invalid_message_protocol_error(server):
    """09. הודעה לא תקינה -> טיפול מבוקר ב-ProtocolError."""
    with pytest.raises(ProtocolError):
        ProtocolMessage.from_bytes(b"\xff\xfe\xfd")

    with pytest.raises(ProtocolError):
        ProtocolMessage.from_user_input("ECHO")

    with pytest.raises(ProtocolError):
        ProtocolMessage.from_user_input("")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((IP, PORT))
        bad_payload = b"|missing_cmd"
        header = len(bad_payload).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER)
        s.sendall(header + bad_payload)
        res = Protocol.receive(s)
        assert res is not None
        assert res.command == "ERROR"
    finally:
        s.close()
        time.sleep(0.2)


def test_10_gradio_two_separate_sessions(server):
    """10. Gradio: שני sessions נפרדים -> שני חיבורים עצמאיים."""
    ui = GradioClientUI(IP, PORT)
    req1 = SimpleNamespace(session_hash="session_1")
    req2 = SimpleNamespace(session_hash="session_2")

    try:
        _call_gradio_method(ui, "connect", IP, PORT, "TIME", [], req1)
        _call_gradio_method(ui, "connect", IP, PORT, "TIME", [], req2)
        time.sleep(0.15)

        assert server.client_count() == 2
    finally:
        _call_gradio_method(ui, "disconnect", "TIME", [], req1)
        _call_gradio_method(ui, "disconnect", "TIME", [], req2)
        time.sleep(0.2)


def test_11_gradio_disconnect_one_session_other_continues(server):
    """11. Gradio: ניתוק session אחד -> השני ממשיך לפעול."""
    ui = GradioClientUI(IP, PORT)
    req1 = SimpleNamespace(session_hash="session_a")
    req2 = SimpleNamespace(session_hash="session_b")

    try:
        _call_gradio_method(ui, "connect", IP, PORT, "PING", [], req1)
        _call_gradio_method(ui, "connect", IP, PORT, "PING", [], req2)

        _call_gradio_method(ui, "disconnect", "PING", [], req1)
        out2 = _call_gradio_method(ui, "send", "PING", "", [], req2)

        assert out2[0] == "Connected"
        assert "PONG" in str(out2[6][-1])
    finally:
        _call_gradio_method(ui, "disconnect", "PING", [], req2)
        time.sleep(0.2)


def test_12_gradio_command_change_data_field(server):
    """12. Gradio: שינוי פקודה -> שדה נתונים מותאם."""
    ui = GradioClientUI(IP, PORT)
    req = SimpleNamespace(session_hash="session_cmd")
    try:
        _call_gradio_method(ui, "connect", IP, PORT, "TIME", [], req)

        try:
            echo_update = _call_gradio_method(ui, "on_command_change", "ECHO", req)
            ping_update = _call_gradio_method(ui, "on_command_change", "PING", req)
        except TypeError:
            echo_update = _call_gradio_method(ui, "on_command_change", "ECHO")
            ping_update = _call_gradio_method(ui, "on_command_change", "PING")

        assert echo_update["interactive"] is True
        assert ping_update["interactive"] is False
    finally:
        _call_gradio_method(ui, "disconnect", "PING", [], req)
        time.sleep(0.2)


def test_13_gradio_connection_error_friendly_message():
    """13. Gradio: שגיאת חיבור -> הודעת שגיאה מובנת ללא Traceback."""
    ui = GradioClientUI(IP, 8099)
    req = SimpleNamespace(session_hash="session_err")

    out = _call_gradio_method(ui, "connect", IP, 8099, "TIME", [], req)
    status = out[0]
    last_msg = str(out[6][-1])

    assert "Disconnected" in status
    assert "Traceback" not in last_msg


def test_14_server_shutdown_releases_resources():
    """14. עצירת שרת עם לקוחות פעילים -> שחרור משאבים."""
    srv = NetworkServer(IP, 8057)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.2)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((IP, 8057))
        time.sleep(0.15)
        assert srv.client_count() == 1

        srv.shutdown()
        assert srv.client_count() == 0
    finally:
        s.close()


def test_15_server_restart_same_port():
    """15. הפעלה מחדש על אותו port -> שרת מאזין בהצלחה."""
    srv1 = NetworkServer(IP, 8058)
    t1 = threading.Thread(target=srv1.start, daemon=True)
    t1.start()
    time.sleep(0.2)
    srv1.shutdown()
    time.sleep(0.2)

    srv2 = NetworkServer(IP, 8058)
    t2 = threading.Thread(target=srv2.start, daemon=True)
    t2.start()
    time.sleep(0.2)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((IP, 8058))
        Protocol.send(s, ProtocolMessage("PING"))
        res = Protocol.receive(s)
        assert res is not None
        assert res.command == "PONG"
    finally:
        s.close()
        srv2.shutdown()


# ==============================================================================
# בדיקות הרחבה ומקרי קצה נוספים (פרוטוקול, NetworkClient, מקביליות ו-Gradio)
# ==============================================================================

def test_16_accept_new_client_while_first_idle(server):
    """16. קבלת חיבור חדש גם כשלקוח קודם מחובר וממתין ללא שליחת קלט."""
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s1.connect((IP, PORT))
        time.sleep(0.1)

        s2.connect((IP, PORT))
        Protocol.send(s2, ProtocolMessage("PING"))
        res = Protocol.receive(s2)
        assert res is not None
        assert res.command == "PONG"
    finally:
        s1.close()
        s2.close()
        time.sleep(0.2)


def test_17_protocol_header_zero_or_exceeds_max_length():
    """17. ולידציית פרוטוקול: אורך כותרת 0 או גדול מ-MAX_LENGTH -> ProtocolError."""
    a1, b1 = socket.socketpair()
    try:
        a1.sendall((0).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER))
        with pytest.raises(ProtocolError):
            Protocol.receive(b1)
    finally:
        a1.close()
        b1.close()

    a2, b2 = socket.socketpair()
    try:
        too_big = (Protocol.MAX_LENGTH + 1).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER)
        a2.sendall(too_big)
        with pytest.raises(ProtocolError):
            Protocol.receive(b2)
    finally:
        a2.close()
        b2.close()


def test_18_protocol_partial_disconnect_raises_protocol_error():
    """18. סגירת שקע באמצע קבלת כותרת או גוף הודעה -> זריקת ProtocolError."""
    a1, b1 = socket.socketpair()
    try:
        a1.sendall(b"\x00\x00")
        a1.close()
        with pytest.raises(ProtocolError):
            Protocol.receive(b1)
    finally:
        b1.close()

    a2, b2 = socket.socketpair()
    try:
        a2.sendall((10).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER) + b"abc")
        a2.close()
        with pytest.raises(ProtocolError):
            Protocol.receive(b2)
    finally:
        b2.close()


def test_19_network_client_and_gradio_share_server(server):
    """19. לקוח NetworkClient ולקוח GradioClientUI פועלים יחד מול אותו שרת."""
    nc = NetworkClient(IP, PORT)
    ui = GradioClientUI(IP, PORT)
    req = SimpleNamespace(session_hash="session_mix")

    try:
        _call_gradio_method(ui, "connect", IP, PORT, "CLIENTS", [], req)
        time.sleep(0.15)

        res = nc.request(ProtocolMessage("CLIENTS"))
        assert res.command == "CLIENTS"
        assert res.data == "2"
    finally:
        nc.close()
        _call_gradio_method(ui, "disconnect", "CLIENTS", [], req)
        time.sleep(0.2)


def test_20_network_client_timeout_closes_and_blocks_next_request():
    """20. לאחר timeout ב-NetworkClient, החיבור נסגר ואסור לשלוח בו בקשה חדשה."""
    dummy_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    dummy_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dummy_srv.bind((IP, 8059))
    dummy_srv.listen(1)

    accepted = []

    def accept_only():
        conn, _ = dummy_srv.accept()
        accepted.append(conn)

    t = threading.Thread(target=accept_only, daemon=True)
    t.start()

    client = None
    try:
        client = NetworkClient(IP, 8059)
        # קיצור זמני של זמן ההמתנה לבדיקה מהירה
        sock = getattr(client, "_NetworkClient__sock", getattr(client, "sock", None))
        if sock is not None:
            sock.settimeout(0.2)

        with pytest.raises(socket.timeout):
            client.request(ProtocolMessage("PING"))

        assert client.connected is False

        with pytest.raises(ConnectionError):
            client.request(ProtocolMessage("PING"))
    finally:
        if client is not None:
            client.close()
        for c in accepted:
            c.close()
        dummy_srv.close()


def test_21_network_client_thread_safe_concurrent_requests(server):
    """21. שליחת בקשות במקביל על אותו NetworkClient מוגנת ב-Lock ולא מתערבבת."""
    client = NetworkClient(IP, PORT)
    errors = []
    results = []

    def worker(idx):
        try:
            msg_text = f"msg_{idx}"
            res = client.request(ProtocolMessage("ECHO", msg_text))
            results.append((msg_text, res.command, res.data))
        except Exception as e:
            errors.append(e)

    try:
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 5
        for expected, cmd, actual in results:
            assert cmd == "ECHO"
            assert actual == expected
    finally:
        client.close()
        time.sleep(0.2)


def test_22_gradio_on_unload_cleans_session(server):
    """22. ניקוי session בעת unload / סגירת לשונית מפנה את החיבור בשרת."""
    ui = GradioClientUI(IP, PORT)
    req = SimpleNamespace(session_hash="session_unload")

    _call_gradio_method(ui, "connect", IP, PORT, "PING", [], req)
    time.sleep(0.15)
    assert server.client_count() == 1

    _call_gradio_method(ui, "on_unload", req)
    time.sleep(0.2)
    assert server.client_count() == 0