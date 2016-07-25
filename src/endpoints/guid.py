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

DELETE_INVALID = "DELETE requests require a GUID in the request URL"
GET_INVALID = "GET requests require a GUID in the request URL"
GUID_INVALID = "Given GUID is malformed. GUIDs must be 32 character hexadecimal strings with all uppercase letters."
USER_INVALID = "User property must be present and non-blank in a POST request"
TIMESTAMP_INVALID = "Expire property must be valid UNIX timestamp"

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
		try:
			# Raises exception on detecting invalid guid
			validateGuid(client_guid)

			if (client_guid):
				guid_object = readGuid(self.guid_collection, client_guid)
				if (guid_object): # Case: we have found the requested guid
					self.set_status(200)
					self.write(json_encode(guid_object))
				else: # Case: We received the message, but no data was found for the given guid
					self.set_status(404)
				self.finish()
			else: # Case: User tried to make a get request without passing a GUID
				raise Exception(GET_INVALID)
		except Exception as e:
			print(e.args[0])
			self.set_status(400, e.args[0])
			self.finish()

	def post(self, client_guid=None):
		try:
			self.body = json_decode(self.request.body)
			self.expiration = validateExpire(self.body)
			self.user = validateUser(self.body)
			self.validated_guid = validateGuid(client_guid)

			if (client_guid): # Case: We are either updating a GUID or creating one that is user-specified
				existing_guid = readGuid(self.guid_collection, self.validated_guid)
				if (existing_guid): # Case: We are updating an existing guid
					updated_guid = updateGuid(self.guid_collection, self.buildUpdatedGuid(existing_guid), existing_guid)
					self.set_status(200)
					self.write(json_encode(updated_guid))
				else: # Case: This guid has not been created yet
					new_guid = insertGuid(self.guid_collection, self.buildNewGuid(self.validated_guid))
					self.set_status(201)
					self.write(json_encode(new_guid))
			else: # Case: We are creating a new GUID and need to generate one on the server. The client has not sent a GUID.
				new_guid = insertGuid(self.guid_collection, self.buildNewGuid(self.validated_guid))
				self.set_status(201)
				self.write(json_encode(new_guid))
			self.finish()
		except Exception as e:
			print(e.args[0])
			self.set_status(400, e.args[0])
			self.finish()
		except: #TODO: Catch JSON conversion error here
			self.set_status(400, "Malformed JSON")
			self.finish()
			print("Unexpected error:", sys.exc_info()[0])
			raise

	def delete(self, client_guid=None):
		try:
			# Raises exception on detecting invalid guid
			validateGuid(client_guid)

			if (client_guid):
				deleteGuid(self.guid_collection, client_guid)
				self.set_status(200)
			else: # Case: User tried to DELETE without sending a guid
				self.set_status(400, DELETE_INVALID)
			self.finish()
		except Exception as e:
			print(e.args[0])
			self.set_status(400, e.args[0])
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

	def buildNewGuid(self, guid):
		return {
			"expire" : self.expiration,
			"guid" : guid,
			"user" : self.body["user"]
		}

def readGuid(guid_collection, client_guid):
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
	
def validateUser(body):
	if ("user" in body and body["user"] != ""):
		return body["user"]
	else:
		raise Exception(USER_INVALID)

# This function will return a spec-valid GUID if passed a falsey parameter.
# If passed an invalid guid it will raise an exception
# If passed a valid guid it will return the valid guid
def validateGuid(client_guid):
	if(client_guid):
		if(guidIsValid(client_guid)):
			return client_guid
		else:
			raise Exception(GUID_INVALID)
	else:
		return createRandom32CharHexString() 

def createRandom32CharHexString():
	# This function first creates a random string of 16 bytes. We create 16 because the 
	# following call to binascii.b2a_hex converts each byte into its two digit Hex equivalent, giving us a 32 byte length string.
	# This string is then decoded into a utf-8 string since that's what we're using throughout the rest of the project,
	# and finally all lower case letters are converted to uppercase.
	return binascii.b2a_hex(os.urandom(16)).decode("utf-8").upper()

def guidIsValid(client_guid):
	# This regex will match on strings that are exactly 32 characters in length, and that contain only 
	# combinations of the numbers 0 through 9 and the uppercase letters A through F
	# Example 9094E4C980C74043A4B586B420E69DDF
	return re.match("^[0-9A-F]{32}$", client_guid)

def validateExpire(body):
	if ("expire" in body):
		if (expirationIsValid(body["expire"])):
			return body["expire"]
		else:
			raise Exception(TIMESTAMP_INVALID)
	else:
		return createTimestampPlus30Days()		

def expirationIsValid(expiration):
	try:
		datetime.datetime.fromtimestamp(int(expiration)).strftime('%Y-%m-%d %H:%M:%S')
		print ('guid expiration is valid')
		return True
	except:
		print("Time stamp is invalid")
		return False

# Returns a Unix timestamp representing the time 30 days after it was called
def createTimestampPlus30Days():
	print ('creating time stamp on server')
	thirtyDaysInTheFuture = datetime.datetime.utcnow() + datetime.timedelta(days=30)
	# This step converts our time tuple into a unix timestamp
	return timegm(thirtyDaysInTheFuture.timetuple())