class ServiceException(Exception):
    def __init__(self, msg: str=None, status_code: int=None):
        self.msg = msg
        self.status_code = status_code
