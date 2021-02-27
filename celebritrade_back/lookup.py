import enchant
from urllib.request import urlopen
import json


api_key=''
d = enchant.Dict("en_US")


def search_string(input):
    tokens = input.split()
    tickers = []
    for token in tokens:
        if token[0]=="#":
            token=token[1:]
        if not d.check(token):
           print(token)

def lookup(token):
    url = f"https://financialmodelingprep.com/api/v3/search?query={token}&limit=10&exchange=NASDAQ&apikey={api_key}"
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)


if __name__=='__main__':
    input_str = ''
    search_string(input_str)