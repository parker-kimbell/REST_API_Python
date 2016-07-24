import tornado.web
import re
import os
import binascii
from calendar import timegm
from pymongo import MongoClient
from tornado.escape import json_decode, json_encode
import datetime
import redis

malformed_guid = """Given GUID is malformed. GUIDs must be 32 character hexadecimal strings with all uppercase letters."""
cache = redis.StrictRedis(host="localhost", port=6379, db=0)

class GuidRequestHandler(tornado.web.RequestHandler):
	def set_default_headers(self):
		self.set_header('Content-Type', 'application/json')
	def get(self, client_guid=None):
		if(client_guid and self.guidIsValid(client_guid)):
			# TODO Need to retrieve from DB here
			client = MongoClient('localhost', 27017)
			db = client.cylance_challenge_db
			guid_collection = db.guids
			guid_object = guid_collection.find_one({"guid" : client_guid})
			if (guid_object):
				# Remove the native _id that Mongo inserts into collections
				del guid_object['_id']
				self.set_status(200)
				cache.set(guid_object['guid'], guid_object)
				self.write(json_encode(guid_object))
			else:
				self.set_status(404)
			client.close()
		else:
			self.set_status(400, malformed_guid)
		self.finish()

	def post(self, client_guid=None):
		try:
			body = json_decode(self.request.body)
			expiration = body["expire"] if "expire" in body else self.createTimestampPlus30Days()

			if (client_guid and self.guidExpirationIsValid(expiration) and self.guidIsValid(client_guid)): # Case: We are either updating a GUID or creating one that is user-specified
				client = MongoClient('localhost', 27017)
				guid_collection = client.cylance_challenge_db.guids
				existing_guid = guid_collection.find_one({"guid" : client_guid})
				print('after find_one')
				if (existing_guid): # Case: We are updating an existing guid
					updated_guid = {
						"expire" : body["expire"] if "expire" in body else existing_guid['expire'],
						"user" : body["user"] if "user" in body else existing_guid["user"]
					}
					guid_collection.update({"guid" : client_guid}, {
						"$set" : updated_guid
					})
					# Add the existing guid property into the JSON object we're about to return as this is part of the spec
					updated_guid["guid"] = existing_guid["guid"]
					cache.set(updated_guid['guid'], updated_guid)
					self.set_status(200)
					self.write(json_encode(updated_guid))
					client.close()
				else: # Case: This guid has not been created yet
					new_guid = {
						"expire" : expiration,
						"guid" : client_guid,
						"user" : body["user"]
					}
					guid_collection.insert(new_guid)
					# Remove the Mongo ID that was inserted after our insert because it is not part of the spec
					del new_guid['_id']
					self.set_status(201)
					self.write(json_encode(new_guid))
					client.close()
			elif (not client_guid and self.guidCreationIsValid(expiration, body["user"])): # Case: We are creating a new GUID and need to generate one on the server
				client = MongoClient('localhost', 27017)
				guid_collection = client.cylance_challenge_db.guids
				guid = self.createRandom32CharHexString()
				new_guid = {
					"expire" : expiration,
					"guid" : guid,
					"user" : body["user"]
				}
				# TODO catch this error case
				guid_collection.insert(new_guid)
				# Remove the Mongo ID that was inserted after our insert because it is not part of the spec
				del new_guid['_id']
				cache.set(new_guid['guid'], new_guid)
				self.set_status(201)
				self.write(json_encode(new_guid))
				client.close();
			else: # Case: Something did not pass validation. TODO: Give specific error messages to what is missing in the API
				self.set_status(400, "Your request is malformed")
				self.finish()
				
		except:
			self.set_status(400, "Malformed JSON")
			self.finish()

	def delete(self, client_guid=None):
		if (self.guidIsValid(client_guid)):
			client = MongoClient('localhost', 27017)
			guid_collection = client.cylance_challenge_db.guids
			guid_collection.remove({"guid" : client_guid})
			self.set_status(200)
			cache.delete(client_guid)
		else:
			self.set_status(400, malformed_guid)
		self.finish()

	# This function will return a Unix timestamp representing the time 30 days after it was called
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