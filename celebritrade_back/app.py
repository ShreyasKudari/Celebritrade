from flask import Flask, request, g, redirect, url_for, jsonify
import json
from urllib.request import urlopen
import tweepy
import threading
from flask_cors import CORS
from pymongo import MongoClient
import os
import config
from google.cloud import language_v1, bigquery
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
CORS_SUPPORTS_CREDENTIALS = True

app = Flask(__name__)
app.config.from_object('config')
account_sid = app.config["ACCOUNT_SID"]
twilio_number = app.config['TWILIO_NUMBER']
# Your Auth Token from twilio.com/console
api_key= app.config['API_KEY']
auth_token  = app.config['AUTH_TOKEN']
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = app.config['GOOGLE']
consumer_key = app.config['CONSUMER_KEY']
consumer_secret = app.config['CONSUMER_SECRET']
access_token = app.config['ACCESS_TOKEN']
access_token_secret = app.config['ACCESS_TOKEN_SECRET']
db_connection_url = app.config['DB_CONNECTION_URL']

cors = CORS(app, resources={r"*": {"origins": "*"}})
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
twiclient = Client(account_sid, auth_token)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
client = MongoClient(db_connection_url)
db = client.celebritrade
users = db.users
followers = db.followers
stream_lock = threading.Lock()



class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        stream_lock.acquire()
        # print(status.user.id)
        # print(status.user.screen_name)
        results, sentiment=analyze(status.text)
        if results != "":
            message_users(results,status.user.id,status.user.screen_name, sentiment)
        stream_lock.release()
    def on_error(self, status_code):
        print(status_code)
        return False


global_stream_listener = MyStreamListener()
global_stream = None
handles = set({})
celebs = []



def initialize():
    stream_lock.acquire()
    global global_stream
    global global_stream_listener
    if global_stream is not None:
        global_stream.disconnect()
    global_stream_listener = MyStreamListener()
    global_stream = tweepy.Stream(auth = api.auth, listener=global_stream_listener)
    global_stream.filter(follow=celebs,is_async = True)
    stream_lock.release()
    



@app.route('/add_user', methods=['POST'])
def add_user():
    req = request.get_json()
    user_ids = list(req["handles"])
    phone = req["phone"]
    #TODO assume phone exists but once twilio is in add a number verification check
    print(user_ids)
    flag = 0
    for user_id in user_ids:
        try:
            user = api.get_user(screen_name=user_id)
            doc = users.find_one({"phone": phone})
            if doc is None:
                users.insert_one({"phone": phone,"option":req["option"],'handles': [str(user.id)]})
                service_confirmation(phone, user.screen_name)
            elif str(user.id) not in doc['handles']:
                users.update_one({"phone": phone}, {'$set':{'option':req['option']},'$push': {'handles': str(user.id)}})
                service_confirmation(phone, user.screen_name)
            else:
                users.update_one({"phone": phone}, {'$set':{'option':req['option']}})
            followdoc = followers.find_one({"celeb":str(user.id)})
            if followdoc is None:
                followers.insert_one({"celeb":str(user.id),"phone":[str(phone)]})
            elif(phone not in followdoc['phone']):
                followers.update_one({"celeb": str(user.id)}, {'$push':{"phone": phone}})
            if(str(user.id) not in handles):
                print(user.screen_name)
                handles.add(str(user.id))
                celebs.append(str(user.id))
                flag = 1
        except Exception:
            return jsonify("Failed")
    
    if flag ==1 :
        initialize()
    return jsonify("Posted")

def service_confirmation(phone, name):
      twiclient.messages.create(
        to='+1'+phone, 
        from_='+1'+twilio_number,
        body="You are now subscibed to "+name+'.\n Send UNSUB to unsubscribe')

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    msg = request.values.get('Body').lower() #gets incoming message
    origin = request.values.get('From')[2:]
    if msg == "UNSUB".lower(): #based on incoming message, send different message
        try:
            doc = users.find_one({'phone':str(origin)})
            for celeb in doc['handles']:
                followers.update_one({'celeb': celeb},{'$pull':{'phone':str(origin)}})
            users.delete_one({'phone':str(origin)})
        except Exception:
            raise
        return "success"
    return "failed"

