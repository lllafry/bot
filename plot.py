from io import BytesIO
from datetime import datetime, timedelta
from apibot import data_index_for_key, KeyErr
from PIL import Image, ImageDraw, ImageFont

def get_plot(data, key, ID, is_admin):
    """Рисует график по указанным входным данным
    key - str по типу '[<username/name/ID>] <keys(ключ/ключи из лога)>'
    или по типу 'all[<value>] <key>'
    
    return data
    data - bytes для отправки ботом"""
    #парсинг key
    KEYS = ['lvl', 'atc', 'def', 'eqatc', 'eqdef']
    if len(key) == 0:
        raise KeyErr('Добавьте к команде один или несколько ключей: {}'.format(
            ' '.join(KEYS)))
    
    is_all, is_common = False, False
    keylist = key.split()
    
    if keylist[0][:3] == 'all':
        all_her = 100
        is_group = False
        temp = keylist[0][3:]
        if len(temp) > 0:
            if temp == '-':
                is_group = True
            elif temp.isdigit():
                if int(temp) < 300:
                    all_her = int(temp)
                else:
                    raise KeyErr('err: ожидалось число 0..300 ({}}'.format(temp))
            else:
                raise KeyErr('err: ожидалось число 0..300 или "-" ({})'.format(temp))
        keylist = keylist[1:]
        if len(keylist) == 0:
            raise KeyErr('err: потерян ключ')
        key = ' '.join(keylist)
        if key not in KEYS:
            raise KeyErr('err: получен недействительный ключ ({})'.format(key))
        is_all = True
    else:
        if is_admin:
            y = len(keylist)
            for i in range(len(keylist)):
                if keylist[i] in KEYS:
                    y = i
                    break
            if y > 0:
                ID = ' '.join(keylist[:y])
                keylist = keylist[y:]
        cur_index = data_index_for_key(data, ID)
        if cur_index == -1:
            raise KeyErr('err: по строке ({}) пользователь не распознан'.format(ID))
        if len(keylist) == 0:
            raise KeyErr('err: потерян ключ')
        if any([x not in KEYS for x in keylist]):
            raise KeyErr('err: не все ключи подходят ({})'.format(' '.join(keylist)))
        is_common = True
    # составление vl словаря (в зависимости от is_all, is_common    
    if is_all:
        cur_indexlist = []
        cur_her = []
        for i in range(len(data)):
            if data[i]['ad']['heroism'] >= all_her or is_group:
                cur_indexlist.append(i)
                cur_her.append(data[i]['ad']['heroism'])
        
        if len(cur_indexlist) == 0:
            raise KeyErr('no users')

        for i in range(len(cur_indexlist)-1):
            for y in range(len(cur_indexlist)-1):
                if cur_her[y] < cur_her[y + 1]:
                    cur_her[y + 1], cur_her[y] = cur_her[y], cur_her[y + 1]
                    cur_indexlist[y], cur_indexlist[y + 1] = (
                        cur_indexlist[y + 1], cur_indexlist[y])
            
        vl = {} # vl = {key arr} key:: <valkey>: {'val':[value arr], 'tm': [time arr]}
        for cur_index in cur_indexlist:
            nick = data[cur_index]['gm']['nick']
            vl[nick] = {'val': [], 'tm': []}
            for i in range(len(data[cur_index]['log'])):
                if data[cur_index]['log'][i]['key'] == key:
                    vl[nick]['val'].append(
                        int(data[cur_index]['log'][i]['msg'].split()[-1]))
                    vl[nick]['tm'].append(datetime.strptime(
                        data[cur_index]['log'][i]['time'],'%d.%m.%Y'))
        for cur_index in cur_indexlist:
            nick = data[cur_index]['gm']['nick']
            if len(vl[nick]['tm']) == 0:
                del vl[nick]
        title = key
    elif is_common:
        nick = data[cur_index]['gm']['nick']
        vl = {}
        for x in keylist:
            vl[x] = {'val': [], 'tm': []}
        
        for i in range(len(data[cur_index]['log'])):
            if data[cur_index]['log'][i]['key'] in keylist:
                key = data[cur_index]['log'][i]['key']
                vl[key]['val'].append(
                    int(data[cur_index]['log'][i]['msg'].split()[-1]))
                vl[key]['tm'].append(datetime.strptime(
                        data[cur_index]['log'][i]['time'],'%d.%m.%Y'))
                
        for x in vl:
            if len(vl[x]['val']) < 1:
                raise KeyErr('err: В одном из подграфиков слишком мало данных для построения')
        title = nick
    else:
        raise KeyErr('err: bad string')
    # процесс рисования
    return plotting(vl, title)


