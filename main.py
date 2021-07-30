#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import json
import logging
import re
from typing import Any, Dict, Callable
import time
import requests
import telebot

import bestdeal
import highprice
import lowprice

try:
    from settings import BOT_TOKEN, API_KEY
except ImportError:
    exit('В файле settings.py нужно создать BOT_TOKEN и API_KEY пример в settings.default.txt')

# print('BOT_TOKEN: ', BOT_TOKEN)
# print('API_KEY: ', API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
users_id_dict = {}


class Variables:
    """ Класс для хранения всех переменных текущего пользователя. """

    def __init__(self):
        self.__variables = {'mode': '',  # словарь для хранения переменных
                            'hotels_limit': 0,
                            'destination_id': 0,
                            'min_price': 0,
                            'max_price': 0,
                            'min_distance': 0,
                            'max_distance': 0
                            }
        self.__cities = {}  # словарь для хранения найденных городов

    def get_arg(self, arg) -> Any:
        """
        Геттер для получения конкретной переменной.

        :param arg - ключ (название переменной)
        :type arg: str
        :rtype [Any]
        """
        return self.__variables[arg]

    def get_city(self, arg) -> str:
        """
        Геттер для получения конкретного города.

        :param arg - ключ (ID города)
        :type arg: int
        :rtype str
        """
        return self.__cities.get(arg, None)

    def get_city_dict(self) -> Dict:
        """
        Геттер для получения всего словаря городов.

        :rtype [Dict]
        """
        return self.__cities

    def set_arg(self, arg, value) -> None:
        """
        Сеттер для записи конкретной переменной.

        :param arg - ключ (название переменной)
        :param value - значение (значение переменной)
        :type arg: str
        :type value: [Any]
        """
        self.__variables[arg] = value

    def set_city(self, arg, value) -> None:  # сеттер для записи конкретного города
        """
        Сеттер для записи данных найденного отеля.

        :param arg - ключ (ID города)
        :param value - значение (название города)
        :type arg: int
        :type value: str
        """
        self.__cities[arg] = value

    def clear_city(self) -> None:
        """ функция очищает словарь найденных городов. """
        self.__cities.clear()

    def replace(self, arg_1, arg_2) -> None:
        """ функция меняет местами две переменные. """
        self.__variables[arg_1], self.__variables[arg_2] = self.__variables[arg_2], self.__variables[arg_1]


def my_logging(func: Callable) -> Callable:
    """
    Декоратор логирования переданной функции
    Перед выполнением функции, записывается в файл errors_log.log:
    наименование функции, пользователь, вызвавший её, отправленная им команда.

    :param func: передаваемая пользователем функция
    :return: wrapped_func
    """

    @functools.wraps(func)
    def wrapped_func(*args, **kwargs) -> Any:

        logging.basicConfig(filename="errors_log.log",  # настройка логирования
                            level=logging.INFO,
                            filemode='w',
                            datefmt='%d-%m-%Y %H:%M:%S',
                            format='%(asctime)s - %(message)s')

        try:  # логирование для всех функций кроме "query_handler"
            username = args[0].from_user.username
            message = args[0].text
            logging.info("\tFunction: %s, Username: %s, message: %s" % (func.__name__, username, message))

        except AttributeError:  # логирование для функции "query_handler"
            username = args[0].from_user.username
            message = args[0].message
            logging.info("\tFunction: %s, Username: %s, message: %s" % (func.__name__, username, message))

        except Exception as error_log:  # логирование для "неожиданной ошибки"
            print('error: ', error_log)
            print('args[0]: ', args[0])
            logging.info("\tFunction: %s, args[0]: %s" % (func.__name__, args[0]))
            logging.exception("Unexpected Error occurred")

        return func(*args, **kwargs)

    return wrapped_func


