# Старт Дениса в Ubuntu VM

Эта инструкция подготавливает рабочую VM, Git и доступ команды к [Denofix/flareledger](https://github.com/Denofix/flareledger). Выполняй команды в терминале Ubuntu. Репозиторий сейчас содержит документацию и структуру; запуск приложения станет следующим этапом после появления исходников и зависимостей.

## 1 Установи Git и официальный GitHub CLI

Проверь уже установленные версии:

```bash
git --version
gh --version
```

Если gh отсутствует или установлен старый пакет из Ubuntu, подключи официальный репозиторий GitHub CLI:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /tmp/flareledger-githubcli-keyring.gpg
sudo install -m 0644 /tmp/flareledger-githubcli-keyring.gpg /etc/apt/keyrings/githubcli-archive-keyring.gpg
printf '%s\n' "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install -y gh
gh --version
```

Источник установки: [официальная инструкция GitHub CLI](https://github.com/cli/cli/blob/trunk/docs/install_linux.md). Если загрузка keyring завершилась ошибкой, сначала исправь её и затем продолжай установку.

## 2 Войди через одноразовый код

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes repo,workflow
```

Терминал покажет одноразовый код. Открой [https://github.com/login/device](https://github.com/login/device) в браузере Windows или Ubuntu, войди как Denofix, введи этот код и подтверди вход GitHub CLI. Вернись в терминал и дождись успешного завершения. Если браузер внутри VM не открылся, используй ту же ссылку в Windows. Код создаётся этой командой на твоей VM; заранее подготовленного кода нет.

Затем:

```bash
gh auth setup-git
gh auth status
gh api user --jq .login
```

Последняя команда должна показать Denofix. Scope workflow нужен для отправки изменений в .github/workflows через HTTPS. Если вход уже выполнен, но прав на workflow не хватает:

```bash
gh auth refresh --hostname github.com --scopes workflow
```

Участники команды входят в собственные аккаунты. Одноразовые коды, токены и файлы авторизации в общий чат не отправляются.

## 3 Настрой автора коммитов

Для твоего аккаунта Denofix:

```bash
git config --global user.name "Denis Voloshyn"
git config --global user.email "108155470+Denofix@users.noreply.github.com"
git config --global init.defaultBranch main
git config --global pull.ff only
git config --global fetch.prune true
git config --global core.autocrlf input
git config --global core.editor nano
```

Адрес выше использует GitHub noreply-формат и ID твоего аккаунта. Свой предпочитаемый адрес можно сверить в [Settings → Emails](https://github.com/settings/emails). Остальные участники указывают собственные имя и email.

Проверка:

```bash
git config --global --get user.name
git config --global --get user.email
git config --global --get pull.ff
```

Вход gh даёт доступ к GitHub, а user.name и user.email задают автора коммитов. Обе настройки нужны.

## 4 Склонируй подготовленный репозиторий

Если удалённый репозиторий ещё пустой и у тебя скачан стартовый архив, сначала выполни [первую публикацию](PUBLISH_BOOTSTRAP_RU.md). После неё main станет доступна для клонирования всей командой. Этот этап нужен потому, что подключение GitHub в чате отклонило создание коммита с ошибкой 403.

```bash
mkdir -p ~/projects
cd ~/projects
gh repo clone Denofix/flareledger
cd flareledger
git switch main
git pull --ff-only origin main
git status --short --branch
python3 scripts/check_repository.py
```

Если папка с этим клоном уже существует, перейди в неё и выполни команды начиная с git switch main. При незакоммиченных изменениях сначала сохрани свою работу; не сбрасывай её ради обновления.

Основные документы: [README](../README.md), [правила команды](../TEAM_RULES.md), [контракт](TECHNICAL_CONTRACT.md), [ближайшие задачи](ROADMAP.md).

## 5 Добавь команду

Открой [Settings → Collaborators](https://github.com/Denofix/flareledger/settings/access), нажми Add people и отправь приглашения по точным GitHub username.

| Участник | Что использовать |
| --- | --- |
| Саят | sayat228, после подтверждения им этого аккаунта |
| Тимофей | Сначала получить его точный GitHub username |
| Иван | Сначала получить его точный GitHub username |

Через CLI можно добавить одного проверенного участника следующим образом. Сначала введи username и проверь профиль:

```bash
read -r -p "GitHub username участника: " FL_TEAM_LOGIN
gh api "users/$FL_TEAM_LOGIN" --jq '{login: .login, profile: .html_url}'
```

Когда убедился, что это нужный человек, отправь приглашение:

```bash
gh api --method PUT "repos/Denofix/flareledger/collaborators/$FL_TEAM_LOGIN"
```

Повтори для каждого участника. Им нужно принять приглашение в GitHub или по письму. Проверить ожидание и принятый доступ:

```bash
gh api --paginate repos/Denofix/flareledger/invitations --jq '.[] | {login: .invitee.login, permissions: .permissions}'
gh api --paginate repos/Denofix/flareledger/collaborators --jq '.[] | {login: .login, push: .permissions.push}'
```

Это личный репозиторий Denofix: collaborator получает доступ на чтение и запись. Тимофей сможет отправлять код и workflow-файлы, а административные настройки и secrets задаёшь ты как владелец. Гибкие роли Maintain/Admin относятся к репозиториям организаций; переносить проект в организацию для начала работы не требуется.

Автоматическая рассылка приглашений из этого документа не выполняется. Перед отправкой нужны подтверждённые аккаунты участников.

## 6 Включи правила main

Открой [Settings → Rules → Rulesets](https://github.com/Denofix/flareledger/settings/rules). Создай активный branch ruleset для main:

1. Require a pull request before merging.
2. Один approval от другого участника.
3. Require conversation resolution.
4. Запрет удаления ветки и force push.
5. После первого успешного запуска CI добавь обязательный check с именем Repository checks.

Проверь первый запуск на [Actions](https://github.com/Denofix/flareledger/actions). Сейчас он проверяет документы и структуру. Сборка backend/frontend будет добавлена Тимофеем после появления реального кода, lock-файла и команд проверок.

Не включай обязательное code-owner approval, пока в CODEOWNERS указан только ты: PR от тебя должен иметь возможность получить review другого участника. После подтверждения команды можно дополнить CODEOWNERS.

Эти правила описаны в репозитории; включение GitHub ruleset выполняет владелец в Settings. В [Actions settings](https://github.com/Denofix/flareledger/settings/actions) проверь, что разрешены используемые GitHub Actions. Для текущего CI секреты и доступ к серверу не нужны.

## 7 Начинай работу через ветку и PR

```bash
git switch main
git pull --ff-only origin main
git switch -c docs/denis-setup
```

Измени нужные файлы, затем:

```bash
python3 scripts/check_repository.py
git diff --check
git add -p
git diff --cached
git commit -m "docs: clarify project setup"
git push -u origin HEAD
gh pr create --base main --fill
gh pr checks --watch
```

Новые файлы добавляй отдельной командой git add с их путями: git add -p выбирает изменения в уже отслеживаемых файлах. Для Тимофея подходит ветка infra/docker-ci, для backend — feat/backend-scaffold, для frontend — feat/frontend-shell.

## 8 Что настроить дальше

| Приоритет | Действие | Что получить |
| --- | --- | --- |
| Сейчас | Войти в GitHub, настроить автора, клонировать main | Готовое рабочее место |
| Сейчас | Получить username, отправить приглашения, включить ruleset | Командный доступ и PR-процесс |
| Следующий PR | Запускаемые backend и frontend | Настоящие зависимости, lock-файл и проверенные команды |
| Следующий PR | Передать и проверить NASA JSON | Контролируемый источник данных для импортера |
| Параллельно | Запросить у Тимофея аудит QResto | IP, доступ, ресурсы, действующий ingress и право размещения |
| После выбора хостинга | Подключить flareledger.fun | Проверенные DNS, HTTPS и доступный сайт |
| После работающего каталога | Проверить бесплатный LLM API | Provider, точная модель, квота и поведение при отказе |

Проверь доступные инструменты VM перед первым PR с приложением:

```bash
python3 --version
node --version
npm --version
docker --version
docker compose version
```

Цель проекта — Python 3.12 и проверенный Node 24. Файлы .python-version и .nvmrc фиксируют цель, но сами ничего не устанавливают. Установка Docker при необходимости: [официальная инструкция для Ubuntu](https://docs.docker.com/engine/install/ubuntu/). Уже работающий Docker достаточно проверить; его переустановка для подготовки Git не нужна.

Пока в backend нет исходников и requirements, а во frontend нет package.json и lock-файла, команды запуска приложения недоступны. README и технический контракт честно фиксируют этот этап. Никаких дополнительных покупок для подготовки репозитория не требуется.

## Официальные справки

- [GitHub CLI login](https://cli.github.com/manual/gh_auth_login)
- [Приглашение collaborators](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)
- [Права в личном репозитории](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
- [API управления collaborators](https://docs.github.com/en/rest/collaborators/collaborators)
