# -*- coding: utf-8 -*-
import re
import time
import traceback
import json
from collections import defaultdict

from bs4 import BeautifulSoup
from datetime import timedelta, datetime
import requests
from selenium import webdriver

# TODO: Download, unzip and cp to chatbot project chromedriver.exe.
#  Link = https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_win32.zip
try:
    WEB_DRIVER_PATH = "chromedriver.exe"
except Exception:
    exit('Download, unzip and cp to chatbot project chromedriver.exe.'
         '\n Link = https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_win32.zip')

FILENAME = 'flight_schedule.json'
FILENAME_NEW_VERSION = 'flight_schedule_new_version.json'


class YaTable:
    def __init__(self, date_range):
        """

        :param date_range: Диапазон дат, за которые необходимо получить расписание полетов
        headers: Метаданные устройства
        website: Основнной сайт, с которого происходит переход по ссылкам
        cities_href: Массив ссылок на сайты рейсов для городов отправления
        date: Теукущая дата, по которой протекает парсинг для городов
        city_name: Город отправления, по которому протекает парсинг информации
        flight_times_mas: Массив с временем отправления для каждого рейса
        companies_mas: Массив авиакомпаний для каждого рейса
        """

        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/87.0.4280.60 YaBrowser/20.12.0.963 Yowser/2.5 Safari/537.36'}
        self.website = 'https://rasp.yandex.ru/'
        self.cities_href = []
        self.date_range = date_range
        self.date = None
        self.city_name = None

        self.flight_times_mas = []
        self.flight_arrivals_mas = []
        self.companies_mas = []
        self.schedule_for_one_city = defaultdict(list)
        self.info = []

    def get_departure_city(self):
        """
        Получение ссылок на сайты рейсов для городов отправления
        """
        website = 'https://rasp.yandex.ru/plane'
        response = requests.get(website, headers=self.headers)

        html_doc = BeautifulSoup(response.text, features='html.parser')
        cities_href = str(html_doc.find_all('a', {'class': 'Link TransportCities__city'}))
        cities_href = re.findall("/station/[0-9]+/?/", cities_href)

        for city in cities_href:
            city_href = self.website + city
            self.cities_href.append(city_href)

    def get_delta_time(self, date):
        """

        :param date: Разница (дни) между текущей и требуемой датой
        :return: Дата для получения информации о рейсах
        """
        delta = timedelta(days=date)
        date = datetime.today() + delta
        date = datetime.strftime(date, '%Y-%m-%d')
        print(date)
        return date

    def parse(self, first_city, last_city, indent, path):
        """
        Парсинг и сохранение в json рейсов в срезе ссылок из списка cities_href за указанный диапазон дат

        :param first_city: номер первой требуемой ссылки из списка cities_href
        :param last_city: номер последней требуемой ссылки из списка cities_href
        :param path: путь к драйверу
        """

        for city_ in self.cities_href[first_city:last_city]:
            self.schedule_for_one_city = defaultdict(list)

            for date_number in range(indent, indent + self.date_range):
                date = self.get_delta_time(date_number)
                city = f'{city_}?date={date}&time=all'
                print(city)
                try:
                    driver = self.make_driver_with_options(path)
                    driver.get(city)
                    time.sleep(50)
                    driver.implicitly_wait(100)
                    print(f'Title: {driver.title!r}')
                    if str(driver.title) is not 'Ой!':
                        self.get_elements_from_web(driver, city)
                        if not self.schedule_for_one_city.keys():
                            self.schedule_for_one_city = {self.city_name: {}}
                        for time_, arrival, company in zip(self.flight_times_mas, self.flight_arrivals_mas,
                                                           self.companies_mas):
                            if not self.schedule_for_one_city[self.city_name]:
                                self.schedule_for_one_city[self.city_name] = {arrival: [{self.date: {time_: company}}]}

                            elif arrival not in self.schedule_for_one_city[self.city_name]:
                                self.schedule_for_one_city[self.city_name][arrival] = [{self.date: {time_: company}}]
                            for date in self.schedule_for_one_city[self.city_name][arrival]:
                                if self.date not in list(date.keys()):
                                    self.schedule_for_one_city[self.city_name][arrival].append({self.date: {time_: company}})
                        self.extend_info()

                except:
                    print(traceback.format_exc())
                finally:
                    driver.quit()

        self.json_dump(self.info, FILENAME)
        self.json_dump(self.info, FILENAME_NEW_VERSION)

    def extend_info(self):
        if not self.info:
            self.info.append(self.schedule_for_one_city)
        else:
            for self_info in self.info:
                if self.city_name in self_info:
                    arrival_cities_in_one_schedule = list(self.schedule_for_one_city[self.city_name].keys())
                    arrival_cities = self_info[self.city_name].keys()
                    for arrival_city in arrival_cities_in_one_schedule:
                        if arrival_city in arrival_cities:
                            date = self.schedule_for_one_city[self.city_name][arrival_city]
                            if date not in self_info[self.city_name][arrival_city]:
                                list(dict(self_info[self.city_name])[arrival_city]).append(date)
                else:
                    self.info.append(self.schedule_for_one_city)

    def get_elements_from_web(self, driver, city):
        """
        Парсинг элементов для получения сведений о каждом рейсе

        :param driver: настройки браузера для парсинга
        :param city: город отправления
        """
        self.city_name = str(driver.find_element_by_class_name('StationPage__title').text)[:-21]
        self.date = driver.find_element_by_class_name('StationPage__whenDate').text

        flight_times = driver.find_elements_by_class_name('StationPlaneTable__time')
        [self.flight_times_mas.append(str(time___.text)) for time___ in flight_times]

        flight_arrivals = driver.find_elements_by_class_name('StationPlaneTable__direction')
        if not flight_arrivals:
            response_city = requests.get(city, headers=self.headers)
            html_doc = BeautifulSoup(response_city.text, features='lxml')
            flight_arrivals = (html_doc.find_all('td', {
                'class': 'StationPlaneTable__direction StationPlaneTable__direction_narrowColumn'}))
            if not flight_arrivals:
                flight_arrivals = (html_doc.find_all('td', {
                    'class': 'StationPlaneTable__direction'}))
        [self.flight_arrivals_mas.append(str(city.text)) for city in flight_arrivals]

        flight_companies = driver.find_elements_by_class_name('StationPlaneTable__companies')
        [self.companies_mas.append(str(company.text)) for company in flight_companies]

    def make_driver_with_options(self, path):
        """
        Параметры работы для движка браузера

        :return: настройки браузера для парсинга
        """
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('hide-scrollbars')
            options.add_argument("--disable-blink-features")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("user-data-dir=./chromeprofile")
            options.add_argument('--disable-extensions')
            options.add_argument("--incognito")
            options.add_argument("--disable-plugins-discovery")
            options.add_argument("--start-maximized")
            options.add_argument("--remote-debugging-port=9222")
            options.set_capability('dom.webdriver.enabled', False)

            driver = webdriver.Chrome(path, options=options)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """ Object.defineProperty(navigator, 'webdriver', {get: () => undefined})""" })
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """const newProto = navigator.__
                    proto_delete newProto.webdriver navigator.__proto__ = newProto"""})
            driver.implicitly_wait(20)
            return driver
        except:
            print(traceback.format_exc())

    def get_results(self):
        """
        Экспорт в json
        """
        dict_str = {self.city_name: None}
        arrivals = {}
        for time_, arrival, company in zip(self.flight_times_mas, self.flight_arrivals_mas, self.companies_mas):
            if arrival not in arrivals:
                arrivals[arrival] = [{self.date: {time_: company}}]
            else:
                arrivals[arrival] += [{self.date: {time_: company}}]

        dict_str[self.city_name] = arrivals
        return dict_str

    def json_dump(self, str, file_):

        with open(file=file_, encoding='UTF-8', mode='w') as file_:
            json.dump(str, file_, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False)


number_of_dates = 5
date_indent = 30
num_city_href_1 = 2
num_city_href_2 = 4

yt = YaTable(number_of_dates)
yt.get_departure_city()
yt.parse(num_city_href_1, num_city_href_2, date_indent, WEB_DRIVER_PATH)
