from flask import Flask, request, make_response, Response, jsonify
import json as JSON
from pymongo.collection import Collection
from collections import OrderedDict
import requests
from Libraries import ninja, utils, http_status_code as HTTP, database as DB
import os

app = Flask(__name__)

database = DB.get_database()
dishes_collection = database['dishes']
meals_collection = database['meals']

utils.init_collection_ticket(dishes_collection)
utils.init_collection_ticket(meals_collection)

def generate_new_id(collection: Collection) -> str:
    ticket_document = collection.find_one({DB.Attributes.Ticket.ticket:{"$exists": True}})
    if ticket_document is not None:
        ticket = ticket_document.get(DB.Attributes.Ticket.ticket)
        id = str(ticket)
        ticket += 1
        collection.update_one({}, {"$set": {DB.Attributes.Ticket.ticket:ticket}})
    else:
        id = None
    return id

def fetch_and_get_as_response(collection: Collection, id=None, name=None) -> Response:
    if id is not None:
        id = str(id)
        document = collection.find_one({DB.Attributes.General.id:id})
    else:
        document = collection.find_one({DB.Attributes.General.name:name})
    if document is not None:
        document.pop('_id', None)
        response = make_response(jsonify(document), HTTP.OK)
    else:
        response = make_response('-5', HTTP.NOT_FOUND)
    return response

def fetch(collection: Collection, id=None, name=None):
    if id is not None:
        id = str(id)
        document = collection.find_one({DB.Attributes.General.id:id})
    else:
        document = collection.find_one({DB.Attributes.General.name:name})
    if document is not None:
        dictionary_object = document
    else:
        dictionary_object = None
    return dictionary_object

def remove_deleted_dish_from_meals(id=None, name=None):
    meals_type = [DB.Attributes.Meals.appetizer, DB.Attributes.Meals.main, DB.Attributes.Meals.dessert]
    dish = fetch(dishes_collection, id=id, name=name)
    if dish is not None:
        dish_id = dish[DB.Attributes.Dishes.id]

        for meal_type in meals_type:
            meals_with_deleted_dish = meals_collection.find({meal_type:dish_id})
            if meals_with_deleted_dish is not None:
                for meal in meals_with_deleted_dish:
                    meal[meal_type] = None
                    meal[DB.Attributes.Meals.cal] -= dish[DB.Attributes.Dishes.cal]
                    if meal[DB.Attributes.Meals.cal] < 0:
                        meal[DB.Attributes.Meals.cal] = 0.0
                    meal[DB.Attributes.Meals.sodium] -= dish[DB.Attributes.Dishes.sodium]
                    meal[DB.Attributes.Meals.sugar] -= dish[DB.Attributes.Dishes.sugar]
                    # Insert the updated meal back into the collection
                    meals_collection.replace_one({"_id": meal["_id"]}, meal)

def delete(collection: Collection, id=None, name=None):
    _id = str(id)
    if id is not None:
        document = collection.find_one({DB.Attributes.General.id:_id})
    else:
        document = collection.find_one({DB.Attributes.General.name:name})
    if document is not None:
        _id = document[DB.Attributes.General.id]
        if (collection == dishes_collection):
            remove_deleted_dish_from_meals(id=id, name=name)
        collection.delete_one({DB.Attributes.General.id:_id})
        response = make_response(str(_id), HTTP.OK)
    else:
        response = make_response('-5', HTTP.NOT_FOUND)
    return response

def create_dish(json, name, id):
    cal = size = sodium = sugar = 0
    for i in range(len(json)):
        cal += json[i].get('calories')
        size += json[i].get('serving_size_g')
        sodium += json[i].get('sodium_mg')
        sugar += json[i].get('sugar_g')

    new_json = OrderedDict([
        (DB.Attributes.Dishes.name, name),
        (DB.Attributes.Dishes.id, str(id)),
        (DB.Attributes.Dishes.cal, cal),
        (DB.Attributes.Dishes.size, size),
        (DB.Attributes.Dishes.sodium, sodium),
        (DB.Attributes.Dishes.sugar, sugar)
    ])

    return JSON.dumps(new_json)