def get_activity(data, key):
    """Выводит 'активность' отряда по записям
    key - str по типу '[<DAYS>] [<start date> [<stop date>]] <ключ>'
    date: str 'DD.MM.YYYY'
    
    return data
    data - bytes для отправки ботом"""
    zero_date = '01.01.2017'
    zdtime = datetime.strptime(zero_date, '%d.%m.%Y')
    def tm2int(tm):
        return (datetime.strptime(tm, '%d.%m.%Y') - zdtime).days
    #парсинг key
    if len(key) == 0:
        raise KeyErr('Добавьте к команде один из ключей: all, lvl, def, atc, ' +
                     'class, nick, eqact, eqdef, eq.[spear, shield, helment, ' +
                     'armor, glove, boot], возможен неполный набор ключа')
    DAYS = 10
    first = key.split()[0]
    if first.isdigit():
        if int(first) > 0 and int(first) < 31:
            DAYS = int(first)
            key = ' '.join(key.split()[1:])
        else:
            raise KeyErr('err: возможно только 1..30 ({})'.format(first))
        if len(key) == 0:
            raise KeyErr('err: потерян ключ')
    w_key = key.split()[-1]
    is_all = True if w_key == 'all' else False
    
    start_int, stop_int = 0, 365000
    start_bool, stop_bool = False, False
    if len(key.split()) > 1:
        if len(key.split()) > 3:
            raise KeyErr('err: слишком много входных аргументов ({})'.format(key))
        try:
            start_int = tm2int(key.split()[0])
        except:
            raise KeyErr('err: задана недействительная начальная дата ({})'.format(
                key.split()[0]))
        if len(key.split()) == 3:
            try:
                stop_int = tm2int(key.split()[1])
            except:
                raise KeyErr('err: задана недействительная конечная дата ({})'.format(
                    key.split()[1]))
    if stop_int < start_int:
        raise KeyErr('err: дата начала больше даты конца')
                         
    left = int(DAYS / 2)
    right = DAYS - left
    starti = start_int - left
    stopi = stop_int + right     
    #создание сырого словаря
    vlt = {}
    for i in range(len(data)):
        for y in range(len(data[i]['log'])):
            if is_all or (w_key == data[i]['log'][y]['key'][0:len(w_key)]):
                tm = tm2int(data[i]['log'][y]['time'])
                if tm < starti:
                    start_bool = True
                    continue
                if tm > stopi:
                    stop_bool = True
                    continue
                if tm in vlt.keys():
                    vlt[tm] += 1
                else:
                    vlt[tm] = 1
    if len(vlt.keys()) <= 2:
        raise KeyErr('err: по входным данным найдено слишком мало записей ({})'.format(
            len(vlt.keys())))
    #создание истинного словаря
    vl = {}
    if is_all:
        title = 'Все записи'
    else:
        title = w_key
    
    min_int = min(vlt.keys())
    if start_bool:
        min_int = start_int
        title += ' c ' +  datetime.strftime(
            zdtime + timedelta(days=min_int), '%d %h %y')
    if stop_bool:
        title += ' по ' + datetime.strftime(
            zdtime + timedelta(days=stop_int), '%d %h %y')
        max_int = stop_int
    else:
        max_int = max(vlt.keys())

    cur_int = min_int - left + 1
    lst = []
    cur_val = 0
    val = []
    tm = []
    while cur_int <= max_int + right:
        if cur_int in vlt.keys():
            lst.append(vlt[cur_int])
            cur_val += vlt[cur_int]
        else:
            lst.append(0)
        if len(lst) > DAYS:
            cur_val -= lst.pop(0)
        if len(lst) == DAYS:
            val.append(cur_val)
            tm.append(zdtime + timedelta(days=cur_int - right))
        cur_int += 1
    vl['act' + ' ' + str(DAYS)] = {'val': val, 'tm': tm}
    return plotting(vl, title)
    

