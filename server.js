const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Хранилище активных сессий
const activeSessions = new Map();

// Веб-страница для управления
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>USB Keyboard Mouse Server</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .session { border: 1px solid #ccc; padding: 15px; margin: 10px 0; }
        .active { background: #e8f5e8; }
        .inactive { background: #f5f5f5; }
      </style>
    </head>
    <body>
      <h1>🌐 USB Keyboard Mouse Cloud Server</h1>
      <p>Сервер запущен и готов к подключениям</p>
      <div id="sessions"></div>
      
      <script src="/socket.io/socket.io.js"></script>
      <script>
        const socket = io();
        socket.on('sessions-update', (sessions) => {
          const div = document.getElementById('sessions');
          div.innerHTML = '<h2>Активные сессии:</h2>' + 
            sessions.map(s => \`
              <div class="session \${s.connected ? 'active' : 'inactive'}">
                <strong>ID:</strong> \${s.id}<br>
                <strong>Тип:</strong> \${s.type}<br>
                <strong>Статус:</strong> \${s.connected ? '🟢 Подключен' : '🔴 Отключен'}<br>
                <strong>Время:</strong> \${new Date(s.lastSeen).toLocaleString()}
              </div>
            \`).join('');
        });
      </script>
    </body>
    </html>
  `);
});

// WebSocket подключения
io.on('connection', (socket) => {
  console.log('🔗 Новое подключение:', socket.id);

  // Регистрация устройства
  socket.on('register', (data) => {
    const { type, deviceId } = data; // type: 'android' | 'pc'
    
    activeSessions.set(socket.id, {
      id: socket.id,
      type,
      deviceId,
      connected: true,
      lastSeen: Date.now(),
      socket: socket
    });

    console.log(`📱 Зарегистрировано устройство: ${type} (${socket.id})`);
    broadcastSessions();
  });

  // Команды клавиатуры от Android к PC
  socket.on('keyboard-command', (data) => {
    console.log('⌨️ Команда клавиатуры:', data);
    
    // Отправляем команду всем подключенным PC клиентам
    activeSessions.forEach((session) => {
      if (session.type === 'pc' && session.connected) {
        console.log(`📤 Отправляю команду клавиатуры PC клиенту ${session.id}`);
        session.socket.emit('keyboard_execute', data);
      }
    });
  });

  // Команды мыши от Android к PC
  socket.on('mouse-command', (data) => {
    console.log('🖱️ Команда мыши:', data);
    
    // Отправляем команду всем подключенным PC клиентам
    activeSessions.forEach((session) => {
      if (session.type === 'pc' && session.connected) {
        console.log(`📤 Отправляю команду мыши PC клиенту ${session.id}`);
        session.socket.emit('mouse_execute', data);
      }
    });
  });

  // Подтверждение выполнения от PC
  socket.on('command-executed', (data) => {
    console.log('✅ Команда выполнена:', data);
    
    // Уведомляем Android об успешном выполнении
    activeSessions.forEach((session) => {
      if (session.type === 'android' && session.connected) {
        session.socket.emit('execution-feedback', data);
      }
    });
  });

  // Heartbeat для поддержания соединения
  socket.on('ping', () => {
    const session = activeSessions.get(socket.id);
    if (session) {
      session.lastSeen = Date.now();
      socket.emit('pong');
    }
  });

  // Отключение
  socket.on('disconnect', () => {
    console.log('❌ Устройство отключено:', socket.id);
    
    const session = activeSessions.get(socket.id);
    if (session) {
      session.connected = false;
      session.lastSeen = Date.now();
    }
    
    broadcastSessions();
  });
});

// Трансляция информации о сессиях
function broadcastSessions() {
  const sessions = Array.from(activeSessions.values()).map(s => ({
    id: s.id,
    type: s.type,
    connected: s.connected,
    lastSeen: s.lastSeen
  }));
  
  io.emit('sessions-update', sessions);
}

// Очистка неактивных сессий
setInterval(() => {
  const now = Date.now();
  activeSessions.forEach((session, id) => {
    if (now - session.lastSeen > 60000) { // 1 минута неактивности
      console.log('🧹 Удаляем неактивную сессию:', id);
      activeSessions.delete(id);
    }
  });
  broadcastSessions();
}, 30000); // Проверяем каждые 30 секунд

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🌐 Сервер запущен на порту ${PORT}`);
  console.log(`📱 Android: подключаться к ws://localhost:${PORT}`);
  console.log(`💻 PC: подключаться к ws://localhost:${PORT}`);
  console.log(`🌍 Web: http://localhost:${PORT}`);
});