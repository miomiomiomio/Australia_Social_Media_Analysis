# #Harvest tweet and store them in the raw db
# #twitter_credentials.json contains credential information
# # 改动：将所有数据存到一个数据库中
import time
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
    """
    Melbourne = [144.5990, -38.4339, 145.4666, -37.5675]
    Brisbane = [152.3828, -27.9386, 153.5467, -26.7922]
    Canberra = [148.9439, -35.5926, 149.3993, -35.1245]
    Perth = [115.4495, -32.4695, 116.4152, -31.4551]
    Adelaide = [138.4362, -35.3503, 138.8480, -34.5716]
    Sydney = [150.2815, -34.1202, 151.3430, -33.5781]
    Darwin = [130.8151, -12.4718, 130.9310, -12.3370]
    """
    AU = [112.4613, -44.0572, 154.6268, -10.2684]
    # 不确定多线程是否会加快速度，一个线程挂了其他也可以继续运行⬅猜想
    thread1 = MyThread('raw_data',AU,0)
    thread2 = MyThread('raw_data',AU,1)
    thread3 = MyThread('raw_data',AU,2)
    thread4 = MyThread('raw_data',AU,3)
    thread5 = MyThread('raw_data',AU,4)
    thread6 = MyThread('raw_data',AU,5)
    thread7 = MyThread('raw_data',AU,6)

    thread1.start()
    # 运行前数据库没有创建时会报错，需要暂停一会，如果运行前数据库已经创建了就不需要
    time.sleep(10)
    thread2.start()
    thread3.start()
    thread4.start()
    thread5.start()
    thread6.start()
    thread7.start()