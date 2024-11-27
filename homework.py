import logging
import os
import requests
import time

from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s %(levelname)s  %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
DELAY_PERIOD = 86400
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов окружения."""
    required_env_vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

    for env_var in required_env_vars:
        if env_var is None:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {env_var}'
            )
            return False

    logger.info('Все необходимые переменные окружения присутствуют.')
    return True


def send_message(bot, message):
    """Отправка сообщения на запрос."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Отправляем сообщение')
    except Exception as error:
        print(f'Не удалось отправить сообщение в Telegram: {error}')
        logger.error(f'Не удалось отправить сообщение в Telegram: {error}')


def get_api_answer(timestamp):
    """Запрос к API Практикума."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        logger.info(f'Отправка запроса к API: {ENDPOINT}')
    except requests.RequestException:
        logger.error(f'API: {ENDPOINT} недоступен')

    if response.status_code != 200:
        logger.error(
            f'Ошибка запроса: статус-код {response.status_code}. '
            'Ответ сервера: {response.text}'
        )
        raise Exception(
            f'Ошибка запроса: статус-код {response.status_code}. '
            'Ответ сервера: {response.text}'
        )

    logger.info('Запрос выполнен успешно.')

    response = response.json()
    return response


def check_response(response):
    """Проверка API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Полученный тип данных не соотвествует ожидаемому')
    elif 'homeworks' not in response:
        raise KeyError('Ключ "homeworks" отсутствует в ответе API.')
    elif not isinstance(response['homeworks'], list):
        raise TypeError('Полученный тип данных не соотвествует ожидаемому')
    try:
        homework = response['homeworks']
        logger.info(
            'API соответствует документации.'
        )
    except Exception as error:
        logger.error(
            'API не соответствует документации.'
            f'Ошибка: {error}'
        )
        return False
    if len(homework) > 0:
        return homework[0]
    return homework


def parse_status(homework):
    """Сравнения статуса работы с значением из константы."""
    if len(homework) == 0:
        return 'Изменений нет'

    # Проверяем, наличие названия домашней работы
    if 'homework_name' not in homework:
        logger.error('Ответ API домашки не содержит ключа "homework_name".')
        raise AssertionError(
            'Ответ API домашки не содержит ключа "homework_name".'
        )
    homework_name = homework['homework_name']

    # Проверяем, наличие статуса
    if 'status' not in homework:
        logger.error('Ответ API домашки не содержит ключа "status".')
        raise AssertionError(
            'Ответ API домашки не содержит ключа "status".'
        )
    homework_status = homework['status']

    # Проверяем, что статус является одним из ожидаемых значений
    allowed_statuses = ['reviewing', 'approved', 'rejected']
    if homework_status in allowed_statuses:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logger.error(
            'Недокументированный статус '
            f'домашней работы: {homework_status}'
        )
        raise AssertionError(
            'Недокументированный статус '
            f'домашней работы: {homework_status}'
        )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        print('Отсутствует обязательная переменная окружения')
        exit()

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - DELAY_PERIOD

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message=message)

        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