def create_meal(meal_name, meal_id, appetizer_id, main_id, dessert_id):
    appetizer_dish = dishes_collection.find_one({DB.Attributes.Dishes.id:appetizer_id})
    main_dish = dishes_collection.find_one({DB.Attributes.Dishes.id:main_id})
    dessert_dish = dishes_collection.find_one({DB.Attributes.Dishes.id:dessert_id})

    total_cal =     appetizer_dish[DB.Attributes.Dishes.cal] + \
                    main_dish[DB.Attributes.Dishes.cal] + \
                    dessert_dish[DB.Attributes.Dishes.cal]
    
    total_sodium =  appetizer_dish[DB.Attributes.Dishes.sodium] + \
                    main_dish[DB.Attributes.Dishes.sodium] + \
                    dessert_dish[DB.Attributes.Dishes.sodium]
    
    total_sugar =   appetizer_dish[DB.Attributes.Dishes.sugar] + \
                    main_dish[DB.Attributes.Dishes.sugar] + \
                    dessert_dish[DB.Attributes.Dishes.sugar]

    new_meal = OrderedDict([
        (DB.Attributes.Meals.name, meal_name),
        (DB.Attributes.Meals.appetizer, str(appetizer_id)),
        (DB.Attributes.Meals.main, str(main_id)),
        (DB.Attributes.Meals.dessert, str(dessert_id)),
        (DB.Attributes.Meals.cal, total_cal),
        (DB.Attributes.Meals.sodium, total_sodium),
        (DB.Attributes.Meals.sugar, total_sugar),
        (DB.Attributes.Meals.id, meal_id)
    ])

    return JSON.dumps(new_meal)

def filter_match_to_diet_meals(all_meals, diet_data):
    filtered_meals = []
    if all_meals is not None:
        for meal in all_meals:
            if meal[DB.Attributes.Meals.cal] <= diet_data[DB.Attributes.Diets.cal] \
                and  meal[DB.Attributes.Meals.sodium] <= diet_data[DB.Attributes.Diets.sodium] \
                and meal[DB.Attributes.Meals.sugar] <= diet_data[DB.Attributes.Diets.sugar]:
                meal.pop('_id', None)
                filtered_meals.append(meal)
    return filtered_meals

@app.route('/dishes', methods=['POST'])
def add_dish():
    if request.is_json:
        json = request.get_json()
        dish_name = json.get('name')
        # no 'name' in json
        if dish_name is None:
            response = make_response('-1', HTTP.BAD_REQUEST)
        # dish is already exists
        elif dishes_collection.find_one({DB.Attributes.Dishes.name:dish_name}) is not None:
            response = make_response('-2', HTTP.BAD_REQUEST)
        else:
            # get dish data from api-ninja
            ninja_response = ninja.request_ninja(dish_name)
            # api-ninja does not recognize dish name supplied
            if ninja_response is None:
                response = make_response('-3', HTTP.BAD_REQUEST)
            # api-ninja server was not reachable or some other server error
            elif ninja_response == 'Server Error':
                response = make_response('-4', HTTP.BAD_REQUEST)
            # legitimate request
            else:
                dish_id = generate_new_id(dishes_collection)
                dish_data = create_dish(JSON.loads(ninja_response), dish_name, dish_id)
                dishes_collection.insert_one(JSON.loads(dish_data))
                response = make_response(str(dish_id), HTTP.CREATED)
    # not a json format
    else:
        response = make_response('0', HTTP.UNSUPPORTED_MEDIA_TYPE)
        
    return response

@app.route('/dishes', methods=['GET'])
def get_dishes():
    # get all dish documents excluding ticket
    all_dishes = dishes_collection.find({DB.Attributes.Dishes.name: {"$exists": True}})
    sorted_dishes = []
    if all_dishes is not None:
        sorted_dishes = sorted(all_dishes, key=lambda dish: int(dish[DB.Attributes.Dishes.id]))
    # Remove _id field from each dish
    for dish in sorted_dishes:
        dish.pop('_id', None)
    response = make_response(jsonify(sorted_dishes), HTTP.OK)
    return response

