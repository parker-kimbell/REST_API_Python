import tornado.web

class guidRequestHandler(tornado.web.RequestHandler):
	def get(self):
		print('get request')
	def post(self):
		print('post request')
	def delete(self):
		print('delete request')

