import os, telebot, random, io, time, json
from pymongo import MongoClient
from datetime import datetime

import traceback
from requests.exceptions import ReadTimeout as req_err_1
from requests.exceptions import ConnectionError as req_err_2

from apibot import parse_message, parse_heroism, show_find, del_find
from apibot import data_index_for_key, KeyErr, update_battle_report, parse_battle_report
from plot import get_plot, get_activity
from table import get_table_image
from mongo import *
import text as text_module

try:
    import my_config
    from telebot import apihelper
    token = my_config.token
    client = MongoClient(my_config.db)
    apihelper.proxy = {'https': my_config.proxy}
    print('local bot')
except ImportError:
    token = os.environ['BOT_TOKEN']
    client = MongoClient(os.environ['BOT_DB'])

db = client.tableaovbot

HELP = text_module.HELP
HELPMORE = text_module.HELPMORE
ADMHELP = text_module.ADMHELP
ADMHELP2 = text_module.ADMHELP2

LOG_CHAT = -1001223157393
ME = 205959167
USERNAME = 'tableaovbot'

ASUKA = ['так уж и быть, отвечу', 'чего тебе', 'baka', '*ррррррр*', '..', '...',
         'не надо мне тут']
TRY_CW3 = ['ну ну', 'he he' ,'это было близко' ,'что-то тут не то' ,'hmmmm' ,
           'вы ошиблись' ]
BAD_ANSWER = ['baka', '...', 'чуть все не сломалось', 'ну ай', 'так...', '1 / 0',
              'лучше не повторяй такое', 'мне больно']
COMMANDS = ['break', 'cmd', 'start', 'help', 'helpmore', 'admhelp', 'admhelp2',
            'asuka', 'chatid', 'addchat', 'delchat', 'table', 'send', 'plot',
            'activity', 'adduser', 'admin', 'data', 'find','delfind', 'deluser',
            'restoreuser', 'setcomm', 'delcomm']
SETCOMM = ['text', 'sticker', 'document', 'voice', 'photo', 'audio']
err_text = 'err: что-то пошло не так'

data = load_data(db)
comms = load_comms(db)
admins = load_admins(db)
chats = load_chats(db)
btl = load_battle_tick(db)

table_file_id = ''
is_table = False
act = [] # [[ID, chatID, arg[]]
users = [] # [ID, time_last_msg, num_msg, time_ban]
temp_setcomm = {}

leave_chats = True

bot = telebot.TeleBot(token, num_threads=3)


### блок 'общих' функций ###
def SEND_DATA(m_chat, m_type, m_data):
    """Универсальная функция отправки сообщений"""
    if m_type == 'text':
        bot.send_message(m_chat, m_data)
    elif m_type == 'text_html':
        bot.send_message(m_chat, m_data, parse_mode='HTML')
    elif m_type == 'sticker':
        bot.send_sticker(m_chat, m_data)
    elif m_type == 'document':
        bot.send_document(m_chat, m_data)
    elif m_type == 'voice':
        bot.send_voice(m_chat, m_data)
    elif m_type == 'photo':
        bot.send_photo(m_chat, m_data)
    elif m_type == 'audio':
        bot.send_audio(m_chat, m_data)
    else:
        bot.send_message(LOG_CHAT, 'err SEND_DATA: получен' +
                         ' неизвестный формат данных ' + m_type)
    return

