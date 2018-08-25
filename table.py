from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta

TBL_CHANGE = [55, 35, 138, 34, 69, 25, 55, 60, 56, 60, 60, 60, 60, 60, 60, 140, 183, 30]
TBL=[0]
for i in range(len(TBL_CHANGE)):
    TBL.append(TBL[-1]+TBL_CHANGE[i])
LFT = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0] # 1: выравнивание слева
DET = LFT # 1: обрезка по размеру

#DRAW = ImageDraw.Draw(Image.new('RGB', (1, 1)))


def sort(data):
    # обновление состояния групп
    timeNow = datetime.now()
    for i in range(len(data)):
        timeData = datetime.strptime(data[i]['ad']['time'], '%d.%m.%Y')
        deltadays = (timeNow-timeData).days
        if (deltadays > 12) and (data[i]['ad']['heroism'] < 50):
            data[i]['ad']['group'] = 1
        else:
            data[i]['ad']['group'] = 0
    # сортировка
    for i in range(len(data)-1):
        isChange = False
        for y in range(len(data)-1):
            if ((data[y]['gm']['exp'] < data[y + 1]['gm']['exp']) and (data[y]['ad']['group'] == data[y + 1]['ad']['group'])) or (data[y]['ad']['group'] > data[y + 1]['ad']['group']):
                isChange = True
                data[y], data[y + 1] = data[y + 1], data[y]
    return


