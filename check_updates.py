import requests

url = "https://api.telegram.org/bot794555801:AAEos1HrFYUDst0orxtRZVjs_8QMIN-HsOM/"


def get_updates_json(request):
    response = requests.get(request + 'getUpdates')
    return response.json()


def last_update(data):
    results = data['result']
    total_updates = len(results) - 1
    return results[total_updates]