def GET_DATA(m):
    """Собирает данные из сообщения
    return dict
    dict: {'type': <some_type>, 'data': <some_data>}"""
    def rep(s):
        return s.replace('<', '&lt;').replace('>', '&gt;')
    is_entities = False
    if m.content_type not in SETCOMM:
        send_to_log('!err: GET_DATA: несоответсвие типов для (' + m.content_type + ')')
        raise SystemError('принудительная остановка бота')
    if m.content_type == 'text':
        to_data = m.text
        to_type = 'text'
        try:
            new_str = ''
            end_str = 0
            if len(m.entities) > 0:
                for i in range(len(m.entities)):
                    if m.entities[i].type in ['italic', 'bold', 'code']:
                        is_entities = True
                        if m.entities[i].type == 'code':
                            t = 'code'
                        else:
                            t = m.entities[i].type[0]
                        offset = m.entities[i].offset
                        new_str += rep(to_data[end_str:offset])
                        new_str += '<' + t + '>'
                        new_str += rep(to_data[offset:offset + m.entities[i].length])
                        new_str += '</' + t + '>'
                        end_str = offset + m.entities[i].length
                new_str += rep(to_data[end_str:])
                to_data = new_str
        except:
            is_entities = False
        if is_entities:
            to_type = 'text_html'
        return {'type': to_type, 'data': to_data}
    elif m.content_type == 'photo':
        return {'type': 'photo', 'data': m.json['photo'][-1]['file_id']}
    else:
        return {'type': m.content_type, 'data': m.json[m.content_type]['file_id']}


def send_to_log(somedata):
    if len(somedata) == 0:
        return
    if type(somedata) == type(''):
        SEND_DATA(LOG_CHAT, 'text', somedata)
    elif type(somedata) == type([]):
        SEND_DATA(LOG_CHAT, 'text', '\n'.join(somedata))
    else:
        SEND_DATA(LOG_CHAT, 'text', 'err send_to_log: формат (' +
                  str(type(somedata)) + ')')
    return


def append_arg_to_act(m, args):
    act.append([m.from_user.id, m.chat.id, args])


def get_arg_from_act(m, remove=True):
    """Возвращает arg[]
    arg[] как минимум содержит один аргумент с пустой строкой или именем
    действующей сложной функции;
    если это имя действующей функции, то количество аргументов тоже
    фиксировано и зависит от функции"""
    for i in range(len(act)):
        if (m.from_user.id == act[i][0]) and (m.chat.id == act[i][1]):
            result = act[i][2].copy()
            if remove:
                del act[i]
            return result
    return ['']


def clear_arg_from_act(m):
    for i in range(len(act)):
        if (m.from_user.id == act[i][0]) and (m.chat.id == act[i][1]):
            del act[i]
            return
    return


def in_act(m, remove=True):
    """Возвращает is_block, arg[]
    is_block: 0, если за секунду пользователем послано <= <число> сообщений
              m, где m - число сообщений, большее <число>
    arg[]: для работы сложных функций по типу setcomm"""
    bad_user = False
    # выход из других чатов
    if m.chat.type != 'private':
        if (m.chat.id not in chats) and leave_chats:
            bot.leave_chat(m.chat.id)
            bad_user = True
    
    num_msg_to_block = 8
    if m.from_user.id in admins:
        num_msg_to_block = 10
    is_find = False
    is_block = 0
    # поиск человека в users (т.е. он ранее отправлял сообщение боту)
    # users = [[user_1], [user_2], ...] # user: [ID, time_last_msg, num_msg, time_ban
    for i in range(len(users)):
        if users[i][0] == m.from_user.id:
            is_find = True
            if m.date == users[i][1]:# в одну секунду
                users[i][2] += 2
            elif m.date - users[i][1] < 10:# < 10 секунд 
                users[i][2] += 1
            else:# обнуление
                users[i][1], users[i][2] = m.date, 0
            if users[i][2] >= num_msg_to_block:# игнорирование текущего сообщения
                is_block = users[i][2]
            if users[i][2] > num_msg_to_block * 2:
                users[i][3] = m.date
            if users[i][3] != 0:# отправка в 'бан'
                if m.date - users[i][3] < 180:
                    bad_user = True
                    is_block = 100
                else:
                    users[i][3] = 0
            break
    if not is_find:
        if not any(x['ID'] == m.from_user.id for x in data):
            if (m.from_user.id != ME) and (m.from_user.id not in admins):
                bad_user = True
        if not bad_user:
            users.append([m.from_user.id, m.date, 0, 0])   
    return bad_user, is_block, get_arg_from_act(m, remove=remove)


