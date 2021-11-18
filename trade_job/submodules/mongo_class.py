from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import BulkWriteError

from trade_job.submodules import properties as prop


class MongoAPI:

    DESCENDING
    ASCENDING

    def __init__(self):
        self.client = MongoClient(prop.MONGO_HOST, prop.MONGO_PORT)
        self.db = self.client['tradejob_db']  # DB名を設定

    def insert_one(self, collection, document):
        col = self.db[collection]
        return col.insert_one(document)

    def insert_many(self, collection, documents):
        col = self.db[collection]
        try:
            return col.insert_many(documents, ordered=False)
        except BulkWriteError:
            pass

    def update_one(self, collection, _filter, _update):
        col = self.db[collection]
        return col.update_one(_filter, _update)

    def update_many(self, collection, _filter, _update):
        col = self.db[collection]
        return col.update_many(_filter, _update)

    def delete_many(self, collection, _filter):
        col = self.db[collection]
        return col.delete_many(_filter)

    def find(self, collection, projection=None, __filter__=None, sort=None, limit=0):
        col = self.db[collection]
        return col.find(projection=projection, filter=__filter__, sort=sort, limit=limit)
