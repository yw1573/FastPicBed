import logging
import os
import shutil
import sqlite3
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

log_file_path = os.path.join(os.getcwd(), 'log.txt')


class MyLog(logging.Logger):
    def __init__(self, name, level=logging.DEBUG, file=log_file_path):
        super().__init__(name, level)
        fmt = '%(asctime)s| %(levelname)-8s | %(name)-12s | %(filename)s [%(lineno)04d] :%(message)s'
        formatter = logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')
        file_handle = logging.FileHandler(file, encoding='utf-8')
        file_handle.setFormatter(formatter)
        self.addHandler(file_handle)
        console_handle = logging.StreamHandler()
        console_handle.setFormatter(formatter)
        self.addHandler(console_handle)


logger = MyLog('FastPicBed')

# 打包
# pyinstaller.exe -F main.py -p log_config.py --noconsole
service_host_ip = '127.0.0.1'
service_host_port = 30001
reload = False
icon = os.path.normpath(os.path.join(os.getcwd(), 'static/ico/favicon.ico'))
db_file = os.path.normpath(os.path.join(os.getcwd(), 'fast_pic_bed.db'))
os.makedirs('saves', exist_ok=True)
upload_dir = os.path.normpath(os.path.join(os.getcwd(), 'saves'))
allowed_extensions = [
    'txt',
    'pdf',
    'png',
    'jpg',
    'jpeg',
    'gif'
]

logger.debug(f'service_host_ip: {service_host_ip}')
logger.debug(f'service_host_port: {service_host_port}')
logger.debug(f'reload: {reload}')
logger.debug(f'icon: {icon}')
logger.debug(f'db_file: {db_file}')
logger.debug(f'upload_dir: {upload_dir}')
logger.debug(f'allowed_extensions: {allowed_extensions}')

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')
tray = None
server = None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.api_route('/', methods=['GET'])
async def root(request: Request):
    pic_num = LiteDB(db_file).counts('pics')
    return templates.TemplateResponse('index.html', {
        'request': request,
        'pic_num': pic_num,
    })


@app.api_route('/', methods=['POST'])
async def root(request: Request, file: UploadFile):
    logger.debug(f'File name: {file.filename}')
    logger.debug(f'File type: {file.content_type}')
    pic_num = LiteDB(db_file).counts('pics')
    if file.filename == '':
        return templates.TemplateResponse('index.html', {
            'request': request,
            'pic_num': pic_num,
            'message': 'File upload failed',
        })
    # if allowed_file(file.filename):
    if True:
        file_name = file.filename
        try:
            url = str('http://127.0.0.1/uploads/' + file_name)
            file_path = os.path.join(upload_dir, file_name)
            content = await file.read()
            with open(file_path, 'wb') as fp:
                fp.write(content)
            LiteDB(db_file).execute(
                'INSERT INTO pics (filename) VALUES (?)',
                (file_name,))
            pic_num = LiteDB(db_file).counts('pics')
            html_data = templates.TemplateResponse('index.html', {
                'request': request,
                'pic_num': pic_num,
                'message': url,
            })

            return html_data
        except Exception as e:
            logger.error(e.args)
    else:
        return templates.TemplateResponse('index.html', {
            'request': request,
            'pic_num': pic_num,
            'message': 'File upload failed',
        })


@app.api_route('/uploads/{filename}', methods=['GET', 'POST'])
async def uploaded_file(filename):
    file_path = os.path.join(os.path.join(os.getcwd(), 'saves'), filename)
    if os.path.exists(file_path):
        logger.debug(f'Return: [{file_path}]')
        return FileResponse(path=file_path)
    else:
        logger.error(f'Not exist: [{file_path}]')
        return None


@app.api_route('/favicon.ico', methods=['GET', 'POST'])
def favicon():
    return FileResponse('static/ico/favicon.ico')


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
            return self.cu.execute(f'SELECT Count(*) FROM {table}').fetchone()[0]


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


if __name__ == '__main__':
    if reload:
        # 这里是清除数据库，清除saves文件夹
        init_db()
    my_config = uvicorn.Config(app=f'{Path(__file__).stem}:app',
                               host=service_host_ip,
                               port=int(service_host_port),
                               access_log=False,
                               reload=False,
                               workers=4)
    my_server = uvicorn.Server(my_config)
    my_server.run()
