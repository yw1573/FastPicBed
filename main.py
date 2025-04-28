import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from db import LiteDB

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

IP = '127.0.0.1'
PORT = 50001
ICON_FILE = os.path.normpath(os.path.join(os.getcwd(), 'static/ico/favicon.ico'))
DB_FILE = os.path.normpath(os.path.join(os.getcwd(), 'fast_pic_bed.db'))
os.makedirs('saves', exist_ok=True)
UPLOAD_DIR = os.path.normpath(os.path.join(os.getcwd(), 'saves'))
ALLOWED_EXTENSIONS = [
    'txt',
    'pdf',
    'png',
    'jpg',
    'jpeg',
    'gif'
]

logger.debug(f'service_host_ip: {IP}')
logger.debug(f'service_host_port: {PORT}')
logger.debug(f'icon: {ICON_FILE}')
logger.debug(f'db_file: {DB_FILE}')
logger.debug(f'upload_dir: {UPLOAD_DIR}')
logger.debug(f'allowed_extensions: {ALLOWED_EXTENSIONS}')

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/saves', StaticFiles(directory='saves'), name='saves')
templates = Jinja2Templates(directory='templates')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.api_route('/', methods=['GET'])
async def root(request: Request):
    pic_num = LiteDB(DB_FILE).counts('pics')
    return templates.TemplateResponse('index.html', {
        'request': request,
        'pic_num': pic_num,
    })


@app.api_route('/', methods=['POST'])
async def root(request: Request, file: UploadFile):
    logger.debug(f'File name: {file.filename}')
    logger.debug(f'File type: {file.content_type}')
    pic_num = LiteDB(DB_FILE).counts('pics')
    if file.filename == '':
        return templates.TemplateResponse('index.html', {
            'request': request,
            'pic_num': pic_num,
            'message': 'File upload failed',
        })
    if allowed_file(file.filename):
        # if True:
        file_name = file.filename
        try:
            url = str('http://127.0.0.1/uploads/' + file_name)
            file_path = os.path.join(UPLOAD_DIR, file_name)
            content = await file.read()
            with open(file_path, 'wb') as fp:
                fp.write(content)
            LiteDB(DB_FILE).execute(
                'INSERT INTO pics (filename) VALUES (?)',
                (file_name,))
            pic_num = LiteDB(DB_FILE).counts('pics')
            html_data = templates.TemplateResponse('index.html', {
                'request': request,
                'pic_num': pic_num,
                'message': url,
            })

            return html_data
        except Exception as e:
            logger.error(e.args)


@app.api_route('/uploads/{filename}', methods=['GET', 'POST'])
async def uploaded_file(filename):
    file_path = os.path.join(os.path.join(os.getcwd(), 'saves'), filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path)
    else:
        logger.error(f'Not exist: [{file_path}]')
        return None


@app.api_route('/uploads/{filename}', methods=['DELETE'])
async def uploaded_file(filename):
    file_path = os.path.join(os.path.join(os.getcwd(), 'saves'), filename)
    sql = f'DELETE FROM pics WHERE filename="{filename}";'
    logger.debug(f'delete sql: {sql}')
    LiteDB(DB_FILE).execute(sql)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"errcore": 200,
                "message": "删除成功"}
    else:
        logger.error(f'Not exist: [{file_path}]')

        return {"errcore": 200,
                "message": "文件不存在"}


@app.get('/file_view')
async def file_view(request: Request, page: int = 1):
    page = max(1, page)
    page_size = 40
    data = LiteDB(DB_FILE).get_paginated_data(page, 'pics', page_size=page_size)
    images = []
    if len(data) < page_size:
        has_next = False
    else:
        has_next = True
    for row in data:
        id = row[0]
        filename = row[1]
        create_time = row[2]
        image_path = f"uploads/{filename}"
        image_data = {
            "id": id,
            "name": filename,
            "create": create_time,
            "url": image_path,
        }
        images.append(image_data)
    return templates.TemplateResponse("file_view.html",
                                      {
                                          "request": request,
                                          "images": images,
                                          "page": page,
                                          "has_next": has_next

                                      })


if __name__ == '__main__':
    my_config = uvicorn.Config(app=f'{Path(__file__).stem}:app',
                               host=IP,
                               port=int(PORT),
                               access_log=True,
                               workers=4)
    my_server = uvicorn.Server(my_config)
    my_server.run()
