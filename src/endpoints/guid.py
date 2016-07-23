import tornado.web
import re

class guidRequestHandler(tornado.web.RequestHandler):
	def get(self, client_guid):
		print('get request')
		print(client_guid)
		guid = client_guid if self.guidIsValid(client_guid) else self.set_status(400, """Given GUID is malformed. GUIDs must be 32 character hexadecimal strings with all uppercase letters.""")
		print(guid)
		self.finish()

	def post(self):
		print('post request')
		expiration = self.get_body_argument('expire')
		user = self.get_body_argument('user')
		self.finish()

	def delete(self):
		print('delete request')
		self.finish()

	def guidIsValid(self, client_guid):
		return re.match("^[0-9A-F]{32}$", client_guid)