### при переходе к супергруппе ###
@bot.message_handler(content_types=['migrate_to_chat_id'])
def command_change_chat_id(m):
    if m.chat.id not in chats: # здесь старое id чата, он должен быть в списке
        return
    chats.remove(m.chat.id)
    chats.append(m.migrate_to_chat_id)
    save_chats(db, chats)
    SEND_DATA(m.migrate_to_chat_id, 'text', 'чат эмигрировал с ' +
              str(m.chat.id) + ' на ' + str(m.migrate_to_chat_id))
    return



### игнорирование пользователей не из списков и покидание плохих чатов ###
###       +        вставка команды start, иначе было бы неудобно       ###
def is_bad_boy(m):
    # выход из других чатов
    if m.chat.type != 'private':
        if (m.chat.id not in chats) and leave_chats:
            bot.leave_chat(m.chat.id)
            return True
    
    num_msg_to_block = 12 if m.from_user.id in admins else 8
    
    is_find = False
    #0 - всё хорошо
    #1 - блокировка за флуд
    #2 - блокировка неизвестного пользователя
    is_block = 0
    # поиск человека в users (т.е. он ранее отправлял сообщение боту в текущей сессии)
    # users = [[user_1], [user_2], ...] # user: [ID, time_last_msg, num_msg, time_ban]
    for i in range(len(users)):
        if users[i][0] == m.from_user.id:
            is_find = True
            if m.date == users[i][1]:# в одну секунду с первым из серии (за 10 сек) сообщением
                users[i][2] += 2
            elif m.date - users[i][1] < 10:# менее 10 секунд: находимся в той же серии
                users[i][2] += 1
            else:# обнуление
                users[i][1], users[i][2] = m.date, 0
            if users[i][2] >= num_msg_to_block:# игнорирование текущего сообщения (но не отправка в 'бан')
                is_block = 1
            if users[i][2] > num_msg_to_block * 2:
                users[i][3] = m.date
            if users[i][3] != 0:# отправка в 'бан' на 3 минуты
                if m.date - users[i][3] < 180:
                    is_block = 1
                else:
                    users[i][3] = 0
            break
    if not is_find: # если пользователь в этой сессии не писал
        if not any(x['ID'] == m.from_user.id for x in data): # и его нет в таблице
            if (m.from_user.id != ME) and (m.from_user.id not in admins): # и он не админ или ME
                is_block = 2 # блокируется
        if not is_block: # читай "иначе"
            users.append([m.from_user.id, m.date, 0, 0])
    return is_block


@bot.message_handler(commands=['start'])
def command_start(m):
    if  m.chat.type != 'private':
        return
    val = is_bad_boy(m);
    if  val == 2:# неизвестный
        SEND_DATA(m.chat.id, 'text', 'Обратитесь к администратору бота')
    elif val == 0:# известный неблокированный
        clear_arg_from_act(m)
        SEND_DATA(m.chat.id, 'text_html', 'Пришлите форвард ответа CW1-бота ' +
                  'на команду <code>/hero</code> или прочтите /help')
    return

@bot.message_handler(func=is_bad_boy)
def kill_bad_boys(m):
    return


### блок напрямую связанных с шаговыми действиями команд ###
@bot.message_handler(commands=['break'])#command
def command_break(m):
    clear_arg_from_act(m)
    return


@bot.message_handler(commands=['cmd'])#command a k
def command_cmd(m):
    cmd = get_arg_from_act(m, False)
    SEND_DATA(m.chat.id, 'text', str(cmd))
    return


@bot.message_handler(func=lambda x: get_arg_from_act(x, False)[0] == 'send',
                     content_types=SETCOMM)#command vip
def send_message_vip(m):
    cmd = get_arg_from_act(m)
    some_data = GET_DATA(m)
    try:
        SEND_DATA(cmd[1], some_data['type'], some_data['data'])
    except:
        SEND_DATA(m.chat.id, 'text', 'отправить сообщение не удалось')
    return


@bot.message_handler(func=lambda x: get_arg_from_act(x, False)[0] == 'setcomm',
                     content_types=SETCOMM)#command (a) k
