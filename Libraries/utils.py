import json as JSON
import Libraries.database as DB
from pymongo.collection import Collection

def init_collection_ticket(collection: Collection):
    ticket = collection.find_one({DB.Attributes.Ticket.ticket: {"$exists": True}})
    if ticket is None:
        collection.insert_one({DB.Attributes.Ticket.ticket: 1})

def is_number(variable):
    return isinstance(variable, (int, float))