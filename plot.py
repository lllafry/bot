<<<<<<< HEAD
from io import BytesIO
from datetime import datetime, timedelta
from apibot import data_index_for_key
from PIL import Image, ImageDraw, ImageFont

def get_plot(data, key, ID, is_admin):
    """Рисует график в зависимости от ключа
    return str, data
    str - строка, len(str) = 0, если все хорошо, иначе текст ошибки
    data - поток байтов для отправки ботом"""
    KEYS = ['lvl', 'atc', 'def', 'eqatc', 'eqdef']
    keylist = key.split()
    all_her = 100
    is_all, is_common = False, False
    
    if keylist[0][:3] == 'all':
        if (keylist[-1] in KEYS) and (len(keylist) == 2):
            temp = keylist[0][3:]
            minus = False
            if len(temp) > 0:
                if temp[0] == '-':
                    minus = True
                    temp = temp[1:]
            if is_admin and temp.isdigit():
                if int(temp) < 300:
                    if minus:
                        all_her = -1
                    else:
                        all_her = int(temp)
            is_all = True
    else:
        for i in range(len(keylist)):
            if keylist[i] in KEYS:
                if (i != 0) and is_admin:
                    ID = keylist[0:i]
                    keylist = keylist[i:]
                break
        if all(x in KEYS for x in keylist) and (len(keylist) > 0):
            is_common = True
    # составление vl словаря (в зависимости от is_all, is_common    
    if is_all:
        key = keylist[-1]
        is_group = True if all_her == -1 else False

        cur_indexlist = []
        cur_her = []
        for i in range(len(data)):
            if data[i]['ad']['heroism'] >= all_her and (
                data[i]['ad']['group'] == 0 or is_group):
                cur_indexlist.append(i)
                cur_her.append(data[i]['ad']['heroism'])
        
        if len(cur_indexlist) == 0:
            return 'no users', None

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
        vl['title'] = key
    elif is_common:
        cur_index = data_index_for_key(data, ID)
        if cur_index == -1:
            return 'bad ID', None
        
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
            if len(vl[x]['val']) < 2:
                return 'too few log-data for plot in key', None
        vl['title'] = nick
    else:
        return 'bad string', None
    # процесс рисования
    return '', plotting(vl)


def plotting(vl):
    """Собственно функция рисования
    return data
    data - поток байт для отправки ботом"""
    # нахождение граничных значений
    title = vl.pop('title')
    is_first = True
    for key in vl:
        for i in range(len(vl[key]['val'])):
            if (i == 0) and is_first:
                vmin = vl[key]['val'][i]
                vmax = vl[key]['val'][i]
                tl = vl[key]['tm'][0]# time left
                tr = vl[key]['tm'][-1]
            else:
                if vl[key]['val'][i] > vmax:
                    vmax = vl[key]['val'][i]
                if vl[key]['val'][i] < vmin:
                    vmin = vl[key]['val'][i]
        if vl[key]['tm'][0] < tl:
            tl = vl[key]['tm'][0]
        if vl[key]['tm'][-1] > tr:
            tr = vl[key]['tm'][-1]

        is_first = False
    
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
    # выборка значений для построения сетки и её создание (~4-8 val )
        # расширяю диапазон только для значений осей
    dv = 1000 * (vmax - vmin)# VALUE
    vdown = 1000 * vmin - 990 * OGR[1] / GRAF[1] * (vmax - vmin) - 1
    vup = 1000 * vmax + (1000 * vmin - vdown)
    dvr = round(vup - vdown)
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
    p += 1 - razr
    vfirst = vdown // step * step
    while vfirst < vdown:
        vfirst += step
    ylabel = [vfirst]
    while ylabel[-1] + step < vup:
        ylabel.append(ylabel[-1] + step)
    ylabelv = [x / 1000 for x in ylabel]
    if p <= 0:
        ylabel = [str(int(x)) for x in ylabelv]
    else:
        ylabel = [str(x).ljust(p + 1 + str(x).find('.'), '0') for x in ylabelv]

    dt = (tr - tl).days# TIME
    tdown = tl - timedelta(days=round(OGR[0] / GRAF[0] * dt))
    tup = tr + (tl - tdown)
    show_days = True if dt < 100 else False# days
    if show_days:
        step = int(dt / 15) + 1
        dtr = (tup - tdown).days
        xlabelday = [tdown]
        temp = 0
        while temp + step <= dtr:
            temp += step
            xlabelday.append(xlabelday[-1] + timedelta(days=step))
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
    

    z = (d1 + OGR[0], d2 + GRAF[1] - OGR[1])# zero
    ps = (GRAF[0] - OGR[0] * 2, GRAF[1] - OGR[1] * 2)# plotsize
    def pos_val(val):
        if dv == 0:
            y = z[1] + ps[1] // 2
        else:
            y = round(z[1] - (val - vmin) / dv * ps[1] * 1000)
        return y
    def pos_tm(tm):
        if dt == 0:
            x = z[0] + ps[0] // 2
        else:
            x = round(z[0] + (tm - tl).days / dt * ps[0])
        return x

    wordh = font.getsize(ylabel[0])[1]
    wordup = wordh // 2
    # теперь рисовка значений на осях
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
    count = [0, 0, 0, 0]# left-up, left-down, rigth-down, rigth-up
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
=======
from io import BytesIO
from datetime import datetime, timedelta
from apibot import data_index_for_key
from PIL import Image, ImageDraw, ImageFont

