import time
import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
import logging
import sys
import telegram
from http import HTTPStatus as status


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN_S')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_S')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID_S')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def check_tokens():
    """Проверяет наличие переменных окружения."""
    required_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if None in required_tokens:
        error_text = 'Отсутствуют переменные окружения'
        logging.critical(error_text)
        return False
    else:
        return True


def send_message(bot, message):
    """Отправляет сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        message_text = 'Сообщение отправлено'
        logging.debug(f'Бот отправил сообщение: {message_text}')
    except Exception as error:
        error_text = f'Сбой при отправке сообщения {error}'
        logging.error(error_text)


def get_api_answer(timestamp):
    """Получает ответ API."""
    try:
        payload = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        python_format = response.json()
        if response.status_code != status.OK:
            error_text = f'Ошибка при обращении к API {response.status_code}'
            logging.error(error_text)
            raise Exception(error_text)
        elif not python_format:
            error_text = 'Список домашних работ пуст'
            logging.debug(error_text)
            return response.json()
        else:
            return python_format
    except requests.RequestException as error:
        error_text = f'Ошибка при обращении к API {error}'
        logging.error(error_text)


def parse_status(homework):
    """Формирует сообщение."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {homework_status}')
    return(
        'Изменился статус проверки работы "{homework_name}" {verdict}'
    ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def check_response(response):
    """Проверяет ответ API."""
    if type(response) is not dict:
        error_text = f'Неправильный тип данных в ответе {type(response)}'
        logging.error(error_text)
        raise TypeError(error_text)
    homeworks = response.get('homeworks')
    if type(homeworks) is not list:
        error_text = 'Неправильный тип данных в ответе'
        logging.error(error_text)
        raise TypeError(error_text)
    elif 'homeworks' in response:
        return True
    else:
        error_text = 'Что-то не так!'
        logging.error(error_text)
        raise Exception(error_text)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
    if not check_tokens():
        sys.exit()
        return 'Отсутствуют переменные окружения'
    while True:
        try:
            check_tokens()
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')[0]
            new_response = get_api_answer(timestamp)
            new_homework = new_response.get('homeworks')[0]
            message = parse_status(new_homework)
            if new_homework == homework:
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
