from flask import Flask, request, make_response, Response, jsonify
import json as JSON
from pymongo.collection import Collection
from Libraries import utils, http_status_code as HTTP, database as DB
import os

app = Flask(__name__)

database = DB.get_database()
diets_collection = database['diets']

def create_diet(diet_name, diet_cal, diet_sodium, diet_sugar):
    diet_data = {
        DB.Attributes.Diets.name: diet_name,
        DB.Attributes.Diets.cal: diet_cal,
        DB.Attributes.Diets.sodium: diet_sodium,
        DB.Attributes.Diets.sugar: diet_sugar
    }
    return JSON.dumps(diet_data)

def fetch_and_get_as_response(collection: Collection, name=None) -> Response:
    document = collection.find_one({DB.Attributes.General.name:name})
    if document is not None:
        document.pop('_id', None)
        response = make_response(jsonify(document), HTTP.OK)
    else:
        response = make_response(f'Diet {name} not found', HTTP.NOT_FOUND)
    return response

@app.route('/diets', methods=['POST'])
def add_diet():
    if request.is_json:
        json = request.get_json()
        diet_name = json.get(DB.Attributes.Diets.name)
        diet_cal = json.get(DB.Attributes.Diets.cal)
        diet_sodium = json.get(DB.Attributes.Diets.sodium)
        diet_sugar = json.get(DB.Attributes.Diets.sugar)
        # one of 'name', 'ca', 'sodium', 'sugar' is missing
        # one of 'name', 'ca', 'sodium', 'sugar' is not a number
        if diet_name is None or diet_cal is None or diet_sodium is None or diet_sugar is None \
            or not utils.is_number(diet_cal) or not utils.is_number(diet_sodium) or not utils.is_number(diet_sugar):
            response = make_response('Incorrect POST format', HTTP.UNPROCESSABLE_ENTITY)
        # diet is already exists
        elif diets_collection.find_one({DB.Attributes.Diets.name:diet_name}) is not None:
            response = make_response(f'Diet with {diet_name} already exists', HTTP.UNPROCESSABLE_ENTITY)
        # legitimate request
        else:
            diets_collection.insert_one(JSON.loads(create_diet(diet_name, diet_cal, diet_sodium, diet_sugar)))
            response = make_response(f'Diet {diet_name} was created successfully', HTTP.CREATED)
    # not a json format
    else:
        response = make_response('POST expects content type to be application/json', HTTP.UNSUPPORTED_MEDIA_TYPE)

    return response

@app.route('/diets', methods=['GET'])
def get_diets():
    # get all diet documents
    all_diets = diets_collection.find({DB.Attributes.Diets.name: {"$exists": True}})
    if all_diets is None:
        all_diets = list()
    else:
        all_diets = list(all_diets)
    # Remove _id field from each diet
    for diet in all_diets:
        diet.pop('_id', None)
    response = make_response(jsonify(all_diets), HTTP.OK)
    return response

@app.route('/diets/<string:name>', methods=['GET'])
def get_diet(name):
    response = fetch_and_get_as_response(diets_collection, name=name)
    return response

@app.route('/diets/kill', methods=['POST'])
def kill():
    # Force a crash by exiting the process
    os._exit(1)

if __name__ == '__main__':
    port = os.environ.get('DIETS_PORT')
    app.run(host='0.0.0.0', port=port)