def work_act_add_data_for_setcomm(m):
    cmd = get_arg_from_act(m)
    is_was = False

    ID = str(m.from_user.id)
    if cmd[2] == cmd[3]:
        temp_setcomm[ID] = {'comm': cmd[1], 'd': []}

    try:
        temp_setcomm[ID]['d'].append(GET_DATA(m))
    except:
        SEND_DATA(m.chat.id, 'text', 'Ошибочка вышла')
        return

    if cmd[2] == 1:
        for i in range(len(comms)):
            if cmd[1] == comms[i]['comm']:
                is_was = True
                del comms[i]
                break
            
        comms.append(temp_setcomm[ID])
        save_comms(db, comms)
        del temp_setcomm[ID]
        
        if is_was:
            SEND_DATA(m.chat.id, 'text', 'Команда ' + cmd[1] +' успешно изменена')
        else:
            SEND_DATA(m.chat.id, 'text', 'Команда ' + cmd[1] +' успешно добавлена')
    else:
        append_arg_to_act(m, [cmd[0], cmd[1], cmd[2] - 1, cmd[3]])
    return


### ловля и игнорирование команд с чужим юзернеймом ###
def is_another_bot(m):
    if m.content_type != 'text':
        return False
    if not m.text[0] == r'/':
        return False
    list_comm = m.text.split()[0].split('@') # в первом слове разделяю на до @ и после
    if len(list_comm) == 2 and list_comm[1].lower() != USERNAME and list_comm[1].lower().endswith('bot'):
        return True
    return False


@bot.message_handler(func=is_another_bot)
def kill_bad_commands(m):
    clear_arg_from_act(m)
    return


@bot.message_handler(commands=['help'])#command
def command_help(m):
    clear_arg_from_act(m)
    msg = HELP
    if len(comms) > 0:
        msg += '\n\nдополнительные команды:\n'
        msg += ', '.join([x['comm'] for x in comms])
    SEND_DATA(m.chat.id, 'text_html', msg)
    return


@bot.message_handler(commands=['helpmore'])#command
def command_helpmore(m):
    clear_arg_from_act(m)
    SEND_DATA(m.chat.id, 'text_html', HELPMORE)
    return


@bot.message_handler(commands=['admhelp'])#command
def command_admhelp(m):
    clear_arg_from_act(m)
    if m.from_user.id not in admins:
        return
    SEND_DATA(m.chat.id, 'text_html', ADMHELP)
    return


@bot.message_handler(commands=['admhelp2'])#command
def command_admhelp2(m):
    clear_arg_from_act(m)
    if m.from_user.id not in admins:
        return
    SEND_DATA(m.chat.id, 'text_html', ADMHELP2)
    return


@bot.message_handler(commands=['asuka'])#command
def command_asuka(m):
    clear_arg_from_act(m)
    if m.from_user.id in admins:
        SEND_DATA(m.chat.id, 'text', random.choice(ASUKA))
    else:
        SEND_DATA(m.chat.id, 'text', 'игнорирую')
    return


@bot.message_handler(commands=['chatid'])#command
def command_chatid(m):
    clear_arg_from_act(m)
    SEND_DATA(m.chat.id, 'text', m.chat.id)
    return


@bot.message_handler(commands=['addchat'])#command a -l
def command_addchat(m):
    clear_arg_from_act(m)
    if (m.chat.type == 'private' or m.chat.id in chats or
        m.from_user.id not in admins):
        return
    chats.append(m.chat.id)
    save_chats(db, chats)
    return


@bot.message_handler(commands=['delchat'])#command a -l
def command_delchat(m):
    clear_arg_from_act(m)
    if (m.chat.type == 'private' or m.chat.id not in chats or
        m.from_user.id not in admins):
        return
    chats.remove(m.chat.id)
    save_chats(db, chats)
    return


@bot.message_handler(commands=['table'])#command
def command_table(m):
    clear_arg_from_act(m)
    global is_table, table_file_id
    is_change, nbtl = update_battle_report(data, btl[0], btl[1], datetime.now())
    if is_change:
        is_table = False
        btl[0] = nbtl
        save_data(db, data);
        save_battle_tick(db, btl);
        
    if is_table:
        SEND_DATA(m.chat.id, 'photo', table_file_id)
    else:
        table_file_id = bot.send_photo(
            m.chat.id, get_table_image(data)).json['photo'][-1]['file_id']
        is_table = True
    return


