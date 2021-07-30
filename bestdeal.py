import json
import re
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

        :param arg - ключ (название отеля)
        :param value - значение (информация об отеле)
        :type arg: str
        :type value: str
        """
        self.__hotels_dict[arg] = value

    def clear(self) -> None:
        """ Функция очищает словарь найденных городов. """
        self.__hotels_dict.clear()


def get_hotels_dict(destination_id: int = 0, min_price: int = 0, max_price: int = 0, min_distance: int = 0,
                    max_distance: int = 0, limit: int = 0, page_number: int = 1) -> Dict:
    """
    Функция получения словаря гостиниц.

    Принимает на вход ID города и максимальное количество искомых гостиниц.
    Если это первый запрос (page_number: int = 1), то осуществляется очистка словаря гостиниц.
    Отправляет API запрос на хост "hotels4.p.rapidapi.com" и преобразует полученные данные в json словарь "data".

    Затем, определяется, если хоть какая-то полезная информация по осуществленному запросу.
    Если ошибки не выявлено (значение ключа "result" не равно "ERROR"), то преобразует полученные данные в словарь
    в виде (название: стоимость и расстояние от центра города).
    При этом, если в полученных данных, у какой-либо гостиницы, отсутствуют данные о стоимости, то её стоимости
    присваивается значение бесконечности (float("inf")).
    В словарь заносятся только те гостиницы, чья стоимость и дистанция в пределах указанных минимум и максимумов.

    Количество гостиниц в словаре ограничено переменной "limit". при этом:
    Если стоимость и дистанция (оба) превысят указанные максимумы, то выставляется флаг "finish" завершения поиска.
    Иначе, текущая функция зацикливается с повышением номера запрашиваемой страницы (page_number += 1).

    :param destination_id: - значение ID города
    :param min_price: - значение минимальной стоимости гостиницы
    :param max_price: - значение максимальной стоимости гостиницы
    :param min_distance: - значение минимальной дистанции от центра города
    :param max_distance: - значение максимальной дистанции от центра города
    :param limit: - значение максимального количества выводимых гостиниц
    :param page_number: - значение номера запрашиваемой страницы
    :type: int
    """

    days_count = 1
    time_add = days_count * 86400
    time_check_in = time.strftime("%Y-%m-%d", time.localtime())
    time_check_out_secs = time.mktime(time.localtime()) + time_add
    time_check_out = time.strftime("%Y-%m-%d", time.localtime(time_check_out_secs))

    hotels = Hotels()
    finish = False
    prev_hotel, last_hotel = '', ''
    while len(hotels.get_dict()) < limit and not finish:
        # print('page_number', page_number)
        url = "https://hotels4.p.rapidapi.com/properties/list"
        querystring = {"adults1": "1",
                       "pageNumber": page_number,  # номер страницы с которой осуществляется запрос данных.
                       "destinationId": destination_id,  # ID города.
                       "pageSize": "25",  # количество выдаваемых значений при запросе с сайта (максимум 25).
                       "checkOut": time_check_out,  # время выезда.
                       "checkIn": time_check_in,  # время заселения.
                       "priceMax": max_price,
                       "sortOrder": "DISTANCE_FROM_LANDMARK",  # отвечает за сортировку (ДИСТАНЦИЯ).
                       "locale": "ru_RU",  # отвечает за язык вывода гостиниц и единиц измерения расстояния (н-р: км.).
                       "currency": "RUB",  # отвечает за конвертацию стоимости в конкретную валюту (н-р: RUB).
                       "priceMin": min_price,
                       "landmarkIds": "City center"
                       }

        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': "hotels4.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        data = json.loads(response.text)

        if data['result'] != 'ERROR':
            for elem in data['data']['body']['searchResults']['results']:
                # print(elem)
                try:
                    price = float(elem['ratePlan']['price']['exactCurrent'])
                except KeyError:
                    price = float("inf")
                distance = re.sub(r"\s\w+", '', elem['landmarks'][0]['distance'])
                distance = float(re.sub(r",", '.', distance))
                # print(f"{elem['name']}\n{price}\n"
                #       f"{elem['landmarks'][0]['distance']}\n")

                if len(hotels.get_dict()) < limit:
                    if min_distance <= distance <= max_distance:
                        text = f"Стоимость: {elem['ratePlan']['price']['current']} \n" \
                               f"Адрес: {elem['address']['streetAddress']} \n" \
                               f"Расстояние от центра города: {elem['landmarks'][0]['distance']}"
                        hotels.set_item(elem['name'], text)
                        last_hotel = elem['name']
                        # print(f"{elem['name']}\n{text}")
                    elif distance > max_distance:
                        finish = True
                        break
                else:
                    break

        if prev_hotel == last_hotel:
            break
        else:
            prev_hotel = last_hotel
            page_number += 1

    return hotels.get_dict()


if __name__ == "__main__":
    get_hotels_dict()
