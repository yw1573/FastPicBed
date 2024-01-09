import logging
import os
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler

os.makedirs("logs", exist_ok=True)
log_file_path = os.path.join(os.getcwd(), "logs/log.txt")


class Mylogging(logging.Logger):
    def __init__(self, name, level=logging.DEBUG, file=log_file_path):
        super().__init__(name, level)
        fmt = "%(asctime)s %(name)s %(levelname)s %(filename)s [%(lineno)04d] :%(message)s"
        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

        # file_handle = logging.FileHandler(file, encoding="utf-8")
        # file_handle.setFormatter(formatter)
        # self.addHandler(file_handle)
        rfile_handle = RotatingFileHandler(file, maxBytes=10*1024*1024, encoding="utf-8",
                                           backupCount=10)
        rfile_handle.setFormatter(formatter)
        self.addHandler(rfile_handle)

        console_handle = logging.StreamHandler()
        console_handle.setFormatter(formatter)
        self.addHandler(console_handle)

        # time_handle = TimedRotatingFileHandler(file, when="s", interval=1,
        #                                        backupCount=3)
        # time_handle.setFormatter(formatter)
        # self.addHandler(time_handle)

