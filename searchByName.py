# https://stackoverflow.com/questions/31571995/tweepy-error-tweeperror-twitter-error-response-status-code-401
# Search tweet by each user name
from tweepy import API
from tweepy import Cursor
from tweepy import OAuthHandler
import logging
import sys
import couchdb
from couchdb import design
import time
logging.getLogger().setLevel(logging.INFO)


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




def get_user_timeline_tweets(db_raw,api):
    result=db_raw.view('raw_tweets/username_not_used')
    for res in result:
        id = res['id']
        tweet = db_raw[id]
        name= tweet['user']['name']
        try:
            for raw_tweet in Cursor(api.user_timeline, id=name).items():
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

            doc=db_raw.get(id)
            doc['username'] = True
            db_raw.save(doc)
        except:
            pass



if __name__ == '__main__':
    consumer_key = 'UlcKpGAMU5fW9uHi1xmEHlfF1'
    consumer_secret = 'sHRmEho9FwnOjHYzaNFj010DR0YyoCdW7Ino1l13L9EfeWCr52'
    access_token = '925304770193104897-XMkXssOdzi2Olfw9cBA4YhCYFq4Nl4P'
    access_secret = 'NR1OQYnZeM756wbfgXClNG3VCXKSBu8rTfD8UMK7uaeHR'
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    api = API(auth)
    couch_raw = couchdb.Server('http://127.0.0.1:5984')
    try:
        db_raw = couch_raw['raw_data']
    except Exception:
        logging.error("Raw tweets DB does not exist.")
        sys.exit(2)
    while True:
        logging.info("Start get tweet by username")
        view_unprocessed_raw(db_raw)
        get_user_timeline_tweets(db_raw,api)
        logging.info("No new tweets, wait for 60 seconds")
        time.sleep(60)
