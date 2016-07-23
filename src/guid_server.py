import tornado.web
import tornado.ioloop
import os.path

from endpoints.helpPage import helpPage as EndpointDocumentationHandler
from endpoints.guid import guidRequestHandler

# This function starts our server listening for calls at specified endpoints
def initialize_server():
	app = tornado.web.Application([
			(r"/", EndpointDocumentationHandler),
			(r"/guid", guidRequestHandler)
		],
		static_path=os.path.join(os.path.dirname(__file__), "static"),
		debug=True
		)
	app.listen(3000)
	print ('starting')
	tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
	initialize_server()