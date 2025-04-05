import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import json
import os

class RelayControlApp:
    CONFIG_FILE = "relay_config.json"
    
    def __init__(self, root):
        self.root = root
        self.root.title("Управление реле")
        self.serial_port = None
        self.config = self.load_config()
        self.last_relay_state = {}  # Для хранения состояний реле
        
        # Переменные для хранения настроек
        self.port_var = tk.StringVar(value=self.config.get("last_port", ""))
        self.relay_num_var = tk.IntVar(value=self.config.get("last_relay_num", 1))
        self.feedback_var = tk.BooleanVar(value=self.config.get("feedback_enabled", False))
        
        # Создание интерфейса
        self.create_widgets()
        
        # Автоматическое обнаружение COM-портов
        self.update_ports()
        
        # Попытка автоматического подключения
        if self.config.get("auto_connect", False) and self.port_var.get():
            self.connect_port()
    
    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        config = {
            "last_port": self.port_var.get(),
            "last_relay_num": self.relay_num_var.get(),
            "feedback_enabled": self.feedback_var.get(),
            "auto_connect": bool(self.serial_port and self.serial_port.is_open)
        }
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(config, f)
    
    def create_widgets(self):
        # Фрейм для настроек порта
        port_frame = ttk.LabelFrame(self.root, text="Настройки порта")
        port_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        ttk.Label(port_frame, text="Порт:").grid(row=0, column=0, padx=5, pady=2)
        self.port_combobox = ttk.Combobox(port_frame, textvariable=self.port_var)
        self.port_combobox.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Button(port_frame, text="Обновить", command=self.update_ports).grid(row=0, column=2, padx=5, pady=2)
        self.connect_button = ttk.Button(port_frame, text="Подключиться", command=self.connect_port)
        self.connect_button.grid(row=0, column=3, padx=5, pady=2)
        
        # Фрейм для управления реле
        control_frame = ttk.LabelFrame(self.root, text="Управление реле")
        control_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        ttk.Label(control_frame, text="Номер реле:").grid(row=0, column=0, padx=5, pady=2)
        ttk.Spinbox(control_frame, from_=1, to=254, textvariable=self.relay_num_var, width=5,
                   command=lambda: self.update_indicator_for_current_relay()).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Checkbutton(control_frame, text="Ожидать ответ", variable=self.feedback_var).grid(row=0, column=2, padx=5, pady=2)
        
        # Индикатор состояния
        self.state_indicator = tk.Canvas(control_frame, width=30, height=30, bg="gray")
        self.state_indicator.grid(row=0, column=3, padx=5, pady=2)
        self.update_indicator("unknown")
        
        ttk.Button(control_frame, text="Включить", command=lambda: self.send_command("on")).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="Выключить", command=lambda: self.send_command("off")).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(control_frame, text="Переключить", command=lambda: self.send_command("toggle")).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(control_frame, text="Запросить статус", command=lambda: self.send_command("status")).grid(row=1, column=3, padx=5, pady=5)
        
        # Фрейм для лога
        log_frame = ttk.LabelFrame(self.root, text="Лог сообщений")
        log_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        
        self.log_text = tk.Text(log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Настройка расширения строк и столбцов
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
    
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
    
    def connect_port(self):
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Ошибка", "Порт не выбран")
            return
        
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.connect_button.config(text="Подключиться")
                self.log_message(f"Отключено от порта {port}")
                self.update_indicator("unknown")
                self.save_config()
                return
            
            self.serial_port = serial.Serial(port, baudrate=9600, timeout=1)
            self.connect_button.config(text="Отключиться")
            self.log_message(f"Подключено к порту {port}")
            self.save_config()
            
            # Очищаем буфер при подключении
            self.clear_serial_buffer()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться: {str(e)}")
            self.update_indicator("unknown")
    
    def clear_serial_buffer(self):
        """Очищает буфер последовательного порта"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            self.log_message("Буфер порта очищен")
    
    def send_command(self, command):
        if not self.serial_port or not self.serial_port.is_open:
            messagebox.showerror("Ошибка", "Порт не подключен")
            return
        
        relay_num = self.relay_num_var.get()
        if relay_num < 1 or relay_num > 254:
            messagebox.showerror("Ошибка", "Номер реле должен быть от 1 до 254")
            return
        
        # Сохраняем номер реле в конфиг
        self.save_config()
        
        # Очищаем буфер перед отправкой команды
        self.clear_serial_buffer()
        
        # Подготовка данных
        data1 = 0xA0
        data2 = relay_num
        data3 = self.get_command_code(command)
        
        if data3 is None:
            return  # Неизвестная команда
        
        # Расчет контрольной суммы
        checksum = (data1 + data2 + data3) % 0x100
        
        # Формирование команды
        cmd_bytes = bytes([data1, data2, data3, checksum])
        
        try:
            # Отправка команды
            self.serial_port.write(cmd_bytes)
            self.log_message(f"Отправлено: {cmd_bytes.hex(' ').upper()}")
            
            # Обновляем индикатор для команд без обратной связи
            if not self.feedback_var.get() and command in ("on", "off"):
                new_state = command
                self.update_indicator(new_state)
                self.last_relay_state[relay_num] = new_state
            
            # Если ожидается ответ
            if self.feedback_var.get() or command == "status":
                response = self.serial_port.read(4)
                if response:
                    self.log_message(f"Получено: {response.hex(' ').upper()}")
                    self.parse_response(response)
                else:
                    self.log_message("Ответ не получен (таймаут)")
                    self.update_indicator("unknown")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка связи: {str(e)}")
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
            self.log_message("Некорректный ответ (длина не 4 байта)")
            return
        
        data1, data2, data3, checksum = response
        
        # Проверка контрольной суммы
        calculated_checksum = (data1 + data2 + data3) % 0x100
        if calculated_checksum != checksum:
            self.log_message("Ошибка контрольной суммы в ответе")
            return
        
        # Проверка первого байта
        if data1 != 0xA0:
            self.log_message("Некорректный первый байт ответа")
            return
        
        # Интерпретация данных
        relay_num = data2
        status = data3
        
        if status in (0x00, 0x02):
            state = "off"
            state_text = "выключено"
        elif status in (0x01, 0x03):
            state = "on"
            state_text = "включено"
        else:
            state = "unknown"
            state_text = f"неизвестное состояние ({hex(status)})"
        
        # Обновляем индикатор, если это текущее реле
        if relay_num == self.relay_num_var.get():
            self.update_indicator(state)
        
        self.last_relay_state[relay_num] = state
        self.log_message(f"Реле {relay_num}: {state_text}")
    
    def log_message(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
    
    def on_closing(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RelayControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()