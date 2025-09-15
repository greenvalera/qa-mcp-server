# Віддалене підключення до MCP сервера

Цей документ описує HTTP API спосіб підключення Cursor до MCP сервера, який запущений на віддаленому хості.

## HTTP/JSON-RPC підключення

Найпростіший та найнадійніший спосіб для віддаленого підключення.

#### Налаштування на сервері

1. Запустіть MCP сервер з HTTP API:
```bash
# Через Docker
docker compose up -d

# Або локально
python -m app.http_api
```

2. Перевірте що сервер працює:
```bash
curl http://your-server:3000/health
```

#### Налаштування в Cursor

1. Створіть конфігурацію `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "qa-search-remote": {
      "url": "http://your-server:3000/jsonrpc",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
```

2. Перезапустіть Cursor

#### Автоматичне налаштування

Використовуйте скрипт для автоматичного налаштування:
```bash
./scripts/setup_remote_connection.sh --host your-server --type http --generate-config
```

## Тестування підключення

### Автоматичне тестування

```bash
# Тест HTTP підключення
./scripts/setup_remote_connection.sh --host your-server --test-connection
```

### Ручне тестування

```bash
# Тест HTTP endpoint
curl http://your-server:3000/health

# Тест JSON-RPC
curl -X POST http://your-server:3000/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

## Налаштування продакшн сервера

### Автоматичне налаштування

```bash
# Базове налаштування
sudo ./scripts/setup_production_server.sh \
  --port 3000 \
  --systemd \
  --firewall

# З SSL та Nginx
sudo ./scripts/setup_production_server.sh \
  --ssl \
  --ssl-cert /path/to/cert.pem \
  --ssl-key /path/to/key.pem \
  --reverse-proxy \
  --nginx-config

# Повне налаштування
sudo ./scripts/setup_production_server.sh \
  --port 3000 \
  --systemd \
  --firewall \
  --reverse-proxy \
  --nginx-config \
  --monitoring \
  --backup
```

### Ручне налаштування

#### 1. Systemd сервіс

Створіть файл `/etc/systemd/system/qa-mcp-server.service`:
```ini
[Unit]
Description=QA MCP Server
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/qa_mcp
User=your-user
Group=your-group
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активуйте сервіс:
```bash
sudo systemctl daemon-reload
sudo systemctl enable qa-mcp-server
sudo systemctl start qa-mcp-server
```

#### 2. Nginx конфігурація

Створіть файл `/etc/nginx/sites-available/qa-mcp-server`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Активуйте конфігурацію:
```bash
sudo ln -s /etc/nginx/sites-available/qa-mcp-server /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 3. Firewall

```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3000/tcp
sudo ufw enable
```

## Безпека

### SSL/TLS

Для продакшн використовуйте SSL сертифікати:

```bash
# З Let's Encrypt
sudo certbot --nginx -d your-domain.com

# Або з власними сертифікатами
sudo ./scripts/setup_production_server.sh \
  --ssl \
  --ssl-cert /path/to/cert.pem \
  --ssl-key /path/to/key.pem
```

### Аутентифікація

Для додаткової безпеки додайте аутентифікацію в Nginx:

```nginx
location / {
    auth_basic "QA MCP Server";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://localhost:3000;
    # ... інші proxy налаштування
}
```

Створіть файл паролів:
```bash
sudo htpasswd -c /etc/nginx/.htpasswd username
```

### VPN

Для максимальної безпеки використовуйте VPN:
- OpenVPN
- WireGuard
- Tailscale

## Моніторинг

### Автоматичний моніторинг

```bash
# Налаштуйте моніторинг
sudo ./scripts/setup_production_server.sh --monitoring

# Перевірте логи
tail -f /var/log/qa-mcp-monitor.log
```

### Ручний моніторинг

```bash
# Статус контейнерів
docker compose ps

# Логи сервісів
docker compose logs -f

# Статус systemd сервісу
systemctl status qa-mcp-server

# Статус Nginx
systemctl status nginx
```

## Бекапи

### Автоматичні бекапи

```bash
# Налаштуйте автоматичні бекапи
sudo ./scripts/setup_production_server.sh --backup

# Створіть бекап вручну
./scripts/backup_database.sh

# Відновіть з бекапу
./scripts/restore_database.sh backups/qa_backup_20241201_120000.tar.gz
```

### Ручні бекапи

```bash
# MySQL бекап
docker compose exec mysql mysqldump -u root -proot --all-databases > backup.sql

# Qdrant бекап
docker compose exec qdrant tar -czf - /qdrant/storage > qdrant_backup.tar.gz
```

## Troubleshooting

### Проблеми з підключенням

1. **"Connection refused"**
   - Перевірте що сервер запущений: `docker compose ps`
   - Перевірте firewall: `sudo ufw status`
   - Перевірте порт: `netstat -tlnp | grep 3000`

2. **"Timeout"**
   - Перевірте мережеве підключення
   - Перевірте логи сервера: `docker compose logs`

3. **"SSL/TLS errors"**
   - Перевірте сертифікати
   - Перевірте дати сертифікатів
   - Перевірте Nginx конфігурацію

### Проблеми з Cursor

1. **"No tools or prompts"**
   - Перевірте конфігурацію `~/.cursor/mcp.json`
   - Перезапустіть Cursor
   - Перевірте логи Cursor

2. **"Method not found"**
   - Перевірте що MCP сервер працює
   - Перевірте версію MCP протоколу
   - Перевірте список доступних інструментів

### Логи та діагностика

```bash
# Логи Docker контейнерів
docker compose logs mcp-server
docker compose logs mysql
docker compose logs qdrant

# Логи systemd сервісу
journalctl -u qa-mcp-server -f

# Логи Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Мережеві з'єднання
netstat -tlnp | grep 3000
ss -tlnp | grep 3000
```

## Приклади конфігурацій

### Мінімальна конфігурація

```json
{
  "mcpServers": {
    "qa-search": {
      "url": "http://192.168.1.100:3000/jsonrpc",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
```


### Конфігурація з SSL

```json
{
  "mcpServers": {
    "qa-search": {
      "url": "https://your-domain.com/jsonrpc",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }
}
```

## Підтримка

Якщо у вас виникли проблеми:

1. Перевірте логи сервера
2. Перевірте мережеве підключення
3. Перевірте конфігурацію Cursor
4. Спробуйте різні методи підключення
5. Зверніться до документації MCP протоколу
