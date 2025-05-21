import logging

class LoggerManager:
    def __init__(self, name, level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        # Prevent adding multiple handlers if the logger already has them
        if not self.logger.handlers:
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            ch = logging.StreamHandler()
            ch.setLevel(level)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def get_logger(self):
        return self.logger

    @classmethod
    def setup_logger(cls, name, level=logging.DEBUG):
        return cls(name, level).get_logger()