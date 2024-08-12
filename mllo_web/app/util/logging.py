import logging


class Logger:
    @classmethod
    def get_logger(cls, name='MLLO'):
        return logging.getLogger(name)