@bot.message_handler(commands=['help', 'start', 'hello_world', 'lowprice', 'highprice', 'bestdeal'])
@my_logging
def start_message(message: Any) -> None:
    """
    Стартовая функция.

    Принимает на вход команды:  '/help', '/hello_world', '/lowprice', '/highprice' и '/bestdeal'.
    Команда:
        /help - выводит подсказку, как начать работать с БОТом
        /hello_world - выводит приветственное сообщение и команды для работы с БОТом
        /lowprice - для поиска самого дешевого жилья
        /highprice - для поиска самого дорогого жилья
        /bestdeal - для поиска самого лучшего жилья

    Если это первый вызов для пользователя, то создается объект класса "Переменные" (Variables), затем обрабатывает,
    полученные от пользователя команды.

    Далее, получает на вход название искомого города и осуществляет переход к функции (get_city)
    поиска указанного города.

    :param message: - получаемое сообщение
           variables -  переменная для хранения режима работы БОТа, в зависимости от полученной команды.
                        Если строчку закомментировать, то при получении соответствующей команды, будет
                        выведено сообщение "В РАЗРАБОТКЕ ...".
    :type: Any
    """

    variables = users_id_dict.get(message.from_user.id, None)
    if not variables:
        users_id_dict[message.from_user.id] = Variables()
        variables = users_id_dict[message.from_user.id]
    variables.set_arg('mode', None)
    if message.text == '/hello_world' or message.text == '/start':
        bot.send_message(message.from_user.id, f'Привет, {message.from_user.first_name}! '
                                               'Это EasyTravelBot, чем я могу тебе помочь?\n'
                                               'Команды:\n'
                                               '/lowprice - для поиска самых дешевых отелей.\n'
                                               '/highprice - для поиска самых дорогих отелей.\n'
                                               '/bestdeal - для поиска самых лучших (близко и дешево) отелей.')
    elif message.text == '/help':
        bot.send_message(message.from_user.id, 'Напиши "Привет" или "/hello_world"')
    else:
        if message.text == '/lowprice':
            bot.send_message(message.from_user.id, 'Поиск самых дешевых отелей ...')
            variables.set_arg('mode', 'lowprice')
        elif message.text == '/highprice':
            bot.send_message(message.from_user.id, 'Поиск самых дорогих отелей ...')
            variables.set_arg('mode', 'highprice')
        elif message.text == '/bestdeal':
            bot.send_message(message.from_user.id, 'Поиск самых лучших (близко и дешево) отелей ...')
            variables.set_arg('mode', 'bestdeal')
        if variables.get_arg('mode'):
            bot.send_message(message.from_user.id, 'Введите название искомого города \n(на русском или английском): ')
            bot.register_next_step_handler(message, get_city)
        else:
            bot.send_message(message.from_user.id, 'В РАЗРАБОТКЕ ... ')


@bot.message_handler(content_types=['text'])
@my_logging
def get_text_messages(message: Any, crush=False) -> None:
    """
    Стартовая функция.

    Принимает на вход сообщение. Если это сообщение 'Привет' или 'привет', то выводит приветственное сообщение и
    список команд для работы с БОТом.
    Иначе, выводится сообщение с указанием, как начать работу с БОТом.

    Если это первый вызов для пользователя или вызов функции был вызван сбоем программы (аргумент функции crush=True),
    то создается объект класса "Переменные" (Variables), затем функция обрабатывает, полученные от пользователя команды.

    :param crush: - флаг сбоя программы (вызывается нажатием кнопки выбора, до запуска БОТ-программы)
    :param message: - получаемое сообщение
    :type: Any
    """

    variables = users_id_dict.get(message.chat.id, None)
    if not variables:
        users_id_dict[message.chat.id] = Variables()
    if str(message.text).lower() == 'привет':
        bot.send_message(message.chat.id, f'Привет, {message.chat.first_name}! '
                                          'Это EasyTravelBot, чем я могу тебе помочь?\n'
                                          'Команды:\n'
                                          '/lowprice - для поиска самых дешевых отелей.\n'
                                          '/highprice - для поиска самых дорогих отелей.\n'
                                          '/bestdeal - для поиска самых лучших (близко и дешево) отелей.')
    else:
        if crush:
            bot.send_message(message.chat.id, 'Произошел сбой ...')
            bot.send_message(message.chat.id, 'Напиши /hello_world.')

        else:
            bot.send_message(message.chat.id, 'Я тебя не понимаю. Напиши /help.')


