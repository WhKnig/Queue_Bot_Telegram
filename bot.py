import json
from collections import OrderedDict
from telebot import TeleBot
import config

bot = TeleBot(config.token)
queues = OrderedDict()
user_states = {}  # Словарь для отслеживания состояния пользователей
participants_message_id = {}  # Словарь для хранения ID сообщений участников очереди по каждой очереди
user_message_ids = {}  # Словарь для хранения ID сообщений пользователей
existing_queues_message_id = {}  # Словарь для хранения ID сообщений о существующих очередях

def read_json():
    global queues
    try:
        with open('queues.json', 'r', encoding='utf-8') as f:
            queues_data = json.load(f)
            queues = OrderedDict((int(k), OrderedDict(v)) for k, v in queues_data.items())
    except FileNotFoundError:
        queues = OrderedDict()
        write_json()
    except json.JSONDecodeError:
        queues = OrderedDict()
        write_json()

def write_json():
    with open('queues.json', 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in queues.items()}, f, ensure_ascii=False)

def clean_queue_name(text):
    """Удаляем имя бота, если оно есть."""
    return text.split('@')[0]

def delete_messages(chat_id, message_ids):
    """Удаляет указанные сообщения в чате."""
    for message_id in message_ids:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
           print(f'Не удалось удалить сообщение {message_id}: {e}')

def delete_messages_lambda(chat_id, message_ids):
    """Использует lambda для удаления сообщений."""
    delete = lambda message_id: bot.delete_message(chat_id, message_id)
    for message_id in message_ids:
        try:
            delete(message_id)
        except Exception as e:
            print(f'Не удалось удалить сообщение {message_id}: {e}')

@bot.message_handler(commands=['start'])
def start_command(msg):
    user_id = msg.from_user.id
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду
    response_msg = bot.send_message(msg.chat.id, 'Дарова!\nЮзайте команды для работы с очередями.\n'
                                   'Команды:\n'
                                   '/create_queue - Новая очередь\n'
                                   '/delete_queue - Удалить очередь\n'
                                   '/join_queue - Встать в очередь\n'
                                   '/leave_queue - Выйти из очереди\n'
                                   '/queue_status - Статус очереди\n'
                                   '/help - Для вывода данного сообщения\n\n'
                                   'P.s если создаете новую очередь то название "/Example" желательно без пробелов')


@bot.message_handler(commands=['help'])
def help_command(msg):
    user_id = msg.from_user.id
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду
    response_msg = bot.send_message(msg.chat.id,
                     'Команды:\n'
                     '/create_queue - Новая очередь\n'
                     '/delete_queue - Удалить очередь\n'
                     '/join_queue - Встать в очередь\n'
                     '/leave_queue - Выйти из очереди\n'
                     '/queue_status - Статус очереди\n'
                     '/help - Для вывода данного сообщения\n\n'
                     'P.s если создаете новую очередь то название "/Example" желательно без пробелов')



