# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime, timedelta
import random
from nltk.stem import SnowballStemmer
from generate_ticket import make_ticket


class Handle:
    """
    Обработчик введенной информации от пользователя для заказа билетов авиакомпании.
    """
    def __init__(self):
        """

        filename: файл для чтения json
        cities_departure: Словарь в формате: {Название города: полная информация об аэропорте}
        cities_arrival: список городов прибытия
        dates: перечень дат по указанным городам отправления и прибытия
        times: перечень рейсов по указанным городам отправления, прибытия и дате
        company: компания перевозчик по выбранному рейсу
        schedule: обрабатываемый json
        """
        self.filename = 'flight_schedule.json'
        self.cities_departure = {}
        self.cities_arrival = []
        self.dates = {}
        self.times = []
        self.companies = []
        self.schedule = {}

    def handle_name(self, text, context):
        name = re.search('\w+', text)
        if name:
            context['name'] = name.group()
            return True
        else:
            return False

    def handle_city_of_departure(self, text, context):
        self.read_json()
        self.get_city_of_departure()
        departure = self.handle_city(text, self.cities_departure)
        if departure:
            context['city_of_departure'] = self.cities_departure[departure]
            return True
        else:
            context['cities'] = self.write_warning(set(self.cities_departure))
            return False

    def handle_arrival_city(self, text, context):
        self.read_json()
        self.get_arrival_city(context)
        arrival = self.handle_city(text, self.cities_arrival)
        if arrival:
            context['arrival_city'] = arrival
            return True
        else:
            context['cities'] = self.write_warning(set(self.cities_arrival))
            return False

    def handle_date(self, text, context):
        today = datetime.now()
        self.read_json()
        date = re.search("^(0[1-9]|1[0-9]|2[0-9]|3[0-1])-(0[1-9]|1[0-2])-202[1-3]$", text)
        if date:
            date = date.group()
            self.get_date(context)
            if date in self.dates.keys():
                date_ = datetime.strptime(date, '%d-%m-%Y')
                if date_ >= today:
                    context['date'] = date
                    self.get_time(context, self.dates[date])
                    return True
                else:
                    warn = 'Вы выбрали дату, которая уже прошла. Выберите предстоящую дату.' \
                           ' Ближайшие даты вылета относительно введенной даты:\n\n'
                    context['wrong_dates'] = warn + self.write_warning(set(self.get_nearest_dates(date)))
                    return False
            else:
                warn = 'В указанную дату рейсов не обнаружено. Выберите подходящую дату.' \
                       ' Ближайшие даты вылета относительно введенной даты:\n\n'
                context['wrong_dates'] = warn + self.write_warning(set(self.get_nearest_dates(date)))
                return False
        else:
            context['wrong_dates'] = 'Дата введена некорректно. Повторите попытку.'
            return False

    def handle_time(self, text, context):
        self.read_json()
        time = re.search("(0[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", text)
        if time:
            time = time.group()
            for number, context_time in enumerate(context['times'].split('—')):
                if time in context_time:
                    context['time'] = time
                    print(number)
                    context['company'] = context['companies'].split('—')[number].replace('.', '')
                    landing_time = datetime.today() + timedelta(hours=random.randint(1, 7))
                    landing_time = datetime.strftime(landing_time, '%H:%M')
                    context['landing_time'] = landing_time
                    return True
            else:
                warn = 'В указанное время рейсов не обнаружено. Выберите подходящее время.' \
                       ' Рейсы относительно введенной даты:\n\n'
                context['times'] = warn + self.write_warning(set(self.times))
                return False
        else:
            warn = 'Время введено некорректно. Повторите попытку. Рейсы относительно введенной даты:\n\n'
            context['times'] = warn + self.write_warning(set(self.times))
            return False

    def handle_number_of_places(self, text, context):
        number_of_places = re.match('[1-5]$', text)
        if number_of_places:
            number_of_places = number_of_places.group()
            context['number_of_places'] = number_of_places
            return True
        else:
            return False

    def handle_comments(self, text, context):
        context['comment'] = text
        return True

    def handle_clarify_the_entered_data(self, text, context):
        clarify = re.match('[Да]|[Нет]|[Д]|[Н]|[д]|[н]|[да]|[нет]', text)
        if clarify:
            clarify = clarify.group()
            context['clarify'] = clarify
            return True
        else:
            return False

    def handle_check_phone_number(self, text, context):
        phone_number = re.match('([8]|[+7])\d{10}', text)
        if phone_number:
            phone_number = phone_number.group()
            context['phone_number'] = phone_number
            del context['times']
            del context['clarify']
            del context['companies']
            try:
                del context['cities']
                del context['wrong_dates']
            except Exception as exc:
                print(f'{exc.args} was empty')
            return True
        else:
            return False

    def handle_city(self, text, cities):
        _text = self.make_stemming(text)
        cities = list(set(cities))
        for num, city in enumerate(map(self.make_stemming, cities)):
            if city == _text:
                return cities[num]
        else:
            return False

    def read_json(self):
        with open(self.filename, mode='r', encoding='UTF-8') as schedule_file:
            self.schedule = json.load(schedule_file)

    def get_city_of_departure(self):
        """
        Получение данных о городах для отправления из json
        """
        for departure_city in self.schedule:
            departure_city = str(departure_city).split(':')[0][2:-1]
            city = re.search('\(.+\)', departure_city)
            if city:
                city = city.group()[1:-1]
            else:
                city_name = re.findall('\w+', departure_city)
                city = ''
                for word in city_name[1:]:
                    city += word
            if city not in self.cities_departure.keys():
                self.cities_departure[city] = departure_city

    def get_arrival_city(self, context):
        """
        Получение данных о городах для отправления из json по указанных параметрам

        :param context: сборщик данных
        """
        self.get_departure_elem(context)
        for arrival_city in self.schedule:
            self.cities_arrival.append(arrival_city)

    def get_departure_elem(self, context):
        for departure in list(self.schedule):
            for key in departure:
                if context['city_of_departure'] == key:
                    self.schedule = list(departure.values()).pop()

    def get_date(self, context):
        """
        Получение данных о датах из json по указанных параметрам

        :param context: сборщик данных
        """
        months = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04', 'мая': '05', 'июня': '06', 'июля':
            '07', 'августа': '08', 'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
        self.get_departure_elem(context)
        for date_time_company in self.schedule[context['arrival_city']]:
            for date in date_time_company:
                day = date.split(',')[0].split(' ')[0]
                month = date.split(',')[0].split(' ')[1]
                if len(day) == 1:
                    day = f'0{day}'
                json_date = f'{day}-{months[month]}-2021'
                self.dates[json_date] = date

    def get_time(self, context):
        """
        Получение данных о времени из json по указанных параметрам

        :param context: сборщик данных
        """
        self.get_departure_elem(context)
        self.schedule = self.schedule[context['arrival_city']]
        for dictionary in self.schedule:
            for time_and_company in dictionary.values():
                for time, company in time_and_company.items():
                    self.times.append(time)
                    self.companies.append(company)
        context['times'] = self.write_warning(set(self.times))
        context['companies'] = self.write_warning(self.companies)

    def get_nearest_dates(self, missing_date):
        """
        Получение ближайших дат к выбранной из json по указанных параметрам

        :param missing_date: выбранная дата
        """
        today = datetime.now()
        print(today)
        dates = []
        for date in self.dates:
            dates.append(date)
        dates.append(missing_date)
        dates_in_dt_format = []
        good_dates = []
        for date in dates:
            dates_in_dt_format.append(datetime.strptime(date, '%d-%m-%Y'))
        dates_in_dt_format.sort()
        for date in dates_in_dt_format:
            if date >= today:
                good_dates.append(datetime.strftime(date, '%d-%m-%Y'))
        if missing_date in good_dates:
            middle_index = good_dates.index(missing_date)
            good_dates.remove(missing_date)
            start = 0 if middle_index < 3 else middle_index - 3
            end = len(good_dates) + 1 if middle_index + 3 > len(good_dates) else good_dates[middle_index + 3]
            good_dates = good_dates[start:end]
        else:
            good_dates = good_dates[:6]
        return good_dates

    def make_stemming(self, word):
        """
        Отбрасывание окончаний при обработке введенного названия города

        :param word: название города
        """
        snowball = SnowballStemmer(language="russian")
        if word is not None:
            word = snowball.stem(word)
            return word

    def write_warning(self, entities):
        warning = ''
        for entity in sorted(entities):
            warning += f'— {entity}.\n'
        return warning

    def handle_cities_of_departure(self, text, context):
        """
        Получение городов отправления из json для сценария 'helping'

        :param context: сборщик данных
        """
        if text == '/d':
            self.read_json()
            self.get_city_of_departure()
            context['departure_cities'] = self.write_warning(self.cities_departure)
            return False
        else:
            return True

    def handle_make_ticket(self, context):
        for num in range(int(context['number_of_places'])):
            place = f"{random.randint(10, 99)}{random.choice('ABCDEFGHIKLMNOPQRSTVXYZ')}"
            path = f"tickets/airplane_ticket_{num + 1}.png"
            make_ticket(context, place, path)