@bot.message_handler(commands=['data'])#command a
def command_data(m):
    clear_arg_from_act(m)
    all_data = {}
    all_data['comms'] = comms
    all_data['admins'] = admins
    all_data['chats'] = chats
    all_data['users'] = data
    with io.StringIO() as file:
        json.dump(all_data, file)
        with io.BytesIO(file.getvalue().encode()) as bfile:
            bfile.name = ('data ' + datetime.strftime(
                datetime.now(), '%d %h %y') + '.txt')
            SEND_DATA(m.chat.id, 'document', bfile)
    return


### блок команд с аргументами ###
def extract_comm(s):
    if not s[0] == r'/':
        return ''
    return s.split()[0].split('@')[0][1:]

def extract_after_comm(s):
    if s.find(' ') == -1:
        return ''
    else:
        return s[s.find(' ') + 1:].strip()

def extract_key(s):
    return (' '.join(extract_comm(s).split('_')[1:]) +
            ' ' + extract_after_comm(s)).strip()

def comm_name(m, name):
    if m.content_type != 'text':
        return False
    return name == extract_comm(m.text).split('_')[0]

def try_extract_ID(s):
    key = extract_key(s)
    if len(key) == 0:
        return 'Потерян обязательный аргумент ID', None
    try:
        return '', int(key)
    except:
        return 'err: полученная строка не является ID (' + key + ')', None


@bot.message_handler(func=lambda m: comm_name(m, 'send'))#command self vip
def command_send(m):
    clear_arg_from_act(m)
    if m.from_user.id != ME:
        return
    msg, chat_id = try_extract_ID(m.text)
    if len(msg) > 0:
        SEND_DATA(m.chat.id, 'text', msg)
        return
    append_arg_to_act(m, ['send', chat_id])
    SEND_DATA(m.chat.id, 'text', 'следующее присланное сообщение будет ' +
              'отправлено на указанное id (отмена по /break)')
    return


@bot.message_handler(func=lambda m: comm_name(m, 'plot'))#command
def command_plot(m):
    clear_arg_from_act(m)
    is_admin = True if m.from_user.id in admins else False
    try:
        plot_file_bytes = get_plot(data, extract_key(m.text),
                                   m.from_user.id, is_admin)
    except KeyErr as e:
        SEND_DATA(m.chat.id, 'text', e)
        return
    except Exception as e:
        SEND_DATA(m.chat.id, 'text', err_text)
        send_to_log('err in plot (' + str(e) + ') with\n' + m.text)
        return
    SEND_DATA(m.chat.id, 'photo', plot_file_bytes)
    return


@bot.message_handler(func=lambda m: comm_name(m, 'activity'))#command a
def command_activity(m):
    clear_arg_from_act(m)
    try:
        plot_file_bytes = get_activity(data, extract_key(m.text))
    except KeyErr as e:
        SEND_DATA(m.chat.id, 'text', e)
        return
    except Exception as e:
        SEND_DATA(m.chat.id, 'text', err_text)
        send_to_log('err in activity (' + str(e) + ') with\n' + m.text)
        return
    SEND_DATA(m.chat.id, 'photo', plot_file_bytes)
    return


@bot.message_handler(func=lambda m: comm_name(m, 'adduser'))#command a
def command_adduser(m):
    clear_arg_from_act(m)
    msg, ID = try_extract_ID(m.text)
    if len(msg) > 0:
        SEND_DATA(m.chat.id, 'text', msg)
        return
    users.append([ID, m.date, 0, 0])
    SEND_DATA(m.chat.id, 'text', 'Пользователь добавлен в временный белый список.')
    return
    

