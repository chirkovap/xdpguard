# XDPGuard - XDP/eBPF DDoS Protection System

⚡ **Высокопроизводительная система защиты от DDoS атак на базе XDP/eBPF для Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Linux-blue.svg)](https://www.linux.org/)
[![Kernel](https://img.shields.io/badge/kernel-4.18+-green.svg)](https://www.kernel.org/)

## 🚀 Возможности

- ⚡ **Экстремальная производительность** - фильтрация до 26 млн пакетов/сек благодаря XDP
- 🛡️ **Многоуровневая защита** - SYN flood, UDP flood, ICMP flood, Connection flood
- 🎯 **Умная блокировка** - Автоматическое обнаружение и блокировка атак
- 📊 **Веб-панель управления** - Красивый веб-интерфейс с real-time статистикой
- 💻 **CLI инструменты** - Полный набор команд для управления
- 🔧 **Гибкая настройка** - YAML конфигурация с множеством параметров
- 🐧 **Поддержка Linux** - Ubuntu, Debian, CentOS, RHEL, Fedora
- 🔄 **Режимы работы** - Router и Bridge mode
- 📈 **Статистика** - Детальная статистика трафика и атак

## 📋 Требования

- **Linux** kernel 4.18+ (рекомендуется 5.4+)
- **Поддерживаемые ОС:**
  - Ubuntu 20.04+
  - Debian 11+
  - CentOS 8+
  - RHEL 8+
  - Fedora 32+
  - Kali Linux
- **Зависимости:**
  - clang/LLVM
  - libbpf
  - Python 3.8+
  - iproute2
  - bpftool
- **Память:** минимум 2 GB RAM
- **Root права** для загрузки XDP программ

## 📦 Быстрая установка

### Автоматическая установка

```bash
# Клонируйте репозиторий
git clone https://github.com/chirkovap/xdpguard.git
cd xdpguard

# Запустите установочный скрипт
sudo bash scripts/install.sh

# Настройте конфигурацию
sudo nano /etc/xdpguard/config.yaml
# ВАЖНО: Измените 'interface' на ваш сетевой интерфейс (узнать: ip link show)

# Запустите сервис
sudo systemctl start xdpguard
sudo systemctl status xdpguard
```

### Ручная установка

```bash
# 1. Установите зависимости

# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip clang llvm libelf-dev libbpf-dev make git curl iproute2 linux-tools-common
sudo apt install -y python3-flask python3-yaml python3-click python3-requests python3-psutil

# CentOS/RHEL/Fedora
sudo yum install -y python3 python3-pip clang llvm elfutils-libelf-devel libbpf-devel make git curl iproute bpftool
sudo yum install -y python3-flask python3-pyyaml python3-click python3-requests python3-psutil

# 2. Клонируйте репозиторий
git clone https://github.com/chirkovap/xdpguard.git
cd xdpguard

# 3. Скомпилируйте XDP программу
cd bpf
sudo make clean
sudo make
sudo make install
cd ..

# 4. Настройте систему
sudo mkdir -p /etc/xdpguard /var/lib/xdpguard /var/log
sudo cp config.yaml /etc/xdpguard/

# ВАЖНО: Отредактируйте конфиг!
sudo nano /etc/xdpguard/config.yaml
# Измените:
# - interface: на ваш интерфейс (найти: ip link show)
# - xdp_mode: xdpgeneric (для совместимости)

# 5. Установите сервис
sudo cp -r python web daemon.py cli.py /opt/xdpguard/
sudo cp systemd/xdpguard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xdpguard
sudo systemctl start xdpguard
```

## ⚙️ Настройка

### Основные параметры конфигурации

Откройте `/etc/xdpguard/config.yaml`:

```yaml
network:
  interface: eth0           # ← Ваш сетевой интерфейс
  xdp_mode: xdpgeneric     # xdpgeneric (совместимость) или xdpdrv (производительность)
  
protection:
  enabled: true
  syn_rate: 30             # SYN пакетов/сек на IP
  conn_rate: 100           # Новых соединений/сек на IP
  udp_rate: 50             # UDP пакетов/сек на IP

blacklist:
  enabled: true
  auto_block_threshold: 1000  # Автоблокировка при превышении
  block_duration: 3600        # Длительность блокировки (секунды)

web:
  host: 0.0.0.0
  port: 8080
  secret_key: "измените-этот-ключ"  # ← Обязательно измените!
```

### Режимы загрузки XDP

```yaml
network:
  xdp_mode: xdpgeneric  # или xdpdrv, или xdpoffload
```

- **xdpgeneric** - Generic/SKB mode (самый совместимый, работает всегда)
- **xdpdrv** - Native driver mode (быстрый, требует поддержки драйвера)
- **xdpoffload** - Hardware offload (самый быстрый, требует поддержки NIC)

**Рекомендация:** Начните с `xdpgeneric`, затем попробуйте `xdpdrv`.

## 🎮 Использование

### Веб-панель управления

Откройте в браузере:
```
http://your-server-ip:8080
```

Возможности панели:
- 📊 Real-time статистика пакетов
- 🚫 Блокировка/разблокировка IP адресов
- 📋 Список заблокированных IP
- ⚙️ Управление настройками
- 📈 Графики трафика

### CLI команды

```bash
# Проверить статус
python3 /opt/xdpguard/cli.py status

# Заблокировать IP
python3 /opt/xdpguard/cli.py block 192.168.1.100

# Разблокировать IP
python3 /opt/xdpguard/cli.py unblock 192.168.1.100

# Список заблокированных IP
python3 /opt/xdpguard/cli.py list-blocked

# Очистить счётчики rate limit
python3 /opt/xdpguard/cli.py clear-rate-limits

# Экспорт статистики
python3 /opt/xdpguard/cli.py export -o stats.json
```

### Systemd команды

```bash
# Запуск
sudo systemctl start xdpguard

# Остановка
sudo systemctl stop xdpguard

# Перезапуск
sudo systemctl restart xdpguard

# Статус
sudo systemctl status xdpguard

# Логи
sudo journalctl -u xdpguard -f

# Автозапуск
sudo systemctl enable xdpguard
```

## 🔍 Проверка работоспособности

```bash
# 1. Проверьте, что сервис запущен
sudo systemctl status xdpguard

# 2. Проверьте, что XDP загружен на интерфейсе
sudo ip link show <your-interface> | grep xdp
# Должно показать "xdp" или "xdpgeneric"

# 3. Проверьте BPF программы
sudo bpftool prog show
# Должна быть программа типа xdp

# 4. Проверьте BPF карты
sudo bpftool map show
# Должны быть карты: blacklist, rate_limit, stats_map

# 5. Проверьте статистику вручную
sudo bpftool map dump name stats_map
# Должны быть ненулевые значения packets_total при наличии трафика

# 6. Проверьте веб-интерфейс
curl http://localhost:8080/api/status

# 7. Проверьте сеть
sudo bpftool net show
```

## 📊 Производительность

| Режим | Производительность | Совместимость | Использование |
|-------|-------------------|---------------|---------------|
| **xdpgeneric** | ~1-2 Mpps | ✅ Все системы | Тестирование, совместимость |
| **xdpdrv** | ~10-20 Mpps | ⚠️ Требует драйвер | Production (рекомендуется) |
| **xdpoffload** | ~26+ Mpps | ❌ Требует NIC | High-load production |

## 🛠️ Устранение проблем

### XDP не загружается

```bash
# Проверьте, что XDP программа скомпилирована
ls -la /usr/lib/xdpguard/xdp_filter.o

# Если нет, перекомпилируйте:
cd /opt/xdpguard/bpf
sudo make clean && sudo make && sudo make install

# Попробуйте загрузить в generic режиме
sudo nano /etc/xdpguard/config.yaml
# Измените: xdp_mode: xdpgeneric
sudo systemctl restart xdpguard
```

### Ошибка BTF

```bash
# Установите bpftool
sudo apt install linux-tools-$(uname -r) linux-tools-common

# Или загрузите в generic режиме (не требует BTF)
sudo ip link set dev <interface> xdpgeneric obj /usr/lib/xdpguard/xdp_filter.o sec xdp
```

### Сервис не запускается

```bash
# Проверьте логи
sudo journalctl -u xdpguard -n 100 --no-pager

# Проверьте конфигурацию
sudo python3 -c "import yaml; yaml.safe_load(open('/etc/xdpguard/config.yaml'))"

# Проверьте интерфейс
ip link show
```

### Веб-панель недоступна

```bash
# Проверьте, что Flask работает
sudo netstat -tlnp | grep 8080

# Проверьте firewall
sudo ufw status
sudo ufw allow 8080

# Или для firewalld
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### Статистика показывает 0

```bash
# Проверьте что XDP загружен
sudo bpftool prog show | grep xdp

# Проверьте статистику напрямую из BPF карты
sudo bpftool map dump name stats_map

# Должны быть ненулевые значения на одном из CPU
# Если есть - обновите код до последней версии:
cd /opt/xdpguard
sudo git pull origin main
sudo rm -rf python/__pycache__
sudo systemctl restart xdpguard
```

### Блокировка IP не работает

```bash
# Проверьте карту blacklist
sudo bpftool map show | grep blacklist

# Попробуйте добавить IP вручную
sudo bpftool map update name blacklist key hex c0 a8 01 64 value hex 01
# (для IP 192.168.1.100: c0=192, a8=168, 01=1, 64=100)

# Проверьте что IP добавлен
sudo bpftool map dump name blacklist
```

## 📚 Документация

- [Архитектура системы](docs/architecture.md)
- [Руководство по настройке](docs/configuration.md)
- [API документация](docs/api.md)
- [Разработка и вклад](CONTRIBUTING.md)
- [Быстрый старт](QUICKSTART.md)

## 🤝 Вклад в проект

Мы приветствуем любой вклад! См. [CONTRIBUTING.md](CONTRIBUTING.md)

### Приоритетные задачи

- [ ] IPv6 поддержка
- [ ] Prometheus/Grafana интеграция
- [ ] Telegram/Email уведомления
- [ ] Geo-IP фильтрация
- [ ] Unit тесты
- [ ] Docker контейнер
- [ ] Helm chart для Kubernetes

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE)

## 👨‍💻 Автор

**chirkovap**

- GitHub: [@chirkovap](https://github.com/chirkovap)
- Проект: [XDPGuard](https://github.com/chirkovap/xdpguard)

## 🙏 Благодарности

- Linux Kernel BPF команда
- IOVisor Project (BCC)
- Cloudflare (за вдохновение архитектурой)
- Сообщество eBPF

## 📧 Поддержка

Если у вас возникли проблемы или вопросы:

1. Проверьте [Issues](https://github.com/chirkovap/xdpguard/issues)
2. Создайте новый Issue с подробным описанием
3. Приложите логи: `sudo journalctl -u xdpguard -n 100`

---

⭐ **Если проект был полезен, поставьте звёздочку!**
