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
        if (globals()[name] is None)
        or (globals()[name] == '')
    ]

    if len(missing_tokens) != 0:
        logging.critical(
            f'Отсутствует обязательные переменные окружения: {missing_tokens}'
        )
        raise ValueError(
            f'Отсутствует обязательные переменные окружения: {missing_tokens}'
        )

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
    logging.info(f'Отправка запроса к API: {ENDPOINT}')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        raise APIStatusError(f'Сбой запроса к API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise APIStatusError

    logging.info('Запрос выполнен успешно.')

    return response.json()


def check_response(response):
    """Проверка API на соответствие документации."""
    logging.info('Проверяем ответ от API.')

    if not isinstance(response, dict):
        raise TypeError(
            f'Полученный тип данных({type(response)}) '
            'не соотвествует ожидаемому'
        )
    if 'homeworks' not in response:
        raise KeyError('Ключ "homeworks" отсутствует в ответе API.')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Полученный тип данных(' + str(type(response['homeworks'])) + ') '
            'не соотвествует ожидаемому'
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
    if len(missing_keys) != 0:
        raise KeyError(
            f'Ответ API домашки не содержит необходимые ключи {missing_keys}'
        )

    # Проверяем, что статус является одним из ожидаемых значений
    if homework['status'] not in HOMEWORK_VERDICTS.keys():
        raise ValueError(
            'Недокументированный статус '
            'домашней работы: ' + str(homework['status'])
        )

    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]

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
            if homework:
                new_message = parse_status(homework[0])
                if new_message != old_message:
                    send_message(bot, new_message)
                    old_message = new_message
            else:
                logging.debug('Изменений статуса нет')
                continue
        except telebot.apihelper.ApiException as error:
            logging.exception(f'Сбой в работе программы: {error}')
        except requests.exceptions.RequestException as error:
            logging.exception(f'Сбой в работе программы: {error}')
        except Exception as error:
            logging.exception(f'Сбой в работе программы: {error}')

            new_message = f'Сбой в работе программы: {error}'
            if new_message != old_message:
                with suppress(Exception):
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
