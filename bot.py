# -*- coding: utf-8 -*-
import logging
import os
from pony.orm import db_session
import handlers
import settings
from vkbottle.bot import Bot, Message   # TODO fix version!!
from vkbottle import PhotoMessageUploader
from models import UserState, Registration

try:
    from settings import TOKEN
except ImportError:
    exit('DO cp settings.py.default settings.py and set TOKEN')

bot = Bot(token=TOKEN)


class CraftsBot:
    """
    Echo bot для vk.com
    Use python3.7
    """

    def __init__(self):
        """

        type: тип события
        bot: экземпляр класса 'Бот' для группы vk.com
        log: переменная логгирования для группы
        """

        self.type = None
        self.log = logging.getLogger('bot')
        self.handlers = handlers.Handle()

    def configure_logging(self):
        """
        Формирование логирования в консоль и в лог-файл
        """

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        stream_handler.setLevel(logging.INFO)

        file_handler = logging.FileHandler(filename="bot.log", mode="a", encoding="UTF-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%d-%m-%Y %H:%M"))
        file_handler.setLevel(logging.DEBUG)

        self.log.addHandler(stream_handler)
        self.log.addHandler(file_handler)
        self.log.setLevel(logging.DEBUG)

    @db_session
    def on_event(self, message, user_id):
        """
        Выбор сценария для ответа пользователю

        :param message: сообщение пользователя
        :param user_id: id пользователя
        :return: ответ пользователю
        """

        self.log.info('Получено сообщение: %s', str(message))

        state = UserState.get(user_id=user_id)
        if state:
            for intent in settings.INTENTS:
                if (intent['name'] == 'Помощь' or intent['name'] == 'Закакз билета') \
                        and message.lower() in intent['token']:
                    state.delete()
                    return self.start_scenario(user_id, intent['scenario'])
            else:
                return self.continue_scenario(message, state)

        else:
            for intent in settings.INTENTS:
                self.log.debug(f'Пользователь получил {intent}')
                if any(token in message.lower() for token in intent['token']):
                    if intent['answer']:
                        return intent['answer']
                    else:
                        return self.start_scenario(user_id, intent['scenario'])
            else:
                return settings.DEFAULT_ANSWER

    def start_scenario(self, user_id, scenario_name):
        """
        Начало сценария

        :param user_id: идентификатор пользователя
        :param scenario_name: наименование сценария
        :return: ответ пользователю
        """

        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        text_to_send = step['text']
        UserState(user_id=user_id, scenario_name=scenario_name, step_name=first_step, context={})
        return text_to_send

    def continue_scenario(self, message, state):
        """
        Продолжение действующего сценария для пользователя, который его не завершил

        :param state: информация о пользователе
        :param message: информация о сообщении пользователя
        :return: ответ пользователю
        """

        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]
        handler = getattr(self.handlers, step['handler'])

        if handler(text=message, context=state.context):
            next_step = steps[step['next_step']]
            text_to_send = next_step['text'].format(**state.context)

            if next_step['next_step']:
                state.step_name = step['next_step']
                state_context = state.context
            else:
                if len(state.context) == len(steps):
                    self.log.info(f'Зарегистрирован вылет с параметрами: {state.context}')
                    Registration(**state.context)
                state_context = state.context
                state.delete()

            return self.send_step(next_step, text_to_send, state_context)

        else:
            return step['failure_text'].format(**state.context)

    def send_step(self, step, text_to_send, context):
        if 'image' in step:
            handler = getattr(self.handlers, step['image'])
            handler(context)
            return [text_to_send,  False]
        else:
            return [text_to_send, True]


@bot.on.message()
async def run(message: Message):
    """
    Ассинхронная функция ожидания ответа на любое сообщение пользователя

    :param message: информация о сообщении пользователя
    """

    users_info = await bot.api.users.get([str(message.from_id)])
    user_id = str(users_info[0].id)
    info = crafts_bot.on_event(message.text, user_id)
    if isinstance(info, list):
        if not info[1]:
            for num in range(len(os.listdir(path="tickets"))):
                path = f"tickets/airplane_ticket_{num + 1}.png"
                uploader = PhotoMessageUploader(api=bot.api)
                photo = await uploader.upload(path)
                if photo:
                    answer = message.answer(attachment=photo)
                    await answer
        info = info[0]
    answer = message.answer(str(info))
    await answer

if __name__ == "__main__":
    crafts_bot = CraftsBot()
    crafts_bot.configure_logging()

    bot.run_forever()
