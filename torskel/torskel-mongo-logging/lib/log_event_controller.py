import tornado.log
from tornado.queues import Queue
from tornado.options import options
#event_control_logger = tornado.log.gen_log

options.define("task_list_size", default=10, type=int)

class TorskelEventLogController(object):

    def __init__(self, events_db):
        self.logger = tornado.log.gen_log
        self.queue = Queue()
        self.db = events_db

    def add_log_event(self, event):

        if isinstance(event, dict):
            self.logger.debug(event)
            self.queue.put(event)

    async def write_log_from_queue(self) -> type(None):
        """
        Забирает из очереди задания на Insert логов пользователя
         и выполняет вставку в базу
        """


        #c = self.db.user_events
        #async for document in c.find({}):
        #    print(document)
        qsize = self.queue.qsize()
        if options.show_log_event_writer:
            self.logger.debug(f'Writing events... queue size = {qsize}')
        if qsize > 0:
            step = qsize if qsize <= options.task_list_size else \
                options.task_list_size
            inserts_list = [await self.queue.get() for _ in range(step)]
            if len(inserts_list) > 0:

                await self.db.user_events.insert_many(inserts_list)
