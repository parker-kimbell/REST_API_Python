from endpoints.guid import GuidRequestHandler
from tornado.testing import AsyncHTTPTestCase
import guid_server
from pymongo import MongoClient
import json
import time
from tornado.escape import json_decode, json_encode

guid_route = 'guid/'
valid_guid = "9094E4C980C74043A4B586B420E69DDF"
invalid_guid_too_short = "9094E4C980C74043A4B586B420E69DD"
invalid_guid_too_long = "9094E4C980C74043A4B586B420E69DDFD"
invalid_guid_non_hex = "9094_4C980C74043A4B586B420E69DDF"
invalid_guid_lower_case = "9094e4C980C74043A4B586B420E69DDF"
inserted_guid = "1014E4C980C74043A4B586B420E69DDF"

class TestGUIDEndpoint(AsyncHTTPTestCase):
	def get_app(self):
		return guid_server.create_app()

	def tearDown(self):
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		guid_collection.remove({"guid" : inserted_guid})
		client.close()

	def test_response_to_found_guid(self):
		# setup
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		guid_object = guid_collection.insert({"guid" : inserted_guid})
		client.close()
		# end setup

		response = self.fetch('/' + guid_route + inserted_guid, method="GET")
		self.assertEqual(response.code, 200)
		body = json_decode(response.body)
		assert body["guid"] == inserted_guid
		
	def test_GET_guid_valid_not_found(self):
		response = self.fetch('/' + guid_route + valid_guid, method="GET")
		self.assertEqual(response.code, 404)

	def test_GET_guid_too_short(self):
		response = self.fetch('/' + guid_route + invalid_guid_too_short, method="GET")
		self.assertEqual(response.code, 400)

	def test_GET_guid_too_long(self):
		response = self.fetch('/' + guid_route + invalid_guid_too_long, method="GET")
		self.assertEqual(response.code, 400)

	def test_GET_guid_non_hex(self):
		response = self.fetch('/' + guid_route + invalid_guid_non_hex, method="GET")
		self.assertEqual(response.code, 400)

	def test_GET_guid_lower_case(self):
		response = self.fetch('/' + guid_route + invalid_guid_lower_case, method="GET")
		self.assertEqual(response.code, 400)

test_user = "test_user"
inserted_user = "inserted_user"
inserted_timestamp = "1134112125"
valid_timestamp = "1294111525"
valid_timestamp_as_number = 1294111525
invalid_timestamp_letter = "8999F"
invalid_timestamp_number_too_large = 9999999999999999999999999999

class TestTimeStampValidator():
	def test_invalid_stamp_is_rejected_letter(self):
		assert False == GuidRequestHandler.guidExpirationIsValid(self, invalid_timestamp_letter)
	def test_invalid_stamp_is_rejected_too_large(self):
		assert False == GuidRequestHandler.guidExpirationIsValid(self, invalid_timestamp_number_too_large)
	def test_valid_stamp_is_accepted(self):
		assert True == GuidRequestHandler.guidExpirationIsValid(self, valid_timestamp)
	def test_valid_stamp_is_accepted_as_number(self):
		assert True == GuidRequestHandler.guidExpirationIsValid(self, 1294111525)

class TestguidEndpointDELETE(AsyncHTTPTestCase):
	def get_app(self):
		return guid_server.create_app()

	def tearDown(self):
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		#TODO: Rename this to clear_db
		guid_object = guid_collection.remove({"user" : test_user})
		client.close()

	def test_DELETE_invalid_guid(self):
		#setup
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		#TODO: Rename this to clear_db
		guid_object = guid_collection.insert({
			"guid" : inserted_guid,
			"expire" : inserted_timestamp,
			"user" : inserted_user
		})
		#end_setup

		response = self.fetch('/' + guid_route + invalid_guid_lower_case, method="DELETE")
		self.assertEqual(response.code, 400)
		assert guid_collection.find_one({"guid":inserted_guid})
		client.close()

	def test_DELETE_valid_guid(self):
		#setup
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		#TODO: Rename this to clear_db
		guid_object = guid_collection.insert({
			"guid" : inserted_guid,
			"expire" : inserted_timestamp,
			"user" : inserted_user
		})
		client.close()
		#end_setup

		response = self.fetch('/' + guid_route + inserted_guid, method="DELETE")
		self.assertEqual(response.code, 200)
		assert not guid_collection.find_one({"guid":inserted_guid})

