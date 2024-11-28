import logging
import os
import time
import telebot
from contextlib import suppress
from http import HTTPStatus

import requests
import sys
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import APIStatusError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REQUIRED_TOKENS = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID'
]
REQUIRED_API_KEYS = [
    'homework_name',
    'status'

]

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов окружения."""
    missing_tokens = [
        name
        for name in REQUIRED_TOKENS
        if not globals()[name]
    ]

    if missing_tokens:
        message = (
            'Отсутствует обязательные ременные окружения: '
            + (', '.join(missing_tokens))
        )
        logging.critical(message)
        raise ValueError(message)

    logging.info('Все необходимые переменные окружения присутствуют.')


def send_message(bot, message):
    """Отправка сообщения на запрос."""
    logging.info('Отправляем сообщение.')

    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logging.debug('Сообщение отправлено.')


def get_api_answer(timestamp):
    """Запрос к API Практикума."""
    logging.info(
        f'Отправка запроса к API: {ENDPOINT}, '
        f'headers: {HEADERS}, params="from_date": {timestamp}'
    )
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        raise APIStatusError(f'Сбой запроса к API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise APIStatusError(
            'Ошибка запроса.'
            f'Статус-код: {response.status_code}. '
            f'Адрес запроса: {response.url}'
            f'Параметры ответа: {response.request}'
        )

    logging.info('Запрос выполнен успешно.')

    return response.json()


def check_response(response):
    """Проверка API на соответствие документации."""
    logging.info('Проверяем ответ от API.')

    if not isinstance(response, dict):
        raise TypeError(
            f'Полученный тип данных ({type(response)}) '
            'не соотвествует ожидаемому (dict)'
        )
    if 'homeworks' not in response:
        raise KeyError('Ключ "homeworks" отсутствует в ответе API.')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            f'Полученный тип данных ({type(response["homeworks"])})'
            'не соотвествует ожидаемому (list)'
        )
    logging.info('API соответствует документации.')


def parse_status(homework):
    """Сравнения статуса работы с значением из константы."""
    logging.info('Проверяем статус домашней работы.')

    # Ищем отсутствующие ключи
    missing_keys = [
        name
        for name in REQUIRED_API_KEYS
        if name not in homework
    ]

    # Проверяем наличие отсутствующих ключей
    if missing_keys:
        raise KeyError(
            f'Ответ API домашки не содержит необходимые ключи {missing_keys}'
        )

    homework_name = homework['homework_name']
    homework_status = homework['status']

    # Проверяем, что статус является одним из ожидаемых значений
    if homework_status not in HOMEWORK_VERDICTS.keys():
        raise ValueError(
            'Недокументированный статус '
            f'домашней работы: {homework_status}'
        )

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks']
            if not homework:
                logging.debug('Изменений статуса нет')
                continue

            new_message = parse_status(homework[0])
            if new_message != old_message:
                send_message(bot, new_message)
                old_message = new_message
            else:
                logging.info(
                    f'Новое сообщение: {new_message} '
                    f'идентично прошлому: {old_message}'
                )

        except (
            telebot.apihelper.ApiException,
            requests.exceptions.RequestException
        ) as error:
            logging.exception(
                f'Сбой при отправке сообщения в Telegram: {error}'
            )

        except Exception as error:
            logging.exception(f'Сбой в работе программы: {error}')

            new_message = f'Сбой в работе программы: {error}'
            if new_message != old_message:
                with suppress(
                    telebot.apihelper.ApiException,
                    requests.exceptions.RequestException
                ):
                    send_message(bot, new_message)
                    old_message = new_message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]-[%(funcName)s] %(message)s',
        level=logging.DEBUG,
        handlers=[logging.StreamHandler(stream=sys.stdout)]
    )
    logging.getLogger("requests").setLevel(logging.WARNING)
    main()
