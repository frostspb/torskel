"""
For use it example you must 'pip install motor'
"""

from tornado.web import url
from tornado.options import options
from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler


settings = {
    'cookie_secret': 'my-secret-key',
}

options.use_events_writer = True
options.use_mongo = True
options.mongo_db_name = 'torskeldb'
options.mongo_auth_db_name = 'torskeldb'
options.mongo_user = 'torskel'
options.mongo_psw = 'torskel'
options.srv_name = 'DB_LOGGER_SERVER'


class MainPageHandler(TorskelHandler):
    def get(self):
        self.write('Hello World!')
        # log this event with simple message
        self.add_log_event({'msg': 'Hi!'})
        """
        This will insert a record in the database like
        {
            "_id" : ObjectId("5bb755c55bbc6d3ed0d50b49"),
            "date_event" : ISODate("2018-10-05T15:14:53.610Z"),
            "user_agent" : "PC / Linux / Chrome 69.0.3497",
            "user_ip" : "::1",
            "handler_url" : "/",
            "server_name" : "DB_LOGGER_SERVER",
            "method" : "GET",
            "msg" : "Hi!"
        }
        """

        # without legacy event
        self.add_log_event({'msg': 'Hi again!'}, use_legacy_event=False)

        """
        This will insert a record in the database like
        {
            "_id" : ObjectId("5bb759395bbc6d4570f892dd"),
            "msg" : "Hi again!"
        }
        """
        self.finish()


handlers = [
    url(r"/", MainPageHandler, name='MainPageHandler'),

]


class EventServer(TorskelServer):
    def __init__(self, handlers, **settings):
        super().__init__(handlers, **settings)


if __name__ == "__main__":
    my_server = EventServer(handlers, **settings)
    my_server.init_srv()
