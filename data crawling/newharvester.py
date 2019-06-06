# #Harvest tweet and store them in the raw db
# #twitter_credentials.json is needed which contains credential information
# This code need to to run before searchByName.py
import time
import socket
import sys
import threading
import logging
import json
import couchdb
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener

# get the ip of the current host so that we do not have to hardcode the ip part.
def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip

def get_database(database_name):
    try:
        ip = get_host_ip()
        #print(ip)
        address = 'http://'+ 'qwe:qwe@' + ip + ':' + '5984'
        couch = couchdb.Server(address)
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
        if "retweeted_status" not in raw_tweet:
            raw_tweet['_id'] = str(raw_tweet['id'])
            try:
                self.db.save(raw_tweet)
            except couchdb.http.ResourceConflict:
                #logging.info('Ignored duplicate tweet')
                pass
        return True

    def on_error(self, status):
        print(status)
        if status == 420:
            # #Returning False on_data method in case rate limit occurs# #
            logging.info(status)
            return False
        else:
            logging.error(str(status)+" auth_index:"+str(self.auth_index))
            return False


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
    logging.basicConfig(level=logging.INFO)
    index = -1
    # get the name of the host
    name = socket.gethostname()
    # We can let different node search different area but we do not have to change the code .
    if name == 'server-one':
        temp = 1
        db_name='raw_data1'
    if name == 'server-two':
        temp = 2
        db_name='raw_data2'
    if name == 'server-three':
        temp = 3
        db_name='raw_data3'
    while True:
        """
        Melbourne = [144.5990, -38.4339, 145.4666, -37.5675]
        Brisbane = [152.3828, -27.9386, 153.5467, -26.7922]
        Canberra = [148.9439, -35.5926, 149.3993, -35.1245]
        Perth = [115.4495, -32.4695, 116.4152, -31.4551]
        Adelaide = [138.4362, -35.3503, 138.8480, -34.5716]
        Sydney = [150.2815, -34.1202, 151.3430, -33.5781]
        Darwin = [130.8151, -12.4718, 130.9310, -12.3370]
        """
        index = index +1
        AU = [[112.4613, -44.0572, 126.5165, -10.2684],[126.5165, -44.0572, 140.5716, -10.2684],[140.5716, -44.0572, 154.6268, -10.2684]]
        
        db = get_database(db_name)
        listener = MyListener(db, index)
        auth = listener.get_twitter_auth()
        stream = Stream(auth, listener)
        stream.filter(locations=AU[temp-1])
        # if one twitter token can not be used, this code can use the next twitter token
        logging.info("Wait for 10s")
        time.sleep(10)