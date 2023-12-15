import requests

def request_ninja(dish):
    api_url = 'https://api.api-ninjas.com/v1/nutrition?query={}'.format(dish)
    response = requests.get(api_url, headers={"YOUR_NINJA_CONNECTION_KEY"})
    if response.status_code == requests.codes.ok:
        if is_recognized(response.text):
            return response.text
        return None
    else:
        return 'Server Error'

def is_recognized(dish):
    if dish == '[]' or dish is None:
        return False
    return True