import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import json
import os

class RelayControlApp:
    CONFIG_FILE = "relay_config.json"
    DEFAULT_LANGUAGE = "en"
    
    def __init__(self, root):
        self.root = root
        self.root.title("Relay Control")
        self.serial_port = None
        self.config = self.load_config()
        self.last_relay_state = {}
        
        # Загрузка языковых ресурсов
        self.languages = self.load_languages()
        self.current_lang = self.config.get("language", self.DEFAULT_LANGUAGE)
        
        # Переменные для хранения настроек
        self.port_var = tk.StringVar(value=self.config.get("last_port", ""))
        self.relay_num_var = tk.IntVar(value=self.config.get("last_relay_num", 1))
        self.feedback_var = tk.BooleanVar(value=self.config.get("feedback_enabled", False))
        self.language_var = tk.StringVar(value=self.current_lang)
        
        # Создание интерфейса
        self.create_widgets()
        
        # Автоматическое обнаружение COM-портов
        self.update_ports()
        
        # Попытка автоматического подключения
        if self.config.get("auto_connect", False) and self.port_var.get():
            self.auto_connect()
    
    def load_languages(self):
        """Загружает языковые ресурсы из конфига"""
        default_languages = {
            "en": {
                "app_title": "Relay Control",
                "port_settings": "Port Settings",
                "port": "Port:",
                "refresh": "Refresh",
                "connect": "Connect",
                "disconnect": "Disconnect",
                "relay_control": "Relay Control",
                "relay_number": "Relay number:",
                "expect_response": "Expect response",
                "on": "On",
                "off": "Off",
                "toggle": "Toggle",
                "get_status": "Get status",
                "message_log": "Message Log",
                "language": "Language:",
                "connected_to_port": "Connected to port {}",
                "disconnected_from_port": "Disconnected from port {}",
                "port_buffer_cleared": "Port buffer cleared",
                "sent": "Sent: {}",
                "received": "Received: {}",
                "no_response": "No response (timeout)",
                "relay_status": "Relay {}: {}",
                "invalid_response": "Invalid response (length not 4 bytes)",
                "checksum_error": "Checksum error in response",
                "invalid_first_byte": "Invalid first byte in response",
                "unknown_state": "unknown state ({})",
                "port_not_selected": "Port not selected",
                "failed_to_connect": "Failed to connect: {}",
                "port_not_connected": "Port not connected",
                "invalid_relay_number": "Relay number must be between 1 and 254",
                "communication_error": "Communication error: {}",
                "port_busy": "Port is busy (maybe used by another application)",
                "auto_connect_failed": "Auto-connect failed: {}",
                "connection_lost": "Connection lost: {}"
            },
            "ru": {
                "app_title": "Управление реле",
                "port_settings": "Настройки порта",
                "port": "Порт:",
                "refresh": "Обновить",
                "connect": "Подключиться",
                "disconnect": "Отключиться",
                "relay_control": "Управление реле",
                "relay_number": "Номер реле:",
                "expect_response": "Ожидать ответ",
                "on": "Включить",
                "off": "Выключить",
                "toggle": "Переключить",
                "get_status": "Запросить статус",
                "message_log": "Лог сообщений",
                "language": "Язык:",
                "connected_to_port": "Подключено к порту {}",
                "disconnected_from_port": "Отключено от порта {}",
                "port_buffer_cleared": "Буфер порта очищен",
                "sent": "Отправлено: {}",
                "received": "Получено: {}",
                "no_response": "Ответ не получен (таймаут)",
                "relay_status": "Реле {}: {}",
                "invalid_response": "Некорректный ответ (длина не 4 байта)",
                "checksum_error": "Ошибка контрольной суммы в ответе",
                "invalid_first_byte": "Некорректный первый байт ответа",
                "unknown_state": "неизвестное состояние ({})",
                "port_not_selected": "Порт не выбран",
                "failed_to_connect": "Не удалось подключиться: {}",
                "port_not_connected": "Порт не подключен",
                "invalid_relay_number": "Номер реле должен быть от 1 до 254",
                "communication_error": "Ошибка связи: {}",
                "port_busy": "Порт занят (возможно, используется другим приложением)",
                "auto_connect_failed": "Автоподключение не удалось: {}",
                "connection_lost": "Соединение потеряно: {}"
            }
        }
        
        if "languages" in self.config:
            return {**default_languages, **self.config["languages"]}
        return default_languages
    
    def t(self, key, *args):
        """Возвращает переведенную строку с подставленными аргументами"""
        lang_dict = self.languages.get(self.current_lang, self.languages[self.DEFAULT_LANGUAGE])
        text = lang_dict.get(key, key)
        return text.format(*args) if args else text
    
    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        config = {
            "last_port": self.port_var.get(),
            "last_relay_num": self.relay_num_var.get(),
            "feedback_enabled": self.feedback_var.get(),
            "auto_connect": bool(self.serial_port and self.serial_port.is_open),
            "language": self.current_lang,
            "languages": self.languages
        }
        with open(self.CONFIG_FILE, "w", encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def change_language(self, *args):
        """Меняет язык интерфейса"""
        self.current_lang = self.language_var.get()
        self.save_config()
        self.update_ui_texts()
    
    def update_ui_texts(self):
        """Обновляет все тексты в интерфейсе согласно текущему языку"""
        self.root.title(self.t("app_title"))
        
        # Обновляем тексты виджетов
        for widget_info in self.widgets_to_translate:
            widget = widget_info["widget"]
            if "text_key" in widget_info:
                widget.config(text=self.t(widget_info["text_key"]))
            if "title_key" in widget_info:
                widget.config(text=self.t(widget_info["title_key"]))
        
        # Обновляем кнопку подключения
        if self.serial_port and self.serial_port.is_open:
            self.connect_button.config(text=self.t("disconnect"))
        else:
            self.connect_button.config(text=self.t("connect"))
    
    def create_widgets(self):
        # Список виджетов для перевода
        self.widgets_to_translate = []
        
        # Фрейм для настроек порта и языка
        settings_frame = ttk.Frame(self.root)
        settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # Фрейм для настроек порта
        port_frame = ttk.LabelFrame(settings_frame)
        port_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        port_label = ttk.Label(port_frame)
        port_label.grid(row=0, column=0, padx=5, pady=2)
        
        self.port_combobox = ttk.Combobox(port_frame, textvariable=self.port_var)
        self.port_combobox.grid(row=0, column=1, padx=5, pady=2)
        
        refresh_button = ttk.Button(port_frame, command=self.update_ports)
        refresh_button.grid(row=0, column=2, padx=5, pady=2)
        
        self.connect_button = ttk.Button(port_frame, command=self.connect_port)
        self.connect_button.grid(row=0, column=3, padx=5, pady=2)
        
        # Фрейм для выбора языка
        lang_frame = ttk.LabelFrame(settings_frame)
        lang_frame.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        lang_label = ttk.Label(lang_frame)
        lang_label.grid(row=0, column=0, padx=5, pady=2)
        
        lang_combobox = ttk.Combobox(lang_frame, textvariable=self.language_var, 
                                    values=list(self.languages.keys()), state="readonly")
        lang_combobox.grid(row=0, column=1, padx=5, pady=2)
        lang_combobox.bind("<<ComboboxSelected>>", self.change_language)
        
        # Фрейм для управления реле
        control_frame = ttk.LabelFrame(self.root)
        control_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        relay_num_label = ttk.Label(control_frame)
        relay_num_label.grid(row=0, column=0, padx=5, pady=2)
        
        ttk.Spinbox(control_frame, from_=1, to=254, textvariable=self.relay_num_var, width=5,
                   command=lambda: self.update_indicator_for_current_relay()).grid(row=0, column=1, padx=5, pady=2)
        
        feedback_check = ttk.Checkbutton(control_frame, variable=self.feedback_var)
        feedback_check.grid(row=0, column=2, padx=5, pady=2)
        
        # Индикатор состояния
        self.state_indicator = tk.Canvas(control_frame, width=30, height=30, bg="gray")
        self.state_indicator.grid(row=0, column=3, padx=5, pady=2)
        self.update_indicator("unknown")
        
        on_button = ttk.Button(control_frame, command=lambda: self.send_command("on"))
        on_button.grid(row=1, column=0, padx=5, pady=5)
        off_button = ttk.Button(control_frame, command=lambda: self.send_command("off"))
        off_button.grid(row=1, column=1, padx=5, pady=5)
        toggle_button = ttk.Button(control_frame, command=lambda: self.send_command("toggle"))
        toggle_button.grid(row=1, column=2, padx=5, pady=5)
        status_button = ttk.Button(control_frame, command=lambda: self.send_command("status"))
        status_button.grid(row=1, column=3, padx=5, pady=5)
        
        # Фрейм для лога
        log_frame = ttk.LabelFrame(self.root)
        log_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        
        self.log_text = tk.Text(log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Настройка расширения строк и столбцов
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        
        # Сохраняем виджеты для перевода
        self.widgets_to_translate = [
            {"widget": port_frame, "title_key": "port_settings"},
            {"widget": port_label, "text_key": "port"},
            {"widget": refresh_button, "text_key": "refresh"},
            {"widget": self.connect_button, "text_key": "connect"},
            {"widget": lang_frame, "title_key": "language"},
            {"widget": lang_label, "text_key": "language"},
            {"widget": control_frame, "title_key": "relay_control"},
            {"widget": relay_num_label, "text_key": "relay_number"},
            {"widget": feedback_check, "text_key": "expect_response"},
            {"widget": on_button, "text_key": "on"},
            {"widget": off_button, "text_key": "off"},
            {"widget": toggle_button, "text_key": "toggle"},
            {"widget": status_button, "text_key": "get_status"},
            {"widget": log_frame, "title_key": "message_log"}
        ]
        
        # Устанавливаем текущий язык
        self.language_var.set(self.current_lang)
        self.update_ui_texts()
    
    def update_indicator_for_current_relay(self):
        """Обновляет индикатор для текущего выбранного реле"""
        relay_num = self.relay_num_var.get()
        state = self.last_relay_state.get(relay_num, "unknown")
        self.update_indicator(state)
    
    def update_indicator(self, state):
        """Обновляет индикатор состояния"""
        color = {
            "on": "red",
            "off": "green",
            "unknown": "gray"
        }.get(state, "gray")
        
        self.state_indicator.delete("all")
        self.state_indicator.create_oval(5, 5, 25, 25, fill=color, outline="black")
        self.state_indicator.create_text(15, 15, text="●", fill="white" if state != "unknown" else "black")
    
    def update_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])
    
    def auto_connect(self):
        """Пытается автоматически подключиться к порту"""
        port = self.port_var.get()
        try:
            self.serial_port = serial.Serial(port, baudrate=9600, timeout=2)
            if self.serial_port.is_open:
                self.connect_button.config(text=self.t("disconnect"))
                self.log_message(self.t("connected_to_port", port))
                self.clear_serial_buffer()
            else:
                raise serial.SerialException("Port open failed")
        except Exception as e:
            self.log_message(self.t("auto_connect_failed", str(e)))
            self.serial_port = None
    
    def connect_port(self):
        """Подключается к выбранному порту"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror(self.t("app_title"), self.t("port_not_selected"))
            return
        
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.serial_port = None
                self.connect_button.config(text=self.t("connect"))
                self.log_message(self.t("disconnected_from_port", port))
                self.update_indicator("unknown")
                self.save_config()
                return
            
            self.serial_port = serial.Serial(port, baudrate=9600, timeout=2)
            if self.serial_port.is_open:
                self.connect_button.config(text=self.t("disconnect"))
                self.log_message(self.t("connected_to_port", port))
                self.save_config()
                self.clear_serial_buffer()
            else:
                raise serial.SerialException("Port open failed")
                
        except Exception as e:
            error_msg = str(e)
            if "Access is denied" in error_msg or "Permission denied" in error_msg:
                error_msg = self.t("port_busy") + " " + error_msg
            messagebox.showerror(self.t("app_title"), error_msg)
            if self.serial_port:
                self.serial_port.close()
            self.serial_port = None
            self.connect_button.config(text=self.t("connect"))
            self.update_indicator("unknown")

    def clear_serial_buffer(self):
        """Очищает буфер последовательного порта"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            self.log_message(self.t("port_buffer_cleared"))
    
    def send_command(self, command):
        """Отправляет команду на реле"""
        if not self.serial_port or not self.serial_port.is_open:
            if self.config.get("auto_connect", False) and self.port_var.get():
                try:
                    self.auto_connect()
                    if not (self.serial_port and self.serial_port.is_open):
                        raise serial.SerialException("Auto-reconnect failed")
                except Exception as e:
                    messagebox.showerror(self.t("app_title"), 
                                       self.t("port_not_connected") + "\n" + str(e))
                    return
            else:
                messagebox.showerror(self.t("app_title"), self.t("port_not_connected"))
                return
        
        relay_num = self.relay_num_var.get()
        if relay_num < 1 or relay_num > 254:
            messagebox.showerror(self.t("app_title"), self.t("invalid_relay_number"))
            return
        
        try:
            # Очищаем буфер перед отправкой
            self.clear_serial_buffer()
            
            # Формируем команду
            data1 = 0xA0
            data2 = relay_num
            data3 = self.get_command_code(command)
            checksum = (data1 + data2 + data3) % 0x100
            cmd_bytes = bytes([data1, data2, data3, checksum])
            
            # Отправляем команду
            self.serial_port.write(cmd_bytes)
            self.log_message(self.t("sent", cmd_bytes.hex(' ').upper()))
            
            # Обновляем индикатор для команд без обратной связи
            if not self.feedback_var.get() and command in ("on", "off"):
                self.update_indicator(command)
                self.last_relay_state[relay_num] = command
            
            # Обрабатываем ответ, если требуется
            if self.feedback_var.get() or command == "status":
                try:
                    response = self.serial_port.read(4)
                    if response:
                        self.log_message(self.t("received", response.hex(' ').upper()))
                        self.parse_response(response)
                    else:
                        self.log_message(self.t("no_response"))
                        self.update_indicator("unknown")
                except Exception as e:
                    self.log_message(self.t("connection_lost", str(e)))
                    self.serial_port.close()
                    self.serial_port = None
                    self.connect_button.config(text=self.t("connect"))
                    self.update_indicator("unknown")
                    
        except Exception as e:
            error_msg = str(e)
            if "failed" in error_msg or "error" in error_msg.lower():
                self.log_message(self.t("communication_error", error_msg))
            messagebox.showerror(self.t("app_title"), self.t("communication_error", error_msg))
            if self.serial_port:
                self.serial_port.close()
            self.serial_port = None
            self.connect_button.config(text=self.t("connect"))
            self.update_indicator("unknown")

    def get_command_code(self, command):
        codes = {
            "off": 0x00 if not self.feedback_var.get() else 0x02,
            "on": 0x01 if not self.feedback_var.get() else 0x03,
            "toggle": 0x04,
            "status": 0x05
        }
        return codes.get(command)
    
    def parse_response(self, response):
        if len(response) != 4:
            self.log_message(self.t("invalid_response"))
            return
        
        data1, data2, data3, checksum = response
        
        # Проверка контрольной суммы
        calculated_checksum = (data1 + data2 + data3) % 0x100
        if calculated_checksum != checksum:
            self.log_message(self.t("checksum_error"))
            return
        
        # Проверка первого байта
        if data1 != 0xA0:
            self.log_message(self.t("invalid_first_byte"))
            return
        
        # Интерпретация данных
        relay_num = data2
        status = data3
        
        if status in (0x00, 0x02):
            state = "off"
            state_text = self.t("off")
        elif status in (0x01, 0x03):
            state = "on"
            state_text = self.t("on")
        else:
            state = "unknown"
            state_text = self.t("unknown_state", hex(status))
        
        # Обновляем индикатор, если это текущее реле
        if relay_num == self.relay_num_var.get():
            self.update_indicator(state)
        
        self.last_relay_state[relay_num] = state
        self.log_message(self.t("relay_status", relay_num, state_text))
    
    def log_message(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
    
    def on_closing(self):
        self.save_config()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RelayControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()