import json
import time
import requests
from typing import Dict
from settings import API_KEY


class Hotels:
    """ Класс для хранения информации о найденных отелях. """

    def __init__(self) -> None:
        self.__hotels_dict = {}

    def get_dict(self) -> Dict:
        """
        Геттер для получения словаря отелей.

        :rtype [Dict]
        """
        return self.__hotels_dict

    def set_item(self, arg, value) -> None:
        """ Сеттер для записи данных найденного отеля.

        :param arg - ключ (ID отеля)
        :param value - значение (информация об отеле)
        :type arg: str
        :type value: str
        """
        self.__hotels_dict[arg] = value

    def clear(self) -> None:
        """ Функция очищает словарь найденных городов. """
        self.__hotels_dict.clear()


def get_hotels_dict(destination_id: int = 0, limit: int = 0, page_number: int = 1) -> Dict:
    """
    Функция получения словаря гостиниц.

    Принимает на вход ID города и максимальное количество искомых гостиниц.
    Если это первый запрос (page_number: int = 1), то осуществляется очистка словаря гостиниц.
    Отправляет API запрос на хост "hotels4.p.rapidapi.com".
    Преобразует полученные данные в словарь в виде (название: стоимость). При этом, если в полученных данных,
    у какой-либо гостиницы, отсутствуют данные о стоимости, то её стоимости присваивается значение НУЛЯ и
    эта гостиница не попадает в словарь гостиниц.

    Количество гостиниц в словаре ограничено переменной "limit". при этом, если в результате работы цикла, размер
    словаря не достиг предельного значения количества выводимых гостиниц, то функция зацикливается с повышением номера
    запрашиваемой страницы (page_number += 1).

    :param destination_id: - значение ID города
    :param limit - значение максимального количества выводимых гостиниц
    :param page_number: - значение номера запрашиваемой страницы
    :type: int
    """

    days_count = 1
    time_add = days_count * 86400
    time_check_in = time.strftime("%Y-%m-%d", time.localtime())
    time_check_out_secs = time.mktime(time.localtime()) + time_add
    time_check_out = time.strftime("%Y-%m-%d", time.localtime(time_check_out_secs))

    hotels = Hotels()
    while len(hotels.get_dict()) < limit:
        # print('page_number', page_number)

        url = "https://hotels4.p.rapidapi.com/properties/list"
        querystring = {"adults1": "1",
                       "pageNumber": "1",  # номер страницы с которой осуществляется запрос данных.
                       "destinationId": destination_id,  # ID города.
                       "pageSize": "25",  # количество выдаваемых значений при запросе с сайта (максимум 25).
                       "checkOut": time_check_out,  # время выезда.
                       "checkIn": time_check_in,  # время заселения.
                       "sortOrder": "PRICE_HIGHEST_FIRST",  # отвечает за сортировку (СНАЧАЛА ДОРОГИЕ).
                       "locale": "ru_RU",  # отвечает за язык вывода гостиниц и единиц измерения расстояния (н-р: км.).
                       "currency": "RUB"}  # отвечает за конвертацию стоимости в конкретную валюту (н-р: RUB).
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = json.loads(response.text)

        for elem in data['data']['body']['searchResults']['results']:
            try:
                price = elem['ratePlan']['price']['current']
            except KeyError:
                price = 0

            if len(hotels.get_dict()) < limit:
                if price != 0:
                    text = f"Стоимость: {price}"
                    hotels.set_item(elem['name'], text)
            else:
                break

        page_number += 1

    return hotels.get_dict()


if __name__ == "__main__":
    get_hotels_dict()
