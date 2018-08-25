import os, telebot, random, io, time, json
from pymongo import MongoClient
from datetime import datetime
import traceback
from apibot import parse_message, parse_heroism, show_find, del_find, data_index_for_key
from plot import get_plot
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


ASUKA = ['так уж и быть, отвечу', 'чего тебе', 'baka', '*ррррррр*', '..', '...',
         'не надо мне тут']
TRY_CW3 = ['ну ну', 'he he' ,'это было близко' ,'что-то тут не то' ,'hmmmm' ,'вы ошиблись' ]
BAD_ANSWER = ['baka', '...', 'чуть все не сломалось', 'ну ай', 'так...',
              'лучше не повторяй такое', 'мне больно']
COMMANDS = ['table', 'help', 'setcomm', 'delcomm', 'get', 'asuka', 'addme',
            'admin', 'admins', 'find', 'delfind', 'deluser']
SETCOMM = ['text', 'sticker', 'document', 'voice', 'photo']


data = load_data(db)
comms = load_comms(db)
admins = load_admins(db)
chats = load_chats(db)

table_file_id = ''
is_table = False
leave_chats = True
act = [] # [[ID, chatID, [arg]]
users = [] # [ID, time_last_msg, num_msg, time_ban]

bot = telebot.TeleBot(token, num_threads=3)


def send_to_log(somelist):
    if len(somelist) == 0:
        return
    string = ''
    for i in range(len(somelist)):
        string += somelist[i] + '\n'
    bot.send_message(-1001223157393, string)
    #time = datetime.now().strftime('%d %h %Y   %H:%M:%S')
    #for x in somelist:
        #db.log.insert_one({'time': time, 'msg': x})

def append_arg_to_act(m, args):
    act.append([m.from_user.id, m.chat.id, args])

def get_arg_from_act(m, remove=True):
    for i in range(len(act)):
        if (m.from_user.id == act[i][0]) and (m.chat.id == act[i][1]):
            result = act[i][2].copy()
            if remove:
                del act[i]
            return result
    return ['']


def in_act(m, remove=True):
    """Возвращает is_block, arg[]
    is_block: 0, если за секунду пользователем послано <= <число> сообщений
              m, где m - число сообщений, большее <число>
    arg[]: для работы сложных функций по типу setcomm"""
    
    bad_user = False
    if m.chat.type != 'private':
        if (m.chat.id not in chats) and leave_chats:
            bot.leave_chat(m.chat.id)
            bad_user = True
    num_msg_to_block = 3
    if m.from_user.id in admins:
        num_msg_to_block = 4
    is_find = False
    is_block = 0
    for i in range(len(users)):
        if users[i][0] == m.from_user.id:
            is_find = True
            if m.date == users[i][1]:# в одну секунду
                users[i][2] += 1
                if users[i][2] >= num_msg_to_block:
                    is_block = users[i][2]
            elif m.date - users[i][1] < 3:# < 3 секунд
                users[i][2] += 0.5
                if users[i][2] >= num_msg_to_block:
                    is_block = users[i][2]
            else:# обнуление
                users[i][1], users[i][2] = m.date, 0
            if users[i][2] > 10:
                users[i][3] = m.date
            if users[i][3] != 0:
                if m.date - users[i][3] < 120:
                    bad_user = True
                else:
                    users[i][3] = 0
            break
    if not is_find:
        if not any(x['ID'] == m.from_user.id for x in data):
            bad_user = True
        users.append([m.from_user.id, m.date, 0, 0])   
    return bad_user, is_block // 1, get_arg_from_act(m, remove=remove)


@bot.message_handler(commands=['cmd'])#command a k
def command_cmd(m):
    bad_user, is_block, cmd = in_act(m, False)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    bot.send_message(m.chat.id, str(cmd))


@bot.message_handler(func=lambda x: get_arg_from_act(x, False)[0] == 'setcomm',
                     content_types=SETCOMM)#command (a) k
