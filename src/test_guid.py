from endpoints.guid import guidRequestHandler
from tornado.testing import AsyncHTTPTestCase
import guid_server

guid_route = 'guid/'
valid_guid = "9094E4C980C74043A4B586B420E69DDF"
invalid_guid_too_short = "9094E4C980C74043A4B586B420E69DD"
invalid_guid_too_long = "9094E4C980C74043A4B586B420E69DDFD"
invalid_guid_non_hex = "9094_4C980C74043A4B586B420E69DDF"
invalid_guid_lower_case = "9094e4C980C74043A4B586B420E69DDF"

class TestGUIDEndpoint(AsyncHTTPTestCase):
	def get_app(self):
		return guid_server.create_app()
	
	def test_GET_guid_valid(self):
		response = self.fetch('/' + guid_route + valid_guid, method="GET")
		self.assertEqual(response.code, 200)

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