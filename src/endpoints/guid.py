import tornado.web
import re
import os
import sys
import binascii
from calendar import timegm
from pymongo import MongoClient
from tornado.escape import json_decode, json_encode
import datetime
import redis

malformed_guid = """Given GUID is malformed. GUIDs must be 32 character hexadecimal strings with all uppercase letters."""
# Intializing my Redis connection here because this is currently the only file that uses it. When that changes TODO: Refactor
# This connection is not closed explicitly as Redis manages this itself
cache = redis.StrictRedis(host="localhost", port=6379, db=0)

class GuidRequestHandler(tornado.web.RequestHandler):
	# Called at the beginning of a request
	def initialize(self):
		# We are just preparing our names here. Mongo lazily loads all connections, so until
		# we actually try to do some CRUD it won't initialize the connection
		self.client = MongoClient('localhost', 27017)
		self.guid_collection = self.client.cylance_challenge_db.guids

	# Called at the beginning of a request
	def set_default_headers(self):
		self.set_header('Content-Type', 'application/json')

	# Called at the end of a request
	def on_finish(self):
		# From http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient.close
		# If this instance is used again it will be automatically re-opened and the threads restarted.
		self.client.close()

	def get(self, client_guid=None):
		if(client_guid and self.guidIsValid(client_guid)):
			# TODO Need to retrieve from DB here
			guid_object = retrieveFromCacheOrDB(self.guid_collection, client_guid)
			if (guid_object):
				self.set_status(200)
				self.write(json_encode(guid_object))
			else:
				self.set_status(404)
		else:
			self.set_status(400, malformed_guid)
		self.finish()

	def post(self, client_guid=None):
		try:
			body = json_decode(self.request.body)
			self.body = json_decode(self.request.body)
			expiration = body["expire"] if "expire" in body else self.createTimestampPlus30Days()

			if (client_guid and self.guidExpirationIsValid(expiration) and self.guidIsValid(client_guid)): # Case: We are either updating a GUID or creating one that is user-specified
				existing_guid = retrieveFromCacheOrDB(self.guid_collection, client_guid)
				if (existing_guid): # Case: We are updating an existing guid
					updated_guid = updateGuid(self.guid_collection, self.buildUpdatedGuid(existing_guid), existing_guid)
					self.set_status(200)
					self.write(json_encode(updated_guid))
				else: # Case: This guid has not been created yet
					new_guid = insertGuid(self.guid_collection, self.buildNewGuid(client_guid, expiration))
					self.set_status(201)
					self.write(json_encode(new_guid))
			elif (not client_guid and self.guidCreationIsValid(expiration, body["user"])): # Case: We are creating a new GUID and need to generate one on the server
				generated_guid = self.createRandom32CharHexString()
				new_guid = insertGuid(self.guid_collection, self.buildNewGuid(generated_guid, expiration))
				self.set_status(201)
				self.write(json_encode(new_guid))
			else: # Case: Something did not pass validation. TODO: Give specific error messages to what is missing in the API
				self.set_status(400, "Your request is malformed")
			self.finish()		
		except: #TODO: Catch JSON conversion error here
			self.set_status(400, "Malformed JSON")
			print("Unexpected error:", sys.exc_info()[0])
			raise
			self.finish()

	def delete(self, client_guid=None):
		if (self.guidIsValid(client_guid)):
			deleteGuid(self.guid_collection, client_guid)
			self.set_status(200)
		else:
			self.set_status(400, malformed_guid)
		self.finish()

	# This function builds a dictionary containing expire and user properties.
	# At this point we have determined that expire and user have valid values if present
	# so we can safely assign them if the request has sent them along. If the request has not sent them
	# along we set them to be their existing values so we can easily send this object in the response
	# in accordance with the spec
	def buildUpdatedGuid(self, existing_guid):
		return {
			"expire" : self.body["expire"] if "expire" in self.body else existing_guid['expire'],
			"user" : self.body["user"] if "user" in self.body else existing_guid["user"]
		}

	def buildNewGuid(self, guid, expiration):
		return {
			"expire" : expiration,
			"guid" : guid,
			"user" : self.body["user"]
		}

	# Returns a Unix timestamp representing the time 30 days after it was called
	def createTimestampPlus30Days(self):
		print ('creating time stamp on server')
		thirtyDaysInTheFuture = datetime.datetime.utcnow() + datetime.timedelta(days=30)
		# This step converts our time tuple into a unix timestamp
		return timegm(thirtyDaysInTheFuture.timetuple())

	def guidCreationIsValid(self, expiration, user):
		if (self.postBodyIsValid() and self.guidExpirationIsValid(expiration) and user):
			print ('guid creation determined to be valid')
			return True
		else:
			return False

	def guidExpirationIsValid(self, expiration):
		try:
			datetime.datetime.fromtimestamp(int(expiration)).strftime('%Y-%m-%d %H:%M:%S')
			print ('guid expiration is valid')
			return True
		except:
			print("Time stamp is invalid")
			return False

	def postBodyIsValid(self):
		try:
			json_decode(self.request.body)
			print ('post body is valid')
			return True
		except e:
			print("JSON was invalid")
			return False

	def guidIsValid(self, client_guid):
		# This regex will match on strings that are exactly 32 characters in length, and that contain only 
		# combinations of the numbers 0 through 9 and the uppercase letters A through F
		# Example 9094E4C980C74043A4B586B420E69DDF
		return re.match("^[0-9A-F]{32}$", client_guid)

	def createRandom32CharHexString(self):
		# This function first creates a random string of 16 bytes. We create 16 because the 
		# following call to binascii.b2a_hex converts each byte into its two digit Hex equivalent, giving us a 32 byte length string.
		# This string is then decoded into a utf-8 string since that's what we're using throughout the rest of the project,
		# and finally all lower case letters are converted to uppercase.
		return binascii.b2a_hex(os.urandom(16)).decode("utf-8").upper()

def retrieveFromCacheOrDB(guid_collection, client_guid):
	cached_guid = cache.get(client_guid)
	if (cached_guid): # Case: We have found an instance of this guid in this cache so we will decode and return it
		return json_decode(cached_guid.decode('utf-8').replace("'", '"'))
	else: # Case: There is no cached version of this guid, so we need to determine if the guid exists in the database or not
		found_guid = guid_collection.find_one({"guid" : client_guid})
		if (found_guid): # Case: The guid exists in the database, so we clean it and cache it before returning it
			# Remove the native _id that Mongo inserts into collections as it cannot be serialized
			del found_guid['_id']
			cache.set(found_guid['guid'], found_guid)
			return found_guid
		else: # Case: The guid does not exist
			return None
		

def updateGuid(guid_collection, updated_guid, existing_guid):
	guid_collection.update({"guid" : existing_guid["guid"]}, {
		"$set" : updated_guid
	})
	# Add the existing guid property into the JSON object we're about to return as this is part of the spec
	updated_guid["guid"] = existing_guid["guid"]
	cache.set(updated_guid["guid"], updated_guid)
	return updated_guid

def insertGuid(guid_collection, new_guid):
	guid_collection.insert(new_guid)
	# Remove the Mongo ID that was inserted after our insert because it is not part of the spec
	del new_guid["_id"]
	cache.set(new_guid["guid"], new_guid)
	return new_guid

def deleteGuid(guid_collection, client_guid):
	guid_collection.remove({"guid" : client_guid})
	cache.delete(client_guid)
	
	
	