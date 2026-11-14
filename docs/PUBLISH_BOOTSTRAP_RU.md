# Первая публикация подготовленного репозитория

Файлы репозитория подготовлены и проверены локально. Попытка записи через подключение GitHub вернула 403 Resource not accessible by integration. Через это подключение коммит не был создан. Для первой публикации используй свою авторизацию GitHub CLI в Ubuntu.

## Подготовка

Распакуй FlareLedger_Repository_Starter.zip. Внутри находятся START_HERE_RU.md и папка flareledger с полным набором файлов, включая скрытые .github, .gitignore и .env.example.

Если Git и gh ещё не установлены, выполни первый раздел [инструкции Ubuntu](SETUP_UBUNTU_RU.md). Далее:

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes repo,workflow
```

Введи показанный терминалом одноразовый код на [https://github.com/login/device](https://github.com/login/device), авторизовавшись как Denofix. После завершения:

```bash
gh auth setup-git
gh api user --jq .login
git config --global user.name "Denis Voloshyn"
git config --global user.email "108155470+Denofix@users.noreply.github.com"
git config --global init.defaultBranch main
git config --global pull.ff only
git config --global fetch.prune true
git config --global core.autocrlf input
```

## Отправка

В терминале перейди именно в распакованную папку flareledger и выполни:

```bash
bash scripts/publish_bootstrap.sh
```

Скрипт проверяет аккаунт Denofix, существование нужного remote, пустую удалённую историю и отсутствие локальных коммитов. Затем инициализирует main, добавляет только файлы из scripts/bootstrap-files.txt, запускает проверку, создаёт коммит от настроенного тобой автора и выполняет обычный push. Force push и приглашения участников скрипт не выполняет.

После успеха открой [репозиторий](https://github.com/Denofix/flareledger) и [Actions](https://github.com/Denofix/flareledger/actions). Удалённый запуск CI можно считать проверенным только после его фактического завершения на GitHub.

Если push отказал после создания локального коммита, исправь доступ и повтори сам push:

```bash
gh auth refresh --hostname github.com --scopes workflow
git push -u origin main
```

Не запускай повторную инициализацию поверх существующей истории. Если main уже появилась из чужого коммита, скрипт остановится: сначала клонируй актуальный репозиторий и перенеси нужные изменения через обычный PR.

## Следующие действия

1. Добавь подтверждённые аккаунты Тимофея, Саята и Ивана по разделу 5 инструкции Ubuntu.
2. Проверь первый CI и включи правила main по разделу 6.
3. Назначь первые PR на backend, frontend, импорт данных и инфраструктуру.
4. Получи у Тимофея параметры QResto и выбери схему подключения flareledger.fun по [инструкции домена](DOMAIN_SETUP_RU.md).
