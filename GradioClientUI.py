import socket
import threading
import gradio as gr

from Protocol import Protocol, ProtocolError
from ProtocolMessage import ProtocolMessage
from networkclient import NetworkClient


class GradioClientUI:
    """ממשק משתמש גרפי רב-משתמשים בדפדפן עבור לקוח תקשורת TCP."""

    # פקודות שהמשתמש רשאי לבחור (מסנן תשובות מערכת פנימיות כמו PONG, BYE, ERROR)
    USER_COMMANDS = [
        cmd for cmd in Protocol.COMMANDS
        if cmd not in ("PONG", "BYE", "ERROR")
    ]

    def __init__(self, ip: str = "127.0.0.1", port: int = 8000):
        """שמירת הגדרות ברירת מחדל, יצירת מילון לקוחות ומנעול ובניית ה-UI."""
        self.__default_ip: str = ip
        self.__default_port: int = port
        self.__clients: dict[str, NetworkClient] = {}
        self.__lock: threading.Lock = threading.Lock()
        self.__theme, self.__css = self.__build_style()
        self.demo: gr.Blocks = self.__build()

    def __build_style(self):
        """בניית ה-Theme וה-CSS עבור ממשק Gradio."""
        cyber_theme = gr.themes.Base(
            primary_hue="emerald",
            secondary_hue="cyan",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
        ).set(
            background_fill_primary="#0d1322",
            background_fill_primary_dark="#0d1322",
            background_fill_secondary="#050811",
            background_fill_secondary_dark="#050811",
            border_color_primary="#10b98155",
            border_color_primary_dark="#10b98155",
            body_background_fill="#070b14",
            body_background_fill_dark="#070b14",
            body_text_color="#e2e8f0",
            body_text_color_dark="#e2e8f0",
            block_background_fill="#0d1322",
            block_background_fill_dark="#0d1322",
            block_border_color="#10b98144",
            block_border_color_dark="#10b98144",
            block_label_text_color="#10b981",
            block_label_text_color_dark="#10b981",
            input_background_fill="#050811",
            input_background_fill_dark="#050811",
            input_border_color="#10b98155",
            input_border_color_dark="#10b98155",
            button_primary_background_fill="#10b981",
            button_primary_background_fill_dark="#10b981",
            button_primary_background_fill_hover="#059669",
            button_primary_text_color="#020617",
            button_primary_text_color_dark="#020617",
        )

        cyber_css = """
        .gradio-container {
            background: radial-gradient(circle at top, #0f1c2e 0%, #070b14 75%) !important;
        }
        .cyber-header {
            text-align: center;
            padding: 14px;
            border: 1px solid #10b981;
            border-radius: 8px;
            background: linear-gradient(90deg, #070b14, #0d2622, #070b14);
            box-shadow: 0 0 18px rgba(16, 185, 129, 0.25);
            margin-bottom: 12px;
        }
        .cyber-header h1 {
            color: #10b981 !important;
            letter-spacing: 3px;
            text-transform: uppercase;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.7);
            margin: 0 !important;
        }
        .top-secret-badge {
            color: #f43f5e !important;
            font-size: 0.85em;
            letter-spacing: 4px;
            font-weight: bold;
            margin-top: 4px !important;
        }
        .rtl-text {
            direction: rtl;
            text-align: right;
            font-family: system-ui, -apple-system, sans-serif;
            line-height: 1.6;
        }
        .rtl-text code {
            background-color: #050811 !important;
            color: #10b981 !important;
            border: 1px solid #10b98166 !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            font-family: 'JetBrains Mono', monospace !important;
            direction: ltr !important;
            display: inline-block !important;
        }
        .row > button, .gr-row > button, button.primary, button.stop {
            align-self: stretch !important;
            height: auto !important;
            min-height: 82px !important;
        }
        /* כפתור Disconnect במצב לא פעיל (אדום כהה מעומעם) */
        #disconnect-btn, #disconnect-btn > button, #disconnect-btn:disabled, #disconnect-btn > button:disabled {
            background: #ba6060 !important;
            background-color: #ba6060 !important;
            color: #fda4af !important;
            border: 1px solid #881337 !important;
            opacity: 0.85 !important;
        }
        /* כפתור Disconnect במצב פעיל (אדום בוהק) */
        #disconnect-btn:not(:disabled), #disconnect-btn > button:not(:disabled) {
            background: #e11d48 !important;
            background-color: #e11d48 !important;
            color: #ffffff !important;
            border: 1px solid #fb7185 !important;
            opacity: 1 !important;
        }
        /* תיקון בועת הודעת המשתמש בצ'אט שלא תהיה לבנה */
        .message.user, [data-testid="user"] {
            background-color: #064e3b !important;
            color: #ecfdf5 !important;
            border: 1px solid #10b98166 !important;
        }
        """
        return cyber_theme, cyber_css

    def launch(self, **kwargs):
        """הפעלת ממשק Gradio בעיצוב Cyber / Top Secret כהה וזוהר."""
        kwargs.setdefault("theme", self.__theme)
        kwargs.setdefault("css", self.__css)
        self.demo.launch(**kwargs)

    # -------------------------------------------------------------------------
    # ניהול Session ולקוחות (Thread-Safe)
    # -------------------------------------------------------------------------

    def __get_session_id(self, request: gr.Request | None) -> str:
        """חילוץ מזהה ייחודי ללשונית הדפדפן מתוך אובייקט הבקשה."""
        if request is not None and getattr(request, "session_hash", None):
            return str(request.session_hash)
        return "default_session"

    def __get_client(self, request: gr.Request | None) -> NetworkClient | None:
        """איתור אובייקט הלקוח המשויך ל-session נתון."""
        session_id = self.__get_session_id(request)
        with self.__lock:
            return self.__clients.get(session_id)

    def __remove_client(self, request: gr.Request | None):
        """הסרת הלקוח של session מהמילון וסגירת החיבור שלו בבטחה."""
        session_id = self.__get_session_id(request)
        with self.__lock:
            client = self.__clients.pop(session_id, None)

        if client is not None:
            client.close()

    def __on_unload(self, request: gr.Request | None = None):
        """ניקוי משאבים אוטומטי בעת סגירת לשונית או רענון הדף."""
        client = self.__get_client(request)
        if client is not None and client.connected:
            try:
                client.request(ProtocolMessage("EXIT", ""))
            except Exception:
                pass
        self.__remove_client(request)

    # -------------------------------------------------------------------------
    # ניהול היסטוריית צ'אט, תצוגת פקדים והודעות שגיאה
    # -------------------------------------------------------------------------

    def __add(self, history: list | None, role: str, text: str) -> list:
        """הוספת פריט חדש להיסטוריית ההודעות בפורמט תואם gr.Chatbot."""
        updated = list(history) if history else []
        updated.append({"role": role, "content": text})
        return updated

    def __describe(self, error: Exception) -> str:
        """המרת חריגות טכניות להודעות ברורות למשתמש ללא חשיפת traceback."""
        if isinstance(error, ConnectionRefusedError):
            return "Connection refused: The server is unreachable or not running."
        if isinstance(error, socket.timeout):
            return "Connection timed out: The server took too long to respond."
        if isinstance(error, ConnectionError):
            return f"Connection lost: {error}"
        if isinstance(error, ProtocolError):
            return f"Protocol error: {error}"
        if isinstance(error, OSError):
            return f"Network error: {error}"
        return f"Unexpected error: {error}"

    def __data_placeholder(self, command: str | None, requires_data: bool) -> str:
        """החזרת טקסט מנחה מתאים לשדה הדאטה בהתאם לפקודה."""
        if not requires_data:
            return "No data required for this command"
        if command == "ECHO":
            return "Enter text for ECHO..."
        return f"Enter data for {command}..." if command else "Enter payload data..."

    def __view(
        self,
        history: list,
        client: NetworkClient | None,
        command: str | None,
        clear_data: bool = False,
        status_override: str | None = None
    ) -> list:
        """
        בניית רשימת העדכונים לכל רכיבי המסך בהתאם למצב החיבור והפקודה הנבחרת.
        סדר הפלטים תואם לרשימת outputs ב-Gradio:
        [status_box, connect_btn, disconnect_btn, command_dd, data_tb, send_btn, chatbot]
        """
        is_connected = client is not None and client.connected
        requires_data = bool(command and command in Protocol.COMMANDS_WITH_DATA)
        placeholder_text = self.__data_placeholder(command, requires_data)

        if status_override is not None:
            status_text = status_override
        elif is_connected:
            status_text = "Connected"
        else:
            status_text = "Disconnected"

        if clear_data:
            data_update = gr.update(
                interactive=(is_connected and requires_data),
                value="",
                placeholder=placeholder_text
            )
        else:
            data_update = gr.update(
                interactive=(is_connected and requires_data),
                placeholder=placeholder_text
            )

        return [
            status_text,                                      # Status
            gr.update(interactive=not is_connected),          # Connect button
            gr.update(interactive=is_connected),              # Disconnect button
            gr.update(interactive=is_connected),              # Command dropdown
            data_update,                                      # Data textbox
            gr.update(interactive=is_connected),              # Send button
            history                                           # Requests and replies
        ]

    # -------------------------------------------------------------------------
    # Callbacks של פעולות המשתמש
    # -------------------------------------------------------------------------

    def __connect(
        self,
        ip: str,
        port: int | float,
        command: str | None,
        history: list,
        request: gr.Request
    ) -> list:
        """יצירת חיבור TCP עצמאי עבור ה-session הנוכחי ועדכון המסך."""
        history = list(history) if history else []
        existing_client = self.__get_client(request)

        if existing_client is not None and existing_client.connected:
            return self.__view(
                history, existing_client, command,
                status_override=f"Already connected to {ip}:{int(port)}"
            )

        # ניקוי חיבור ישן אם נותר במצב מנותק
        self.__remove_client(request)

        clean_ip = (ip or self.__default_ip).strip()
        try:
            clean_port = int(port)
            if not (1 <= clean_port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
        except (TypeError, ValueError):
            err_msg = "Invalid port number. Please enter a port between 1 and 65535."
            history = self.__add(history, "assistant", f"⚠️ {err_msg}")
            return self.__view(history, None, command, status_override=err_msg)

        try:
            new_client = NetworkClient(ip=clean_ip, port=clean_port)
            session_id = self.__get_session_id(request)
            with self.__lock:
                self.__clients[session_id] = new_client

            status_msg = f"Connected to {clean_ip}:{clean_port}"
            return self.__view(history, new_client, command, clear_data=True, status_override=status_msg)

        except Exception as e:
            err_desc = self.__describe(e)
            history = self.__add(history, "assistant", f"⚠️ {err_desc}")
            return self.__view(history, None, command, status_override=f"Disconnected ({err_desc})")

    def __disconnect(
        self,
        command: str | None,
        history: list,
        request: gr.Request
    ) -> list:
        """שליחת פקודת EXIT, סגירת החיבור של ה-session ועדכון המסך."""
        history = list(history) if history else []
        client = self.__get_client(request)

        if client is not None and client.connected:
            try:
                exit_msg = ProtocolMessage("EXIT", "")
                history = self.__add(history, "user", "EXIT")
                reply = client.request(exit_msg)
                reply_text = f"{reply.command}: {reply.data}" if reply.data else reply.command
                history = self.__add(history, "assistant", reply_text)
            except Exception as e:
                history = self.__add(history, "assistant", f"⚠️ {self.__describe(e)}")

        self.__remove_client(request)
        return self.__view(
            history, None, command, clear_data=True,
            status_override="Disconnected (Closed by user)"
        )

    def __send(
        self,
        command: str | None,
        data: str,
        history: list,
        request: gr.Request
    ) -> list:
        """בניית הודעת פרוטוקול, שליחתה דרך NetworkClient והצגת התשובה."""
        history = list(history) if history else []
        client = self.__get_client(request)

        if client is None or not client.connected:
            self.__remove_client(request)
            err_msg = "Not connected to server. Please click Connect first."
            history = self.__add(history, "assistant", f"⚠️ {err_msg}")
            return self.__view(history, None, command, status_override="Disconnected")

        if not command:
            err_msg = "Please select a command first."
            history = self.__add(history, "assistant", f"⚠️ {err_msg}")
            return self.__view(history, client, command, status_override="Connected")

        requires_data = command in Protocol.COMMANDS_WITH_DATA
        clean_data = (data or "") if requires_data else ""

        # בדיקת תקינות קלט לפני שליחה לשרת
        if requires_data and not clean_data.strip():
            err_msg = f"Command '{command}' requires data in the Data field."
            history = self.__add(history, "assistant", f"⚠️ {err_msg}")
            return self.__view(history, client, command, status_override="Connected")

        try:
            msg = ProtocolMessage(command, clean_data)
        except ProtocolError as pe:
            err_desc = self.__describe(pe)
            history = self.__add(history, "assistant", f"⚠️ {err_desc}")
            return self.__view(history, client, command, status_override="Connected")

        # הצגת הבקשה בצד המשתמש
        user_display = f"{command} {clean_data}".strip()
        history = self.__add(history, "user", user_display)

        try:
            response = client.request(msg)

            # עיצוב התשובה מהשרת
            if response.data:
                bot_display = f"{response.command}: {response.data}"
            else:
                bot_display = response.command

            history = self.__add(history, "assistant", bot_display)

            # אם המשתמש בחר EXIT מתוך רשימת הפקודות ושלח
            if command == "EXIT" or response.command in ("BYE", "EXIT"):
                self.__remove_client(request)
                return self.__view(
                    history, None, command, clear_data=True,
                    status_override="Disconnected (EXIT sent)"
                )

            return self.__view(
                history, client, command, clear_data=True,
                status_override="Connected"
            )

        except Exception as e:
            err_desc = self.__describe(e)
            history = self.__add(history, "assistant", f"⚠️ {err_desc}")
            self.__remove_client(request)
            return self.__view(
                history, None, command, clear_data=True,
                status_override="Disconnected (Connection lost)"
            )

    def __on_command_change(self, command: str | None, request: gr.Request):
        """עדכון זמינות שדה Data כאשר המשתמש מחליף פקודה."""
        client = self.__get_client(request)
        is_connected = client is not None and client.connected
        requires_data = bool(command and command in Protocol.COMMANDS_WITH_DATA)

        return gr.update(
            interactive=(is_connected and requires_data),
            value="",
            placeholder=self.__data_placeholder(command, requires_data)
        )

    def __clear_log(self) -> list:
        """ניקוי היסטוריית ההודעות המוצגת ללא ניתוק מהשרת."""
        return []

    # -------------------------------------------------------------------------
    # בניית ממשק Gradio
    # -------------------------------------------------------------------------

    def __build(self) -> gr.Blocks:
        """בניית רכיבי המסך בעיצוב CyberVault Top Secret."""
        choices = list(self.USER_COMMANDS)
        default_cmd = "TIME" if "TIME" in choices else (choices[0] if choices else None)

        with gr.Blocks(title="CYBERVAULT // SECURE TERMINAL") as demo:
            # כותרת Top Secret זוהרת
            with gr.Column(elem_classes="cyber-header"):
                gr.Markdown("# 🛡️ CYBERVAULT // TCP TERMINAL")
                gr.Markdown("🔒 CLEARANCE LEVEL: TOP SECRET — MULTI-SESSION NODE", elem_classes="top-secret-badge")

            # כיס מתקפל עם הסבר על המערכת והפקודות
            with gr.Accordion("📂 [CLASSIFIED BRIEFING] הסבר על המערכת והפקודות — לחצו לפתיחה", open=False):
                gr.Markdown(
                    """
                    ### איך המערכת עובדת?
                    ממשק זה הוא **לקוח TCP** (צד המשתמש) המתחבר לשרת מרובה־לקוחות (`NetworkServer`).
- **הפרדה בין לשוניות:** כל לשונית בדפדפן מקבלת מזהה ייחודי (`session_hash`) וחיבור TCP עצמאי משלה (`NetworkClient`), כך שלקוחות שונים יכולים לעבוד במקביל מבלי להפריע זה לזה.
- **שכבות המערכת:** הממשק (Gradio) מעביר בקשות ללוגיקת הלקוח (`NetworkClient`), שמקודדת אותן לפי חוזה התקשורת (`Protocol` / `ProtocolMessage`) ושולחת לשרת.

                    ---

                    ### פירוט הפקודות הזמינות:
- **`PING`** — בדיקת תקינות וזמינות החיבור מול השרת (השרת מחזיר `PONG`).
- **`ECHO`** — שליחת טקסט חופשי אל השרת וקבלתו בחזרה (דורש הזנת טקסט בשדה **Data**).
- **`TIME`** — קבלת התאריך והשעה הנוכחיים מהשרת.
- **`CLIENTS`** — הצגת מספר הלקוחות המחוברים כרגע לשרת במקביל.
- **`EXIT`** — שליחת בקשת יציאה מסודרת לשרת (השרת מחזיר `Goodbye`) וסגירת החיבור של הלשונית הנוכחית.
                    """,
                    elem_classes="rtl-text"
                )

            # כרטיסיית חיבור וסטטוס
            with gr.Group():
                with gr.Row():
                    ip_input = gr.Textbox(
                        label="TARGET SERVER IP",
                        value=self.__default_ip,
                        scale=3
                    )
                    port_input = gr.Number(
                        label="PORT",
                        value=self.__default_port,
                        precision=0,
                        scale=1
                    )
                    connect_btn = gr.Button("⚡ CONNECT", variant="primary", scale=1)
                    disconnect_btn = gr.Button(
                        "⛔ DISCONNECT",
                        variant="stop",
                        interactive=False,
                        scale=1,
                        elem_id="disconnect-btn"
                    )

                status_box = gr.Textbox(
                    label="CONNECTION STATUS",
                    value="Disconnected",
                    interactive=False
                )

            # מסוף היסטוריית הבקשות והתשובות
            chatbot = gr.Chatbot(
                label="REQUESTS & REPLIES",
                height=175
            )

            # כרטיסיית שליחת פקודה
            with gr.Group():
                with gr.Row():
                    command_dd = gr.Dropdown(
                        label="COMMAND",
                        choices=choices,
                        value=default_cmd,
                        interactive=False,
                        scale=1
                    )
                    data_tb = gr.Textbox(
                        label="PAYLOAD / DATA",
                        placeholder="No data required for this command",
                        interactive=False,
                        scale=3
                    )
                    send_btn = gr.Button("📡 TRANSMIT", variant="primary", interactive=False, scale=1)

            clear_btn = gr.Button("🧹 PURGE LOG", size="sm")

            # רשימת הפקדים המשותפת לעדכוני מצב
            ui_outputs = [
                status_box,
                connect_btn,
                disconnect_btn,
                command_dd,
                data_tb,
                send_btn,
                chatbot
            ]

            # חיבור אירועים (Callbacks)
            connect_btn.click(
                fn=self.__connect,
                inputs=[ip_input, port_input, command_dd, chatbot],
                outputs=ui_outputs
            )

            disconnect_btn.click(
                fn=self.__disconnect,
                inputs=[command_dd, chatbot],
                outputs=ui_outputs
            )

            send_btn.click(
                fn=self.__send,
                inputs=[command_dd, data_tb, chatbot],
                outputs=ui_outputs
            )

            # שליחה גם בלחיצה על Enter בתוך שדה Data
            data_tb.submit(
                fn=self.__send,
                inputs=[command_dd, data_tb, chatbot],
                outputs=ui_outputs
            )

            # שינוי מצב שדה Data בעת החלפת פקודה
            command_dd.change(
                fn=self.__on_command_change,
                inputs=[command_dd],
                outputs=[data_tb]
            )

            # ניקוי לוג ללא ניתוק
            clear_btn.click(
                fn=self.__clear_log,
                inputs=[],
                outputs=[chatbot]
            )

            # ניקוי חיבור אוטומטי בסגירת לשונית / רענון דף (נתמך בגרסאות Gradio חדשות)
            if hasattr(demo, "unload"):
                demo.unload(fn=self.__on_unload)

        return demo


if __name__ == "__main__":
    ui = GradioClientUI(ip="127.0.0.1", port=8000)
    ui.launch()