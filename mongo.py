def load_data(db):
    return db.users.find_one()['users']

def load_comms(db):
    return db.comms.find_one()['comms']

def load_admins(db):
    return db.admins.find_one()['admins']

def load_chats(db):
    return db.chats.find_one()['chats']

def load_back_data(db, ID):
    data = db.back_data.find_one({'ID': ID})
    db.back_data.delete_many({'ID': ID})
    return data

def load_battle_tick(db):
    return db.btl.find_one()['btl']

def save_data(db, data):
    obj_id = db.users.find_one()['_id']
    db.users.insert_one({'users': data})
    db.users.delete_one({'_id': obj_id})

def save_comms(db, data):
    obj_id = db.comms.find_one()['_id']
    db.comms.insert_one({'comms': data})
    db.comms.delete_one({'_id': obj_id})

def save_admins(db, data):
    obj_id = db.admins.find_one()['_id']
    db.admins.insert_one({'admins': data})
    db.admins.delete_one({'_id': obj_id})

def save_chats(db, data):
    obj_id = db.chats.find_one()['_id']
    db.chats.insert_one({'chats': data})
    db.chats.delete_one({'_id': obj_id})

def save_back_data(db, user):
    db.back_data.delete_one({'ID': user['ID']})
    db.back_data.insert_one(user)

def save_battle_tick(db, data):
    obj_id = db.btl.find_one()['_id']
    db.btl.insert_one({'btl': data})
    db.btl.delete_one({'_id': obj_id})