class TestguidEndpointPOST(AsyncHTTPTestCase):
	def get_app(self):
		return guid_server.create_app()

	def tearDown(self):
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		#TODO: Rename this to clear_db
		guid_object = guid_collection.remove({"user" : test_user})
		client.close()

	def test_POST_no_guid_name_valid_expire_valid(self):
		post_body = {
			"expire" : valid_timestamp,
			"user" : test_user
		}
		response = self.fetch('/' + guid_route, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 201)
		body = json_decode(response.body)
		assert body["user"] == test_user
		assert body["expire"] == valid_timestamp
		assert body["guid"] 

	def test_POST_no_guid_name_valid_no_expire(self):
		post_body = {
			"user" : test_user
		}
		response = self.fetch('/' + guid_route, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 201)
		body = json_decode(response.body)
		assert body["user"] == test_user
		assert body["expire"] > time.time()
		assert body["guid"]

	def test_POST_guid_valid_name_valid_no_expire(self):
		post_body = {
			"user" : test_user
		}
		response = self.fetch('/' + guid_route, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 201)
		body = json_decode(response.body)
		assert body["user"] == test_user
		assert body["expire"] > time.time()
		assert body["guid"]

	def test_POST_invalid_guid(self):
		post_body = {
			"user" : test_user
		}
		response = self.fetch('/' + guid_route + invalid_guid_lower_case, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 400)

	def test_POST_valid_guid_valid_name_valid_expire_insert_new(self):
		post_body = {
			"user" : test_user,
			"expire" : valid_timestamp
		}
		response = self.fetch('/' + guid_route + valid_guid, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 201)
		body = json_decode(response.body)
		assert body["user"] == test_user
		assert body["expire"] == valid_timestamp
		assert body["guid"] == valid_guid

	def test_POST_valid_guid_valid_name_valid_expire_valid_update_existing(self):
		#setup
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		#TODO: Rename this to clear_db
		guid_object = guid_collection.insert({
			"guid" : inserted_guid,
			"expire" : inserted_timestamp,
			"user" : inserted_user
		})
		client.close()
		#end_setup

		post_body = {
			"guid" : valid_guid,
			"user" : test_user,
			"expire" : valid_timestamp
		}
		response = self.fetch('/' + guid_route + inserted_guid, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 200)
		body = json_decode(response.body)
		print(body)
		assert body["user"] == test_user
		assert body["expire"] == valid_timestamp
		assert body["guid"] == inserted_guid

	def test_POST_valid_guid_valid_name_valid_no_expire_update_existing(self):
		#setup
		client = MongoClient('localhost', 27017)
		db = client.cylance_challenge_db
		guid_collection = db.guids
		#TODO: Rename this to clear_db
		guid_object = guid_collection.insert({
			"guid" : inserted_guid,
			"expire" : inserted_timestamp,
			"user" : inserted_user
		})
		client.close()
		#end_setup

		post_body = {
			"guid" : valid_guid,
			"user" : test_user
		}
		response = self.fetch('/' + guid_route + inserted_guid, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 200)
		body = json_decode(response.body)
		print(body)
		assert body["user"] == test_user
		assert body["expire"] == inserted_timestamp
		assert body["guid"] == inserted_guid

	def test_POST_invalid_expire(self):
		post_body = {
			"user" : test_user,
			"expire" : invalid_timestamp_letter
		}
		response = self.fetch('/' + guid_route + valid_guid, method="POST", body=json.dumps(post_body))
		self.assertEqual(response.code, 400)