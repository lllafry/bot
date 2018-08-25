import datetime

def _toint(s):
    """Превращает максимальное число символов строки в число
    Пример:
    21вуп34 -> 21, -31 e -> -31, e32 -> 0, 3.1 -> 3"""
    isNegative = False
    if len(s) > 1:
        if s[0] == '-' and s[1].isdigit():
            isNegative = True
    for i in range(len(s)+1):
        if not(s[i:i+1].isdigit() or ((i == 0) and isNegative)):
            break
    if i > 0:
        return int(s[0:i])
    else:
        return 0

def _decode_equip_upgrade(s):
    """Вырезает улучшение экипировки из строки и помещает его в отдельную
    return str1, str2, True
    str1 - экипировка без улучшения
    str2 - улучшение экипировки
    True - флаг о том
    """
    if len(s) < 5:
        return [s, '', True]
    if s[0] == '\u26a1':
        if s[2] == '0':
            return [s[4:], '', True]
        return [s[s.find(' ', 3, 10)+1:], '+' + s[2:s.find(' ', 3, 10)], True]
    else:
        return [s, '', True]

def _decode_equip(s):
    """Парсит строку с экипировкой
    return eq, inter
    eq - dict с пропарсенной экипировкой
    inter - dict в внутренними сообщениями парсера
    """
    code = False
    ticks = 0
    s_orig = s
    inter = {'msg': [], 'send': []}
    #   0      1      2      3     4    5
    # spear shield helment glove armor boot
    result = ['', '', '', '', '', '']
    if s == '':
        return [dict(spear = result[0], shield = result[1], helmet = result[2],
            glove = result[3], armor = result[4], boot = result[5]),
            inter]
        
    s = [_decode_equip_upgrade(x) for x in s.split('\n')]
    # Сначала поиск сетов Т1-Т4 (кроме кузнеца) без оружия
    equipType = [['Щит', 'Кинжал'], ['Шлем', 'Шапка'], ['Перчатки', 'Браслеты'],
             ['Броня', 'Куртка'], ['Сапоги', 'Ботинки']]
    equipSet = [[['отчаяния', 'Отч'], ['ночного ордена', 'Ночь']], [['крестоносца', 'К'],
        ['триумфа', 'Т']], [['паладина', 'П'], ['демона', 'Д']], [['хранителя', 'Х'],
        ['охотника', 'О']] ]
    for y in range(0, 5):
        isFind = False;
        for i in range(0, len(s[:y+2])):
            if isFind:
                break
            for par in range(0, 2):
                if isFind:
                    break
                if code:
                    inter['msg'].append('@  {} {}'.format(s[i][0].split(' ')[0], equipType[y][par]))
                ticks += 1
                if s[i][0].split(' ')[0] == equipType[y][par]:
                    for j in range(0, 4):
                        if code:
                            inter['msg'].append('@ @  {} {}'.format(s[i][0].split(' ')[1], equipSet[j][par][0]))
                        ticks += 1
                        if s[i][0].split(' ')[1] == equipSet[j][par][0]:
                            if code:
                                inter['msg'].append('@ @ @  {} to {}'.format(equipType[y][par] + ' ' +
                                                                             equipSet[j][par][0] + s[i][1], y + 1))
                            isFind = True
                            result[y+1] = equipSet[j][par][1] + s[i][1]
                            s[i][2] = False
                            break
        s = [x for x in s if x[2]]
    # Теперь поиск оружия Т1-Т4, которое отделяется от остальных
    
    if len(s) > 0: # для однословного
        is_find = False
        equipSet = [['Алебарда', 'К'], ['Трезубец', 'П'], ['Хранитель', 'Х'], ['Рапира', 'Рапира'],
                    ['Нарсил', 'Т'], ['Экскалибур', 'Д'], ['Костолом', 'Кост']]
        for x in equipSet:
            if code:
                inter['msg'].append('@  {} {}'.format(s[0][0].split(' ')[0], x[0]))
            ticks += 1
            if s[0][0].split(' ')[0] == x[0]:
                if code:
                    inter['msg'].append('@ @ @  {} to 0'.format(s[0][0].split(' ')[0] + s[0][1]))
                result[0] = x[1] + s[0][1]
                s[0][2] = False
                is_find = True
                break
        if not is_find : # для многословного
            equipSet = [['Черная пика', 'Отч'], ['Эльфийское копье', 'Эльф'], ['Свет луны', 'Ночь'],
                        ['Кирка шахтера', 'Кирка'], ['Молот гномов', 'Мол.гн.'], ['Кузнечный молот', 'Кузн']]
            for x in equipSet:
                if code:
                    inter['msg'].append('@  {} in string[0]'.format(x[0]))
                ticks += 1
                if s[0][0].find(x[0]) > -1:
                    if code:
                        inter['msg'].append('@ @ @ {} to 0'.format(x[0] + s[0][1]))
                    result[0] = x[1] + s[0][1]
                    s[0][2] = False
                    break
    s = [x for x in s if x[2]]
    # Теперь поиск мифрилового сета
    equipType = ['щит', 'шлем', 'перчатки', 'броня', 'сапоги']
    equipSet = ['Мифрилов','М']
    for i in range(0, len(s)):
        if code:
            inter['msg'].append('@  {} {}'.format(s[i][0].split(' ')[0][:8], equipSet[0]))
        ticks += 1
        if s[i][0].split(' ')[0][:8] == equipSet[0]:
            for y in range(0, 5):
                if code:
                    inter['msg'].append('@ @  {} {}'.format(s[i][0].split(' ')[1], equipType[y]))
                ticks += 1
                if s[i][0].split(' ')[1] == equipType[y]:
                    if code:
                        inter['msg'].append('@ @ @  {} to {}'.format(s[i][0].split(' ')[0] + ' ' +
                                                                     equipType[y] + s[i][1], y + 1))
                    result[y + 1] = equipSet[1] + s[i][1]
                    s[i][2] = False
                    break
    s = [x for x in s if x[2]]
    # Теперь поиск аксессуаров
    equipSet = ['Кроличья лапка', 'Фляга', 'Коготь вампира', 'Бутылка']
    for i in range(0, len(s)):
        for x in equipSet:
            if code:
                inter['msg'].append('@ {} in string[{}]'.format(x, i))
            ticks += 1
            if s[i][0].find(x) > -1:
                if code:
                    inter['msg'].append('@ @ @ {}'.format(x))
                s[i][2] = False
                break
    s = [x for x in s if x[2]]
    # Теперь поиск сета кузнеца
    equipSet = [['Кузнечная роба', 'Кузн', 4], ['Рукавицы', 'Кузн', 3], ['Клещи', 'Кузн', 1]]
    for i in range(0, len(s)):
        for x in equipSet:
            if code:
                inter['msg'].append('@ finding {} in s[{}]...'.format(x[0], i))
            ticks += 1
            if s[i][0].find(x[0]) != -1:
                if code:
                    inter['msg'].append('@ @ @ {} to {}'.format(x[0] + s[i][1], x[2]))
                result[x[2]] = x[1] + s[i][1]
                s[i][2] = False
    s = [x for x in s if x[2]]
    #конец
    inter['ticks'] = ticks
    bad = 0
    for x in result:
        if len(x) == 0:
            bad += 1
    if len(s) > 0:
        for i in range(len(s)):
            inter['msg'].append('В парсере экипировки не распознана строка\n' + s[i][0])
    if bad > 0 and len(s) > 0:
        inter['send'].append('экипировка не была полностью распознана')
        for i in range(len(result)):
            if result[i] == '':
                result[i] = 'wrong'
    if inter['ticks'] > 70:
        inter['msg'].append('ticks: ' + str(inter['ticks']) + '\n\n' + s_orig)
                            
    return [dict(spear = result[0], shield = result[1], helmet = result[2],
            glove = result[3], armor = result[4], boot = result[5]),
            inter]

