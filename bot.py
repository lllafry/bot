import os, telebot, random, io
from pymongo import MongoClient
from datetime import datetime 
from apibot import parse_message, parse_heroism, show_find, del_find, data_index_for_key
from plot import get_plot
from table import get_table_image
from mongo import *

token = os.environ['BOT_TOKEN']

client = MongoClient(os.environ['BOT_DB'])
db = client.tableaovbot

HELP = """список доступных команд:
*chatid* - вывести ID текущего чата
*table* - вывести таблицу отряда
*plot* <ключ> - вывести некий график
*find* <ключ> - вывести некие данные о вас (лс)
*delfind* <доступные номера> - удалить некие данные о вас (лс)
подробнее: /helpmore"""
HELPMORE = """бот принимает в лс форварды ваших профилей
<ключ> - доступные ключи можно узнать, отправив пустую команду
<доступные номера> - список номеров строк из find через пробел
delfind работает только следующей командой после find
(лс) - работает только в личной беседе, в группах игнорируется
бот пытается игнорировать массовое появление сообщений от вас
информация о командах администратора  по /admhelp"""
ADMHELP = """*cmd* - показывает содержимое внутреннего флага о вас в данный момент, имеет наивысший приоритет
*setcomm* <commname> - создает новую команду с низким приоритетом, commname - имя новой команды без слеша английскими буквами. далее нужно будет выслать сообщение с текстом (приоритет - после cmd)
*delcomm* <commname> - удаляет низкоприоритетную команду
*asuka* - на вызов не администратора отвечает 'игнорирую', на ваш вызов же ответит случайной фразой из некого набора
*addchat* - добавляет чат в список рабочих чатов, иначе бот по любой команде попытается выйти. нужно добавить бота в чат и вызвать эту команду
*adduser* <ID> - добавляет нового пользователя в некий временный белый список, новые пользователи (нет в таблице) полностью игнорируются ботом. после этой команды бот будет обрабатывать присланный пользователем 'херо'
find, plot могут иметь дополнительный аргумент (find <пользователь> <ключ>)
<пользователь> - ID, игровой ник, юзернейм. частично поддерживаются прошлые ники и юзернеймы, ники из нескольких слов
plot all <one key> - строит график для нескольких пользователей по одному ключу
*deluser* <пользователь> - удаляет всевозможные данные о игроке, в том числе административные права. после первого вызова команда покажет найденого по ключу пользователя и попросит подтвердить удаление повторным вводом команды
*admin* <ключ1> - добавить исключить пользователя из списка администраторов, работает по реплаю, <ключ1> - give / take, кандидат на добавление должен быть в таблице"""
ASUKA = ['так уж и быть, отвечу', 'чего тебе', 'baka', '*ррррррр*', '..', '...',
         'не надо мне тут']
TRY_CW3 = ['ну ну', 'he he' ,'это было близко' ,'что-то тут не то' ,'hmmmm' ,'вы ошиблись' ]
BAD_ANSWER = ['baka', '...', 'чуть все не сломалось', 'ну ай', 'так...',
              'лучше не повторяй такое', 'мне больно']
COMMANDS = ['table', 'help', 'setcomm', 'delcomm', 'get', 'asuka', 'addme',
            'admin', 'admins', 'find', 'delfind', 'deluser']



data = load_data(db)
comms = load_comms(db)
admins = load_admins(db)
chats = load_chats(db)

table_file_id = ''
is_table = False
leave_chats = True
act = [] # [[ID, chatID, [arg]]
users = [] # [ID, time_last_msg, num_msg, time_ban]

#token = os.environ['TELEGRAM_TOKEN']
#apihelper.CONNECT_TIMEOUT = 10

bot = telebot.TeleBot(token, num_threads=1)


def send_to_log(somelist):
    if len(somelist) == 0:
        return
    time = datetime.now().strftime('d h Y   H:M:S')
    for x in somelist:
        db.log.insert_one({'time': time, 'msg': x})

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
        num_msg_to_block = 5
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
    #print('work')    
    return bad_user, is_block // 1, get_arg_from_act(m, remove=remove)