@app.route('/dishes/', methods=['GET'])
@app.route('/dishes/<int:id>', methods=['GET'])
@app.route('/dishes/<string:name>', methods=['GET'])
def get_dish(id=None, name=None):
    # ID specified
    if id is not None:
        response = fetch_and_get_as_response(dishes_collection, id=id)
    # name specified
    elif name is not None:
        response = fetch_and_get_as_response(dishes_collection, name=name)
    else:
        response = make_response('-1', HTTP.BAD_REQUEST)
    return response

@app.route('/dishes/', methods=['DELETE'])
@app.route('/dishes/<int:id>', methods=['DELETE'])
@app.route('/dishes/<string:name>', methods=['DELETE'])
def delete_dish(id=None, name=None):
    # ID specified
    if id is not None:
        response = delete(dishes_collection, id=id)
    # name specified
    elif name is not None:
        response = delete(dishes_collection, name=name)
    else:
        response = make_response('-1', HTTP.BAD_REQUEST)
    return response

@app.route('/meals', methods=['POST'])
def add_meal():
    if request.is_json:
        json = request.get_json()
        meal_name = str(json.get(DB.Attributes.Meals.name))
        appetizer_id = str(json.get(DB.Attributes.Meals.appetizer))
        main_id = str(json.get(DB.Attributes.Meals.main))
        dessert_id = str(json.get(DB.Attributes.Meals.dessert))
        # no name or appetizer or main or dessert in json
        # comparing to 'None' because of the str(None)
        if meal_name == 'None' or appetizer_id == 'None' or \
            main_id == 'None' or dessert_id == 'None':
            response = make_response('-1', HTTP.BAD_REQUEST)
        # meal is already exists
        elif meals_collection.find_one({DB.Attributes.Meals.name:meal_name}) is not None:
            response = make_response('-2', HTTP.BAD_REQUEST)
        # dish ID's are not numbers
        elif not appetizer_id.isdigit() or not main_id.isdigit() or not dessert_id.isdigit():
            response = make_response('-1', HTTP.BAD_REQUEST)
        # one or more of the dish id's does not exist
        elif dishes_collection.find_one({DB.Attributes.Dishes.id:appetizer_id}) is None \
            or dishes_collection.find_one({DB.Attributes.Dishes.id:main_id}) is None \
            or dishes_collection.find_one({DB.Attributes.Dishes.id:dessert_id}) is None:
            response = make_response('-5', HTTP.NOT_FOUND)
        else:
            meal_id = generate_new_id(meals_collection)
            meals_collection.insert_one(JSON.loads(create_meal(meal_name, meal_id, appetizer_id, main_id, dessert_id)))
            response = make_response(str(meal_id), HTTP.CREATED)
    # not a json format
    else:
        response = make_response('0', HTTP.UNSUPPORTED_MEDIA_TYPE)
    
    return response

@app.route('/meals', methods=['GET'])
def get_meals():
    diet_name = request.args.get('diet')
    # no 'diet' query specified
    if diet_name is None:
        # get all dish documents excluding ticket
        all_meals = meals_collection.find({DB.Attributes.Meals.name: {"$exists": True}})
        sorted_meals = []
        if all_meals is not None:
            sorted_meals = sorted(all_meals, key=lambda meal: int(meal[DB.Attributes.Meals.id]))
        # Remove _id field from each meal
        for meal in sorted_meals:
            meal.pop('_id', None)
        response = make_response(jsonify(sorted_meals), HTTP.OK)
    else:
        diets_service_address = f'http://Diets-Service:5002/diets/{diet_name}'
        try:
            response = requests.get(diets_service_address)
            if response.status_code == HTTP.OK:
                diet_data = response.json()
                all_meals = meals_collection.find({DB.Attributes.Meals.name: {"$exists": True}})
                all_meals_match_to_diet = filter_match_to_diet_meals(all_meals, diet_data)
                response = make_response(jsonify(all_meals_match_to_diet), HTTP.OK)
            else:
                response = make_response(response.text, response.status_code)
        except requests.exceptions.ConnectionError:
            error_msg = f'Failed to establish a connection with {diets_service_address}. Try again later...'
            response = make_response(error_msg, HTTP.BAD_GATEWAY)
    return response

