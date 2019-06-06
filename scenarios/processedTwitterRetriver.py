# #This file is used to gater processed data in different databases.
import threading
import couchdb
import logging
import sys
import time
from couchdb import design

ip = "172.26.38.9"
gluton = ['glunttony_tweets1', 'glunttony_tweets2', 'glunttony_tweets3']
lust = ['lust_processed_tweets1', 'lust_processed_tweets2', 'lust_processed_tweets3']

def view_uncollected_data(dataset):
    map_fnc = """function(doc) {
        if (!doc.collected) {
            emit(doc._id, null);
        }
    }"""

    view = design.ViewDefinition(
        'processed_data', 'uncollected', map_fnc
    )
    view.sync(dataset)

def view_lust_collected_data(db):
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

def view_gluttony_collected_data(db):
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
'''
def view_collected_data(db):
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
    view=design.ViewDefinition('sentiment_analysis','sentiment_analysis',map_fnc,reduce_fun=reduce_fnc)
    view.sync(db)
'''

def copy_tweets(db_to_collect, db_col, sen):
    uncollected_view = db_to_collect.view('processed_data/uncollected')
    for twitter in uncollected_view:
        id = twitter['id']
        tweet = db_to_collect[id]
        collected_tweet = {
            '_id': id,
            'code': tweet['code'],
            'text': tweet['text'],
            sen: tweet[sen],
        }
        try:
            db_col.save(collected_tweet)
        except couchdb.http.ResourceConflict:
            #三个数据库中可能存在相同的
            pass
        doc = db_to_collect.get(id)
        doc['collected'] = True
        db_to_collect.save(doc)
    



class ReadDB(threading.Thread):
    def __init__(self,ip,dataset_name, db_col, sen):
        threading.Thread.__init__(self)
        self.ip = ip
        self.dataset_name = dataset_name
        self.db_col = db_col
        self.sen = sen
    def run(self):
        stroed_data = couchdb.Server('http://qwe:qwe@' + self.ip +':5984')
        try:
            data_to_collect = stroed_data[self.dataset_name]
        except Exception:
            logging.error(self.ip+" doesn't contain " + self.dataset_name)
            #terminate thread
            sys.exit(2)

        '''
        couch_col = couchdb.Server('http://qwe:qwe@127.0.0.1:5984')
        if self.dataset_name in couch_col:
            db_col = couch_col[self.dataset_name]
        else:
            dp_col = couch_col.create(self.dataset_name)
        view_collected_data(dp_col)
        '''
        while True:
            logging.info('Collecting data ' + self.ip + ' ' + self.dataset_name)
            view_uncollected_data(data_to_collect)
            copy_tweets(data_to_collect, self.db_col, self.sen)
            logging.info(self.ip + ' ' + self.dataset_name + ' Tweets collected, sleeping...Wait for 1200 seconds')
            time.sleep(1200)


        

        
        


class Scenarios(threading.Thread):
    def __init__(self, db):
        threading.Thread.__init__(self)
        self.db = db
    
    def run(self):
        couch_col = couchdb.Server('http://qwe:qwe@127.0.0.1:5984')
        # couch_col = couchdb.Server('http://127.0.0.1:5984')
        if self.db is "glutton_collected":
            db_names = gluton
            if self.db in couch_col:
                db_col = couch_col[self.db]
            else:
                db_col = couch_col.create(self.db)
            sen = 'gluttony'    
            logging.info("Collecting glutton data")
            view_gluttony_collected_data(db_col)
        else:
            db_names = lust
            if self.db in couch_col:
                db_col = couch_col[self.db]
            else:
                db_col = couch_col.create(self.db)
            sen = 'lustSentiment'
            logging.info("Collectiong lust data")
            view_lust_collected_data(db_col)
        #view_collected_data(db_col)    
        thread3 = ReadDB(ip,db_names[0],db_col,sen)
        thread4 = ReadDB(ip,db_names[1],db_col,sen)
        thread5 = ReadDB(ip,db_names[2],db_col,sen)
        thread3.start()
        thread4.start()
        thread5.start()
            


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    thread1 = Scenarios("glutton_collected")
    thread2 = Scenarios("lust_collected")
    thread1.start()
    thread2.start()
    
        