# 🚀 XDPGuard Quick Start Guide

Быстрое развертывание за 5 минут!

## 📋 Минимальные требования

- Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Kali Linux
- Linux kernel 4.18+
- Root права (sudo)
- 2 GB RAM

## ⚡ Установка за 4 шага

### 1️⃣ Клонирование репозитория

```bash
cd /opt
sudo git clone https://github.com/chirkovap/xdpguard.git
cd xdpguard
```

### 2️⃣ Запуск установки

```bash
sudo chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

Скрипт автоматически:
- Установит все зависимости
- Скомпилирует XDP программу
- Настроит systemd сервис

### 3️⃣ Настройка интерфейса

```bash
# Узнайте ваш сетевой интерфейс
ip link show

# Отредактируйте конфигурацию
sudo nano /etc/xdpguard/config.yaml
```

Измените эти параметры:

```yaml
network:
  interface: ens33        # ← Замените на ваш интерфейс (eth0, ens3, и т.д.)
  xdp_mode: xdpgeneric   # ← Оставьте xdpgeneric для совместимости
```

Сохраните файл (Ctrl+O, Enter, Ctrl+X).

### 4️⃣ Запуск сервиса

```bash
# Запустите XDPGuard
sudo systemctl start xdpguard

# Проверьте статус
sudo systemctl status xdpguard

# Если всё ОК, должно показать:
# ● xdpguard.service - XDPGuard DDoS Protection System
#    Loaded: loaded
#    Active: active (running)
```

## ✅ Проверка работы

### Проверка 1: XDP загружен

```bash
sudo ip link show <ваш-интерфейс>
```

Должно показать `xdp` или `xdpgeneric` в выводе.

### Проверка 2: Веб-панель работает

```bash
# Проверьте API
curl http://localhost:8080/api/status

# Откройте в браузере
firefox http://localhost:8080
```

### Проверка 3: CLI инструменты

```bash
python3 /opt/xdpguard/cli.py status
```

## 🎯 Первые шаги

### Блокировка IP адреса

```bash
# Через CLI
python3 /opt/xdpguard/cli.py block 192.168.1.100

# Или через API
curl -X POST http://localhost:8080/api/block \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100"}'

# Или через веб-панель
http://localhost:8080 → введите IP → нажмите Block
```

### Просмотр статистики

```bash
# CLI
python3 /opt/xdpguard/cli.py status

# API
curl http://localhost:8080/api/status | python3 -m json.tool

# Веб-панель
http://localhost:8080
```

### Просмотр логов

```bash
# Real-time логи
sudo journalctl -u xdpguard -f

# Последние 50 строк
sudo journalctl -u xdpguard -n 50
```

## 🔧 Базовые настройки

### Изменение портов защиты

```bash
sudo nano /etc/xdpguard/config.yaml
```

```yaml
network:
  protected_ports:
    - 80    # HTTP
    - 443   # HTTPS
    - 22    # SSH
    - 3306  # MySQL (добавить)
    - 5432  # PostgreSQL (добавить)
```

Перезапустите:
```bash
sudo systemctl restart xdpguard
```

### Изменение лимитов rate limiting

```yaml
protection:
  syn_rate: 30      # SYN пакетов/сек на IP
  conn_rate: 100    # Новых соединений/сек на IP
  udp_rate: 50      # UDP пакетов/сек на IP
```

### Добавление whitelist IP

```yaml
whitelist_ips:
  - 127.0.0.1
  - 192.168.1.0/24    # ← Добавьте вашу сеть
  - 10.0.0.5          # ← Или конкретный IP
```

## 🐛 Решение проблем

### Проблема: Сервис не запускается

```bash
# Смотрите логи ошибок
sudo journalctl -u xdpguard -n 100 --no-pager

# Проверьте конфигурацию
sudo python3 -c "import yaml; yaml.safe_load(open('/etc/xdpguard/config.yaml'))"
```

### Проблема: XDP не загружается

```bash
# Проверьте, скомпилирована ли XDP программа
ls -la /usr/lib/xdpguard/xdp_filter.o

# Если нет, перекомпилируйте
cd /opt/xdpguard/bpf
sudo make clean && sudo make && sudo make install

# Убедитесь, что используете xdpgeneric режим
sudo nano /etc/xdpguard/config.yaml
# Измените: xdp_mode: xdpgeneric
sudo systemctl restart xdpguard
```

### Проблема: Веб-панель недоступна

```bash
# Проверьте, что порт открыт
sudo netstat -tlnp | grep 8080

# Откройте в firewall
sudo ufw allow 8080
# или
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### Проблема: "BTF is required"

```bash
# Используйте xdpgeneric режим (не требует BTF)
sudo nano /etc/xdpguard/config.yaml
# Измените: xdp_mode: xdpgeneric
sudo systemctl restart xdpguard
```

## 📊 Мониторинг

### Real-time мониторинг через веб-панель

Откройте `http://your-server-ip:8080`

Вы увидите:
- 📈 Статистику пакетов в реальном времени
- 🚫 Список заблокированных IP
- 💨 Throughput и drop rate
- ⚡ Быстрые действия (блокировка/разблокировка)

### Мониторинг через CLI

```bash
# Непрерывный мониторинг
watch -n 1 'python3 /opt/xdpguard/cli.py status'

# Или через API
watch -n 1 'curl -s http://localhost:8080/api/status | python3 -m json.tool'
```

### Проверка BPF статистики

```bash
# Показать загруженные BPF программы
sudo bpftool prog show

# Показать BPF карты
sudo bpftool map show

# Показать статистику сети
sudo bpftool net show
```

## 🎓 Следующие шаги

1. **Настройте автоматические уведомления** - см. [README.md](README.md)
2. **Интегрируйте с Prometheus/Grafana** - см. документацию
3. **Оптимизируйте для production** - см. [CONTRIBUTING.md](CONTRIBUTING.md)
4. **Попробуйте native режим (xdpdrv)** для большей производительности

## 💡 Полезные команды

```bash
# Перезапуск сервиса
sudo systemctl restart xdpguard

# Остановка сервиса
sudo systemctl stop xdpguard

# Просмотр конфигурации
cat /etc/xdpguard/config.yaml

# Экспорт статистики
python3 /opt/xdpguard/cli.py export -o stats.json

# Очистка счётчиков
python3 /opt/xdpguard/cli.py clear-rate-limits

# Список всех заблокированных IP
python3 /opt/xdpguard/cli.py list-blocked
```

## 📖 Дополнительная документация

- [README.md](README.md) - Полная документация
- [CONTRIBUTING.md](CONTRIBUTING.md) - Как внести вклад
- [GitHub Issues](https://github.com/chirkovap/xdpguard/issues) - Сообщить о проблеме

---

**Готово! Ваша система защищена от DDoS атак! 🛡️**

Если возникли проблемы, создайте [Issue](https://github.com/chirkovap/xdpguard/issues) с описанием и логами.