@app.route('/meals/', methods=['GET'])
@app.route('/meals/<int:id>', methods=['GET'])
@app.route('/meals/<string:name>', methods=['GET'])
def get_meal(id=None, name=None):
    # ID specified
    if id is not None:
        response = fetch_and_get_as_response(meals_collection, id=id)
    # name specified
    elif name is not None:
        response = fetch_and_get_as_response(meals_collection, name=name)
    else:
        response = make_response('-1', HTTP.BAD_REQUEST)
    return response

@app.route('/meals/', methods=['DELETE'])
@app.route('/meals/<int:id>', methods=['DELETE'])
@app.route('/meals/<string:name>', methods=['DELETE'])
def delete_meal(id=None, name=None):
    # ID specified
    if id is not None:
        response = delete(meals_collection, id=id)
    # name specified
    elif name is not None:
        response = delete(meals_collection, name=name)
    else:
        response = make_response('-1', HTTP.BAD_REQUEST)
    return response

@app.route('/meals/', methods=['PUT'])
@app.route('/meals/<int:id>', methods=['PUT'])
def update_meal(id=None):
    if id is not None:
        id = str(id)
        meal_to_update = meals_collection.find_one({DB.Attributes.Meals.id:id})
        # no meal with such id exists
        if meal_to_update is None:
            response = make_response('-5', HTTP.NOT_FOUND)
        else:
            if request.is_json:
                json = request.get_json()
                new_meal_name = str(json.get(DB.Attributes.Meals.name))
                new_appetizer_id = str(json.get(DB.Attributes.Meals.appetizer))
                new_main_id = str(json.get(DB.Attributes.Meals.main))
                new_dessert_id = str(json.get(DB.Attributes.Meals.dessert))
                # no name or appetizer or main or dessert in json
                if new_meal_name == 'None' or new_appetizer_id == 'None' \
                    or new_main_id == 'None' or new_dessert_id == 'None':
                    response = make_response('-1', HTTP.BAD_REQUEST)
                # dish id's are not numbers
                elif not new_appetizer_id.isdigit() or not new_main_id.isdigit() or not new_dessert_id.isdigit():
                    response = make_response('-1', HTTP.BAD_REQUEST)
                # one or more of the dish id's does not exist
                elif dishes_collection.find_one({DB.Attributes.Dishes.id:new_appetizer_id}) is None \
                    or dishes_collection.find_one({DB.Attributes.Dishes.id:new_main_id}) is None \
                    or dishes_collection.find_one({DB.Attributes.Dishes.id:new_dessert_id}) is None:
                    response = make_response('-5', HTTP.NOT_FOUND)
                # naming a meal with a name that is already used in different meal
                elif new_meal_name != meal_to_update[DB.Attributes.Meals.name] \
                        and meals_collection.find_one({DB.Attributes.Meals.name:new_meal_name}) is not None:
                    response = make_response('-1', HTTP.BAD_REQUEST)
                else:
                    meal_id = id
                    delete_meal(id=meal_id)
                    meals_collection.insert_one(JSON.loads(create_meal(new_meal_name, meal_id, new_appetizer_id, new_main_id, new_dessert_id)))
                    response = make_response(str(meal_id), HTTP.OK)
            # not a json format
            else:
                response = make_response('0', HTTP.UNSUPPORTED_MEDIA_TYPE)
    else:
        response = make_response('-1', HTTP.BAD_REQUEST)
    
    return response

@app.route('/meals/kill', methods=['POST'])
def kill():
    # Force a crash by exiting the process
    os._exit(1)

if __name__ == '__main__':
    port = os.environ.get('MEALS_PORT')
    app.run(host='0.0.0.0', port=port)