@my_logging
def get_city(message: Any) -> None:
    """
    Функция поиска города.

    Принимает на вход сообщение с названием города. Затем отправляет API запрос на хост "hotels4.p.rapidapi.com" и
    преобразует полученные данные в словарь.
    В полученном словаре ищет элементы, соответствующие группе 'CITY_GROUP' ('group': 'CITY_GROUP'), а в нем элементы,
    соответствующие типу 'CITY' ('type': 'CITY').
    Затем создает элементы словаря для каждого найденного города в формате: (ID города: Название) и добавляет этот
    город в кнопку клавиатуры БОТа.
    Если ни одного города с указанным названием не будет найдено (длина словаря будет равна НУЛЮ), то выводится
    соответствующее сообщение и запускается функция ввода нового названия (get_city_name).
    Иначе, выводятся кнопки со всем найденными городами.

    Если вместо названия города придет команда на изменение режима работы, цикл работы БОТа перезапускается (вызывается
    функция "start_message(message)".

    :param message: - получаемое сообщение
           message.text - название города
    :type: message: Any
           message.text: str
    """

    try:
        if message.text.startswith('/'):
            start_message(message)
            return
    except AttributeError:
        pass

    else:
        variables = users_id_dict[message.from_user.id]
        variables.clear_city()
        city = message.text
        url = "https://hotels4.p.rapidapi.com/locations/search"
        querystring = {"query": city, "locale": "ru_RU"}
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = json.loads(response.text)
        try:
            city_choice = 'Обнаружены следующие города:'
            for elem in data['suggestions']:
                if elem['group'] == 'CITY_GROUP':
                    keyboard = telebot.types.InlineKeyboardMarkup()
                    for i_elem in elem['entities']:
                        if i_elem['type'] == 'CITY':
                            current_city = re.sub(r"<[^.]*>\b", '', i_elem['caption'])
                            current_city = re.sub(r"<[^.]*>", '', current_city)
                            variables.set_city(i_elem['destinationId'], {'caption': current_city})
                            callback_message = f"{i_elem['destinationId']}|{message.from_user.id}"
                            key_city = telebot.types.InlineKeyboardButton(text=current_city,
                                                                          callback_data=callback_message)
                            keyboard.add(key_city)
                    if len(variables.get_city_dict()) == 0:
                        bot.send_message(message.chat.id,
                                         'Городов с указанным названием не обнаружено. Попробуйте еще раз.')
                        get_city_name(message)
                    else:
                        bot.send_message(message.chat.id, text=city_choice, reply_markup=keyboard)
        except KeyError:
            bot.send_message(message.chat.id, 'Сбой в получении данных с сервера.')
            print("data['message']: ", data['message'])
        except Exception as error_get_city:
            print('data_except: ', data)
            print('Exception: ', error_get_city.__class__)
            print('Exception: ', error_get_city)


@my_logging
def get_city_name(message: Any) -> None:
    """
    Функция повторного запроса названия города.

    Принимает на вход сообщение с названием города. Затем вызывает функцию поиска города (get_city)

    :param message: - получаемое сообщение
    :type: Any
    """

    bot.send_message(message.from_user.id, 'Введите название искомого города \n(на русском или английском): ')
    bot.register_next_step_handler(message, get_city)