def get_plot(data, key, ID, is_admin):
    """Рисует график в зависимости от ключа
    return str, data
    str - строка, len(str) = 0, если все хорошо, иначе текст ошибки
    data - поток байтов для отправки ботом"""
    KEYS = ['lvl', 'atc', 'def', 'eqatc', 'eqdef']
    keylist = key.split()
    all_her = 100
    is_all, is_common = False, False
    
    if keylist[0][:3] == 'all':
        if (keylist[-1] in KEYS) and (len(keylist) == 2):
            temp = keylist[0][3:]
            minus = False
            if len(temp) > 0:
                if temp[0] == '-':
                    minus = True
                    temp = temp[1:]
            if is_admin and temp.isdigit():
                if int(temp) < 300:
                    if minus:
                        all_her = -1
                    else:
                        all_her = int(temp)
            is_all = True
    else:
        for i in range(len(keylist)):
            if keylist[i] in KEYS:
                if (i != 0) and is_admin:
                    ID = keylist[0:i]
                    keylist = keylist[i:]
                break
        if all(x in KEYS for x in keylist) and (len(keylist) > 0):
            is_common = True
    # составление vl словаря (в зависимости от is_all, is_common    
    if is_all:
        key = keylist[-1]
        is_group = True if all_her == -1 else False

        cur_indexlist = []
        cur_her = []
        for i in range(len(data)):
            if data[i]['ad']['heroism'] >= all_her and (
                data[i]['ad']['group'] == 0 or is_group):
                cur_indexlist.append(i)
                cur_her.append(data[i]['ad']['heroism'])
        
        if len(cur_indexlist) == 0:
            return 'no users', None

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
        vl['title'] = key
    elif is_common:
        cur_index = data_index_for_key(data, ID)
        if cur_index == -1:
            return 'bad ID', None
        
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
            if len(vl[x]['val']) < 2:
                return 'too few log-data for plot in key', None
        vl['title'] = nick
    else:
        return 'bad string', None
    # процесс рисования
    return '', plotting(vl)


def plotting(vl):
    """Собственно функция рисования
    return data
    data - поток байт для отправки ботом"""
    # нахождение граничных значений
    title = vl.pop('title')
    is_first = True
    for key in vl:
        for i in range(len(vl[key]['val'])):
            if (i == 0) and is_first:
                vmin = vl[key]['val'][i]
                vmax = vl[key]['val'][i]
                tl = vl[key]['tm'][0]# time left
                tr = vl[key]['tm'][-1]
            else:
                if vl[key]['val'][i] > vmax:
                    vmax = vl[key]['val'][i]
                if vl[key]['val'][i] < vmin:
                    vmin = vl[key]['val'][i]
        if vl[key]['tm'][0] < tl:
            tl = vl[key]['tm'][0]
        if vl[key]['tm'][-1] > tr:
            tr = vl[key]['tm'][-1]

        is_first = False
    
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
    # выборка значений для построения сетки и её создание (~4-8 val )
        # расширяю диапазон только для значений осей
    dv = 1000 * (vmax - vmin)# VALUE
    vdown = 1000 * vmin - 990 * OGR[1] / GRAF[1] * (vmax - vmin) - 1
    vup = 1000 * vmax + (1000 * vmin - vdown)
    dvr = round(vup - vdown)
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
    p += 1 - razr
    vfirst = vdown // step * step
    while vfirst < vdown:
        vfirst += step
    ylabel = [vfirst]
    while ylabel[-1] + step < vup:
        ylabel.append(ylabel[-1] + step)
    ylabelv = [x / 1000 for x in ylabel]
    if p <= 0:
        ylabel = [str(int(x)) for x in ylabelv]
    else:
        ylabel = [str(x).ljust(p + 1 + str(x).find('.'), '0') for x in ylabelv]

    dt = (tr - tl).days# TIME
    tdown = tl - timedelta(days=round(OGR[0] / GRAF[0] * dt))
    tup = tr + (tl - tdown)
    show_days = True if dt < 100 else False# days
    if show_days:
        step = int(dt / 15) + 1
        dtr = (tup - tdown).days
        xlabelday = [tdown]
        temp = 0
        while temp + step <= dtr:
            temp += step
            xlabelday.append(xlabelday[-1] + timedelta(days=step))
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
    

    z = (d1 + OGR[0], d2 + GRAF[1] - OGR[1])# zero
    ps = (GRAF[0] - OGR[0] * 2, GRAF[1] - OGR[1] * 2)# plotsize
    def pos_val(val):
        if dv == 0:
            y = z[1] + ps[1] // 2
        else:
            y = round(z[1] - (val - vmin) / dv * ps[1] * 1000)
        return y
    def pos_tm(tm):
        if dt == 0:
            x = z[0] + ps[0] // 2
        else:
            x = round(z[0] + (tm - tl).days / dt * ps[0])
        return x

    wordh = font.getsize(ylabel[0])[1]
    wordup = wordh // 2
    # теперь рисовка значений на осях
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
    count = [0, 0, 0, 0]# left-up, left-down, rigth-down, rigth-up
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
>>>>>>> a6de427c77d3a1c76259a29f3f0fcf7cbacd4e2e
