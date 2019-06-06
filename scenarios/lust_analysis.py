# # Process raw data and store in new db
# # each tweet include id, text, sentiment, lga_code
import couchdb
from couchdb import design
import logging
import sys
import fiona
import time
from textblob import TextBlob
from shapely.geometry import shape, Point
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from nltk.stem import PorterStemmer
from textblob import TextBlob
from textblob import Word
import socket
import nltk
import re

GEO_JSON = "Crime.json"

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


def runLustAnalysis(text):
    f = open('pornographyDic.txt')
    line = f.readlines()
    line = str(line)
    sl = line.split(',')
    nl = []
    for w in sl:
        w = w.strip('[\'')
        w = w.strip('\']')
        nl.append(w.lower())

    ps = PorterStemmer()
    analyzer = SentimentIntensityAnalyzer()
    if len(text)>=3:
        blob = TextBlob(text)
    else:
        return 0
    lang = blob.detect_language()
    #pornoWordsCount = 0
    #pornoWebCount = 0
    if lang != 'en':
        try:
            text = str(blob.translate(to='en'))
            blob = TextBlob(text)
        except:
            return 0
    polarity_result = analyzer.polarity_scores(text)
    nounPhrase = blob.noun_phrases
    #print(nounPhrase)
    processed = []
    nounPhrasePorn = 0
    for word in nounPhrase:
        #w = Word(str(word).lower())
        #print(str(word).lower())
        if str(word).lower() in nl:
            nounPhrasePorn += 1
            processed.append(str(word).lower())
    if len(nounPhrase)!=0:
        npRate = ((nounPhrasePorn*1.0)/len(nounPhrase))
    else:
        npRate = 0

    textTokens = nltk.word_tokenize(text)
    posTagged = nltk.pos_tag(textTokens)
    nouns = list(filter(lambda x:x[1]=='NN', posTagged))
    nounPorn = 0
    print(nouns)
    for noun in nouns:
        if noun not in nounPhrase:
            #w = Word(noun[0].lower())
            print(ps.stem(noun[0]))
            if noun[0].lower() in nl:
                #print(str(w.singularize()))
                nounPorn+=1
                processed.append(noun[0].lower())
    if len(nouns)!=0:            
        nRate = ((nounPorn*1.0)/len(nouns))
    else:
        nRate = 0
    
    verbs = list(filter(lambda x:x[1]=='VB' or x[1]=='VBP', posTagged))
    verbsPorn = 0
    print(verbs)
    for verb in verbs:
        if str(ps.stem(verb[0])) in nl:
            verbsPorn+=1
            processed.append(str(ps.stem(verb[0])))
    if len(verbs)!=0:
        vRate = verbsPorn/len(verbs)
    else:
        vRate = 0
    
    avgRate = 0
    
    if len(nounPhrase)!=0 and len(nouns)!=0 and len(verbs)!=0:
        avgRate = (npRate*0.15 + nRate*0.7 + vRate*0.15) * polarity_result['compound']
    elif len(nounPhrase) is 0:
        if len(nouns) is 0:
            avgRate = vRate * polarity_result['compound']
        elif len(verbs) is 0:
            avgRate = nRate * polarity_result['compound']
        else:
            avgRate = (nRate*0.7 + vRate*0.3) * polarity_result['compound']
    elif len(nouns) is 0:
        if len(verbs) is 0:
            avgRate = npRate * polarity_result['compound']
        else:
            avgRate = (npRate*0.5 + vRate*0.5) * polarity_result['compound']
    else:
        avgRate = (npRate*0.15 + nRate*0.85) * polarity_result['compound']

    #lustLevel = {'Lust' : avgRate}
    return avgRate
    #print('score: %s' % str(polarity_result))


def view_unprocessed_raw(db):
    map_fnc = """function(doc) {
        if (!doc.lust_processed) {
            emit(doc._id, null);
        }
    }"""
    view = design.ViewDefinition(
        'raw_tweets', 'lust_unprocessed', map_fnc
    )
    view.sync(db)


def view_processed_data(db):
    map_fnc="""function (doc) {
       emit(doc.code, doc.lustSentiment);
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
    results = db_raw.view('raw_tweets/lust_unprocessed')
    print(results)
    for res in results:
        # Get tweet based on id.
        id = res['id']
        tweet = db_raw[id]
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
                    code = multi['properties']['lga_code18']
                    sentiment = runLustAnalysis(tweet['text'])
                    stored_tweet = {
                        '_id': id,
                        'code': code,
                        'text': tweet['text'],
                        'lustSentiment': sentiment,
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
        doc['lust_processed'] = True
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
        new_database="lust_processed_tweets1"
    if name == 'server-two':
        db_name='raw_data2'
        new_database="lust_processed_tweets2"
    if name == 'server-three':
        db_name='raw_data3'
        new_database="lust_processed_tweets3"

    logging.basicConfig(level=logging.INFO)
    # Read locations into memory.
    multipol = fiona.open(GEO_JSON)
    # Get raw tweets db.
    ip = get_host_ip()
    address = 'http://' + 'qwe:qwe@'+ ip + ':' + '5984'
    couch_raw = couchdb.Server(address)
    try: 
        db_raw = couch_raw[db_name]
    except Exception:
        logging.error("Raw tweets DB does not exist.")
        sys.exit(2)

    couch_pro_lust = couchdb.Server(address)
    # couch_pro_lust = couchdb.Server('http://127.0.0.1:5984')
    if new_database in couch_pro_lust:
        db_pro_lust = couch_pro_lust[new_database]
    else:
        db_pro_lust = couch_pro_lust.create(new_database)
    view_processed_data(db_pro_lust)
    # Tag and store tweets.
    while True:
        logging.info("Start processing")
        view_unprocessed_raw(db_raw)
        tag_tweets(db_raw, db_pro_lust, multipol)
        logging.info("Tweets processed, sleeping...Wait for 1200 seconds")
        time.sleep(1200)