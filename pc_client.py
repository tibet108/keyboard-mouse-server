import socketio
import time
import json
import keyboard
import mouse
import threading
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import uuid

class RemoteInputClient:
    def __init__(self):
        self.sio = socketio.Client()
        self.device_id = str(uuid.uuid4())
        self.connected = False
        self.setup_socketio()
        
        # GUI
        self.setup_gui()
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("🖥️ Remote Input Client")
        self.root.geometry("700x600")
        
        # Статус подключения
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(pady=10, fill='x', padx=10)
        
        self.status_label = tk.Label(self.status_frame, text="❌ Не подключен", 
                                   font=('Arial', 12, 'bold'))
        self.status_label.pack(side='left')
        
        self.connect_btn = tk.Button(self.status_frame, text="🔗 Подключиться", 
                                   command=self.toggle_connection)
        self.connect_btn.pack(side='right')
        
        # Настройки сервера
        self.server_frame = tk.Frame(self.root)
        self.server_frame.pack(pady=5, fill='x', padx=10)
        
        tk.Label(self.server_frame, text="Сервер:").pack(side='left')
        self.server_entry = tk.Entry(self.server_frame, width=40)
        self.server_entry.insert(0, "https://keyboard-mouse-server.onrender.com/")
        self.server_entry.pack(side='left', padx=5)
        
        # Статистика команд
        self.stats_frame = tk.Frame(self.root, relief='groove', bd=2)
        self.stats_frame.pack(pady=5, fill='x', padx=10)
        
        tk.Label(self.stats_frame, text="📊 Статистика команд:", font=('Arial', 10, 'bold')).pack()
        
        stats_row = tk.Frame(self.stats_frame)
        stats_row.pack()
        
        self.keyboard_count = tk.Label(stats_row, text="⌨️ Клавиатура: 0", fg='blue')
        self.keyboard_count.pack(side='left', padx=10)
        
        self.mouse_count = tk.Label(stats_row, text="🖱️ Мышь: 0", fg='green')
        self.mouse_count.pack(side='left', padx=10)
        
        self.error_count = tk.Label(stats_row, text="❌ Ошибки: 0", fg='red')
        self.error_count.pack(side='left', padx=10)
        
        # Лог событий
        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=10, fill='both', expand=True, padx=10)
        
        log_header = tk.Frame(log_frame)
        log_header.pack(fill='x')
        
        tk.Label(log_header, text="📋 Лог событий:", font=('Arial', 10, 'bold')).pack(side='left')
        
        self.clear_btn = tk.Button(log_header, text="🗑️ Очистить", command=self.clear_logs)
        self.clear_btn.pack(side='right')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state='disabled')
        self.log_text.pack(fill='both', expand=True)
        
        # Инициализируем счетчики
        self.keyboard_commands = 0
        self.mouse_commands = 0
        self.error_commands = 0
        
    def log(self, message):
        """Добавление сообщения в лог"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)
        print(f"[{timestamp}] {message}")
    
    def clear_logs(self):
        """Очистка логов"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log("📋 Логи очищены")
    
    def update_stats(self, command_type, error=False):
        """Обновление статистики команд"""
        if error:
            self.error_commands += 1
            self.error_count.config(text=f"❌ Ошибки: {self.error_commands}")
        elif command_type == 'keyboard':
            self.keyboard_commands += 1
            self.keyboard_count.config(text=f"⌨️ Клавиатура: {self.keyboard_commands}")
        elif command_type == 'mouse':
            self.mouse_commands += 1
            self.mouse_count.config(text=f"🖱️ Мышь: {self.mouse_commands}")
    
    def setup_socketio(self):
        @self.sio.event
        def connect():
            self.connected = True
            self.log("🟢 Подключен к серверу")
            
            # Регистрируемся как PC клиент
            self.sio.emit('register', {
                'type': 'pc',
                'deviceId': self.device_id
            })
            
            # Обновляем GUI
            self.root.after(0, self.update_connection_status)
        
        @self.sio.event
        def disconnect():
            self.connected = False
            self.log("🔴 Отключен от сервера")
            self.root.after(0, self.update_connection_status)
        
        @self.sio.event
        def keyboard_execute(data):
            """Выполнение команд клавиатуры"""
            self.log(f"🎹 Получена команда клавиатуры: {data}")
            try:
                action = data.get('action')
                key = data.get('key')
                
                if action == 'key_press':
                    self.log(f"⌨️ Нажатие клавиши: {key}")
                    keyboard.press(key)
                    
                elif action == 'key_release':
                    self.log(f"⌨️ Отпускание клавиши: {key}")
                    keyboard.release(key)
                    
                elif action == 'key_tap':
                    self.log(f"⌨️ Нажатие+отпускание: {key}")
                    keyboard.press_and_release(key)
                    
                elif action == 'type_text':
                    text = data.get('text', '')
                    self.log(f"⌨️ Ввод текста: {text}")
                    keyboard.write(text)
                
                # Обновляем статистику
                self.root.after(0, lambda: self.update_stats('keyboard'))
                
                # Подтверждаем выполнение
                self.sio.emit('command_executed', {
                    'type': 'keyboard',
                    'success': True,
                    'data': data
                })
                
            except Exception as e:
                self.log(f"❌ Ошибка выполнения клавиатуры: {e}")
                self.root.after(0, lambda: self.update_stats('keyboard', error=True))
                self.sio.emit('command_executed', {
                    'type': 'keyboard',
                    'success': False,
                    'error': str(e),
                    'data': data
                })
        
        @self.sio.event
        def mouse_execute(data):
            """Выполнение команд мыши"""
            self.log(f"🖱️ Получена команда мыши: {data}")
            try:
                action = data.get('action')
                
                if action == 'move':
                    x = data.get('x', 0)
                    y = data.get('y', 0)
                    relative = data.get('relative', True)
                    
                    if relative:
                        self.log(f"🖱️ Относительное движение мыши: ({x}, {y})")
                        mouse.move(x, y, absolute=False)
                    else:
                        self.log(f"🖱️ Абсолютное движение мыши: ({x}, {y})")
                        mouse.move(x, y, absolute=True)
                        
                elif action == 'click':
                    button = data.get('button', 'left')
                    self.log(f"🖱️ Клик {button} кнопкой мыши")
                    mouse.click(button)
                    
                elif action == 'press':
                    button = data.get('button', 'left')
                    self.log(f"🖱️ Нажатие {button} кнопки мыши")
                    mouse.press(button)
                    
                elif action == 'release':
                    button = data.get('button', 'left')
                    self.log(f"🖱️ Отпускание {button} кнопки мыши")
                    mouse.release(button)
                    
                elif action == 'scroll':
                    delta = data.get('delta', 1)
                    self.log(f"🖱️ Прокрутка: {delta}")
                    mouse.wheel(delta)
                
                # Обновляем статистику
                self.root.after(0, lambda: self.update_stats('mouse'))
                
                # Подтверждаем выполнение
                self.sio.emit('command_executed', {
                    'type': 'mouse',
                    'success': True,
                    'data': data
                })
                
            except Exception as e:
                self.log(f"❌ Ошибка выполнения мыши: {e}")
                self.root.after(0, lambda: self.update_stats('mouse', error=True))
                self.sio.emit('command_executed', {
                    'type': 'mouse',
                    'success': False,
                    'error': str(e),
                    'data': data
                })
    
    def update_connection_status(self):
        """Обновление статуса подключения в GUI"""
        if self.connected:
            self.status_label.config(text="🟢 Подключен", fg="green")
            self.connect_btn.config(text="❌ Отключиться")
        else:
            self.status_label.config(text="🔴 Не подключен", fg="red")
            self.connect_btn.config(text="🔗 Подключиться")
    
    def toggle_connection(self):
        """Переключение соединения"""
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Подключение к серверу"""
        server_url = self.server_entry.get().strip()
        if not server_url:
            self.log("❌ Введите адрес сервера")
            return
            
        try:
            self.log(f"🔄 Подключение к {server_url}...")
            self.sio.connect(server_url)
        except Exception as e:
            self.log(f"❌ Ошибка подключения: {e}")
    
    def disconnect(self):
        """Отключение от сервера"""
        try:
            self.sio.disconnect()
        except Exception as e:
            self.log(f"❌ Ошибка отключения: {e}")
    
    def start_heartbeat(self):
        """Поддержание соединения"""
        def heartbeat():
            while True:
                if self.connected:
                    try:
                        self.sio.emit('ping')
                    except:
                        pass
                time.sleep(30)  # Каждые 30 секунд
        
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
    
    def run(self):
        """Запуск приложения"""
        self.log("🚀 Remote Input Client запущен")
        self.log("💡 Подключитесь к серверу для получения команд")
        
        # Запускаем heartbeat
        self.start_heartbeat()
        
        # Запускаем GUI
        try:
            self.root.mainloop()
        finally:
            if self.connected:
                self.disconnect()

if __name__ == "__main__":
    # Проверяем зависимости
    try:
        import keyboard
        import mouse
        import socketio
    except ImportError as e:
        print("❌ Отсутствуют зависимости:")
        print("Установите: pip install python-socketio keyboard mouse")
        sys.exit(1)
    
    client = RemoteInputClient()
    client.run()