def _decode_pet(s):
    """Парсит строки с питомцем
    return petL, petT
    petL - int уровень питомца"""
    p = s.find(':') + 2
    if s[p] == '\U0001f40e': # Первое поколение
        petType = 'Конь'
    elif s[p] == '\U0001f437':
        petType = 'Свин'
    elif s[p] == '\U0001f423':
        petType = 'Гусь'
    elif s[p] == '\U0001f434':
        petType = 'Осел'
    elif s[p] == '\U0001f64a': # Второе поколение
        petType = 'Эвок'
    elif s[p] == '\U0001f98f':
        petType = 'Тонт'
    elif s[p] == '\U0001f916': # Третье поколение
        petType = 'Голм'
    elif s[p] == '\U0001f318': # Четвертое поколение
        petType = 'Обор'
    elif s[p] == '\U0001f621':
        petType = 'Упрь'
    elif s[p] == '\U0001f415':
        petType = 'Собк'
    elif s[p] == '\U0001f989':
        petType = 'Сова'
    elif s[p] == '\U0001f40d': # Пятое поколение
        petType = 'Вася'
    elif s[p] == '\U0001f408': # Шестое поколение
        petType = 'Котя'
    elif s[p] == '\U0001f45e':
        petType = 'Бшмк'
    elif s[p] == '\U0001f987':
        petType = 'Вамп'
    elif s[p] == '\U0001f43a':
        petType = 'Волк'
    elif s[p] == '\U0001f43b': # Седьмое поколение
        petType = 'Миша'
    elif s[p] == '\U0001f42d':
        petType = 'Поля'
    else:
        petType = '????'
    p = s.find('(') + 1
    petLevel = _toint(s[p:p+10])
    return [petLevel, petType]