@bot.callback_query_handler(func=lambda call: True)
@my_logging
def query_handler(call: Any) -> None:
    """
    Функция обработки результата нажатия кнопки.

    Принимает на вход сообщение с результатом выбора пользователя и его ID. Затем разделяет это сообщение на две
    соответствующие части.
    Затем проверяется имеется для данного пользователя объект класса "Переменные" (наличие данных в словаре
    "users_id_dict" под ID пользователя).
    Если результат отрицательный, следовательно, произошел сбой программы и цикл работы БОТа перезапускается
    (вызывается функция "get_text_messages(call.message, True)", где True - флаг произошедшего сбоя.

    Затем проверяется, что пришло в первой части сообщения (содержание переменной "choice"):
    Если это цифры, то произошел выбор города.
    Если это буквы, то произошел выбор действий.

    Для выбора города:
    Если выбран режим выбора лучшего предложения гостиниц (items_dict['mode'] == 'bestdeal'), то
    осуществляется переход в функцию получения и обработки минимальной стоимости гостиницы (get_min_price).
    Иначе, осуществляется переход в функцию получения и обработки количества выводимых гостиниц (get_limit) .

    Для выбора действий:
    Сначала объявляются переменные, в зависимости от того, на каком этапе произошел выбор действий: на этапе задания
    цены или дистанции от центра города.
    Затем:
    Если был выбор "поменять местами" ('replace'), то вызывается функция замены местами двух переменных
    variables.replace(min_value, max_value) и переход на следующий этап ('next_step').
    Если был выбор "ввести все значения заново" ('rewrite'), то осуществляется переход на начало текущего этапа
    ('prev_step').

    :param call: - получаемое сообщение
           call.data - текст с результатом выбора пользователя и его ID
    :type: call: Any
           call.data: int
    """

    temp = call.data.split('|')
    choice = temp[0]  # результат выбора пользователя
    user_id = int(temp[1])  # ID пользователя
    variables = users_id_dict.get(user_id, None)
    if not variables:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        get_text_messages(call.message, True)
        return

    if choice.isdigit():  # выбор города
        variables.set_arg('destination_id', choice)
        chosen_city = variables.get_city(choice)
        if chosen_city:
            choice_message = f"Вы выбрали: {variables.get_city(choice)['caption']}"
        else:
            bot.send_message(call.message.chat.id, f"Ошибка! Выбирайте город только из таблицы выше!")
            get_city(call)
            return
        bot.answer_callback_query(callback_query_id=call.id, text=choice_message)
        # bot.edit_message_text(f"Результаты для города: {cities_dict[call.data]['caption']}",
        #                       call.message.chat.id, call.message.id)
        # bot.delete_message(call.message.chat.id, call.message.id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"Результаты для города: {variables.get_city(choice)['caption']}")
        if variables.get_arg('mode') == 'bestdeal':
            bot.send_message(call.message.chat.id, 'Укажите минимальную стоимость, руб')
            bot.register_next_step_handler(call.message, get_min_price)
        else:
            bot.send_message(call.message.chat.id, 'Сколько гостиниц (не более 25) вывести на экран?')
            bot.register_next_step_handler(call.message, get_limit)

    elif choice.isalpha():  # выбор действия
        min_value, max_value, prev_step, next_step, prev_message, next_message = '', '', None, None, '', ''
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        if re.search('сумму', call.message.text):  # этап цены
            min_value, max_value, prev_step, next_step = 'min_price', 'max_price', get_min_price, get_min_distance
            prev_message = 'Укажите минимальную стоимость, руб'
            next_message = 'Укажите минимальную дальность от центра города, км.: '
        elif re.search('дистанцию', call.message.text):  # этап дистанции
            min_value, max_value, prev_step, next_step = 'min_distance', 'max_distance', get_min_distance, get_limit
            prev_message = 'Укажите минимальную дальность от центра города, км.: '
            next_message = 'Сколько гостиниц (не более 25) вывести на экран?'

        if choice == 'replace':
            variables.replace(min_value, max_value)
            choice_message = 'Вы выбрали: Поменять местами максимальное и минимальное значение.'
            bot.answer_callback_query(callback_query_id=call.id, text=choice_message)
            bot.send_message(call.message.chat.id, choice_message)
            bot.send_message(call.message.chat.id, f"Минимальное значение {variables.get_arg(min_value)} \n"
                                                   f"Максимальное значение {variables.get_arg(max_value)} ")
            bot.send_message(call.message.chat.id, next_message)
            bot.register_next_step_handler(call.message, next_step)
        elif choice == 'rewrite':
            choice_message = 'Вы выбрали: Попробовать ввести все значения заново.'
            bot.answer_callback_query(callback_query_id=call.id, text=choice_message)
            bot.send_message(call.message.chat.id, choice_message)
            bot.send_message(call.message.chat.id, prev_message)
            bot.register_next_step_handler(call.message, prev_step)


def get_min_price(message: Any) -> None:
    """ Функция шаблонов для получения минимальной стоимости гостиницы. """

    min_price_next_message = 'Укажите максимальную стоимость, руб: '
    get_min_args(message, 'min_price', min_price_next_message, get_min_price, get_max_price)


def get_max_price(message: Any) -> None:
    """ Функция шаблонов для получения максимальной стоимости гостиницы. """

    max_price_next_message = 'Укажите минимальную дальность от центра города, км.: '
    max_price_except = 'Вы ввели максимальную сумму меньше (или равную) минимальной.\n' \
                       'Что желаете сделать?'
    get_max_args(message, 'min_price', 'max_price', max_price_next_message, max_price_except,
                 get_max_price, get_min_distance)


def get_min_distance(message: Any) -> None:
    """ Функция шаблонов для получения минимальной дистанции между гостиницей и центром города. """

    min_distance_next_message = 'Укажите максимальную дальность от центра города, км.: '
    get_min_args(message, 'min_distance', min_distance_next_message, get_min_distance, get_max_distance)


