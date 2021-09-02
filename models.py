from pony.orm import Database, Required, Json, Optional
from settings import DB_CONFIG


db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """Состтояние пользователя внутри сценария"""
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)


class Registration(db.Entity):
    """Заявка пользователя на бронирование билета"""
    name = Required(str)
    city_of_departure = Required(str)
    arrival_city = Required(str)
    date = Required(str)
    time = Required(str)
    company = Required(str)
    number_of_places = Required(str)
    comment = Optional(str)
    phone_number = Required(str)
    landing_time = Required(str)


db.generate_mapping(create_tables=True)
