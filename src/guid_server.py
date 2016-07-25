import tornado.web
import tornado.ioloop
import os.path

import constants.constants as constants
from endpoints.guid import GuidRequestHandler

def create_app(conf):
	return tornado.web.Application([
		(r"/guid", GuidRequestHandler, conf),
		(r"/guid/(.*)", GuidRequestHandler, conf)
	],
	static_path=os.path.join(os.path.dirname(__file__), "static"),
	debug=True
	)

def create_test_app():
	return create_app({
		"mongoCollection" : constants.TEST_COLLECTION,
		"redisDB" : constants.TEST_REDIS_DB
	})

# This function starts our server listening for calls at specified endpoints
def initialize_server():
	app = create_app({
		"mongoCollection" : constants.COLLECTION,
		"redisDB" : constants.REDIS_DB
	})
	app.listen(3000)
	tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
	initialize_server()