# #This file is used for harvest tweet and store them in the corresponding database# #
# #twitter_credentials.json contains credential information# #
import sys
import threading
import logging
import json
import couchdb
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener


def get_database(database_name):
    try:
        couch = couchdb.Server('http://127.0.0.1:5984')
        # Check if database exists, create if not
        db_name = database_name
        if db_name in couch:
            logging.info("Database {} already exists.".format(db_name))
            db = couch[db_name]
        else:
            logging.info("Create {} database.".format(db_name))
            db = couch.create(db_name)
    except Exception as e:
        logging.error(str(e)+"couchdb error")
        sys.exit(2)
    return db


class MyListener(StreamListener):

    def __init__(self, db, auth_index):
        self.db= db
        self.auth_index = auth_index

    def get_twitter_auth(self):
        with open('twitter_credentials.json') as fp:
            jconfig = json.load(fp)
            try:
                ckey = jconfig['Authentication'][self.auth_index]['ConsumerKey']
                csecret = jconfig['Authentication'][self.auth_index]['ConsumerSecret']
                atoken = jconfig['Authentication'][self.auth_index]['AccessToken']
                asecret = jconfig['Authentication'][self.auth_index]['AccessTokenSecret']
            except Exception as e:
                logging.error(str(e)+" read_authentication_error")
                sys.exit(2)
        auth = OAuthHandler(ckey, csecret)
        auth.set_access_token(atoken, asecret)
        return auth

    def on_data(self, data):
        raw_tweet = json.loads(data)
        raw_tweet['_id'] = str(raw_tweet['id'])
        try:
            self.db.save(raw_tweet)
        except couchdb.http.ResourceConflict:
            logging.info('Ignored duplicate tweet')
        return True

    def on_error(self, status):
        if status == 420:
            # #Returning False on_data method in case rate limit occurs# #
            logging.info(status)
            return False
        else:
            logging.error(str(status)+" auth_index:"+str(self.auth_index))


class MyThread(threading.Thread):
    def __init__(self, db, region, auth_index):
        threading.Thread.__init__(self)
        self.db = db
        self.region = region
        self.auth_index = auth_index

    def run(self):
        db = get_database(self.db)
        listener = MyListener(db,self.auth_index)
        auth = listener.get_twitter_auth()
        stream = Stream(auth, listener)
        stream.filter(locations=self.region)


if __name__ == "__main__":
    Melbourne = [144.67, -38.16, 145.39, -37.58]
    Brisbane = [152.65, -27.75, 153.44, -27.05]
    Canberra = [149.00, -35.45, 149.16, -35.15]
    Perth = [115.80, -31.94, 115.86, -31.90]
    Adelaide = [138.47, -35.02, 138.73, -34.72]
    Sydney = [150.74, -34.03, 151.28, -33.67]
    Darwin = [130.82, -12.48, 130.86, -12.44]
    AU = [115.86, -34.74, 152.51, -14.35]
    thread1 = MyThread('melbourne_raw_data',Melbourne,0)
    thread2 = MyThread('brisbane_raw_data',Brisbane,1)
    thread3 = MyThread('canberra_raw_data',Canberra,2)
    thread4 = MyThread('perth_raw_data',Perth,3)
    thread5 = MyThread('adelaide_raw_data',Adelaide,4)
    thread6 = MyThread('sydney_raw_data',Sydney,5)
    thread7 = MyThread('darwin_raw_data',Darwin,6)

    thread1.start()
    thread2.start()
    thread3.start()
    thread4.start()
    thread5.start()
    thread6.start()
    thread7.start()