"""
Class for getting service status
"""

from torskel.torskel_handler import TorskelHandler


# pylint: disable=W0223
class TorskelPingHandler(TorskelHandler):
    """
    Return status of service
    """

    async def get_ok_status(self):
        self.write(self.get_result_dict(code=0, message='Service is up'))
        self.finish()

    async def get(self):
        """
        HTTP GET request
        :return:
        """
        await self.get_ok_status()

    async def post(self):
        """
        http POST request
        :return:
        """
        await self.get_ok_status()