def get_table_image(data):
    
    def row(i):
        return (i + 1) * 20
    
    def coordinate(area, font, string):
        r = [TBL[area[1]], row(area[0]) + 3]
        if DET[area[1]] or not LFT[area[1]]:
            px = TBL_CHANGE[area[1]]-2
            lens = font.getsize(string)[0]
        if DET[area[1]]:
            while lens > px:
                bad = (lens - px) // 7 + 1
                string = string[:len(string) - bad]
                lens = font.getsize(string)[0]
        if LFT[area[1]]:
            r[0] += 2
        else:
            r[0] += (px - lens) // 2 + 2
        return [(r[0], r[1]), string]

    sort(data)
    # компактизация 'data' в 'dat' и 'group'
    lenD = len(data)
    dat, group = [], []
    timeNow = datetime.now()
    for i in range(lenD):
        timeData = datetime.strptime(data[i]['ad']['time'], '%d.%m.%Y')
        deltD = str((timeNow - timeData).days)
        if data[i]['gm']['isPB'] > 0:
            df = '~' + str(data[i]['gm']['def'])
        else:
            df = str(data[i]['gm']['def'])
        if data[i]['gm']['petL'] > 0:
            pL = str(data[i]['gm']['petL'])
        else:
            pL = ''
        if data[i]['ad']['heroism'] > 0:
            her = str(data[i]['ad']['heroism'])
        else:
            her = ''
        dat.append([deltD, str(i+1), data[i]['gm']['nick'],
                    str(data[i]['gm']['lvl']), df,
                    str(data[i]['gm']['atc']),
                    data[i]['gm']['plCl'][:3],
                    data[i]['gm']['petT'], pL,
                    data[i]['gm']['eq']['spear'],
                    data[i]['gm']['eq']['shield'],
                    data[i]['gm']['eq']['armor'],
                    data[i]['gm']['eq']['helmet'],
                    data[i]['gm']['eq']['glove'],
                    data[i]['gm']['eq']['boot'],
                    data[i]['ad']['username'],
                    data[i]['ad']['name'], her])
        group.append(data[i]['ad']['group'])
    # создание пустого образца с title и с серой колонкой
    w = TBL[-1]
    h = (lenD + 1) * 20             
    im = Image.new('RGB', (w, h), (220, 230, 241))
    draw = ImageDraw.Draw(im, 'RGB')
    font = ImageFont.truetype(r'calibry.ttf', size = 15)
    fontb = ImageFont.truetype(r'calibrib.ttf', size = 15)
    
    title = ['Прошло', '#', 'Ник в игре', 'Ур.', 'Защита', 'Атака', 'Класс', 'Питомец',
             'Ур. пит.', 'Копье', 'Щит', 'Броня', 'Шлем', 'Перчатки', 'Сапоги',
             'Юзернейм', 'В телеграме', 'Гер']
    wht = (255, 255, 255)    
    draw.rectangle((TBL[0], row(-1),  TBL[18], row(0)), (79, 129, 189))
    for y in range(len(TBL)-1):
        coord, string = coordinate((-1, y), font, title[y])
        draw.text(coord, string, wht, font)
        
    isGreyRow = False
    for i in range(lenD):
        if not isGreyRow and (group[i] == 1):
            draw.rectangle((TBL[1], row(i),  TBL[9], row(i + 1)), (178, 178, 178))
            draw.rectangle((TBL[15], row(i),  TBL[18], row(i + 1)), (178, 178, 178))
            isGreyRow = True
            continue
        if i % 2 == 0:
            draw.rectangle((TBL[1], row(i),  TBL[9], row(i + 1)), (242, 242, 242))
            draw.rectangle((TBL[15], row(i),  TBL[18], row(i + 1)), (242, 242, 242))
    # создание разноцветной шкалы для первой колонки y = 0
    cl1 = (147, 210, 144) # зеленый
    cl2 = (255, 235, 132) # желтый средний 
    cl3 = (255, 80, 80) # красный
    cols = []
    for i in range(0, 5):
        col = (cl1[0] + (cl2[0] - cl1[0]) * i // 5, cl1[1] + (cl2[1] - cl1[1]) * i // 5,
               cl1[2] + (cl2[2] - cl1[2]) * i // 5)
        cols.append(col)
    for i in range(5, 14):
        col = (cl2[0] + (cl3[0] - cl2[0]) * (i - 5) // 9, cl2[1] + (cl3[1] - cl2[1]) * (i - 5) // 9,
               cl2[2] + (cl3[2] - cl2[2]) * (i - 5) // 9)
        cols.append(col)
        
    for i in range(lenD):
        delT = 13 if int(dat[i][0]) > 13 else int(dat[i][0])
        delT = delT if delT >= 0 else 0
        draw.rectangle((TBL[0], row(i),  TBL[1], row(i + 1)), cols[delT])             
    # заполнение экипировки изображениями y = 9..14
    blk = (0, 0, 0)
    grn = (0, 97, 0)
    ylw = (156, 101, 0)
    yl = (240, 240, 0)
    blu = (102, 255, 255)
    #                0      1        2        3      4         5    
    #              серый розовый оранжевый зеленый голубой пурпурный
    cols = [(217, 217, 217), (255, 204, 204), (255, 235, 156), (198, 239, 206),
          blu, (255, 102, 255)]
    imC = Image.new('RGB', (60, 20), blu) # создание сложной картинки
    drC = ImageDraw.Draw(imC, 'RGBA')
    x, y = 1, 0
    for i in range(3):
        drC.ellipse((y, x, 60 - y, 20 - x), (240, 240,0, 50 + 20 * i), blu)
        x, y = x + 2 , y + 5 
    del drC# создание завершено
    
    for i in range(lenD):
        for y in range(9, 15):
            s = (dat[i][y] + '+')[0:dat[i][y].find('+')]
            coord, string = coordinate((i, y), font, dat[i][y])
            col = blk
            if s in ['Отч', 'Ночь']:
                colNum = 6
                im.paste(imC, (TBL[y], row(i)))
            elif s in ['Кузн']:
                colNum = 5
            elif s in ['К', 'Т', 'Кост']:
                colNum = 4
            elif s in ['П', 'Д', 'Мол.гн.']:
                colNum = 3
                col = grn
            elif s in ['Х', 'О', 'Кирка']:
                colNum = 2
                col = ylw
            elif s in ['М', 'Рапира', 'Кинж']:
                colNum = 1
            else:
                colNum = 0
            if not colNum == 6:
                draw.rectangle((TBL[y], row(i),  TBL[y + 1], row(i + 1)), cols[colNum])
            draw.text(coord, string, col, font)
    imC.close()
    # заполнение героизма в таблице y = 17
    grey = (128, 128, 128)
    grn = (0, 97, 0)
    for i in range(lenD):
        her = dat[i][17]
        if len(her) > 0:
            if int(her) < 100:
                coord, string = coordinate((i, 17), font, her)
                if int(her) < 50:
                    col = grey
                else:
                    col = blk
                draw.text(coord, string, col, font)
            else:
                coord, string = coordinate((i, 17), fontb, her)
                draw.text(coord, string, grn, fontb)
    # заполнение уровней персонажей в таблице y = 3
    for i in range(lenD):
        level = int(dat[i][3])
        coord, string = coordinate((i, 3), font, str(level))
        if level < 25:
            col = (255, 124, 128)
        elif level < 35:
            col = (255, 192, 0)
        elif level < 40:
            col = (146, 208, 80)
        elif level < 50:
            col = (0, 176, 80)
        else:
            col = (2, 53, 216)
        draw.text(coord, string, col, font)
    # заполнение таблицы остальными данными
    for i in range(lenD):
        for y in (0, 1, 2, 4, 5, 6, 7, 8, 15, 16):
            coord, string = coordinate((i, y), font, dat[i][y])
            draw.text(coord, string, blk, font)
    # обрамляющая рамка в 1 пиксель
    draw.rectangle((0, 0, w-1, h-1), outline=(190, 190, 190))
    #im.show()
    del draw
    with BytesIO() as file:
            im.save(file, 'png')
            image_data = file.getvalue()
    im.close()
    
    return image_data
