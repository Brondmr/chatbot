import settings
from bot import CraftsBot
from handlers import Handle
from vkbottle.bot import Bot, Message

import unittest
from unittest.mock import Mock, patch
from pony.orm import db_session, rollback
from freezegun import freeze_time


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()
    return wrapper


class TestCase(unittest.TestCase):

    def setUp(self):
        self.bot = Bot('')
        self.text = "Привет"
        self.RAW_EVENT = {
            'type': 'message_new',
            'object': {'date': 232142434, 'from_id': 234324234, 'id': 119, 'out': 0, 'peer_id': 89893434, 'text':
                       'привет, bot', 'conversation_message_id': 119, 'fwd_message': [], 'important': False,
                       'random_id': 0, 'attachments': [], 'is_hidden': False
                       },
            'group_id': 183721469
                         }
        self.INPUTS = [
            'привет',
            'Как дела',
            'Хочу начать бронь',
            '/ticket',
            'Алина',
            'Астрахань',
            'Хабаровск',
            'ы',
            '01-05-2021',
            '14-09',
            '14-10-2021',
            '30-09-2021',
            '17:20',
            '2',
            ':)',
            'да',
            '892222222222'
        ]
        self.EXPECTED_OUTPUTS = [
            settings.INTENTS[3]['answer'],
            settings.DEFAULT_ANSWER,
            settings.SCENARIOS['helping']['steps']['step1']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step0']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step1']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step2']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step3']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step3']['failure_text']
                .format(wrong_dates='Дата введена некорректно. Повторите попытку.'),
            settings.SCENARIOS['booking_tickets']['steps']['step3']['failure_text']
                .format(wrong_dates='В указанную дату рейсов не обнаружено. Выберите подходящую дату. '
                                    'Ближайшие даты вылета относительно введенной даты:'
                                    '\n\n— 29-09-2021.\n— 30-09-2021.\n'),
            settings.SCENARIOS['booking_tickets']['steps']['step3']['failure_text']
                .format(wrong_dates='Дата введена некорректно. Повторите попытку.'),
            settings.SCENARIOS['booking_tickets']['steps']['step3']['failure_text']
                .format(wrong_dates='В указанную дату рейсов не обнаружено. Выберите подходящую дату.'\
                        ' Ближайшие даты вылета относительно введенной даты:\n\n— 29-09-2021.\n— 30-09-2021.\n'),
            settings.SCENARIOS['booking_tickets']['steps']['step4']['text'].format(times='— 17:20.\n'),
            settings.SCENARIOS['booking_tickets']['steps']['step5']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step6']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step7']['text']
                .format(name='Алина', city_of_departure='Аэропорт Астрахань', arrival_city='Хабаровск',
                        date='30-09-2021', time='17:20', number_of_places='2', comment=':)'),
            settings.SCENARIOS['booking_tickets']['steps']['step8']['text'],
            settings.SCENARIOS['booking_tickets']['steps']['step9']['text']
        ]
        self.CONTEXT = {'name': 'Алина', 'city_of_departure': 'Аэропорт Астрахань', 'arrival_city':
                        'Хабаровск', 'date': '30-09-2021', 'time': '17:20', 'number_of_places': '2', 'landing_time':
                        '19:40', 'company': 'Аэрофлот'}

    def test1_message_text_ok(self):

        @self.bot.on.message(text=self.text)
        def test_hi_handler_1(message: Message):
            request = message
            assert request == self.text

        test_hi_handler_1(message=self.text)

    def test2_message_text_answer_ok(self):
        @self.bot.on.message(text="Пока")
        def test_hi_handler_2(message: Message):
            request = message
            assert request == self.text

        test_hi_handler_2(message=self.text)

    def test3_message_text_answer_err(self):
        @self.bot.on.message(text="Пока")
        def test_hi_handler_3(message: Message):
            request = message
            assert request != self.text

        test_hi_handler_3(message="Пока")

    def test4_message_text_answer_not_equal(self):
        text = "Пока"

        @self.bot.on.message(text=text)
        def test_hi_handler_4(message: Message):
            message_mock = Mock(Message)
            message_mock.text = message
            assert message_mock.answer(message_mock.text) is not text

        test_hi_handler_4(message=text)

    def test5_message_text_answer_are_equal(self):
        text = "Пока"

        @self.bot.on.message(text=text)
        def test_hi_handler_5(message: Message):
            message_mock = Mock(Message)
            message_mock.text = message
            assert message_mock.text is text

        test_hi_handler_5(message=text)

    @isolate_db
    @freeze_time("2021-09-13")
    def test_event(self):
        real_outputs = []
        with patch('models.Registration'), \
             patch('handlers.Handle.handle_make_ticket'),\
             patch('logging.getLogger'):
            for input_text in self.INPUTS:
                craft_bot = CraftsBot()
                answer = craft_bot.on_event(input_text, '111001111011111110011')
                if isinstance(answer, list):
                    answer = str(answer[0])
                real_outputs.append(answer)
            assert real_outputs == self.EXPECTED_OUTPUTS

    def test_handle_make_ticket(self):
        with patch('generate_ticket.make_driver_with_options'), \
             patch('generate_ticket.get_avatar'), \
             patch('generate_ticket.make_avatar'),\
             patch('os.remove'):
            Handle().handle_make_ticket(self.CONTEXT)


if __name__ == "__main__":
    unittest.main()
