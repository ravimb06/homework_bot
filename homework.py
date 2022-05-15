import logging
import sys
import os
from urllib import response
import telegram
import requests
import time

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(lineno)s,'
)
handler.setFormatter(formatter)


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
    """Отправляет сообщение в Телеграм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logging.error(f'{error} Не удалось отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает запрос к API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    if response.status_code != 200:
        logger.error(f'Статус код: {response.status_code}')
        raise Exception(f'Статус код: {response.status_code}')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    if type(homeworks) != list:
        raise TypeError(f'{type(homeworks)} - это не список!')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if not homework.get('homework_name') or not homework.get('status'):
        logger.error('Отсутствуют ожидаемые ключи в ответе API.')
        raise KeyError('Отсутствуют ожидаемые ключи в ответе API.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not HOMEWORK_STATUSES[homework_status]:
        logger.error(f'Статус {homework_status} не документирован')
        raise ValueError(f'Статус {homework_status} не документирован')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    none_tokens = {
        PRACTICUM_TOKEN: 'Отсутствует PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'Отсутствует TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'Отсутствует TELEGRAM_CHAT_ID'
    }
    for token, status in none_tokens.items():
        if token is None:
            logger.critical(f'Отсутствует токен {status}')
            return False
        else:
            return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    check_tokens()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = check_response(response)[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                message = 'Вы не сдали ни одной домашки за этот период'
                logger.info(message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