def plotting(vl, title):
    """Собственно функция рисования
    # vl = {ключи} ключ:: <valkey>: {'val':[value arr], 'tm': [time arr]}
    # в vl для каждого ключа len(val) == len(tm) > 0

    return data
    data - bytes для отправки ботом"""
    # проверка правильности vl
    if len(vl.keys()) == 0:
        raise Exception('err in plotting: не обнаружены данные для построения')
    if any([len(vl[key]['val']) != len(vl[key]['tm']) or len(vl[key]['tm']) == 0 for key in vl]):
        raise Exception('err in plotting: встречены массивы разной / нулевой длины')
    # создание пустого макета с ником
    SIZE = (900, 500)# размер всей картинки
    GRAF = (800, 400)# размер полотна для графика
    OGR = (20, 16)# размер пустой зоны в полотне
    blk = (0, 0, 0)
    blka = (0, 0, 0, 255)
    bkgr = (250, 250, 250) # цвет заднего фона
    ogrclr = (234, 234, 242) # цвет внутри графика
    
    im = Image.new('RGB', SIZE, bkgr)
    draw = ImageDraw.Draw(im, 'RGBA')
    
    font = ImageFont.truetype(r'calibry.ttf', size = 23)
    draw.text([(SIZE[0] - font.getsize(title)[0]) // 2, 20], title, blk, font)
    font = ImageFont.truetype(r'calibry.ttf', size = 16)
    
    d1 = (SIZE[0] - GRAF[0]) // 2  # длина полосок между
    d2 = (SIZE[1] - GRAF[1]) // 2
    draw.rectangle([d1, d2, d1 + GRAF[0], d2 + GRAF[1]], ogrclr)
    # нахождение граничных значений
    vmin = min([min(vl[key]['val']) for key in vl])
    vmax = max([max(vl[key]['val']) for key in vl])
    tl = min([vl[key]['tm'][0] for key in vl])
    tr = max([vl[key]['tm'][-1] for key in vl])
    # расширение граничных значений и выборка ключевых отметок для сетки
    dv = vmax - vmin### VALUE ###
    ddv = 0.97 * OGR[1] / GRAF[1] * dv
    vup = vmax + ddv
    vdown = vmin - ddv
    dvr = vup - vdown
    is_y = True if dv > 0.05 else False
    if not is_y:
        ylabel = [str(vmin)]
        ylabelv = [vmin]
    else:
        razr = 0
        if dvr >= 1000:
            while dvr >= 1000:
                dvr //= 10
                razr += 1
        else:
            while dvr < 100:
                dvr *= 10
                razr -= 1
        # dvr in[100..999.(9)]
        k = 9 #коэффициент количества позиций в ylabel
        p = 1
        if dvr < 20 * k:
            step = 20
        elif dvr < 25 * k:
            step = 25
            p = 2
        elif dvr < 50 * k:
            step = 50
        elif dvr < 100 * k:
            step = 100
            p = 0
        else:
            step = 200
            p = 0
        step *= 10 ** razr
        p += -2 - razr
        vfirst = vdown // step * step
        while vfirst < vdown:
            vfirst += step
        ylabel = [vfirst]
        if vfirst > vup:
            raise Exception('err in plotting: 1-ое vl значение больше ' +
                            'верхней границы ({}) > ({})'.format(vfirst, vup))
        i = 1
        while ylabel[0] + i * step < vup:
            ylabel.append(ylabel[0] + i * step)
            i += 1
        ylabelv = ylabel
        if p <= 0:
            ylabel = [str(int(x)) for x in ylabel]
        else:
            ylabel = [str(x).ljust(p + 1 + str(x).find('.'), '0') for x in ylabel]
    
    dt = (tr - tl).days### TIME ###
    ddt = timedelta(days=int(0.97 * OGR[0] / GRAF[0] * dt))
    tdown = tl - ddt
    tup = tr + ddt
    is_x = True if dt != 0 else False
    if not is_x:
        xlabelday = [tl]
        show_days = True
        dtmonth = 0
        dtyear = 0
    else:
        show_days = True if dt < 100 else False# days
        if show_days:
            step = int(dt / 15) + 1
            dtr = (tup - tdown).days
            xlabelday = [tdown]
            temp = 0
            i = 1
            while i * step <= dtr:
                temp += step
                xlabelday.append(xlabelday[0] + timedelta(days=i * step))
                i += 1
        
        dtyear = int(datetime.strftime(tup, '%Y')) - int(datetime.strftime(tdown, '%Y'))
        if dtyear == 0:
            dtmonth =  int(datetime.strftime(tup, '%m')) - int(datetime.strftime(tdown, '%m'))
        else:
            dtmonth = (dtyear * 12 - int(datetime.strftime(tdown, '%m')) +
                       int(datetime.strftime(tup, '%m')))
        k = 15
        if dtmonth < k:# months
            step = 1
        elif dtmonth < 2 * k:
            step = 2
        elif dtmonth < 4 * k:
            step = 4
        else:
            step = 6
        yearstart = int(datetime.strftime(tdown, '%Y'))
        monthstart = int(datetime.strftime(tdown, '%m'))
        month_1 = datetime.strptime(str(yearstart), '%Y')
        i = 1
        ii = 0
        while month_1 < tdown:
            i += step
            while i > 12:
                i -= 12
                ii += 1
            month_1 = datetime.strptime(str(yearstart + ii) + str(i).zfill(2), '%Y%m')
        xlabelmonth = [month_1]
        while xlabelmonth[-1] < tup:
            i += step
            while i > 12:
                i -= 12
                ii += 1
            xlabelmonth.append(datetime.strptime(str(yearstart + ii) +
                                                 str(i).zfill(2), '%Y%m'))
        xlabelmonth = xlabelmonth[:-1]
        year_1 = datetime.strptime(str(yearstart), '%Y')# years
        if year_1 < tdown:
            year_1 = datetime.strptime(str(yearstart + 1), '%Y')
        xlabelyear = [year_1]
        i = 0
        while xlabelyear[-1] < tup:
            i += 1
            xlabelyear.append(datetime.strptime(str(yearstart + i), '%Y'))
        xlabelyear = xlabelyear[:-1]
    
    # теперь рисовка значений на осях
    z = (d1 + OGR[0], d2 + GRAF[1] - OGR[1])# zero left down
    ps = (GRAF[0] - OGR[0] * 2, GRAF[1] - OGR[1] * 2)# plotsize
    def pos_val(val):
        if is_y:
            y = round(z[1] - (val - vmin) / dv * ps[1])
        else:
            y = z[1] - ps[1] // 2
        return y
    def pos_tm(tm):
        if is_x:
            x = round(z[0] + (tm - tl).days / dt * ps[0])
        else:
            x = z[0] + ps[0] // 2
        return x
    wordh = font.getsize(ylabel[0])[1]
    wordup = wordh // 2
    
    for i in range(len(ylabel)):# value
        pos = pos_val(ylabelv[i])
        draw.line((d1, pos, d1 + GRAF[0], pos), bkgr)
        draw.text((d1 - 8 - font.getsize(ylabel[i])[0], pos - wordup),
                  ylabel[i], blk, font)
    position = d2 + GRAF[1] + wordup# time
    if show_days:# days
        for i in range(len(xlabelday)):
            pos = pos_tm(xlabelday[i])
            string = datetime.strftime(xlabelday[i], '%d')
            draw.line((pos, d2, pos, d2 + GRAF[1]), bkgr)
            draw.text((pos - font.getsize(string)[0] // 2, position),
                       string, blk, font)
        position += wordh + 3
    if dtmonth > 0:# months
        for i in range(len(xlabelmonth)):
            pos = pos_tm(xlabelmonth[i])
            string = datetime.strftime(xlabelmonth[i], '%h')
            if not show_days:
                draw.line((pos, d2, pos, d2 + GRAF[1]), bkgr)
            draw.text((pos - font.getsize(string)[0] // 2, position),
                      string, blk, font)
    else:
        pos = pos_tm(xlabelday[0])
        string = datetime.strftime(xlabelday[0], '%h')
        draw.text((pos - font.getsize(string)[0] // 2, position),
                      string, blk, font)
    position += wordh + 3
    if dtyear > 0:# years
        for i in range(len(xlabelyear)):
            pos = pos_tm(xlabelyear[i])
            string = datetime.strftime(xlabelyear[i], '%Y')
            draw.text((pos - font.getsize(string)[0] // 2, position),
                      string, blk, font)
    else:
        if dtmonth > 0:
            pos = pos_tm(xlabelmonth[0])
            string = datetime.strftime(xlabelmonth[0], '%Y')
        else:
            pos = pos_tm(xlabelday[0])
            string = datetime.strftime(xlabelday[0], '%Y')
        draw.text((pos - font.getsize(string)[0] // 2, position),
                      string, blk, font)   
            
    # создание информационной панели
    clrs =[(76, 114, 176), (221, 132, 82), (85, 168, 104), (196, 78, 82),# 12
           (129, 114, 179), (147, 120, 96), (218, 139, 195), (140, 140, 140),
           (204, 185, 116), (100, 181, 205), (0, 51, 0), (102, 204, 153)]
    info = []
    maxsize = 0
    for key in vl:
        info.append([key, font.getsize(key)[0]])
        if info[-1][1] > maxsize:
            maxsize = info[-1][1]
    w = maxsize + 40
    h = len(info) * (wordh + 5) + 20
    lbl = Image.new('RGBA', (w, h), (ogrclr[0], ogrclr[1], ogrclr[2], 190))
    drawl = ImageDraw.Draw(lbl)
    drawl.rectangle((0, 0, w-1, h-1), outline=(148, 148, 148, 240))
    for i in range(len(info)):
        drawl.text((33, 11 + (wordh + 5) * i), info[i][0], blka, font)
        drawl.line((10, 17 + (wordh + 5) * i, 27, 17 + (wordh + 5) * i), clrs[i % 12], 3)
    del drawl
    k = 7
    poslbl = [d1 + k, d2 + k]
    count = [0, 0, 0, 0]# left-up, left-down, right-down, right-up
    board = [d1 + w, d1 + GRAF[0] - w, d2 + h, d2 + GRAF[1] - h]
    # заполнение графиков и подсчет оптимального положения для панели
    def pos(tm, val):
        x = pos_tm(tm)
        y = pos_val(val)
        if x < board[0]:
            if y < board[2]:
                count[0] += 1
            elif y > board[3]:
                count[1] += 1
        elif x > board[1]:
            if y < board[2]:
                count[3] += 1
            elif y > board[3]:
                count[2] += 1
        return (x, y)
    
    def line(x1, y1, x2, y2, col):
        #Рисует линию по алгоритму Ву с толщиной в ~ 3 пикселя
        col_a = (col[0], col[1], col[2], 200)
        def dot(x, y):
            draw.point((x, y), col)
            d = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            for p in d:
                draw.point((x + p[0], y + p[1]), col_a)
        dot(x1, y1)
        dot(x2, y2)
        if x1 == x2:
            draw.line((x1, y1, x2, y2), col)
            draw.line((x1 + 1, y1, x2 + 1, y2), col_a)
            draw.line((x1 - 1, y1, x2 - 1, y2), col_a)
            return
        if y1 == y2:
            draw.line((x1, y1, x2, y2), col)
            draw.line((x1, y1 + 1, x2, y2 + 1), col_a)
            draw.line((x1, y1 - 1, x2, y2 - 1), col_a)
            return
        def plot(x, y, col, c, ch):
            if ch:
                x, y = y, x
            draw.point((x, y), (col[0], col[1], col[2], c))
        if abs((y2 - y1) / (x2 - x1)) > 1:
            ch = True
            x1, x2, y1, y2 = y1, y2, x1, x2
        else:
            ch = False
        if x2 < x1:
            x1, x2, y1, y2 = x2, x1, y2, y1
        gradient = (y2 - y1) / (x2 - x1)
        intery = y1 + gradient
          
        for x in range(x1 + 1, x2):
            plot(x, int(intery) - 1, col, int(255 * (1 - (intery - int(intery)))), ch)
            plot(x, int(intery), col, 255, ch)
            plot(x, int(intery) + 1, col, 255, ch)
            plot(x, int(intery) + 2, col, int(255 * (intery - int(intery))), ch)
            intery = intery + gradient

    
    def drawline(xy, col):
        x0, y0 = pos(xy[0], xy[1])
        x1, y1 = pos(xy[2], xy[3])
        line(x0, y0, x1, y1, col)
    num = 0
    for key in vl:
        if len(vl[key]['val']) == 1:
            x, y = pos(vl[key]['tm'][0], vl[key]['val'][0])
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), clrs[num % 12])
        for i in range(len(vl[key]['val']) - 1):
            drawline((vl[key]['tm'][i], vl[key]['val'][i],
                      vl[key]['tm'][i + 1], vl[key]['val'][i + 1]), clrs[num % 12])

        num += 1
    # определение оптимальной позиции для информационной панели и заключительные действия
    #print(count)
    cur = count.pop(0)
    p = 0
    for i in range(3):
        if cur > count[i]:
            p = i + 1
            cur = count[i]
    #print(p)
    if p == 2 or p == 3:
        poslbl[0] += GRAF[0] - w - 2 * k
    if p == 1 or p == 2:
        poslbl[1] += GRAF[1] - h - 2 * k
        
    im.paste(lbl, poslbl, lbl)
    lbl.close()
    del draw
    #im.show()
    with BytesIO() as file:
        im.save(file, 'png')
        plot_data = file.getvalue()
    im.close()
    return plot_data
