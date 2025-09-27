# Terminal Chat App (Python + asyncio)

## Descripción
Este proyecto implementa un sistema de chat multiusuario en terminal usando Python 3 y asyncio.  
Incluye dos componentes principales:

- **Servidor (`server.py`)**: recibe conexiones de múltiples clientes, gestiona los apodos, mensajes públicos, privados y eventos. Muestra en consola todo lo que ocurre (conexiones, comandos, mensajes, errores) y, opcionalmente, puede guardar toda la sesión en un archivo.
- **Cliente (`client.py`)**: aplicación de terminal que permite conectarse al servidor, elegir un apodo y participar en el chat en tiempo real.

El chat funciona sobre TCP puro (no HTTP), lo que lo hace ligero, rápido y fácil de usar en redes locales o a través de Internet (con IP pública o VPS).
```

## Uso

### Servidor
Por defecto escucha en 0.0.0.0:5555.

- Ejecutar sin guardar sesión:
```bash
./server.py
```

- Ejecutar guardando todo lo que ocurre en un archivo (JSON Lines):
```bash
./server.py --save chat_session.jsonl
```

El servidor siempre muestra los eventos en la terminal y, si se usa `--save`, también los guarda en el archivo indicado.

### Cliente
Conectar a un servidor:
```bash
./client.py --host 127.0.0.1 --port 5555 --nick Johan
```

- `--host`: IP del servidor (ej. `192.168.0.10` en LAN o IP pública de un VPS).  
- `--port`: puerto del servidor (por defecto 5555).  
- `--nick`: apodo inicial (opcional, también se puede poner con `/nick`).  

Ejemplo con dos clientes en la misma máquina:
```bash
./client.py --host 127.0.0.1 --port 5555 --nick Juan
./client.py --host 127.0.0.1 --port 5555 --nick José
```

## Comandos disponibles
Dentro del cliente puedes usar:

- **`/nick <nombre>`** → Define o cambia el apodo.  
- **`/list`** → Lista de usuarios conectados.  
- **`/msg <usuario> <texto>`** → Envía un mensaje privado a un usuario.  
- **`/me <acción>`** → Envía un mensaje de acción (ej: `/me saluda`).  
- **`/quit`** → Desconectarse del chat.  
- **`/help`** → Mostrar ayuda de comandos.  

Cualquier texto que escribas sin `/` se envía al chat público.

## Funcionamiento interno

### Flujo del servidor
1. Acepta conexiones TCP en el puerto 5555.  
2. Envía un mensaje de bienvenida a cada cliente.  
3. Gestiona comandos (`/nick`, `/list`, `/msg`, etc.) y mensajes normales.  
4. Difunde mensajes públicos a todos los clientes (broadcast).  
5. Registra absolutamente todo lo que ocurre en consola y, si está activado, en archivo.  
6. Maneja desconexiones y limpia los usuarios automáticamente.  

### Flujo del cliente
1. Abre conexión TCP al servidor.  
2. Lanza dos tareas:  
   - Una lee el teclado y envía los mensajes/comandos.  
   - Otra escucha al servidor y muestra los mensajes recibidos.  
3. Mantiene la sesión activa hasta que el usuario escriba `/quit` o el servidor cierre la conexión.  

## Escenarios de red
- **LAN/WiFi local**: todos los clientes en la misma red → usar IP privada del servidor (`192.168.x.x`).  
- **Internet (remoto)**:  
  - Servidor con IP pública o VPS.  
  - Puerto 5555 abierto en firewall/router.  
  - Clientes conectan con la IP pública del servidor.  

## Registro de sesiones
- En consola: siempre se muestra todo en tiempo real.  
- En archivo (`--save`): se guarda en formato JSON Lines (`.jsonl`), ideal para análisis con `jq`, Python o sistemas de logging.  

Ejemplo:
```json
{"ts": "2025-09-26T23:00:00Z", "level": "INFO", "msg": "Nick set", "meta": {"new": "Johan"}}
{"ts": "2025-09-26T23:00:05Z", "level": "INFO", "msg": "Public message", "meta": {"from": "Johan", "len": 12, "preview": "Hola a todos"}}
```

