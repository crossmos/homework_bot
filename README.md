# FriednsWishesBot
Telegram-бот (pyTelegramBotAPI), который помогает отслеживать статус проекта отправленного на проверку на ЯндексПрактикуме. Бот отправляет запрос (requests) к API Яндекс Домашка, чтобы узнать статус.

## Используемый стэк
1. requests
2. pyTelegramBot

## Как запустить проект
1. Создать бот через @BotFather и получить токен этого бота
2. В корневой директории проекта создать файл ".env" и заполнить его
```
PRACTICUM_TOKEN=YOUR_TOKEN
TELEGRAM_TOKEN = YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID = YOUR_TELEGRAM_ID
```
3. Выполнить команду
4. Установить и запустить вирутальное окружение
```
python -m venv venv
```
```
source venv/Scripts/activate
```
или
```
python3 -m venv venv
```
```
source venv/bin/activate
```
5. Установить зависимости из файла "requirements.txt"
```
pip install -r requirements.txt
```
6. Запустить скрипт homework.py
```
python homework.py
```
или
```
cd bot/
```
```
python3 homework.py
```
7. Откройте своего бота и введите команду /start
