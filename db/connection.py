import pymysql

def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='admin@123',
        db='yatrii',
        cursorclass=pymysql.cursors.DictCursor
    )
