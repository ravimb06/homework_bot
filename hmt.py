import json
import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """
    Функция отправляет сообщение в Telegram чат.
    И логгирует ситуацию,при которой сообщение отправлено не было.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение успешно отправлено')
    except Exception as error:
        logger.error(f'Сообщение не отправлено из-за ошибки: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    if response.status_code != 200:
        logger.debug(f'Статус код: {response.status_code}')
        raise Exception(f'Статус код: {response.status_code}')
    try:
        response_json = response.json()
    except json.JSONDecodeError:
        raise Exception('Не удалось сериализовать ответ')
    return response_json


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    if type(homeworks) != list:
        raise TypeError(f'{type(homeworks)} - это не список!')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ee статус."""
    homework_name = homework['homework_name']
    if not homework['status']:
        raise KeyError('В API нет поля "status"')
    homework_status = homework.get('status')
    if not HOMEWORK_STATUSES[homework_status]:
        raise ValueError(f'Статуса {homework_status} нет в списке')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    none_tokens_info = {
        PRACTICUM_TOKEN: 'Отсутствует PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'Отсутствует TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'Отсутствует TELEGRAM_CHAT_ID'
    }
    for token, status in none_tokens_info.items():
        if token is None:
            logger.critical(f'Отсутствует токен {status}')
            return False
        else:
            return True


def main():
    """Основная логика работы бота."""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        logger.info('Ваш бот инициализирован')
    except Exception as error:
        logger.error(f'Не получилось иницировать бота. Ошибка: {error}')
    current_timestamp = int(0)
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения!')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            homeworks = check_response(response)
            if homeworks:
                homework = check_response(response)[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.info('Вы не сдали ни одной домашки за этот период')
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
