import os
import time
import traceback
from io import BytesIO
import random
from os.path import isfile, join

import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor
from selenium import webdriver
from selenium.webdriver import ActionChains


# TODO: Download, unzip and cp to chatbot project chromedriver.exe.
#  Link = https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_win32.zip

try:
    WEB_DRIVER_PATH = "chromedriver.exe"
except Exception:
    exit('Download, unzip and cp to chatbot project chromedriver.exe.'
         '\n Link = https://chromedriver.storage.googleapis.com/92.0.4515.107/chromedriver_win32.zip')


def put_data(context, place):

    """Заполнение билета данными пользователя"""

    info = {'fio': [(47, 125), str(context['name']).upper()],
            'from_': [(47, 195), str(context['city_of_departure']).upper()],
            'to': [(47, 260), str(context['arrival_city']).upper()],
            'date': [(417, 260), context['date']],
            'time': [(530, 260), context['time']],
            'place': [(160, 325), str(place).upper()],
            'landing_time': [(530, 325), context['landing_time']],
            'company': [(417, 195), str(context['company']).upper()],
            'row': [(417, 325), str(random.randint(1, 30))],
            }
    template = 'ticket_template.png'
    font_path = 'ofont.ru_ZurichCyrillic BT.ttf'
    im = Image.open(template)
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(font_path, size=14)
    for info in info.values():
        coordinate, data = info

        draw.text(coordinate, data, font=font, fill=ImageColor.colormap['black'])
    return im


def make_driver_with_options(path):
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

        driver = webdriver.Chrome(executable_path=path, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """ Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"""})
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """const newProto = navigator.__
                  proto_delete newProto.webdriver navigator.__proto__ = newProto"""})
        driver.implicitly_wait(50)
        return driver
    except:
        print(traceback.format_exc())


def get_avatar(driver):

    """Получение возмодных аватаров с сайта генерации фото профиля"""

    try:
        url = 'https://tools.seo-zona.ru/face.html'
        driver.get(url)
        element = driver.find_element_by_id('start')
        action_chains = ActionChains(driver)
        action_chains.context_click(element).perform()
        element.click()
        time.sleep(3)
        driver.implicitly_wait(10)
        photos = driver.find_elements_by_css_selector('img')

        faces = []
        [faces.append(photo.get_attribute('src')) for photo in photos]
        return faces.pop()

    except:
        print(traceback.format_exc())
    finally:
        driver.quit()


def scale_image(input_image_path, out_path, width=None, height=None):

    """Уменьшение фото"""

    original_image = Image.open(input_image_path)

    w, h = original_image.size

    if width and height:
        max_size = (width, height)
    elif width:
        max_size = (width, h)
    elif height:
        max_size = (w, height)
    else:
        raise RuntimeError('Width or height required!')

    try:
        original_image.thumbnail(max_size, Image.ANTIALIAS)
        original_image.save(out_path)
        scaled_image = Image.open(out_path)
        return scaled_image
    except Exception as exc:
        print(exc.args)


def make_avatar(photo, im, out_path):

    """Добавление фото профиля на билет"""

    avatar_offset = (550, 62)
    try:
        response = requests.get(photo)
        avatar_file_like = BytesIO(response.content)

        scaled_photo = scale_image(input_image_path=avatar_file_like, out_path='scaled_img.jpg', width=130)
        scaled_photo = scaled_photo.convert('RGB')
        im.paste(scaled_photo, avatar_offset)
        temp_file = BytesIO()
        im.save(temp_file, 'png')
        if out_path:
            im.save(out_path.lower())
    except:
        print(traceback.format_exc())


def make_ticket(context, place, path):

    """Выполнение"""

    try:
        folder = join(os.getcwd(), 'tickets')
        files = [f for f in os.listdir(folder) if isfile(join(folder, f))]
        [os.remove(join(folder, file)) for file in files]
    except Exception as exc:
        print(exc.args)

    im = put_data(context, place)
    driver = make_driver_with_options(WEB_DRIVER_PATH)
    faces = get_avatar(driver)
    make_avatar(faces, im, path)
    try:
        os.remove('scaled_img.jpg')
    except Exception as exc:
        print(exc.args)



