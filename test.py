import socket
import threading
import time
from types import SimpleNamespace
import pytest

from networkserver import NetworkServer
from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage
from GradioClientUI import GradioClientUI

IP = "127.0.0.1"
PORT = 8055


@pytest.fixture(scope="module")
def server():
    srv = NetworkServer(IP, PORT)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.3)
    yield srv
    srv.shutdown()


def test_01_three_clients_ping(server):
    clients = []
    for _ in range(3):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP, PORT))
        clients.append(s)

    for s in clients:
        Protocol.send(s, ProtocolMessage("PING"))
        res = Protocol.receive(s)
        assert res.command == "PONG"

    for s in clients:
        s.close()
    time.sleep(0.2)


def test_02_parallel_echo_and_time(server):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

    s1.close()
    s2.close()
    time.sleep(0.2)


def test_03_clients_count_three(server):
    clients = []
    for _ in range(3):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP, PORT))
        clients.append(s)
    time.sleep(0.1)

    Protocol.send(clients[0], ProtocolMessage("CLIENTS"))
    res = Protocol.receive(clients[0])
    assert res.command == "CLIENTS"
    assert res.data == "3"

    for s in clients:
        s.close()
    time.sleep(0.2)


def test_04_exit_single_client_others_continue(server):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.connect((IP, PORT))
    s2.connect((IP, PORT))

    Protocol.send(s1, ProtocolMessage("EXIT"))
    res1 = Protocol.receive(s1)
    assert res1.command == "BYE"
    s1.close()

    Protocol.send(s2, ProtocolMessage("PING"))
    res2 = Protocol.receive(s2)
    assert res2.command == "PONG"

    s2.close()
    time.sleep(0.2)


def test_05_clients_after_handler_removed(server):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.connect((IP, PORT))
    s2.connect((IP, PORT))
    time.sleep(0.1)

    Protocol.send(s2, ProtocolMessage("EXIT"))
    Protocol.receive(s2)
    s2.close()
    time.sleep(0.2)

    Protocol.send(s1, ProtocolMessage("CLIENTS"))
    res = Protocol.receive(s1)
    assert res.command == "CLIENTS"
    assert res.data == "1"

    s1.close()
    time.sleep(0.2)


def test_06_sudden_disconnect(server):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.connect((IP, PORT))
    s2.connect((IP, PORT))
    time.sleep(0.1)

    s2.close()
    time.sleep(0.2)

    Protocol.send(s1, ProtocolMessage("PING"))
    assert Protocol.receive(s1).command == "PONG"

    s1.close()
    time.sleep(0.2)


def test_07_unknown_command_returns_error(server):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((IP, PORT))

    payload = b"UNKNOWN|"
    header = len(payload).to_bytes(4, "big")
    s.sendall(header + payload)

    res = Protocol.receive(s)
    assert res.command == "ERROR"

    s.close()
    time.sleep(0.2)


def test_08_split_tcp_message(server):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((IP, PORT))

    raw = ProtocolMessage("ECHO", "SplitMessage").to_bytes()
    header = len(raw).to_bytes(Protocol.HEADER_SIZE, Protocol.BYTE_ORDER)
    packet = header + raw

    for byte in packet:
        s.sendall(bytes([byte]))
        time.sleep(0.01)

    res = Protocol.receive(s)
    assert res.command == "ECHO"
    assert res.data == "SplitMessage"

    s.close()
    time.sleep(0.2)


def test_09_invalid_message_protocol_error(server):
    with pytest.raises(ProtocolError):
        ProtocolMessage.from_bytes(b"\xff\xfe\xfd")

    with pytest.raises(ProtocolError):
        ProtocolMessage.from_user_input("ECHO")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((IP, PORT))
    bad_payload = b"|missing_cmd"
    s.sendall(len(bad_payload).to_bytes(4, "big") + bad_payload)
    res = Protocol.receive(s)
    assert res.command == "ERROR"

    s.close()
    time.sleep(0.2)


def test_10_gradio_two_separate_sessions(server):
    ui = GradioClientUI(IP, PORT)
    req1 = SimpleNamespace(session_hash="session_1")
    req2 = SimpleNamespace(session_hash="session_2")

    ui._GradioClientUI__connect(IP, PORT, "TIME", [], req1)
    ui._GradioClientUI__connect(IP, PORT, "TIME", [], req2)
    time.sleep(0.1)

    assert server.client_count() == 2

    ui._GradioClientUI__disconnect("TIME", [], req1)
    ui._GradioClientUI__disconnect("TIME", [], req2)
    time.sleep(0.2)


def test_11_gradio_disconnect_one_session_other_continues(server):
    ui = GradioClientUI(IP, PORT)
    req1 = SimpleNamespace(session_hash="session_a")
    req2 = SimpleNamespace(session_hash="session_b")

    ui._GradioClientUI__connect(IP, PORT, "PING", [], req1)
    ui._GradioClientUI__connect(IP, PORT, "PING", [], req2)

    ui._GradioClientUI__disconnect("PING", [], req1)
    out2 = ui._GradioClientUI__send("PING", "", [], req2)

    assert out2[0] == "Connected"
    assert "PONG" in out2[6][-1]["content"]

    ui._GradioClientUI__disconnect("PING", [], req2)
    time.sleep(0.2)


def test_12_gradio_command_change_data_field(server):
    ui = GradioClientUI(IP, PORT)
    req = SimpleNamespace(session_hash="session_cmd")
    ui._GradioClientUI__connect(IP, PORT, "TIME", [], req)

    echo_update = ui._GradioClientUI__on_command_change("ECHO", req)
    ping_update = ui._GradioClientUI__on_command_change("PING", req)

    assert echo_update["interactive"] is True
    assert ping_update["interactive"] is False

    ui._GradioClientUI__disconnect("PING", [], req)
    time.sleep(0.2)


def test_13_gradio_connection_error_friendly_message():
    ui = GradioClientUI(IP, 8099)
    req = SimpleNamespace(session_hash="session_err")

    out = ui._GradioClientUI__connect(IP, 8099, "TIME", [], req)
    status = out[0]
    last_msg = out[6][-1]["content"]

    assert "Disconnected" in status
    assert "Traceback" not in last_msg
    assert "Connection" in last_msg


def test_14_server_shutdown_releases_resources():
    srv = NetworkServer(IP, 8057)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.2)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((IP, 8057))
    time.sleep(0.1)
    assert srv.client_count() == 1

    srv.shutdown()
    assert srv.client_count() == 0
    s.close()


def test_15_server_restart_same_port():
    srv1 = NetworkServer(IP, 8058)
    t1 = threading.Thread(target=srv1.start, daemon=True)
    t1.start()
    time.sleep(0.2)

    # סגירת השרת הראשון ושחרור הפורט
    srv1.shutdown()
    time.sleep(0.2)

    # הפעלת שרת חדש על אותו פורט בדיוק
    srv2 = NetworkServer(IP, 8058)
    t2 = threading.Thread(target=srv2.start, daemon=True)
    t2.start()
    time.sleep(0.2)

    # וידוא שאפשר להתחבר לשרת החדש בהצלחה
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((IP, 8058))
    time.sleep(0.1)

    assert srv2.client_count() == 1

    # ניקוי וסגירה בסוף הבדיקה
    srv2.shutdown()
    s.close()
    time.sleep(0.2)