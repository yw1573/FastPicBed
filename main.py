import os
import sys

import uvicorn
import pystray
import sqlite3
import shutil
import time
import random
import json
from log_config import Mylogging
from PIL import Image
from pystray import MenuItem
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi import Request
from fastapi import UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

with open("config.json", "r") as f:
    config = json.load(f)

service_host_ip = "127.0.0.1"
if config["service_host_ip"]:
    service_host_ip = config["service_host_ip"]

service_host_port = 30001
if config["service_host_port"]:
    service_host_port = config["service_host_port"]

reload = False
if config["reload"]:
    reload = config["reload"]

icon = ""
if config["icon"]:
    icon = config["icon"]
    if not os.path.exists(icon):
        print(f"The icon file {icon} does not exist")
        sys.exit(1)
else:
    icon = os.path.join(os.getcwd(), "static/ico/favicon.ico")
icon = os.path.normpath(icon)

db_file = ""
if config["db_dir"]:
    db_dir = config["db_dir"]
    if not os.path.exists(db_dir):
        print(f"The database dir {db_dir} does not exist")
        sys.exit(2)
    if not os.path.isdir(db_dir):
        print(f"{db_dir} This is not a directory")
        sys.exit(2)
    db_file = db_dir + "/fast_pic_bed.db"
else:
    db_dir = os.path.join(os.getcwd(), "db")
    os.makedirs(db_dir, exist_ok=True)
    db_file = db_dir + "/fast_pic_bed.db"
db_file = os.path.normpath(db_file)

upload_dir = ""
if config["upload_dir"]:
    upload_dir = config["upload_dir"]
    if not os.path.exists(upload_dir):
        print(f"The database dir {upload_dir} does not exist")
        sys.exit(3)
else:
    upload_dir = os.path.join(os.getcwd(), "saves")
    os.makedirs(upload_dir, exist_ok=True)
upload_dir = os.path.normpath(upload_dir)

log_file = ""
if config["log_dir"]:
    log_dir = config["log_dir"]
    if not os.path.exists(log_dir):
        print(f"The database dir {log_file} does not exist")
        sys.exit(4)
    if not os.path.isdir(log_file):
        print(f"{log_file} This is not a directory")
        sys.exit(4)
    log_file = log_dir + "/log.txt"
else:
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir + "/log.txt"
log_file = os.path.normpath(log_file)

allowed_extensions = []
if config["allowed_extensions"]:
    allowed_extensions = config["allowed_extensions"]
else:
    allowed_extensions = [
        "txt",
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "gif"
    ]

logger = Mylogging("FastPicBed", file=log_file)

logger.debug(f"service_host_ip: {service_host_ip}")
logger.debug(f"service_host_port: {service_host_port}")
logger.debug(f"reload: {reload}")
logger.debug(f"icon: {icon}")
logger.debug(f"db_file: {db_file}")
logger.debug(f"upload_dir: {upload_dir}")
logger.debug(f"log_file: {log_file}")
logger.debug(f"allowed_extensions: {allowed_extensions}")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
tray = None
server = None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.api_route("/", methods=["GET"])
async def root(request: Request):
    logger.debug(request.method)
    pic_num = LiteDB(db_file).counts("pics")
    logger.debug(pic_num)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pic_num": pic_num,
    })


@app.api_route("/", methods=["POST"])
async def root(request: Request, file: UploadFile):
    logger.debug(request.method)
    logger.debug(f"file name: {file.filename}")
    logger.debug(f"file type: {file.content_type}")
    url = ""
    pic_num = LiteDB(db_file).counts("pics")
    logger.debug(pic_num)
    if file.filename == "":
        return templates.TemplateResponse("index.html", {
            "request": request,
            "pic_num": pic_num,
            "message": "文件上传失败",
        })
    if allowed_file(file.filename):
        file_suffix = os.path.splitext(file.filename)[-1]
        file_prefix = (time.strftime("%Y%m%d_%H_%M_%S", time.localtime(time.time())) +
                       str(random.randint(1, 9999)))
        file_name = str(file_prefix + file_suffix)
        # file_name = file.filename
        try:
            # db =
            url = str("http://127.0.0.1/uploads/" + file_name)
            file_path = os.path.join(upload_dir, file_name)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            LiteDB(db_file).execute(
                "INSERT INTO pics (filename)"
                " VALUES (?)",
                (file_name,))
            pic_num = LiteDB(db_file).counts("pics")
            logger.debug(pic_num)
            html_data = templates.TemplateResponse("index.html", {
                "request": request,
                "pic_num": pic_num,
                "message": url,
            })
            json_data = {
                "request": request,
                "pic_num": pic_num,
                "message": url,
            }

            return html_data
        except Exception as e:
            logger.debug(e.args)
    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "pic_num": pic_num,
            "message": "文件上传失败",
        })


@app.api_route("/uploads/{filename}", methods=["GET"])
async def uploaded_file(filename):
    logger.debug(filename)
    file_path = os.path.join(os.path.join(os.getcwd(), "saves"), filename)
    logger.debug(file_path)
    return FileResponse(
        path=file_path
    )


@app.api_route("/favicon.ico", methods=["GET"])
def favicon():
    return FileResponse("static/ico/favicon.ico")


def singleton(cls):
    _instance = {}

    def inner(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return inner


@singleton
class LiteDB:
    def __init__(self, filename):
        self.filename = filename
        self.db = sqlite3.connect(self.filename)
        self.cu = self.db.cursor()

    def close(self):
        self.cu.close()
        self.db.close()

    def execute(self, sql, values=None):
        try:
            if values is None:
                self.cu.execute(sql)
            else:
                if type(values) is list:
                    self.cu.executemany(sql, values)
                else:
                    self.cu.execute(sql, values)
            count = self.db.total_changes
            self.db.commit()
        except Exception as e:
            logger.error(e)
            return False, e
        if count > 0:
            return True
        else:
            return False

    def query(self, sql, values=None):
        if values is None:
            self.cu.execute(sql)
        else:
            self.cu.execute(sql, values)
        return self.cu.fetchall()

    def counts(self, table):
        if table is None:
            return 0
        else:
            return self.cu.execute(f"SELECT Count(*) FROM {table}").fetchone()[0]


class Tray:
    def __init__(self):
        self.menu = None
        self.tray = None
        ico = icon
        self.image = Image.open(ico)
        self.create_menu()
        self.create_tray()

    def create_menu(self):
        self.menu = (
            MenuItem("菜单1", lambda: logger.debug("点击了菜单1")),
            MenuItem("菜单2", lambda: logger.debug("点击了菜单2")),
            MenuItem("退出", lambda: self.close())
        )

    def create_tray(self):
        self.tray = pystray.Icon("name", self.image, "鼠标移动到\n托盘图标上\n展示内容", self.menu)

    def run(self):
        self.tray.run()

    def close(self):
        self.tray.stop()


def create_tray():
    logger.debug("create tray")
    my_tray = Tray()
    my_tray.run()


def create_server():
    my_config = uvicorn.Config("main:app", host=service_host_ip, port=int(service_host_port), access_log=True,
                               workers=1)
    my_server = uvicorn.Server(my_config)
    my_server.run()


def init_db():
    if os.path.isfile(db_file):
        os.remove(db_file)
    shutil.rmtree(upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    db = LiteDB(db_file)
    sql = '''
    CREATE TABLE pics(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    '''
    db.execute(sql)


def thread_management():
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(create_tray)
        executor.submit(create_server)


if __name__ == '__main__':
    if reload:
        init_db()
    thread_management()