@bot.message_handler(func=lambda m: comm_name(m, 'admin'))#command a
def command_admin(m):
    clear_arg_from_act(m)
    if (m.from_user.id not in admins) and (m.from_user.id != ME):
        return
    key = extract_key(m.text)
    if key not in ['give', 'take']:
        return
    try:
        ID = m.reply_to_message.from_user.id
    except:
        return
    if key == 'give':
        if ID not in admins:
            admins.append(ID)
            save_admins(db, admins)
            SEND_DATA(m.chat.id, 'text', 'ok')
    elif key == 'take':
        if ID in admins:
            admins.remove(ID)
            save_admins(db, admins)
            SEND_DATA(m.chat.id, 'text', 'ok')
    return


@bot.message_handler(func=lambda m: comm_name(m, 'find'))#command l k
def command_find(m):
    cmd = get_arg_from_act(m)
    if m.chat.type != 'private':
        return
    is_admin = m.from_user.id in admins
    try:
        infostr, args = show_find(data, extract_key(m.text),
                                  cmd, m.from_user.id, is_admin)
    except KeyErr as e:
        SEND_DATA(m.chat.id, 'text', e)
        return
    except Exception as e:
        SEND_DATA(m.chat.id, 'text', err_text)
        send_to_log('err in find (' + str(e) + ') with\n' + m.text)
        return
    append_arg_to_act(m, args)
    SEND_DATA(m.chat.id, 'text_html', infostr)
    return


@bot.message_handler(commands=['delfind'])#command l k
def command_delfind(m):
    cmd = get_arg_from_act(m)
    if m.chat.type != 'private':
        return
    if cmd[0] != 'find':
        return
    strlist = extract_after_comm(m.text).split()
    if len(strlist) == 0:
        return
    if any(not x.isdigit() for x in strlist):
        SEND_DATA(m.chat.id, 'text', random.choice(BAD_ANSWER))
        return
    intlist = [int(x) for x in strlist]
    if (max(intlist) > len(cmd[2]) + cmd[4] - 1) or (min(intlist) < cmd[4]):
        SEND_DATA(m.chat.id, 'text', random.choice(BAD_ANSWER))
        return
    
    is_change = del_find(data, cmd[1], cmd[2], intlist, cmd[4])
    if is_change:
        save_data(db, data)
        SEND_DATA(m.chat.id, 'text', 'done')
    return


@bot.message_handler(func=lambda m: comm_name(m, 'deluser'))#command a k
def command_deluser(m):
    global is_table
    cmd = get_arg_from_act(m)
    if m.from_user.id not in admins:
        return
    key = extract_key(m.text)
    
    if cmd[0] == 'deluser':
        if len(key) > 0:
            return
        deleted_user = None
        ID = cmd[1]
        nick = cmd[2]
        for i in range(len(data)):# удаляю в основной базе
            if data[i]['ID'] == ID:
                deleted_user = data[i].copy()
                del data[i]
                break
        for i in range(len(users)):# удаляю из добавленных по /adduser
            if users[i][0] == ID:
                del users[i]
                break
        is_table = False
        if deleted_user != None:
            save_back_data(db, deleted_user)
            save_data(db, data)
        save_admins(db, admins)
        
        SEND_DATA(m.chat.id, 'text', 'Игрок {} был удален'.format(nick))
        return
    
    if len(key) == 0:
        return

    cur_index = data_index_for_key(data, key)
    if cur_index == -1:
        SEND_DATA(m.chat.id, 'text', 'Пользователь не найден')
        return
    ID = data[cur_index]['ID']
    nick = data[cur_index]['gm']['nick']
    username = data[cur_index]['ad']['username']
    
    append_arg_to_act(m, ['deluser', ID, nick])
    SEND_DATA(m.chat.id, 'text', 'Для удаления игрока {} {} {} нажмите /deluser'.format(
        nick, username, ID))
    return


@bot.message_handler(commands=['restoreuser'])#command a k
def command_restoreuser(m):
    global is_table
    clear_arg_from_act(m)
    if m.from_user.id not in admins:
        return
    msg, ID = try_extract_ID(m.text)
    if len(msg) > 0:
        SEND_DATA(m.chat.id, 'text', msg)
        return
    some_data = load_back_data(db, ID)
    if some_data == None:
        SEND_DATA(m.chat.id, 'text', 'Пользователь не найден')
        return
    del some_data['_id']
    is_table = False
    data.append(some_data)
    save_data(db, data)
    SEND_DATA(m.chat.id, 'text', some_data['gm']['nick'] + ' восстановлен')
    return