def _is_warlord(nick):
    """Определяет наличие в нике звезды варлорда и убирает ее.
    Возвращает [bool, nick]"""
    if len(nick) < 2:
        return [False, nick]
    if nick[0:2] == '\u2b50\ufe0f': # Определяет наличие в нике звезды варлорда
        return [True, nick[2:]]
    else:
        return [False, nick]


def _parse_data_gm(s):
    """Парсит профиль по /hero
    return is_good, inter, gm
    is_good - bool пропарсено ли сообщение
    inter - dict внутренние сообщения системы
    gm - результат парсинга"""
    if s[-6:] != r'/class':
        return False, {'msg': [], 'send': []}, {}
    flag = s[0:2] # Парсит строку и заполняет переменные
    p = 2
    nick = s[p:s.find(', ', p, p + 50)]
    p = s.find(', ', p, p + 20) + 2
    plClass = s[p:s.find(' ', p, p + 50)]
    p = s.find('Уровень: ', p, p + 50) + 9
    level = _toint(s[p:p+10])
    if level < 1:
        return False, {'msg': ['Параметр level < 1 ({})'.format(level)], 'send': []}, {}
    p = s.find('Атака: ', p, p + 50) + 7
    attack = _toint(s[p:p+10])
    if attack < 1:
        return False, {'msg': ['Параметр attack < 1 ({})'.format(attack)], 'send': []}, {}
    p = s.find('Защита: ', p, p + 50) + 8
    defense = _toint(s[p:p+10])
    if defense < 1:
        return False, {'msg': ['Параметр defense < 1 ({})'.format(defense)], 'send': []}, {}
    p = s.find('Опыт: ', p, p + 50) + 6
    experience = _toint(s[p:p + 10])
    p = s.find('Выносливость: ', p, p + 50) + 14
    p = s.find(r'/', p, p + 50) + 1
    stamina = _toint(s[p:p+10])
    if stamina < 1:
        return False, {'msg': ['Параметр stamina < 1 ({})'.format(stamina)], 'send': []}, {}
    p = s.find('Экипировка', p, p + 50) + 10
    ATC = '\u2694\ufe0f'
    DEF = '\U0001f6e1'
    if  s.find(ATC, p, p + 10) > -1:
        p = s.find('+', p, p + 10)+1
        equipAttack = _toint(s[p:p+10])
    else:
        equipAttack = 0
    if  s.find(DEF, p, p + 10) > -1:
        p = s.find('+', p, p + 10)+1
        equipDefense = _toint(s[p:p+10])
    else:
        equipDefense = 0
    if s.find('Экипировка: [-]', p - 10, p + 50) > 0:
        equip, inter = _decode_equip('')
    else:
        p = s.find(':', p, p + 50) + 2
        equip, inter = _decode_equip(s[p:s.find('Рюкзак: ', p, p + 500)-3])
    p = s.find('Рюкзак: ', p, p + 500) + 8
    bag = _toint(s[p:p+10])
    p = s.find('Склад: ', p, p + 50) + 7
    stock = _toint(s[p:p+10])
    p = s.find('/stock', p, p + 50) + 8
    pet = s[p:p+60]
    if (pet.find('Питомец') != -1) or (pet.find('Помощник') != -1):
        petLevel, petType = _decode_pet(pet)
    else:
        petLevel = 0
        petType = ''

    if plClass[0:3] == 'Пал': # Определяет наличие бонуса паладина
        selfAttack = attack//1.03 - equipAttack
        selfDefense = round(1.07 * (level + 1 + equipDefense - selfAttack))
        if (7 + selfDefense * 1.04) > defense:
            isPalBonus = False
        else:
            isPalBonus = True
    else:
        isPalBonus = False

    isWarlord, nick = _is_warlord(nick)
    data = {'flag': flag, 'nick': nick, 'plCl': plClass, 'lvl': level,
            'atc': attack, 'def': defense, 'exp': experience, 'stamina': stamina,
            'eqAtc': equipAttack, 'eqDef': equipDefense, 'eq': equip, 'bag': bag,
            'stock': stock, 'petL': petLevel, 'petT': petType, 'isPB': isPalBonus,
            'isWL': isWarlord}         
    return True, inter, data


