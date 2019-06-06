# https://stackoverflow.com/questions/31571995/tweepy-error-tweeperror-twitter-error-response-status-code-401
# Search tweet by each user name
# we also search each user's friends' twitter to reduce personal influence
# This coed need to be run after newharvester.py
from tweepy import API
from tweepy import Cursor
from tweepy import OAuthHandler
import time
import logging
import sys
import couchdb
from couchdb import design
import time
import socket
logging.getLogger().setLevel(logging.INFO)
#get the ip of the node so that we do not have to hardcode the ip part
def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


# create a view of raw db so that the precessed twitter will not be shown in this view again
# which can prevent one twitter from been processed many times
def view_unprocessed_raw(db):
    map_fnc = """function(doc) {
        if (!doc.username) {
            emit(doc._id, null);
        }
    }"""
    view = design.ViewDefinition(
        'raw_tweets', 'username_not_used', map_fnc
    )
    view.sync(db)

# api.friends and api.user_timeline in search API
def get_user_timeline_tweets(db_raw,api):
    result=db_raw.view('raw_tweets/username_not_used')
    for res in result:
        id = res['id']
        tweet = db_raw[id]
        name= tweet['user']['screen_name']
        try:
            for friend in Cursor(api.friends, screen_name=name).items(100):
                friend_id=friend._json['id']
                try:
                    for friend_raw_tweet in Cursor(api.user_timeline,user_id=friend_id).items(100):
                        friend_raw_tweet._json['_id'] = str(friend_raw_tweet._json['id'])
                        friend_raw_tweet._json['username'] = True
                        try:
                            db_raw.save(friend_raw_tweet._json)
                        except couchdb.http.ResourceConflict:
                            pass
                except:
                    pass
        except:
            pass
        try:
            for raw_tweet in Cursor(api.user_timeline, screen_name=name).items(100):
                '''
                tweet_temp = {'id': status.id_str, 'user': status._json['user'], 'place': status._json['place'],
                                    'text': status.text, 'coordinates': status._json['coordinates']}
                '''
                raw_tweet._json['_id'] = str(raw_tweet._json['id'])
                raw_tweet._json['username'] = True
                try:
                    db_raw.save(raw_tweet._json)
                    #print(raw_tweet._json)
                except couchdb.http.ResourceConflict:
                    pass

            doc = db_raw.get(id)
            doc['username'] = True
            db_raw.save(doc)
        except:
            pass



if __name__ == '__main__':
    logging.info("wait for 20s")
    time.sleep(20)
    consumer_key = 'UlcKpGAMU5fW9uHi1xmEHlfF1'
    consumer_secret = 'sHRmEho9FwnOjHYzaNFj010DR0YyoCdW7Ino1l13L9EfeWCr52'
    access_token = '925304770193104897-XMkXssOdzi2Olfw9cBA4YhCYFq4Nl4P'
    access_secret = 'NR1OQYnZeM756wbfgXClNG3VCXKSBu8rTfD8UMK7uaeHR'
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    api = API(auth,wait_on_rate_limit= True)
    # get the name of the host
    name = socket.gethostname()
    # We can let different node search different area but we do not have to change the code.
    if name == 'server-one':
        temp = 1
        db_name='raw_data1'
    if name == 'server-two':
        temp = 2
        db_name='raw_data2'
    if name == 'server-three':
        temp = 3
        db_name='raw_data3'
    '''
    consumer_key2='kiLz9KGKoly1YqlFniL91Avcl'
    consumer_secret2='Ff7NxXzN9eUrHOWyWyjlscXwLSC3pUMwYBaVMmy37mOe6yNVUg'
    access_token2= '925304770193104897-UiszSjN3pO0faPZNyd1E6bwgEW68jJy'
    access_secret2= 'mqIOj8W9oYNSoqY5KrX1GmPGEXZkTq9IYSNsfsJVRS1k5'
    auth2 = OAuthHandler(consumer_key2, consumer_secret2)
    auth2.set_access_token(access_token2, access_secret2)
    api2 = API(auth2, wait_on_rate_limit=True)

    consumer_key3="JKzUa3F0yiNLq460kORxe0KM2",
    consumer_secret3="1efpSOFxA0VF3IIOor16jIguTcOOIdO9dd8znDQRvE6fRQY4FT",
    access_token3= "757469703547879424-PQCqCVPhItFqIljX7PxSH6BDbyqg5Mh",
    access_secret3= "s146GWiClnBv7s2VOBsEMzZjTnNTj82LX9H9kWT8k7LDY"
    auth3 = OAuthHandler(consumer_key3, consumer_secret3)
    auth3.set_access_token(access_token3, access_secret3)
    api3 = API(auth3, wait_on_rate_limit=True)
    '''
    # couch_raw = couchdb.Server('http://172.26.38.74:5984')
    ip = get_host_ip()
    address = 'http://' + 'qwe:qwe@' + ip + ':' + '5984'
    print(address)
    couch_raw = couchdb.Server(address)
    try:
        db_raw = couch_raw[db_name]
    except Exception:
        logging.error("Raw tweets DB does not exist.")
        sys.exit(2)
    while True:
        logging.info("Start get tweet by username")
        view_unprocessed_raw(db_raw)
        get_user_timeline_tweets(db_raw,api)
        logging.info("No new tweets, wait for 60 seconds")
        time.sleep(60)