@bot.message_handler(func=lambda m: comm_name(m, 'setcomm'))#command a k
def command_setcomm(m):
    clear_arg_from_act(m)
    if m.from_user.id not in admins:
        return
    key = extract_key(m.text).lower()
    if len(key) == 0:
        SEND_DATA(m.chat.id, 'text',
                  'err: ожидалось название команды для добавления')
        return
    num = 1
    listkey = key.split()
    if len(listkey) == 2:
        try:
            num = int(listkey[1])
        except:
            SEND_DATA(m.chat.id, 'text', 'err: ожидалось число (' + listkey[1] + ')')
            return
        if num < 1 or num > 10:
            SEND_DATA(m.chat.id, 'text', 'err: возможно только 1-10 (' + str(num)
                      + ')')
            return
        else:
            key = listkey[0]
    listkey = key.split()
    if len(listkey) != 1:
        SEND_DATA(m.chat.id, 'text', 'err: ожидалась команда из одного слова ('
                  + key + ')')
        return
    if any((ord(char) > ord('z') or ord(char) < ord('a')) for char in key):
        SEND_DATA(m.chat.id, 'text', 'err: команда должна содержать только ' +
                  'английские буквы (' + key + ')')
        return

    if key in COMMANDS:
        SEND_DATA(m.chat.id, 'text', 'Имя для команды зарезервировано')
        return
    append_arg_to_act(m, ['setcomm', key, num, num])
    ending = ['о', 'е'] if num == 1 else ['ы', 'я']
    SEND_DATA(m.chat.id, 'text', 'Хорошо, теперь пришлите выводим' +
              ending[0] + 'е  по команде ' + key + ' сообщени' + ending[1])
    return


@bot.message_handler(func=lambda m: comm_name(m, 'delcomm'))#command a
def command_delcomm(m):
    clear_arg_from_act(m)
    if m.from_user.id not in admins:
        return
    key = extract_key(m.text)
    if len(key) == 0:
        SEND_DATA(m.chat.id, 'text', 'err: ожидалось название команды для удаления')
        return
    if len(key.split()) != 1:
        SEND_DATA(m.chat.id, 'text', 'err: ожидалась команда из одного слова (' +
                  key + ')')
        return
    if any((ord(char) > ord('z') or ord(char) < ord('a')) for char in key):
        SEND_DATA(m.chat.id, 'text', 'err: такой команды точно нет (' + key + ')')
        return

    if key in COMMANDS:
        SEND_DATA(m.chat.id, 'text', random.choice(BAD_ANSWER))
        return
    for i in range(len(comms)):
        if key == comms[i]['comm']:
            del comms[i]
            save_comms(db, comms)
            SEND_DATA(m.chat.id, 'text', 'Команда ' + key + ' успешно удалена')
            return
    SEND_DATA(m.chat.id, 'text', 'Команды ' + key + ' нет в списке')
    return


### для команд из setcomm ###
def is_from_comm(m):
    if  m.content_type != 'text':
        return False
    command = extract_comm(m.text)
    if len(command) == 0:
        return False
    if any([x['comm'] == command for x in comms]):
        return True
    return False


@bot.message_handler(func=is_from_comm)
def command_from_comm(m):
    clear_arg_from_act(m)
    command = extract_comm(m.text)
    for i in range(len(comms)):
        if command == comms[i]['comm']:
            for y in range(len(comms[i]['d'])):
                if y > 0:
                    time.sleep(0.15)
                try:
                    SEND_DATA(m.chat.id, comms[i]['d'][y]['type'],
                              comms[i]['d'][y]['data'])
                except:
                    SEND_DATA(m.chat.id, 'text',
                              'Данные по команде вероятно были потеряны')
            break
    return