def _changes_to_log(data_main, data_new):
    """Сверяет два экземпляра data_main и data_new, добавляет изменения в лог data_main
    return is_data, is_table
    is_data - есть ли хоть какие-то изменения в информации
    is_table - есть ли изменения, отражающиеся на таблице"""
    is_data, is_table = False, False
    time_now = datetime.datetime.now()
    time_main = datetime.datetime.strptime(data_main['ad']['time'], '%d.%m.%Y')
    time_new_str = data_new['ad']['time']
    time_new = datetime.datetime.strptime(time_new_str, '%d.%m.%Y')
    deltadays_old = (time_now-time_main).days
    deltadays_new = (time_now-time_new).days

    if deltadays_old != deltadays_new:
        is_table = True
    if data_main['ad']['name'] != data_new['ad']['name']:
        is_table = True

    if len(data_main['log']) == 0:
        cur = [-1]
    else:
        cur = [data_main['log'][-1]['id']]
    
    def inc(val):
        val[0] += 1
        return val[0]

    if data_main['ad']['name'] != data_new['ad']['name']:
        is_table = True
    if data_main['ad']['username'] != data_new['ad']['username']:
        is_table = True
        data_main['iden'].append(data_new['ad']['username'])
    if data_main['gm']['nick'] != data_new['gm']['nick']:
        is_table = True
        data_main['iden'].append(data_new['gm']['nick'])
        data_main['log'].append({'key': 'nick', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['nick'] + ' ' + data_new['gm']['nick'])})

    if data_main['gm']['lvl'] != data_new['gm']['lvl']:
        is_table = True
        data_main['log'].append({'key': 'lvl', 'id': inc(cur), 'time': time_new_str, 'msg':(
            str(data_main['gm']['lvl']) + ' ' + str(data_new['gm']['lvl']))})
    if data_main['gm']['atc'] != data_new['gm']['atc']:
        is_table = True
        data_main['log'].append({'key': 'atc', 'id': inc(cur), 'time': time_new_str, 'msg':(
            str(data_main['gm']['atc']) + ' ' + str(data_new['gm']['atc']))})
    if data_main['gm']['def'] != data_new['gm']['def']:
        is_table = True
        if not(data_main['gm']['isPB'] or data_new['gm']['isPB']):
            data_main['log'].append({'key': 'def', 'id': inc(cur), 'time': time_new_str, 'msg':(
                str(data_main['gm']['def']) + ' ' + str(data_new['gm']['def']))})
    if data_main['gm']['plCl'] != data_new['gm']['plCl']:
        is_table = True
        data_main['log'].append({'key': 'class', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['plCl'] + ' ' + data_new['gm']['plCl'])})
    if data_main['gm']['eqAtc'] != data_new['gm']['eqAtc']:
        is_table = True
        data_main['log'].append({'key': 'eqatc', 'id': inc(cur), 'time': time_new_str, 'msg':(
            str(data_main['gm']['eqAtc']) + ' ' + str(data_new['gm']['eqAtc']))})
    if data_main['gm']['eqDef'] != data_new['gm']['eqDef']:
        is_table = True
        data_main['log'].append({'key': 'eqdef', 'id': inc(cur), 'time': time_new_str, 'msg':(
            str(data_main['gm']['eqDef']) + ' ' + str(data_new['gm']['eqDef']))})

    if data_main['gm']['eq']['spear'] != data_new['gm']['eq']['spear']:
        is_table = True
        data_main['log'].append({'key': 'eq.spear', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['eq']['spear'] + ' ' + data_new['gm']['eq']['spear'])})
    if data_main['gm']['eq']['shield'] != data_new['gm']['eq']['shield']:
        is_table = True
        data_main['log'].append({'key': 'eq.shield', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['eq']['shield'] + ' ' + data_new['gm']['eq']['shield'])})
    if data_main['gm']['eq']['armor'] != data_new['gm']['eq']['armor']:
        is_table = True
        data_main['log'].append({'key': 'eq.armor', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['eq']['armor'] + ' ' + data_new['gm']['eq']['armor'])})
    if data_main['gm']['eq']['helmet'] != data_new['gm']['eq']['helmet']:
        is_table = True
        data_main['log'].append({'key': 'eq.helmet', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['eq']['helmet'] + ' ' + data_new['gm']['eq']['helmet'])})
    if data_main['gm']['eq']['glove'] != data_new['gm']['eq']['glove']:
        is_table = True
        data_main['log'].append({'key': 'eq.glove', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['eq']['glove'] + ' ' + data_new['gm']['eq']['glove'])})
    if data_main['gm']['eq']['boot'] != data_new['gm']['eq']['boot']:
        is_table = True
        data_main['log'].append({'key': 'eq.boot', 'id': inc(cur), 'time': time_new_str, 'msg':(
            data_main['gm']['eq']['boot'] + ' ' + data_new['gm']['eq']['boot'])})
        

    if (data_main['gm']['petT'] != data_new['gm']['petT']) or (
        data_main['gm']['petL'] != data_new['gm']['petL']):
        is_table = True
    if data_main['gm'] != data_new['gm'] or is_table:
        is_data = True
    
    return is_data, is_table

