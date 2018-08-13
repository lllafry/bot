from json import load, dump

def load_data():
    with open(r'config/dat.txt') as file:
        data = load(file)
    return data

def save_data(data):
    with open (r'config/dat.txt', 'w') as file:
        dump(data, file)
    return

def load_comm():
    with open(r'config/comm.txt') as file:
        data = load(file)
    return data

def save_comm(data):
    with open (r'config/comm.txt', 'w') as file:
        dump(data, file)
    return

def load_log():
    with open(r'config/TableEx.txt') as file:
        data = load(file)
    return data

def save_log(data):
    with open (r'config/TableEx.txt', 'w') as file:
        dump(data, file)
    return

def load_info():
    with open(r'config/users and chats.txt') as file:
        data = load(file)
    return data['admins'], data['chats']

def save_info(admins, chats):
    with open (r'config/users and chats.txt', 'w') as file:
        data = {}
        data['admins'] = admins
        data['chats'] = chats
        dump(data, file)
    return 