### блок использующих форварды команд ###
def forward_ID(m, msg_text_end_with=''):
    """Возвращает ID форварда или 0"""
    try:
        if m.forward_from.id > 0:
            if len(msg_text_end_with) > 0:
                if not m.text.endswith(msg_text_end_with):
                    return 0
            return m.forward_from.id
    except:
        pass
    return 0


def forward_ID_find(m, text_to_find):
    """Возвращает ID форварда или 0"""
    try:
        if m.forward_from.id > 0:
            if m.text.find(text_to_find) != -1:
                return m.forward_from.id
    except:
        pass
    return 0


@bot.message_handler(func=lambda m: forward_ID(m, r'/class') == 587303845)#from CW1
def parse_forward_from_CW1(m):
    global is_table
    clear_arg_from_act(m)
    if m.chat.type != 'private':
        return
    is_admin = True if m.from_user.id in admins else False
    is_change_data, is_change_table, inter = parse_message(data, m, is_admin)
    send_to_log(inter['msg'])
    SEND_DATA(m.chat.id, 'text', inter['main'])
    if is_change_data:
        save_data(db, data)
    if is_change_table:
        is_table = False
    return


#@bot.message_handler(func=lambda m: forward_ID(m, 'через отряд') == 279170062)#from kesha
#def parse_forward_with_heroism(m):
#    global is_table
#    clear_arg_from_act(m)
#    is_change, inter = parse_heroism(data, m)
#    send_to_log(inter['msg'])
#    if is_change:
#        save_data(db, data)
#        is_table = False
#    if 'main' in inter.keys():
#       SEND_DATA(m.chat.id, 'text', inter['main'])
#    return


@bot.message_handler(func=lambda m: forward_ID_find(m, 'Твои результаты в бою:') == 587303845)#battle report
def parse_report_from_battle(m):
    global is_table
    clear_arg_from_act(m)

    is_change, nbtl = update_battle_report(data, btl[0], btl[1], datetime.now())
    if is_change:
        is_table = False
        btl[0] = nbtl
        save_data(db, data)
        save_battle_tick(db, btl)
        #send_to_log('Произошла битва ' + str(btl[0]) + '.')
    
    is_change, inter = parse_battle_report(data, m, btl[0], btl[1])
    send_to_log(inter['msg'])
    if is_change:
        save_data(db, data)
        is_table = False
    if 'main' in inter.keys():
       SEND_DATA(m.chat.id, 'text', inter['main'])
    return


@bot.message_handler(func=lambda m: forward_ID(m, r'/stock') == 265204902)#from CW3
def forward_from_CW3(m):
    clear_arg_from_act(m)
    if m.chat.type != 'private':
        return
    SEND_DATA(m.chat.id, 'text', random.choice(TRY_CW3))
    return


@bot.message_handler(func=lambda m: forward_ID(m), content_types=SETCOMM)#from any
def forward_from_any_user(m):
    clear_arg_from_act(m)
    if m.chat.type != 'private':
        return
    if m.forward_from.is_bot:
        from_who = 'бота' if m.forward_from.id != 669479634 else 'меня'
    else:
        from_who = 'пользователя'
    bot.reply_to(m, 'Форвард от ' + from_who + ' @' + m.forward_from.username +
                 ' (' + str(m.forward_from.id) + ')\nВремя: ' +
                 str(time.ctime(m.forward_date + 3 * 3600)) + ' (+3)')
    return


### команда - заглушка ###
@bot.message_handler(content_types=SETCOMM)
def some_data(m):
    clear_arg_from_act(m)
    return


### основной цикл ###
send_to_log('~~запуск бота~~')
while True:
    try:
        bot.polling(none_stop=True,timeout=10)
    except (req_err_1, req_err_2):
        pass
    except Exception as e:
        try:
            send_to_log('~ошибка при поллинге\n\n' +
                        str(e) + '\n\n' + str(traceback.format_exc()))
        except:
            send_to_log('~ошибка при поллинге\n\n' + str(e))
        send_to_log('!остановка бота')
        raise SystemError('принудительная остановка бота')