@bot.message_handler(commands=['cmd'])#command a k
def command_cmd(m):
    bad_user, is_block, cmd = in_act(m, False)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    bot.send_message(m.chat.id, str(cmd))


@bot.message_handler(func=lambda x: get_arg_from_act(x, False)[0] == 'setcomm')#command (a) k
def work_act_add_text_for_setcomm(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user:
        return
    for i in range(len(comms)):
        if cmd[1] == comms[i]['comm']:
            comms[i]['text'] = m.text
            save_comms(db, comms)
            bot.send_message(m.chat.id, 'Команда {} успешно изменена'.format(cmd[1]))
            return
    comms.append({'comm': cmd[1], 'text': m.text})
    save_comms(db, comms)
    bot.send_message(m.chat.id, 'Команда {} успешно добавлена'.format(cmd[1]))


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
    bot.send_message(m.chat.id, msg, parse_mode='Markdown')


@bot.message_handler(commands=['helpmore'])#command
def command_helpmore(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    bot.send_message(m.chat.id, HELPMORE, parse_mode='Markdown')

@bot.message_handler(commands=['admhelp'])#command
def command_admhelp(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.from_user.id not in admins:
        return
    bot.send_message(m.chat.id, ADMHELP, parse_mode='Markdown')

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


@bot.message_handler(commands=['plot'])#command
def command_plot(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    s_key = extract_after_comm(m.text)
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


def extract_comm(s):
    if not s[0] == r'/':
        return ''
    return s.split()[0].split('@')[0][1:]

def extract_after_comm(s):
    if s.find(' ') == -1:
        return ''
    else:
        return s[s.find(' '):].strip()

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
        if not any(x['ID'] == ID for x in data['data']):
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


@bot.message_handler(commands=['find'])#command l k
def command_find(m):
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
    if m.chat.type != 'private':
        return
    s_key = extract_after_comm(m.text)
    NO_KEY = ('Добавьте к команде один из ключей: all, lvl, def, ' +
              'atc, class, nick, eqact, eqdef, eq.[spear, shield, ' +
              'helment, armor, glove, boot], возможен неполный набор ключа')
    if len(s_key) == 0:
        bot.send_message(m.chat.id, NO_KEY)
        return
    is_admin = True if m.from_user.id in admins else False
    msg, infostr, args = show_find(data, s_key, m.from_user.id, is_admin)
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
    if any(not x.isdigit() for x in strlist):
        bot.send_message(m.chat.id, random.choice(BAD_ANSWER))
    intlist = [int(x) for x in strlist]
    if (max(intlist) > len(cmd[2])) or (min(intlist) < 1):
        bot.send_message(m.chat.id, random.choice(BAD_ANSWER))
    is_admin = True if m.from_user.id in admins else False
    
    is_change = del_find(data, cmd[1], cmd[2], intlist)
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
            if data[i]['ad']['ID'] == ID:
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
        bot.send_message(m.chat.id, 'Хорошо, теперь пришлите выводимый ' +
                         'по команде {} текст'.format(command))


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
    if m.content_type != 'text':
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
            bot.send_message(m.chat.id, comms[i]['text'])
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
    date = time.ctime(m.forward_date)
    if m.forward_from.is_bot:
        from_who = 'бота' if m.forward_from.id != 669479634 else 'меня'
    else:
        from_who = 'пользователя'
    msg = 'Форвард от {} @{} ({})\nВремя: {} (+3)'.format(from_who,
                                                          m.forward_from.username,
                                                          m.forward_from.id, date)
    bot.reply_to(m, msg)


@bot.message_handler(fun=lambda x: True)
def all_private_data(m):
    if m.content_type != 'text':
        return
    bad_user, is_block, cmd = in_act(m)
    if bad_user or is_block:
        return
        


bot.polling(none_stop=True)
