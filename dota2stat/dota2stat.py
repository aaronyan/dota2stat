import os, json, pprint, pandas as pd, matplotlib.pyplot as plt, seaborn
import primary_attribute as pa
from dota2py import api
from pymongo import Connection

pp = pprint.PrettyPrinter(indent = 2)
pd.set_option('display.width', 1000)

class Credentials(object):
	def __init__ (self, api_key = None, account_id = None, \
				  db_name = None, collection_name = None):
		self.api_key = api_key
		self.account_id = account_id
		self.db_name = db_name
		self.collection_name = collection_name

if __name__ == "__main__":
	# API Credentials and Mongo db name and collection name
	api_key = os.environ.get('DOTA2_API_KEY')
	account_id = int(os.environ.get('DOTA2_ACCOUNT_ID'))
	db_name = 'dota2'
	collection_name = 'aaron'
	
	cred = Credentials(api_key = api_key, account_id = account_id,
					   db_name = db_name, collection_name = collection_name)

	results_primary = pa.calc_primary_attribute_stats(cred)
	print results_primary