def get_max_distance(message: Any) -> None:
    """ Функция шаблонов для получения максимальной дистанции между гостиницей и центром города. """

    max_distance_next_message = 'Сколько гостиниц (не более 25) вывести на экран?'
    max_distance_except = 'Вы ввели максимальную дистанцию меньше (или равную) минимальной.\n' \
                          'Что желаете сделать?'
    get_max_args(message, 'min_distance', 'max_distance', max_distance_next_message, max_distance_except,
                 get_max_distance, get_limit)


@my_logging
def get_min_args(message: Any, min_arg: str, next_message: str, get_minimum: Any, get_maximum: Any) -> None:
    """
    Функция получения минимального значения аргумента.

    Принимает на вход сообщение с минимальным значением аргумента.
    Проверяет, что это сообщение является целым числом.
    Если так, то осуществляется запрос максимальной суммы и осуществляется переход в функцию получения и обработки этой
    суммы (get_maximum).
    Иначе, выводится сообщение об ошибке и текущая функция возвращается к вызвавшей её функции.

    :param message: - получаемое сообщение
    :param min_arg: - значение минимального числа
    :param next_message: - сообщение для перехода к следующему этапу
    :param get_minimum: - переменная для функции назначения
    :param get_maximum: - переменная для функции назначения
    :type: message: Any
           min_arg: str
           next_message: str
           get_minimum: func
           get_maximum: func
    """

    if message.text.startswith('/'):
        start_message(message)
        return
    variables = users_id_dict[message.from_user.id]
    temp = re.sub(r",", '.', message.text)
    try:
        variables.set_arg(min_arg, abs(float(temp)))
        bot.send_message(message.from_user.id, next_message)
        bot.register_next_step_handler(message, get_maximum)
    except ValueError:
        bot.send_message(message.chat.id, 'Вводить можно только числа. Попробуйте еще раз.')
        bot.register_next_step_handler(message, get_minimum)


@my_logging
def get_max_args(message: Any, min_arg: str, max_arg: str, next_message: str, except_message: str,
                 get_maximum: Any, get_next: Any) -> None:
    """
    Функция получения максимального значения аргумента.

    Принимает на вход сообщение с максимальным значением аргумента.
    Проверяет, что это сообщение является целым числом.
    Если так, то:
    1. осуществляется проверка, что максимальное значение аргумента больше минимального.
    1.1. если Верно, то осуществляется переход в следующую функцию получения и обработки сообщения (get_next).
    1.2. иначе, осуществляется переход в функцию получения и обработки минимального значения аргумента (get_minimum).
    2. при ошибке, выводится сообщение об ошибке и текущая функция возвращается к вызвавшей её функции.

    :param message: - получаемое сообщение
    :param min_arg: - значение минимального числа
    :param max_arg: - значение максимального числа
    :param next_message: - сообщение для перехода к следующему этапу
    :param except_message: - сообщение об ошибке
    :param get_maximum: - переменная для функции назначения
    :param get_next: - переменная для функции (этапа) назначения
    :type: message: Any
           min_arg: str
           max_arg: str
           next_message: str
           except_message: str
           get_maximum: func
           get_next: func
    """

    if message.text.startswith('/'):
        start_message(message)
        return
    variables = users_id_dict[message.from_user.id]
    temp = re.sub(r",", '.', message.text)
    try:
        variables.set_arg(max_arg, abs(float(temp)))
        if variables.get_arg(max_arg) > variables.get_arg(min_arg):
            bot.send_message(message.from_user.id, next_message)
            bot.register_next_step_handler(message, get_next)
        else:
            except_choice = except_message
            except_choice_1 = 'Поменять местами максимальное и минимальное значение.'
            except_choice_2 = 'Попробовать ввести все значения заново.'
            keyboard_except = telebot.types.InlineKeyboardMarkup()
            key_except_1 = telebot.types.InlineKeyboardButton(text=except_choice_1,
                                                              callback_data=f'replace|{message.from_user.id}')
            key_except_2 = telebot.types.InlineKeyboardButton(text=except_choice_2,
                                                              callback_data=f'rewrite|{message.from_user.id}')
            keyboard_except.add(key_except_1)
            keyboard_except.add(key_except_2)
            bot.send_message(message.chat.id, text=except_choice, reply_markup=keyboard_except)
    except ValueError:
        bot.send_message(message.chat.id, 'Вводить можно только числа. Попробуйте еще раз.')
        bot.register_next_step_handler(message, get_maximum)


