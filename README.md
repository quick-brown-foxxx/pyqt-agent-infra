# vagrant-qt-proto

Минимальный прототип для проверки тестовой инфраструктуры Qt/PySide6 в headless VM.

## Требования

- Vagrant + VirtualBox
- `make`

## Быстрый старт

```bash
make up           # поднять VM, ~10 мин первый раз
make test         # быстрые тесты (offscreen)
make test-full    # полные тесты с AT-SPI и scrot
make screenshot   # скриншот текущего экрана VM
```

## Структура

```
.
├── Vagrantfile          # Ubuntu 22.04, 2GB RAM, headless
├── provision.sh         # Xvfb, PySide6, AT-SPI, PulseAudio
├── pytest.ini
├── app/
│   └── main.py          # PySide6 приложение (1 файл)
├── tests/
│   └── test_main.py     # pytest-qt + AT-SPI smoke + screenshot
├── scripts/
│   ├── vm-run.sh        # выполнить команду в VM (ControlMaster)
│   └── screenshot.sh    # скриншот VM → хост
└── Makefile
```

## Что проверяем

| Тест | Что валидирует |
|------|----------------|
| `test_initial_state` | pytest-qt baseline |
| `test_add_item` | state transitions |
| `test_atspi_accessibility_tree` | AT-SPI виден в Xvfb |
| `test_screenshot_via_scrot` | scrot видит Xvfb |
| `test_widget_grab` | Qt-internal fallback |

## Workflow агента (вариант Б)

Агент работает на хосте, VM только execution environment:

```bash
./scripts/vm-run.sh "pytest /vagrant/tests/ -v"
./scripts/screenshot.sh ./debug/after_action.png
```
