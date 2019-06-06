# # Process raw data and store in new db
# # each tweet include id, text, sentiment, PHNcode
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer, negated
import re
from gluttony_keywords import GluttonyKeywords
import math
from textblob import TextBlob
import fiona
import couchdb
from couchdb import design
import logging
import sys
from shapely.geometry import shape, Point
import socket
import time


GEO_JSON = "PHIDU.json"
# new_database = "glunttony_tweets"

analyzer = SentimentIntensityAnalyzer()


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


def analyzing_sentiment_score(text):

    return analyzer.polarity_scores(text)


def analyzing_negation(text):

    return negated(text)


def sigmoid(x):
    return 1.0 / (1 + math.exp(-float(x)))


def grade_function(text,index):

    graded = TextBlob(text)
    text_words = graded.words
    number = len(text_words)
    if number is 0:
        grade = 0
    else:
        grade = sigmoid(index/number)

    return grade


class GluttonyAnalysis:

    def __init__(self, raw_tweet):

        self.text = raw_tweet["text"]
        #self.text = raw_tweet

    def analyzing_gluttony(self):

        twitter_text = self.text

        gluttony_flag = False

        sentiment_result= analyzing_sentiment_score(twitter_text)
        sentiment_score = sentiment_result['compound']

        related_index = 0

        if not analyzing_negation(twitter_text):

            for food in GluttonyKeywords.unhealthfood:
                if re.search(r'\b' + food, twitter_text):
                    gluttony_flag = True
                    related_index = related_index + 1
                    print(food)

            for food in GluttonyKeywords.healthfood:
                if re.search(r'\b' + food, twitter_text):

                    related_index = related_index + 1

                    if sentiment_score < -0.05:
                        gluttony_flag = True

        grade = grade_function(twitter_text, related_index)

        return gluttony_flag, grade


def view_unprocessed_raw(db):
    map_fnc = """function(doc) {
        if (!doc.gluttony_processed) {
            emit(doc._id, null);
        }
    }"""
    view = design.ViewDefinition(
        'raw_tweets', 'gluttony_unprocessed', map_fnc
    )
    view.sync(db)


def view_processed_data(db):
    map_fnc="""function (doc) {
       emit(doc.code, doc.gluttony);
    }"""
    reduce_fnc="""function (keys, values, rereduce) {
        var analysis = { count: 0, polarity: 0 };
        if (rereduce){
              for(var i=0; i < values.length; i++) {
                analysis.count += values[i].count;
                analysis.polarity += values[i].polarity;
                }
                analysis.polarity = analysis.polarity / analysis.count;
                return analysis;
        }
        analysis.count = values.length;
        analysis.polarity = sum(values);
        return analysis;
    }"""
    # analysis.count = values.length 意思是有多少条记录
    # analysis.polarity = sum(values) 意思是把这些记录的值加起来
    view=design.ViewDefinition('sentiment_analysis','sentiment_analysis',map_fnc,reduce_fun=reduce_fnc)
    view.sync(db)


def tag_tweets(db_raw, db_pro, multipol):
    # Tag raw tweets and add phn_code into processed tweet
    results = db_raw.view('raw_tweets/gluttony_unprocessed')
    for res in results:
        # Get tweet based on id.
        id = res['id']
        tweet = db_raw[id]

        # Look for coordinates in tweet, which can be a exact coordinates or midpoint.
        coords = ()
        # Look for coordinates in tweet, which can be a exact coordinates or midpoint.
        if tweet['coordinates']:
            raw = tweet['coordinates']
            coords = tuple(raw['coordinates'])
        # Get the midpoint of this twitter.
        elif tweet['place']:
            if tweet['place']['bounding_box']:
                if tweet['place']['bounding_box']['coordinates']:
                    coords = average_bounding_box(
                        tweet['place']['bounding_box']['coordinates']
                    )

        # Attempt to process if location exists.
        if coords != ():
            point = Point(coords)

            code = None

            for multi in multipol:
                if point.within(shape(multi['geometry'])):
                    code = multi['properties']['phn_code']
                    gluttony, gluttony_level = GluttonyAnalysis(tweet).analyzing_gluttony()
                    #sentiment = TweetAnalyzer(tweet).analyzeSentiment()

                    if gluttony:
                        stored_tweet = {
                            '_id': id,
                            'code': code,
                            'text': tweet['text'],
                            'gluttony': gluttony_level,
                        }
                    else:
                        stored_tweet = {
                            '_id': id,
                            'code': code,
                            'text': tweet['text'],
                            'gluttony': 0,
                        }
                    try:
                        db_pro.save(stored_tweet)
                    except couchdb.http.ResourceConflict:
                        pass
                    break
        else:
            pass

        doc = db_raw.get(id)
        # processed tweet will not in the view
        doc['gluttony_processed'] = True
        db_raw.save(doc)


def average_bounding_box(box):
    # find the midpoint
    lng = 0
    lat = 0
    for i in range(len(box[0])):
        lng += box[0][i][0]
        lat += box[0][i][1]
    lat /= 4
    lng /= 4
    return lng, lat


if __name__ == "__main__":

    name = socket.gethostname()
    if name == 'server-one':
        db_name='raw_data1'
        new_database="glunttony_tweets1"
    if name == 'server-two':
        db_name='raw_data2'
        new_database="glunttony_tweets2"
    if name == 'server-three':
        db_name='raw_data3'
        new_database="glunttony_tweets3"

    """ raw_text = [
        "I think is great and sometime eat chocolate are very convience",
        "hamberger,jicama"
                ]
    for text in raw_text:
        flag, index = GluttonyAnalysis(text).analyzing_gluttony()
        score = analyzer.polarity_scores(text)
        print(score, flag, index)
        
    """
    logging.basicConfig(level=logging.INFO)
    multipol = fiona.open(GEO_JSON)

    ip = get_host_ip()
    address = 'http://'+ 'qwe:qwe@' + ip + ':' + '5984'
    couch_raw = couchdb.Server(address)

    # couch_raw = couchdb.Server('http://172.26.38.135:5984')
    try:
        db_raw = couch_raw[db_name]
    except Exception:
        logging.error("Raw tweets DB does not exist.")
        sys.exit(2)

    # couch_pro = couchdb.Server('http://172.26.38.135:5984')
    couch_pro = couchdb.Server(address)

    if new_database in couch_pro:
        db_pro = couch_pro[new_database]
    else:
        db_pro = couch_pro.create(new_database)

    view_processed_data(db_pro)

    while True:
        logging.info("Start processing")
        view_unprocessed_raw(db_raw)
        tag_tweets(db_raw, db_pro, multipol)
        logging.info("Tweets processed, sleeping...Wait for 1200 seconds")
        time.sleep(1200)