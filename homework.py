import logging
import sys
import os
import telegram
import requests
import exceptions
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

TELEGRAM_RETRY_TIME = 600
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
    except telegram.error.TelegramError as error:
        logging.error(f'{error}. Не удалось отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает запрос к API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        raise exceptions.EndpointRequestError(
            'Ошибка запроса к эндпоинт'
        ) from e
    if response.status_code != 200:
        logger.error(f'Код {response.status_code}. Эндпоинт недоступен')
        raise exceptions.EndpointError(
            f'Код {response.status_code}. Эндпоинт недоступен'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('ожидается словарь!')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks"')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('ожидается список!')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if not homework['homework_name']:
        logger.error('Отсутствует ожидаемый ключ "homework_name" в ответе.')
        raise KeyError('Отсутствует ожидаемый ключ "homework_name" в ответе.')
    homework_name = homework['homework_name']
    if not homework['status']:
        logger.error('Отсутствует ожидаемый ключ "status" в ответе.')
        raise KeyError('Отсутствует ожидаемый ключ "status" в ответе.')
    homework_status = homework['status']
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
    tokens_none = []
    for token, status in none_tokens.items():
        if token is None:
            tokens_none.append(status)
    if tokens_none:
        logger.critical('Отсутствует токен(ы): ' + ', '.join(tokens_none))
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    if not check_tokens():
        raise exceptions.TokensNoneError
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = check_response(response)
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                message = 'Вы не сдали ни одной домашки за этот период'
                logger.info(message)
            current_timestamp = response.get('current_date')
        except Exception:
            message = 'Сбой в работе программы'
            logger.exception(message)
            send_message(bot, message)
        finally:
            time.sleep(TELEGRAM_RETRY_TIME)


if check_tokens() and __name__ == '__main__':
    main()
