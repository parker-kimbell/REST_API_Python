import tornado.web
import tornado.ioloop
import os.path

from endpoints.helpPage import helpPage as EndpointDocumentationHandler
from endpoints.guid import GuidRequestHandler

def create_app():
	return tornado.web.Application([
		(r"/", EndpointDocumentationHandler),
		(r"/guid", GuidRequestHandler),
		(r"/guid/(.*)", GuidRequestHandler)
	],
	static_path=os.path.join(os.path.dirname(__file__), "static"),
	debug=True
	)
# This function starts our server listening for calls at specified endpoints
def initialize_server():
	app = create_app()
	app.listen(3000)
	print ('starting')
	tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
	initialize_server()