@bot.message_handler(commands=['create_queue'])
def create_queue_command(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду
    user_states[user_id] = 'awaiting_queue_name_create'
    response_msg = bot.send_message(msg.chat.id, f'@{username}, введите название новой очереди.')
    user_message_ids[user_id] = [response_msg.message_id]  # Сохраняем ID сообщения

@bot.message_handler(commands=['delete_queue'])
def delete_queue_command(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду

    # Проверка на приватный чат
    if msg.chat.type == 'private':
        a = list_queues_join(msg.chat.id)
        if a == 1:
            user_states[user_id] = 'awaiting_queue_name_delete'
            response_msg = bot.send_message(msg.chat.id, f'@{username}, введите название очереди для удаления.')
            user_message_ids[user_id] = [response_msg.message_id]  # Сохраняем ID сообщения
    else:
        if is_user_admin(msg.chat.id, user_id):  # Проверка на администратора
            if list_queues_join(msg.chat.id) == 1:
                user_states[user_id] = 'awaiting_queue_name_delete'
                response_msg = bot.send_message(msg.chat.id, f'@{username}, введите название очереди для удаления.')
                user_message_ids[user_id] = [response_msg.message_id]  # Сохраняем ID сообщения
        else:
            response_msg = bot.send_message(msg.chat.id, f'@{username},чё дох*я умный? Иди на х*й)))\n'
                                                         'Только админы могут удалять очереди, сорян(((')
            


@bot.message_handler(commands=['join_queue'])
def join_queue_command(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду
    if list_queues_join(msg.chat.id) == 1:
        user_states[user_id] = 'awaiting_queue_name_join'
        response_msg = bot.send_message(msg.chat.id, f'@{username}, введите название очереди, в которую хотите встать.')
        user_message_ids[user_id] = [response_msg.message_id]  # Сохраняем ID сообщения

@bot.message_handler(commands=['leave_queue'])
def leave_queue_command(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду
    if list_queues_join(msg.chat.id) == 1:
        user_states[user_id] = 'awaiting_queue_name_leave'
        response_msg = bot.send_message(msg.chat.id, f'@{username}, введите название очереди, из которой хотите выйти.')
        user_message_ids[user_id] = [response_msg.message_id]  # Сохраняем ID сообщения

@bot.message_handler(commands=['queue_status'])
def queue_status_command(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    delete_messages_lambda(msg.chat.id, [msg.message_id])  # Удаляем команду
    if list_queues_join(msg.chat.id) == 1:
        user_states[user_id] = 'awaiting_queue_name_status'
        response_msg = bot.send_message(msg.chat.id, f'@{username}, введите название очереди для просмотра участников.')
        user_message_ids[user_id] = [response_msg.message_id]  # Сохраняем ID сообщения

@bot.message_handler(func=lambda msg: True)
def handle_text(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name  # Используем username или имя, если username нет
    text = clean_queue_name(msg.text.strip())  # Очищаем команду от имени бота

    # Удаляем все сообщения пользователя, кроме последнего
    if user_id not in user_message_ids:
        user_message_ids[user_id] = []

    if user_id in user_states:
        state = user_states[user_id]

        # Удаляем предыдущие сообщения и текущее сообщение пользователя
        messages_to_delete = user_message_ids[user_id] + [msg.message_id]

        # Удаляем предыдущее сообщение о существующих очередях, если оно существует
        if msg.chat.id in existing_queues_message_id:
            messages_to_delete.append(existing_queues_message_id[msg.chat.id])

        delete_messages_lambda(msg.chat.id, messages_to_delete)

        if state == 'awaiting_queue_name_create':
            if msg.chat.id not in queues:
                queues[msg.chat.id] = OrderedDict()
            if text not in queues[msg.chat.id]:
                queues[msg.chat.id][text] = OrderedDict()
                write_json()
                response_msg = bot.send_message(msg.chat.id, f'Очередь "{text}" создана пользователем @{username}!')
            else:
                response_msg = bot.send_message(msg.chat.id, f'@{username}, очередь "{text}" уже существует!')
            del user_states[user_id]

        elif state == 'awaiting_queue_name_delete':
            if text in queues.get(msg.chat.id, {}):
                del queues[msg.chat.id][text]
                write_json()
                response_msg = bot.send_message(msg.chat.id, f'Очередь "{text}" удалена пользователем @{username}!')
            else:
                response_msg = bot.send_message(msg.chat.id, f'@{username}, очередь "{text}" не найдена!')
            del user_states[user_id]

        elif state == 'awaiting_queue_name_join':
            if text in queues.get(msg.chat.id, {}):
                user_id_str = str(user_id)
                if user_id_str not in queues[msg.chat.id][text]:
                    queues[msg.chat.id][text][user_id_str] = (msg.from_user.first_name, msg.from_user.last_name or '')
                    write_json()

                    # Удаляем предыдущее сообщение участников этой очереди, если оно существует
                    if text in participants_message_id:
                        try:
                            bot.delete_message(msg.chat.id, participants_message_id[text])
                        except Exception as e:
                            print(f'Не удалось удалить сообщение: {e}')

                    participants = [f"{name} {last_name}" for id, (name, last_name) in \
                                    queues[msg.chat.id][text].items()]
                    participants_list = "\n".join(participants)

                    if participants:
                        participants_message = bot.send_message(msg.chat.id, f'Очередь "{text}".\n'
                                                                             f'Участники очереди:\n\n{participants_list}')
                    else:
                        participants_message = bot.send_message(msg.chat.id, f'Очередь "{text}" пустая!')
                    participants_message_id[text] = participants_message.id  # Сохраняем ID сообщения для конкретной очереди
                    response_msg = bot.send_message(msg.chat.id, f'Пользователь @{username} добавлен в очередь "{text}".')
                else:
                    response_msg = bot.send_message(msg.chat.id, f'@{username}, вы уже в очереди "{text}".')
            else:
                response_msg = bot.send_message(msg.chat.id, f'@{username},очередь "{text}" не найдена!')
            del user_states[user_id]

        elif state == 'awaiting_queue_name_leave':
            if text in queues.get(msg.chat.id, {}):
                user_id_str = str(user_id)
                if user_id_str in queues[msg.chat.id][text]:
                    del queues[msg.chat.id][text][user_id_str]
                    write_json()

                    # Удаляем предыдущее сообщение участников этой очереди, если оно существует
                    if text in participants_message_id:
                        try:
                            bot.delete_message(msg.chat.id, participants_message_id[text])
                        except Exception as e:
                            print(f'Не удалось удалить сообщение: {e}')

                    participants = [f"{name} {last_name}" for id, (name, last_name) in \
                                    queues[msg.chat.id][text].items()]
                    participants_list = "\n".join(participants)

                    if participants:
                        participants_message = bot.send_message(msg.chat.id, f'Очередь "{text}".\n'
                                                                             f'Участники очереди:\n\n{participants_list}')
                    else:
                        participants_message = bot.send_message(msg.chat.id, f'@{username}, очередь "{text}" пустая!')
                    participants_message_id[text] = participants_message.id  # Сохраняем ID сообщения для конкретной очереди
                    response_msg = bot.send_message(msg.chat.id, f'Пользователь @{username} вышел из очереди "{text}".')
                else:
                    response_msg = bot.send_message(msg.chat.id, f'@{username} не в очереди "{text}".')
            else:
                response_msg = bot.send_message(msg.chat.id, f'@{username}, очередь "{text}" не найдена!')
            del user_states[user_id]

        elif state == 'awaiting_queue_name_status':
            if text in queues.get(msg.chat.id, {}):
                participants = [f"{name} {last_name}" for id, (name, last_name) in \
                                queues[msg.chat.id][text].items()]
                participants_list = "\n".join(participants)

                if participants:
                    response_msg = bot.send_message(msg.chat.id, f'Очередь "{text}".\n'
                                                                 f'Участники очереди:\n\n{participants_list}')
                else:
                    response_msg = bot.send_message(msg.chat.id, f'Очередь "{text}" пустая!')
            else:
                response_msg = bot.send_message(msg.chat.id, f'Очередь "{text}" не найдена!')
            del user_states[user_id]

    # Обновляем ID сообщений пользователя
    user_message_ids[user_id] = [msg.message_id]  # Сохраняем только последнее сообщение пользователя


def list_queues(chat_id):
    """Выводит список доступных очередей для данного чата."""
    if chat_id in queues and queues[chat_id]:
        response = 'Существующие очереди:\n\n' + '\n\n'.join(queues[chat_id].keys())
        existing_queues_message = bot.send_message(chat_id, response)
        existing_queues_message_id[chat_id] = existing_queues_message.message_id  # Сохраняем ID сообщения
    else:
        bot.send_message(chat_id, 'Нет существующих очередей.')

def list_queues_join(chat_id):
    """Выводит список доступных очередей для данного чата."""
    if chat_id in queues and queues[chat_id]:
        response = 'Существующие очереди:\n\n' + '\n\n'.join(queues[chat_id].keys())
        existing_queues_message = bot.send_message(chat_id, response)
        existing_queues_message_id[chat_id] = existing_queues_message.message_id  # Сохраняем ID сообщения
        return 1
    else:
        bot.send_message(chat_id, 'Нет существующих очередей.')
        return 0

def is_user_admin(chat_id, user_id):
    """Проверяет, является ли пользователь администратором."""
    administrators = bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in administrators)

if __name__ == '__main__':
    read_json()
    bot.polling(none_stop=True)
