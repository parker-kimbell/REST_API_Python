import tornado.web
from motor import MotorClient
from tornado.escape import json_decode, json_encode
from tornado import gen
import redis
import constants.constants as constants
import validators.guidValidator as validator
import CRUDLib.mongoCacheCRUD as crud

class GuidRequestHandler(tornado.web.RequestHandler):
	# Called at the beginning of a request
	def initialize(self, mongoCollection, redisDB):
		# From https://motor.readthedocs.io/en/stable/differences.html
		# Motor’s client classes do no I/O in their constructors; they connect on demand, when you first attempt an operation.
		# We are just preparing our names here. Mongo lazily loads all connections, so until
		# we actually try to do some CRUD it won't initialize the connection
		self.client = MotorClient(constants.MONGO_URL, 27017)
		self.guid_collection = self.client.cylance_challenge_db[mongoCollection]
		# This connection is not closed explicitly as Redis manages this itself
		self.cache = redis.StrictRedis(host=constants.REDIS_URL, port=6379, db=redisDB)
  
	# Called at the beginning of a request
	def set_default_headers(self):
		self.set_header('Content-Type', 'application/json')

	# Called at the end of a request
	def on_finish(self):
		self.client.close()

	@gen.coroutine
	def get(self, client_guid=None):
		try:
			# Raises exception on detecting invalid guid
			validator.validateGuid(client_guid)

			if (client_guid):
				guid_object = yield crud.readGuid(self.guid_collection, client_guid, self.cache)
				if (guid_object): # Case: we have found the requested guid
					self.set_status(200)
					self.write(json_encode(guid_object))
				else: # Case: We received the message, but no data was found for the given guid
					self.set_status(404)
				self.finish()
			else: # Case: User tried to make a get request without passing a GUID
				raise Exception(constants.GET_INVALID)
		except Exception as e:
			print(e.args[0])
			self.set_status(400, e.args[0])
			self.finish()

	@gen.coroutine
	def post(self, client_guid=None):
		try:
			# If all of this validation completes without raising an exception
			# we know we have valid inputs for all properties
			self.body = json_decode(self.request.body)
			self.expiration = validator.validateExpire(self.body)
			self.user = validator.validateUser(self.body)
			self.validated_guid = validator.validateGuid(client_guid)

			if (client_guid): # Case: We are either updating a GUID or creating one that is user-specified
				existing_guid = yield crud.readGuid(
					self.guid_collection, 
					self.validated_guid, 
					self.cache)
				if (existing_guid): # Case: We are updating an existing guid
					updated_guid = yield crud.updateGuid(
						self.guid_collection, 
						self.buildUpdatedGuid(existing_guid), 
						existing_guid, self.cache)
					self.set_status(200)
					self.write(json_encode(updated_guid))
				else: # Case: This guid has not been created yet
					new_guid = yield crud.insertGuid(
						self.guid_collection, 
						self.buildNewGuid(self.validated_guid), 
						self.cache)
					self.set_status(201)
					self.write(json_encode(new_guid))
			else: # Case: We are creating a new GUID and need to generate one on the server. The client has not sent a GUID.
				new_guid = yield crud.insertGuid(self.guid_collection, 
					self.buildNewGuid(self.validated_guid), 
					self.cache)
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

	@gen.coroutine
	def delete(self, client_guid=None):
		try:
			# Raises exception on detecting invalid guid
			validator.validateGuid(client_guid)

			if (client_guid):
				yield crud.deleteGuid(
					self.guid_collection, 
					client_guid, 
					self.cache)
				self.set_status(200)
			else: # Case: User tried to DELETE without sending a guid
				self.set_status(400, constants.DELETE_INVALID)
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