def _parse_data_ad(m):
    """Собирает из сообщения юзернейм и подобную информацию
    return ad
    ad - dict ..."""
    fname = m.from_user.first_name
    lname = m.from_user.last_name
    if (type(fname) == type('')) and (type(lname) == type('')):
        name = fname + ' ' + lname
    else:
        if type(fname) == type(''):
            name = fname
        elif type(lname) == type(''):
            name = lname
        else:
            name = 'without name'
        
    timeData = datetime.datetime.fromtimestamp(m.forward_date)
    time = timeData.strftime('%d.%m.%Y')
    timeNow = datetime.datetime.now()
    deltadays = (timeNow-timeData).days
    group = 1 if deltadays > 12 else 0
    return dict(name = name, username = '@' + m.from_user.username, time = time,
                 heroism = 0, group = group)


def parse_message(data, m, admins):
    """alldata - dict с информацией
    m - объект от бота
    admins - список админов
    return: is_data_change, is_table_change, inter
    inter - dict внутренние сообщения, должна включать main, send, msg
    main - str сообщения, отправляемого ботом назад
    send - list дополнительных сообщений. хм....
    msg - list сообщений, которые могут идти только в какой-нибудь лог"""
    def edit_main_send(inter):
        for i in range(len(inter['send'])):
            if i == 0:
                if len(inter['send']) == 1:
                    inter['main'] += '\n\nпримечание:'
                else:
                    inter['main'] +='\n\nпримечания:'
            inter['main'] += '\n   {}'.format(inter['send'][i])
        return 
    isok, inter, gm = _parse_data_gm(m.text)
    ad = _parse_data_ad(m)
    ID = m.from_user.id
    if not isok:
        inter['main'] = 'baka'
        edit_main_send(inter)
        return False, False, inter
    is_admin = True if ID in admins else False
    is_admin_work = False
    if is_admin:
        for i in range(len(data)):
            if data[i]['gm']['nick'] == gm['nick'] and data[i]['ID'] != ID:
                adm_name = m.from_user.first_name
                ID = data[i]['ID']
                is_admin_work = True# администратор обновляет не себя (явно)
                time = ad['time']
                ad = data[i]['ad']
                ad['time'] = time
                ad['group'] = 0
                break

    for i in range(len(data)):
        if data[i]['ID'] == ID:
            if not is_admin_work:
                # проверка, вдруг пользователь прислал информацию не о себе (многие данные изменены)
                index = 0
                if data[i]['gm']['nick'] != gm['nick']:
                    index += 8
                if data[i]['gm']['eq'] != gm['eq']:
                    index += 3
                
                def not_equal(int1, int2, percent):# процент совпадения
                    if int1 < int2:
                        int1, int2 = int2, int1 #int1 >= int2
                    return True if int1 * (percent / 100) > int2 else False

                if not_equal(data[i]['gm']['lvl'], gm['lvl'], 95):
                    index += 3
                if not_equal(data[i]['gm']['def'], gm['def'], 90):
                    index += 1
                if not_equal(data[i]['gm']['atc'], gm['atc'], 85):
                    index += 1
                if not_equal(data[i]['gm']['exp'], gm['exp'], 90):
                    index += 3
                if not_equal(data[i]['gm']['stamina'], gm['stamina'], 90):
                    index += 3
                if not_equal(data[i]['gm']['petL'], gm['petL'], 90):
                    index += 2
                if not_equal(data[i]['gm']['bag'], gm['bag'], 50):
                    index += 1
                if index > 10:
                    inter['msg'].append('index: ' + str(index) + '\nДля пользователя ' +
                                        data[i]['gm']['nick'] + ' и присланного от него ' +
                                        gm['nick'])
                if index >= 15:
                    if is_admin:
                        inter['main'] = ('Скорее всего вы обновляете другого человека с ' +
                                         'новым ником, такое недопустимо. Если же это ' +
                                         'ваши данные, то они слишком сильно изменились '
                                         'и внутренний индекс недоверия к ним составил ' +
                                         str(index) + ' из 25 возможных (<15 для прохождения)')
                    else:
                        inter['main'] = ('Скорее всего вы прислали чужие данные. Или ' +
                                         'ваши данные сильно изменились. Внутренний ' +
                                         'индекс недоверия к ним составил ' + str(index) +
                                         ' из 25 возможных (<15 для прохождения)')
                    edit_main_send(inter)
                    return False, False, inter
            if gm['exp'] < data[i]['gm']['exp']:
                inter['main'] = 'Предоставлена устаревшая информация о ' + gm['nick']
                edit_main_send(inter)
                return False, False, inter
            is_data, is_table = _changes_to_log(data[i], {'gm': gm, 'ad': ad})
            if not is_data:
                inter['main'] = ('Информация о ' + gm['nick'] +
                                 ' не изменилась с предыдущего получения')
                edit_main_send(inter)
                return False, False, inter
            if is_admin_work:
                inter['main'] = ('Информация о ' + gm['nick'] +
                                 ' обновлена администратором ' + str(adm_name))
            else:
                inter['main'] = 'Информация о ' + gm['nick'] + ' обновлена'

            data[i]['gm'] = gm
            heroism = data[i]['ad']['heroism']
            data[i]['ad'] = ad
            data[i]['ad']['heroism'] = heroism

            edit_main_send(inter)
            return is_data, is_table, inter

    if not is_admin:
        data.append({'ID': ID, 'gm': gm, 'ad': ad, 'iden': [gm['nick'], ad['username']],
                     'log': []})
        inter['main'] = '{} успешно добавлен в таблицу'.format(gm['nick'])
        edit_main_send(inter)
        return True, True, inter

    inter['main'] = 'Пустой исход'
    edit_main_send(inter)
    return False, False, inter