def work_act_add_data_for_setcomm(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user:
        return
    is_was, good_type = False, False
    for i in range(len(comms)):
        if cmd[1] == comms[i]['comm']:
            is_was = True
            del comms[i]
            break
    try:
        if m.content_type == 'text':
            to_send = m.text
            try:
                new_str = ''
                end_str = 0
                if len(m.entities) > 0:
                    for i in range(len(m.entities)):
                        if m.entities[i].type in ['italic', 'bold', 'code']:
                            if m.entities[i].type == 'code':
                                t = 'code'
                            else:
                                t = m.entities[i].type[0]
                            offset = m.entities[i].offset
                            new_str += to_send[end_str:offset]
                            new_str += '<' + t + '>'
                            new_str += to_send[offset:offset + m.entities[i].length]
                            new_str += '</' + t + '>'
                            end_str = offset + m.entities[i].length
                    new_str += to_send[end_str:]
                    to_send = new_str
            except:
                pass
            comms.append({'comm': cmd[1], 'type': 'text',
                          'data': to_send})
            good_type = True
        elif m.content_type == 'sticker':
            comms.append({'comm': cmd[1], 'type': 'sticker',
                          'data': m.json['sticker']['file_id']})
            good_type = True
        elif m.content_type == 'document':
            comms.append({'comm': cmd[1], 'type': 'document',
                          'data': m.json['document']['file_id']})
            good_type = True
        elif m.content_type == 'voice':
            comms.append({'comm': cmd[1], 'type': 'voice',
                          'data': m.json['voice']['file_id']})
            good_type = True
        elif m.content_type == 'photo':
            comms.append({'comm': cmd[1], 'type': 'photo',
                          'data': m.json['photo'][-1]['file_id']})
            good_type = True
    except:
        bot.send_message(m.chat.id, 'Ошибочка вышла')
        return

    save_comms(db, comms)
    if not good_type and is_was:
        bot.send_message(m.chat.id, 'Команда ' + cmd[1] +
                         ' была удалена, а для новой данных не оказалось')
        return
    if is_was:
        bot.send_message(m.chat.id, 'Команда ' + cmd[1] +' успешно изменена')
    else:
        bot.send_message(m.chat.id, 'Команда ' + cmd[1] +' успешно добавлена')


@bot.message_handler(commands=['start'])#command
def command_start(m):
    bad_user, is_block, cmd = in_act(m)
    if is_block:
        return
    if  m.chat.type == 'private':
        if bad_user:
            bot.send_message(m.chat.id, 'Обратитесь к администратору бота')
        else:
            bot.send_message(m.chat.id, 'Пришлите форвард ответа CW1-бота на команду /hero или прочтите /help')


@bot.message_handler(commands=['help'])#command
def command_help(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    msg = HELP
    for i in range(len(comms)):
        if i == 0:
            msg += '\n\nдополнительные команды:\n'
        msg += comms[i]['comm']
        if i != len(comms) - 1:
            msg += ', '
    bot.send_message(m.chat.id, msg, parse_mode='HTML')
    #Markdown


@bot.message_handler(commands=['helpmore'])#command
def command_helpmore(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    bot.send_message(m.chat.id, HELPMORE, parse_mode='HTML')

@bot.message_handler(commands=['admhelp'])#command
def command_admhelp(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    bot.send_message(m.chat.id, ADMHELP, parse_mode='HTML')

@bot.message_handler(commands=['asuka'])#command
def command_asuka(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or (is_block > 5):
        return
    if m.from_user.id in admins:
        bot.send_message(m.chat.id, random.choice(ASUKA))
    else:
        bot.send_message(m.chat.id, 'игнорирую')


@bot.message_handler(commands=['chatid'])#command
def command_chatid(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    bot.send_message(m.chat.id, m.chat.id)


@bot.message_handler(commands=['addchat'])#command a -l
def command_addchat(m):
    if (m.chat.type != 'private') and (m.chat.id not in chats) and (m.from_user.id in admins):
        chats.append(m.chat.id)
        save_chats(db, chats)
    bad_user, is_block, cmd = in_act(m)


@bot.message_handler(commands=['table'])#command
def command_table(m):
    global is_table, table_file_id
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if is_table:
        bot.send_photo(m.chat.id, table_file_id)
    else:
        image_file_bytes = get_table_image(data)
        answer = bot.send_photo(m.chat.id, image_file_bytes)
        del image_file_bytes
        try:
            table_file_id = answer.json['photo'][-1]['file_id']
            del answer
            is_table = True
        except:
            pass

def extract_comm(s):
    if not s[0] == r'/':
        return ''
    return s.split()[0].split('@')[0][1:]

def extract_after_comm(s):
    if s.find(' ') == -1:
        return ''
    else:
        return s[s.find(' '):].strip()

def plot_work(m):
    if m.content_type != 'text':
        return False
    command = extract_comm(m.text)
    if len(command) == 0:
        return False
    if command[:4] != 'plot':
        return False
    return True


@bot.message_handler(func=plot_work)#command
def command_plot(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    s_key = (extract_comm(m.text)[4:].replace('_', ' ') + ' ' + extract_after_comm(m.text)).strip()
    
    if len(s_key) == 0:
        bot.send_message(m.chat.id, 'Добавьте к команде один или несколько ключей:'+
                         ' lvl, atc, def, eqatc, eqdef')
        return
    is_admin = True if m.from_user.id in admins else False
    msg, plot_file_bytes = get_plot(data, s_key, m.from_user.id, is_admin)
    if len(msg) == 0:
        answer = bot.send_photo(m.chat.id, plot_file_bytes)
        del plot_file_bytes, answer
    else:
        bot.send_message(m.chat.id, msg)



@bot.message_handler(commands=['adduser'])#command a
def command_adduser(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    ID = extract_after_comm(m.text)
    if not ID.isdigit():
        return
    users.append([int(ID), m.date, 0, 0])
    bot.send_message(m.chat.id, 'ok')
    

@bot.message_handler(commands=['admin'])#command a
def command_admin(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    todo = extract_after_comm(m.text)
    if todo not in ['give', 'take']:
        return
    if (m.from_user.id not in admins) and (m.from_user.id != 205959167):
        return
    try:
        ID = m.reply_to_message.from_user.id
    except:
        return
    if todo == 'give':
        if not any(x['ID'] == ID for x in data):
            bot.send_message(m.chat.id, 'Пользователь должен быть в таблице')
        elif ID in admins:
            return
        else:
            admins.append(ID)
            save_admins(db, admins)
            bot.send_message(m.chat.id, 'ok')
    else:
        if ID in admins:
            admins.remove(ID)
            save_admins(db, admins)
            bot.send_message(m.chat.id, 'ok')


@bot.message_handler(commands=['data'])#command a
def command_data(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    all_data = {}
    all_data['comms'] = comms
    all_data['admins'] = admins
    all_data['chats'] = chats
    all_data['users'] = data
    #doc = open(r'config/alldata.txt', 'rb')
    #answer = bot.send_document(m.chat.id, doc)
    #return
    with io.StringIO() as file:
        json.dump(all_data, file)
        data_bytes = file.getvalue().encode()
        with io.BytesIO(data_bytes) as bfile:
            bfile.name = 'data.txt'
            answer = bot.send_document(m.chat.id, bfile)
        del data_bytes, answer


def find_work(m):
    if m.content_type != 'text':
        return False
    command = extract_comm(m.text)
    if len(command) == 0:
        return False
    if command[:4] != 'find':
        return False
    return True


@bot.message_handler(func=find_work)#command l k
def command_find(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.chat.type != 'private':
        return
    
    s_key = (extract_comm(m.text)[4:].replace('_', ' ') + ' ' + extract_after_comm(m.text)).strip()

    NO_KEY = ('Добавьте к команде один из ключей: all, lvl, def, ' +
              'atc, class, nick, eqact, eqdef, eq.[spear, shield, ' +
              'helment, armor, glove, boot], возможен неполный набор ключа')
    if len(s_key) == 0:
        bot.send_message(m.chat.id, NO_KEY)
        return
    is_admin = True if m.from_user.id in admins else False
    start_with = 0
    ID = m.from_user.id
    if cmd[0] == 'find' and s_key == 'next':
        if len(cmd[2]) > 0:
            start_with = cmd[2][-1] + 1
            ID = cmd[1]
            s_key = cmd[3]
    msg, infostr, args = show_find(data, s_key, ID, is_admin, start_with)
    if len(msg) == 0:
        bot.send_message(m.chat.id, infostr, parse_mode='HTML')
        append_arg_to_act(m, args)
    else:
        bot.send_message(m.chat.id, msg)
            
        

@bot.message_handler(commands=['delfind'])#command l k
def command_delfind(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.chat.type != 'private':
        return
    if cmd[0] != 'find':#to find
        return
    strlist = extract_after_comm(m.text).split()
    if len(strlist) == 0:
        return
    if any(not x.isdigit() for x in strlist):
        bot.send_message(m.chat.id, random.choice(BAD_ANSWER))
        return
    intlist = [int(x) for x in strlist]
    if (max(intlist) > len(cmd[2]) + cmd[4] - 1) or (min(intlist) < cmd[4]):
    #if (max(intlist) > len(cmd[2])) or (min(intlist) < 1):
        bot.send_message(m.chat.id, random.choice(BAD_ANSWER))
        return
    is_admin = True if m.from_user.id in admins else False
    
    is_change = del_find(data, cmd[1], cmd[2], intlist, cmd[4])
    if is_change:
        save_data(db, data)
        bot.send_message(m.chat.id, 'done')


@bot.message_handler(commands=['deluser'])#command a k
def command_deluser(m):
    global is_table
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    
    w_key = extract_after_comm(m.text)
    
    if cmd[0] == 'deluser':
        ID = cmd[1]
        nick = cmd[2]
        if len(w_key) > 0:
            return
        for i in range(len(data)):# удаляю в основной базе
            if data[i]['ID'] == ID:
                del data[i]
                break
        for i in range(len(users)):# удаляю из добавленных по /adduser
            if users[i][0] == ID:
                del users[i]
                break
        for i in range(len(admins)):# удаляю из админов
            if admins[i] == ID:
                del admins[i]
                break
        is_table = False
        save_data(db, data)
        save_admins(db, admins)
        
        bot.send_message(m.chat.id, 'Игрок {} был удален'.format(nick))
        return
    
    if len(w_key) == 0:
        return

    cur_index = data_index_for_key(data, w_key)
    if cur_index == -1:
        return
    ID = data[cur_index]['ID']
    nick = data[cur_index]['gm']['nick']
    
    bot.send_message(m.chat.id, 'Для удаления игрока {} {} {} нажмите /deluser'.format(
        nick, data[cur_index]['ad']['username'], ID))
    append_arg_to_act(m, ['deluser', ID, nick])
            

@bot.message_handler(commands=['setcomm'])#command a k
def command_setcomm(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id in admins:
        command = extract_after_comm(m.text).lower()
        if len(command) == 0:
            bot.send_message(m.chat.id, 'Потерян указатель на команду')   
            return
        if command in COMMANDS:
            bot.send_message(m.chat.id, 'Имя для команды зарезервировано')
            return
        if any((ord(char) > ord('z') or ord(char) < ord('a')) for char in command):
            bot.send_message(m.chat.id, 'Команда должна содержать только английские буквы')
            return
        append_arg_to_act(m, ['setcomm', command])
        bot.send_message(m.chat.id, 'Хорошо, теперь пришлите выводимое ' +
                         'по команде {} сообщение'.format(command))


@bot.message_handler(commands=['delcomm'])#command a
def command_delcomm(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id in admins:
        command = extract_after_comm(m.text)
        if len(command) == 0:
            bot.send_message(m.chat.id, 'Потерян указатель на команду')   
            return
        if command in COMMANDS:
            bot.send_message(m.chat.id, random.choice(BAD_ANSWER))
            return
        if any((ord(char) > ord('z') or ord(char) < ord('a')) for char in command):
            bot.send_message(m.chat.id, 'Такой команды точно нет')   
            return
        for i in range(len(comms)):
            if command == comms[i]['comm']:
                del comms[i]
                save_comms(db, comms)
                bot.send_message(m.chat.id, 'Команда {} успешно удалена'.format(command))
                return
        bot.send_message(m.chat.id, 'Команды {} нет в списке'.format(command))   


def is_from_comm(m): #последняя
    if  m.content_type != 'text':
        return False
    command = extract_comm(m.text).lower()
    if len(command) == 0:
        return False
    for i in range(len(comms)):
        if command == comms[i]['comm']:
            return True
    return False

@bot.message_handler(func=is_from_comm)#last command
def command_from_comm(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    command = extract_comm(m.text).lower()
    for i in range(len(comms)):
        if command == comms[i]['comm']:
            try:
                if comms[i]['type'] == 'text':
                    try:
                        bot.send_message(m.chat.id, comms[i]['data'], parse_mode='HTML')
                    except:
                        bot.send_message(m.chat.id, comms[i]['data'])
                elif comms[i]['type'] == 'sticker':
                    bot.send_sticker(m.chat.id, comms[i]['data'])
                elif comms[i]['type'] == 'document':
                    bot.send_document(m.chat.id, comms[i]['data'])
                elif comms[i]['type'] == 'voice':
                    bot.send_voice(m.chat.id, comms[i]['data'])
                elif comms[i]['type'] == 'photo':
                    bot.send_photo(m.chat.id, comms[i]['data'])
            except:
                bot.send_message(m.chat.id, 'Данные по команде вероятно были потеряны')    
            break

def forward_ID(m, msg_text_end_with=''):
    """Возвращает ID форварда или 0"""
    if m.content_type != 'text':
        return 0
    try:
        if m.forward_from.id > 0:
            if m.text.endswith(msg_text_end_with):
                return m.forward_from.id
    except:
        pass
    return 0

@bot.message_handler(func=lambda m: forward_ID(m, r'/class') == 587303845)#from CW1
def parse_forward_from_CW1(m):
    global is_table
    bad_user, is_block, cmd = in_act(m)
    if bad_user or (is_block > 10):
        return
    is_change_data, is_change_table, inter = parse_message(data, m, admins)
    send_to_log(inter['msg'])
    bot.send_message(m.chat.id, inter['main'])
    if is_change_data:
        save_data(db, data)
    if is_change_table:
        is_table = False
    del inter


@bot.message_handler(func=lambda m: forward_ID(m, 'через отряд') == 279170062)#from kesha
def parse_forward_with_heroism(m):
    global is_table
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    is_change, inter = parse_heroism(data, m)
    send_to_log(inter['msg'])
    if is_change:
        save_data(db, data)
        is_table = False
    if 'main' in inter.keys():
        bot.send_message(m.chat.id, inter['main'])


@bot.message_handler(func=lambda m: forward_ID(m, r'/stock') == 265204902)#from CW3
def forward_from_CW3(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    msg = random.choice(TRY_CW3)
    bot.send_message(m.chat.id, msg)


@bot.message_handler(func=lambda m: forward_ID(m))#from any
def forward_from_any_user(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.chat.type != 'private':
        return
    date = time.ctime(m.forward_date + 3 * 3600)
    if m.forward_from.is_bot:
        from_who = 'бота' if m.forward_from.id != 669479634 else 'меня'
    else:
        from_who = 'пользователя'
    msg = 'Форвард от {} @{} ({})\nВремя: {} (+3)'.format(from_who,
                                                          m.forward_from.username,
                                                          m.forward_from.id, date)
    bot.reply_to(m, msg)


@bot.message_handler(content_types=SETCOMM)
def all_private_data(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
        
bot.send_message(-1001223157393, '~первичный запуск бота')
is_first_work = True
while True:
    try:
        if is_first_work:
            is_first_work = False
        else:
            try:
                bot.send_message(-1001223157393, '~запуск бота')
            except:
                pass
        bot.polling(none_stop=True,timeout=10)
    except requests.exceptions:
        bot.send_message(-1001223157393, '~хе-хе')
    except Exception as e:
        try:
            
            bot.send_message(-1001223157393, '~ошибка при поллинге\n\n' +
                             str(e) + '\n\n' + str(traceback.format_exc()))
        except:
            bot.send_message(-1001223157393, '~ошибка при поллинге\n\n' +
                             str(e))
        bot.send_message(-1001223157393, '!остановка бота')
        raise SystemExit(1)
        