@my_logging
def get_limit(message: Any) -> None:
    """
    Функция получения максимального количества выводимых на экран гостиниц.

    Принимает на вход сообщение с максимальным числом гостиниц.
    Проверяет, что это сообщение является целым числом.
    Если так, то:
    1. осуществляется проверка, что это значение меньше цифры "25".
    1.1. если Верно, то осуществляется переход в функцию получения списка гостиниц и их цен (get_price_list).
    1.2. иначе, выводится сообщение об ошибке и текущая функция зацикливается.
    2. при ошибке, выводится сообщение об ошибке и текущая функция зацикливается.

    :param message: - получаемое сообщение
           message.text - значение количества гостиниц
           items_dict['max_distance'] - переменная для хранения количества гостиниц
    :type: message: Any
           message.text: int
    """

    variables = users_id_dict[message.from_user.id]
    try:
        variables.set_arg('hotels_limit', abs(int(message.text)))
        if variables.get_arg('hotels_limit') <= 25:
            bot.send_message(message.chat.id, f"Начинаю поиск. Это может занять продолжительное время")
            get_price_list(message)
        else:
            bot.send_message(message.chat.id, 'Вы ввели число больше 25. Попробуйте еще раз.')
            bot.register_next_step_handler(message, get_limit)
    except ValueError:
        bot.send_message(message.chat.id, 'Вводить можно только числа (целые). Попробуйте еще раз.')
        bot.register_next_step_handler(message, get_limit)


@my_logging
def get_price_list(message: Any) -> None:
    """
    Функция получения получения списка гостиниц и их цен.

    В зависимости от текущего режима работы БОТа (значения переменной items_dict['mode']), осуществляет запуск (импорт)
    соответствующего скрипта, передав ему необходимые аргументы.
    Если, в результате выполнения скрипта, словарь гостиниц окажется НЕ пустым, то на экран будет выведен список из
    найденных гостиниц и их стоимости. В случае с режимом "bestdeal", будет указана еще и дистанция от центра города.
    Иначе, будет выведено сообщение от отсутствии найденных предложений и осуществится запуск функции смены
    названия искомого города (get_city_name) для повторения поиска в текущем режиме..

    :param message: - получаемое сообщение
    :type: message: Any
    """

    hotels_dict = {}
    variables = users_id_dict[message.from_user.id]
    if variables.get_arg('mode') == 'lowprice':
        hotels_dict = lowprice.get_hotels_dict(variables.get_arg('destination_id'), variables.get_arg('hotels_limit'))
    elif variables.get_arg('mode') == 'highprice':
        hotels_dict = highprice.get_hotels_dict(variables.get_arg('destination_id'), variables.get_arg('hotels_limit'))
    elif variables.get_arg('mode') == 'bestdeal':
        hotels_dict = bestdeal.get_hotels_dict(variables.get_arg('destination_id'), variables.get_arg('min_price'),
                                               variables.get_arg('max_price'), variables.get_arg('min_distance'),
                                               variables.get_arg('max_distance'), variables.get_arg('hotels_limit'))
    hotels_quantity = len(hotels_dict)
    if hotels_quantity > 0:
        for name, price in hotels_dict.items():
            bot.send_message(message.chat.id, f"Гостиница: {name}\n{price}")
        if hotels_quantity < variables.get_arg('hotels_limit'):
            bot.send_message(message.chat.id,
                             f"Заданным параметрам поиска соответствует лишь {hotels_quantity} гостиниц")
    else:
        bot.send_message(message.chat.id, f"Для заданных параметров ничего не найдено. Попробуйте еще раз.")
        get_city_name(message)


try:
    bot.polling(none_stop=True, interval=0)
except requests.exceptions.ReadTimeout:
    time.sleep(1000)
    print("Переподключение к серверам")
    logging.exception("Переподключение к серверам")
    bot.polling(none_stop=True, interval=0)
except Exception as error_main:
    print('Unexpected Error: ')
    print('Exception: ', error_main)
    print('Exception: ', error_main.__class__)
    logging.exception("Unexpected Error occurred")