def parse_heroism(alldata, m):
    va = '\U0001f1fb\U0001f1e6'
    emj = '\U0001f530'
    inter = {'msg': []}
    herdic = []
    is_change = False
    timeNow = datetime.datetime.now()
    timeData = datetime.datetime.fromtimestamp(m.forward_date)
    if (timeNow - timeData).total_seconds() > 3600:
        inter['main'] = 'Предоставленные данные устарели (1 час)'
        return False, inter
    s = m.text
    del m
    if s[:5] != 'Отряд':
        return False, inter
    p = s[:50].find('Бойцы')
    if p == -1:
        return False, inter
    p = s[:70].find(va)
    if p == -1:
        return False, inter
    ticks = 0
    while s.find(va, p, p + 100) != -1:
        ticks += 1
        if ticks > 150:
            inter['msg'].append('hero error in ticks')
            break
        p = s.find(va, p, p + 100) + 2
        nick = s[p:s.find(', ' + emj, p, p + 30)]
        p = s.find(', ' + emj, p, p + 30) + 3
        heroism = _toint(s[p:p + 10])

        find = 0
        for i in range(len(alldata)):
            if nick == alldata[i]['gm']['nick']:
                find += 1
                position = i
        if find == 1:
            herdic.append([nick, heroism])
        else:
            inter['msg'].append('hero error in name {} find {}'.format(nick, find))
    for i in range(len(alldata)):
        is_find = False
        for y in range(len(herdic)):
            if alldata[i]['gm']['nick'] == herdic[y][0]:
                is_find = True
                if alldata[i]['ad']['heroism'] != herdic[y][1]:
                    is_change = True
                    alldata[i]['ad']['heroism'] = herdic[y][1]
        if not is_find:
            if alldata[i]['ad']['heroism'] != 0:
                is_change = True
                alldata[i]['ad']['heroism'] = 0
    if is_change:
        inter['main'] = 'Героизм обновлен.'
    return is_change, inter


