"""
Writing evet logs into base
"""
import tornado.log
from tornado.queues import Queue
from tornado.options import options


class TorskelEventLogController:
    """
    Class for write events
    """

    def __init__(self):
        self.logger = tornado.log.gen_log
        self.queue = Queue()

    def add_log_event(self, event):
        """
        Put event into queue
        :param event:
        :return:
        """
        if isinstance(event, dict):
            self.logger.debug(event)
            self.queue.put(event)

    # pylint: disable=C0103
    async def write_log_from_queue(self, db, collection_name,
                                   events_writer_func) -> type(None):
        """
        Retrieves events from the queue.
        and performs the insert into the database
        """

        qsize = self.queue.qsize()
        if options.show_log_event_writer:
            self.logger.info('Writing events... queue size = %s', qsize)
        if qsize > 0:
            step = qsize if qsize <= options.task_list_size else \
                options.task_list_size
            inserts_list = [await self.queue.get() for _ in range(step)]
            if inserts_list:
                await events_writer_func(db, collection_name, inserts_list)
