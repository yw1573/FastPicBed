import logging
import math
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

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

service_host_ip = '127.0.0.1'
# service_host_port = 30001
service_host_port = 30002
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
    # else:
    #     return templates.TemplateResponse('index.html', {
    #         'request': request,
    #         'pic_num': pic_num,
    #         'message': 'File upload failed',
    #     })


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


@app.api_route('/file_view/{page}', response_class=HTMLResponse, methods=['GET', 'POST'])
async def file_view(request: Request, page: int):
    page = max(1, page)
    data, total = LiteDB(db_file).get_paginated_data(page, 'pics', page_size=50)
    total_pages = math.ceil(total / 50)
    return templates.TemplateResponse("file_view.html",
                                      {
                                          "request": request,
                                          "data": data,
                                          "total_pages": total_pages,
                                          "current_page": page
                                      })


if __name__ == '__main__':
    my_config = uvicorn.Config(app=f'{Path(__file__).stem}:app',
                               host=service_host_ip,
                               port=int(service_host_port),
                               access_log=True,
                               reload=True,
                               workers=4)
    my_server = uvicorn.Server(my_config)
    my_server.run()