def data_index_for_key(data, obj):
    """obj - некий ключ (nick, ID, username) типа int, str или list
    return - int индекс положения пользователя в data
    Пример использования:
        index = data_index_for_key(data, 'Strawberry')
        data[index]
    
    если obj не интерпритируется в индекс, возвращает -1"""
    if type(obj) == type(0):
        for i in range(len(data)):
            if obj == data[i]['ID']:
                return i
        return -1
    elif type(obj) == type(''):
        word = obj
    elif type(obj) == type([]):
        word = ''
        for x in obj:
            word += x + ' '
        word = word[:-1]
    else:
        return -1
    
    if word.isdigit():
        for i in range(len(data)):
            if int(word) == data[i]['ID']:
                return i
    for i in range(len(data)):
        if word in data[i]['iden']:
            return i
    return -1


def show_find(data, key, ID, is_admin, start_with = 0):
    """key - str по типу '[username/name/ID ]key_in_log_keys'
    ID - int ID вызвавшего команду пользователя
    is_admin - bool является ли пользователь админом
    start_with - int id лога, начиная с короторого ведется поиск записей

    return msg, infostr, args
    msg - str с нулевой длиной, если все хорошо, иначе текст ошибки
    infostr - str найденные по ключу записи
    args - list - аргумент для работы бота при вызове delfind, find_next
    """
    if len(key.split()) != 1:
        if not is_admin:
            return 'bad key', '', []
        ID = key.split()[:-1]
    
    cur_index = data_index_for_key(data, ID)
    if cur_index == -1:
        return 'bad ID', '', []


    w_key = key.split()[-1]
    is_all = True if w_key == 'all' else False

    cur_id = []
    correct_len, num_start, num_stop = 0, 0, 0
    for i in range(len(data[cur_index]['log'])):
        if is_all or (w_key == data[cur_index]['log'][i]['key'][0:len(w_key)]):
            correct_len += 1
            if data[cur_index]['log'][i]['id'] >= start_with:
                if num_start == 0:
                    num_start = correct_len
                if correct_len - num_start <= 49:
                    cur_id.append(data[cur_index]['log'][i]['id'])
                    if correct_len - num_start == 49:
                        num_stop = correct_len
                    
    if num_stop ==0:
        num_stop = correct_len
    
    if data[cur_index]['ID'] != ID:
        infostr = 'Пользователь {}.\n'.format(data[cur_index]['gm']['nick'])
    else:
        infostr = ''

    if start_with > 0 and num_start == 0:
        return 'и г н о р и р у ю', '', []
    if correct_len == num_stop and correct_len > 0 and is_all and num_start == 1:
        infostr += 'Все записи (' + str(correct_len) +'):'
    elif correct_len == 0:
        infostr += 'Для ключа ' + w_key + ' записи не найдены'
    elif correct_len <= 50:
        if (correct_len // 10 == 1) or (correct_len % 10 in range(5, 10)) or (
            correct_len % 10 == 0):
            ending = ['о', 'ей']  
        elif correct_len % 10 in range(2, 5):
            ending = ['о', 'и']
        else:
            ending = ['а', 'ь']
        infostr += ('Для ключа ' + w_key + ' найден{} ' + str(correct_len) +
                    ' запис{}:').format(ending[0], ending[1])
    elif is_all:
        infostr += ('Показаны ' + str(num_start) +
                    '-' + str(num_stop) + ' записи из ' + str(correct_len) + ':')
    else:
        infostr += ('Для ключа ' + w_key + ' показаны ' + str(num_start) +
                    '-' + str(num_stop) + ' записи из ' + str(correct_len) + ':')
        
    size = 1 if num_stop - num_start < 9 else 2
    num = num_start
    before_time = ''
    for i in range(len(data[cur_index]['log'])):
        if data[cur_index]['log'][i]['id'] in cur_id:
            bold = True if before_time != data[cur_index]['log'][i]['time'] else False
            before_time = data[cur_index]['log'][i]['time']
            temp = (str(num).zfill(size) + ') ' + data[cur_index]['log'][i]['time'] +
                    ' ' + data[cur_index]['log'][i]['key'] +
                    ' ' + data[cur_index]['log'][i]['msg'])
            num += 1
            if bold:
                infostr += '\n' + '<b>' + temp + '</b>'
            else:
                infostr += '\n' + temp
    if num_stop < correct_len:
        infostr += '\nследующие записи /find_next' 
    return '', infostr, ['find', data[cur_index]['ID'], cur_id, w_key, num_start]


def del_find(data, ID, cur_id, intlist, num_start):
    """ID - int ID человека, чей лог меняется
    cur_id - list id высвеченных данных лога
    intList - list номеров, введенных пользователем
    
    return is_change
    is_change - bool были ли осуществлены изменения
    """
    cur_index = data_index_for_key(data, ID)
    if cur_index == -1:
        return False

    del_id = []
    for x in intlist:
        del_id.append(cur_id[x - num_start])
    for i in range(len(data[cur_index]['log']) - 1, -1, -1):
        if data[cur_index]['log'][i]['id'] in del_id:
            del data[cur_index]['log'][i]


    return True if len(del_id) > 0 else False 
