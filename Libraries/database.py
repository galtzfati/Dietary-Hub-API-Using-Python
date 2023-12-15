from pymongo import MongoClient
import os

def get_database():
    mongo_uri = os.environ.get('MONGO_URI')
    database_name = os.environ.get('DATABASE_NAME')
    client = MongoClient(mongo_uri)
    database = client[database_name]
    return database

class Attributes:
    class General:
        name = 'name'
        id = 'ID'
    class Ticket:
        ticket = 'ticket'
    class Meals:
        name = 'name'
        id = 'ID'
        appetizer = 'appetizer'
        main = 'main'
        dessert = 'dessert'
        cal = 'cal'
        sodium = 'sodium'
        sugar = 'sugar'
    class Dishes:
        name = 'name'
        id = 'ID'
        cal = 'cal'
        size = 'size'
        sodium = 'sodium'
        sugar = 'sugar'
    class Diets:
        name = 'name'
        cal = 'cal'
        sodium = 'sodium'
        sugar = 'sugar'