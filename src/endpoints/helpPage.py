import tornado.web

class helpPage(tornado.web.RequestHandler):
	def get(self):
		self.render('helpPage.html')