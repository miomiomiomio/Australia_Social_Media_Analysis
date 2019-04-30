# # Process raw data and store in new db
# # each tweet include id, text, sentiment, phn_code
import couchdb
from couchdb import design
import logging
import sys
import fiona
import time
from textblob import TextBlob
from shapely.geometry import shape, Point

new_database = "processed_tweets"
GEO_JSON = "PHIDU.json"


# For sentiment analyze, need to be improved
class TweetAnalyzer:
    """Class to analyse sentiment of text."""

    def __init__(self, raw_tweet):
        """Initialise new analysis."""
        self.raw_tweet = raw_tweet
        self.blob = TextBlob(raw_tweet["text"])

    def analyzeSentiment(self):
        """Return sentiment score as float with range of [-1.0, 1.0]."""
        return self.blob.sentiment.polarity

    def analyzeSubjectivity(self):
        """
        Return subjectivity score within range of [0.0, 1.0].
        0.0 is very objective and 1.0 is very subjective.
        """
        return self.blob.sentiment.subjectivity


def view_unprocessed_raw(db):
    map_fnc = """function(doc) {
        if (!doc.processed) {
            emit(doc._id, null);
        }
    }"""
    view = design.ViewDefinition(
        'raw_tweets', 'unprocessed', map_fnc
    )
    view.sync(db)


def view_processed_data(db):
    map_fnc="""function (doc) {
       emit(doc.code, doc.sentiment);
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
    results = db_raw.view('raw_tweets/unprocessed')
    for res in results:
        # Get tweet based on id.
        id = res['id']
        tweet = db_raw[id]

        # Look for coordinates in tweet, which can be a exact coordinates or midpoint.
        if tweet['coordinates']:
            raw = tweet['coordinates']
            coords = tuple(raw['coordinates'])
        # Get the midpoint of this twitter.
        elif tweet['place']:
                coords = average_bounding_box(
                    tweet['place']['bounding_box']['coordinates']
                )

        # Attempt to process if location exists.
        if coords:
            point = Point(coords)
            code = None
            for multi in multipol:
                if point.within(shape(multi['geometry'])):
                    code = multi['properties']['phn_code']
                    sentiment = TweetAnalyzer(tweet).analyzeSentiment()
                    stored_tweet = {
                        '_id': id,
                        'code': code,
                        'text': tweet['text'],
                        'sentiment': sentiment,
                        }
                    db_pro.save(stored_tweet)
                    break
        else:
            logging.info("No coordinates found.")

        doc = db_raw.get(id)
        # processed tweet will not in the view
        doc['processed'] = True
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
    logging.basicConfig(level=logging.INFO)
    # Read locations into memory.
    multipol = fiona.open(GEO_JSON)
    # Get raw tweets db.
    couch_raw = couchdb.Server('http://127.0.0.1:5984')
    try:
        db_raw = couch_raw['raw_data']
    except Exception:
        logging.error("Raw tweets DB does not exist.")
        sys.exit(2)

    # Get processed tweets db.
    couch_pro = couchdb.Server('http://127.0.0.1:5984')
    if new_database in couch_pro:
        db_pro = couch_pro[new_database]
    else:
        db_pro = couch_pro.create(new_database)
    view_processed_data(db_pro)
    # Tag and store tweets.
    while True:
        logging.info("Start processing")
        view_unprocessed_raw(db_raw)
        tag_tweets(db_raw, db_pro, multipol)
        logging.info("Tweets processed, sleeping...Wait for 1200 seconds")
        time.sleep(1200)
