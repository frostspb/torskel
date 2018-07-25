from torskel.torskel_handler import TorskelHandler


class TestPage(TorskelHandler):
    def get(self):
        self.write('Hi')
        self.finish()


class TestUserIp(TorskelHandler):
    def get(self):
        self.write(self.get_user_ip())
        self.finish()