def message_users(results, userid, screenname, sentiment):
    doc=followers.find_one({"celeb": str(userid)})
    s_score = str((sentiment+1)*100/2)
    for phone in doc['phone']:
        text = "Hey There! "+screenname+" appears to have just tweeted about: \n"+results+"\n Sentiment: "\
        +s_score+"% positive"
        twiclient.messages.create(
        to='+1'+phone, 
        from_='+1'+twilio_number,
        body=text)

        if users.find_one({"phone":phone})['option'].upper()=="call+text".upper():
            twiclient.calls.create(
                twiml='<Response><Say>Update from Celebritrade. Check messages</Say></Response>',
                to='+1'+phone,
                from_='+1'+twilio_number
            )

def analyze(tweet):
    # Instantiates a client
    client = language_v1.LanguageServiceClient()
    query_client = bigquery.Client()
    # The text to analyze
    text = tweet
    type_ = language_v1.Document.Type.PLAIN_TEXT
    text = text.replace("#","")
    text = text.replace("$","")
    # Optional. If not specified, the language is automatically detected.
    # For list of supported languages:
    # https://cloud.google.com/natural-language/docs/languages
    language = "en"
    document = {"content": text, "type_": type_, "language": language}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = language_v1.EncodingType.UTF8

    response = client.analyze_entities(request = {'document': document, 'encoding_type': encoding_type})
    sentiment = client.analyze_sentiment(request = {'document': document, 'encoding_type': encoding_type})
   

    results = []
    tickers = []
    for entity in response.entities:
        # print(u"Representative name for the entity: {}".format(entity.name))
        items = entity.name.split()
        block = {'STOCK','SHARE','HOLDINGS', 'COMMON', 'CORP','CORPORATION'}
        for item in items:
            if item.upper() not in block and language_v1.Entity.Type(entity.type_).name != "NUMBER":
            

                query_job = query_client.query(
                    """
                    SELECT Symbol, Name
                    FROM `querytest-1611951823682.Stocks.Nasdaq` 
                    WHERE UPPER(Name) like UPPER('{}')
                    OR Symbol = UPPER('{}')
                    LIMIT 5
                    """.format('%'+item+' %', item)
                )
                query_results = query_job.result()
                results.append(query_results)
        # # Get entity type, e.g. PERSON, LOCATION, ADDRESS, NUMBER, et al
        # print(u"Entity type: {}".format(language_v1.Entity.Type(entity.type_).name))

        # # Get the salience score associated with the entity in the [0, 1.0] range
        # print(u"Salience score: {}".format(entity.salience))
    stocks = ""
    for result in results:
        for row in result:
            stocks+='$'+row.Symbol+" @ Price:"+str(lookup_price(row.Symbol))+"\n"
            tickers.append(row.Symbol)
        stocks+="\n"
    if(len(tickers)>0):
        stocks+=getnewslinks(tickers)
    return stocks, sentiment.document_sentiment.score

@app.route('/')
def index():
    return "Hello world"
def lookup_price(token):
    url = f"https://financialmodelingprep.com/api/v3/quote-short/{token}?apikey={api_key}"
    response = urlopen(url)
    data = response.read().decode("utf-8")
    data = json.loads(data)
    if len(data)>0:
        return data[0]['price']
    else:
        return "N/A"

def getnewslinks(tickers):
    links = []
    token = ",".join(tickers)
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={token}&limit=3&apikey={api_key}"
    response = urlopen(url)
    data = response.read().decode("utf-8")
    data = json.loads(data)
    for item in data:
        links.append(item["url"])
    return "\n".join(links)


if __name__=='__main__':
    app.run(host='127.0.0.1',port="5050")
