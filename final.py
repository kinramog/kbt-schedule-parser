from html import entities
import time
import requests
from bs4 import BeautifulSoup
import telebot
#from telebot import types
import json
from threading import Thread

users_group_file = "users_groups.json"
def find_grup(user):
    with open("users_groups.json", "r", encoding='utf-8') as f_o:
        data_from_json = json.load(f_o)

        if str(user) in data_from_json:
            return data_from_json[str(user)]["group"].upper()

#i = 0
prev_len = 0
def parser(rasp_kbt_url):
    try:
        src_days = requests.get(rasp_kbt_url)
        soup_days = BeautifulSoup(src_days.text, 'lxml')
        dates_count = soup_days.find_all("div", class_="col-lg-4")
    except Exception as ex:
        print(f"Не удалось запарсить сайт с расписаниями в parser.\nТекст ошибки: {ex}")
    
    global prev_len
    #print(len(dates_count), prev_len)  
    #global i
    #i += 1
    #print(i)

    if len(dates_count) != prev_len:
        prev_len = len(dates_count)
        return True

def get_schedule(rasp_kbt_url, grup):
    try:
        src_days = requests.get(rasp_kbt_url)
        soup_days = BeautifulSoup(src_days.text, 'lxml')
        day_url = soup_days.find("a", class_="btn btn-primary").get("href")
        src_schedule = requests.get(rasp_kbt_url + day_url)
        soup_schedule = BeautifulSoup(src_schedule.text, 'lxml')
        tabs = soup_schedule.find_all("table")
    except Exception as ex:
        print(f"Проблема в get_schedule. Что то с сайтом?\nТекст ошибки: {ex}")

    schedule = ""
    for s in range(len(tabs)):
        rows = tabs[s].find_all("tr")
        col = rows[0].find_all("td")
        for i in range(len(col)):
            if grup in col[i].text.upper():
                norm_len = len(col)
                for j in range(len(rows)):
                    cols = rows[j].find_all("td")
                    if len(cols) < norm_len:         # для правки двойных строк
                        schedule += rows[j].find_all("td")[i-1].text.strip() + '\n' + '\n'
                    else:
                        schedule += rows[j].find_all("td")[i].text.strip() + '\n' + '\n'

                break

    if schedule != '':
        return schedule
    else:
        return 'Группа не найдена.\nВозможно, вы некорректно ввели название. \nСмена группы /change'

def telegram_bot(token):
    bot = telebot.TeleBot(token)
    rasp_kbt_url = "https://raspmoskbt.ru"
    
    def looker(message):
        while True:          
            #проверить, как работает цикл, при нескольких юзерах
            if parser(rasp_kbt_url):
                with open("users_groups.json", "r", encoding='utf-8') as f_o:
                    data_from_json = json.load(f_o)
                if str(message.from_user.id) in data_from_json: #Если id юзера совпадает с id в БД, то кидаем расписание
                    bot.send_message(message.chat.id, get_schedule(rasp_kbt_url, find_grup(message.chat.id)))
            time.sleep(300)   #парсит сайт каждые 5 минут

            

    @bot.message_handler(commands=['start']) # \\\\\\\\\\Запускает парсер////////// 
    def start(message):
        print(message.text, "  ---  ", message.from_user.username, message.chat.id)          # убрать потом
        with open("users_groups.json", "r", encoding='utf-8') as f_o:
            data_from_json = json.load(f_o)

        if str(message.from_user.id) not in data_from_json:
            bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! Напишите /reg")
        else:
            bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}!\nВы уже зарегистрированы. \nЖдите расписание. \nЧтобы сменить группу, напишите /change")

        th_looker = Thread(target=looker(message), args=())
        th_looker.start()


    @bot.message_handler(commands=['reg']) # \\\\\\\\\\Регистрация пользователя////////// 
    def reg(message):
        print(message.text, "  ---  ", message.from_user.username, message.chat.id)          # убрать потом
        with open("users_groups.json", "r", encoding='utf-8') as f_o:
            data_from_json = json.load(f_o)

        if str(message.from_user.id) not in data_from_json:
            bot.send_message(message.chat.id, "Напишите свою группу в формате ХХ00-00. Например: ИС22-21")
            bot.register_next_step_handler(message, group_write)
        else:
            bot.send_message(message.chat.id, "Вы уже зарегистрированы.\n Чтобы сменить группу, напишите /change")

    def group_write(message):
        print(message.text, "  ---  ", message.from_user.username, message.chat.id)          # убрать потом
        with open("users_groups.json", "r", encoding='utf-8') as f_o:
            data_from_json = json.load(f_o)

        user_id = message.from_user.id
        user_group = message.text.strip()

        if str(user_id) not in data_from_json:
            data_from_json[user_id] = {"group": user_group}
            bot.send_message(message.chat.id, f"Записал группу. Ваша группа: {user_group}")
        else:
            bot.send_message(message.chat.id, "Вы уже зарегистрированы.")

        with open('users_groups.json', 'w', encoding='utf-8') as f_o:
            json.dump(data_from_json, f_o, indent=4, ensure_ascii=False)


    @bot.message_handler(commands=['change']) # \\\\\\\\\\Смена группы////////// 
    def change(message):
        print(message.text, "  ---  ", message.from_user.username, message.chat.id)          # убрать потом

        bot.send_message(message.chat.id, "Введите новую группу")
        bot.register_next_step_handler(message, change_group)

    def change_group(message): 
        print(message.text, "  ---  ", message.from_user.username, message.chat.id)          # убрать потом
        with open("users_groups.json", "r", encoding='utf-8') as f_o:
            data_from_json = json.load(f_o)

        if str(message.chat.id) in data_from_json:
            data_from_json[str(message.chat.id)] = {"group": message.text}

        with open(users_group_file, 'w', encoding='utf-8') as f_o:
            json.dump(data_from_json, f_o, indent=4, ensure_ascii=False)
        bot.send_message(message.chat.id, f"Группу поменял. Теперь вы в {message.text}")


    @bot.message_handler(commands=['last_schedule']) # \\\\\\\\\\Присылает последнее расписание////////// 
    def last_schedule(message):
        print(message.text, "  ---  ", message.from_user.username)      # убрать потом

        with open(users_group_file, "r", encoding='utf-8') as f_o:
            data_from_json = json.load(f_o)

        if str(message.from_user.id) in data_from_json:
            bot.send_message(message.chat.id, get_schedule(rasp_kbt_url, find_grup(message.chat.id)))
        else:
            bot.send_message(message.chat.id, "Ты еще не зарегистрирован.\nНапиши /reg")

    #bot.infinity_polling()
    bot.infinity_polling(timeout=30, long_polling_timeout = 10)


def main():
    # th_pars = Thread(target=scheduled_pars, args=())
    # th_pars.start()
    try:
        th_bot = Thread(target=telegram_bot("ENTER YOUR TOKEN HERE"), args=())
        th_bot.start()
    except Exception as ex:
        print(f"Бот свалился по неведомой причине.\nТекст ошибки: {ex}")


if __name__ == "__main__":
    main()
