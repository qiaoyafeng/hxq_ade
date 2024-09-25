import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import uvicorn

from fastapi.openapi.docs import get_swagger_ui_html

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, UploadFile, Request, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse
from mimetypes import guess_type

from api.detect import detect_api
from api.file import file_api
from api.schemas import ImageDetectRequest
from utils import get_resp, replace_special_character, build_resp
from config import Config, settings

app = FastAPI(
    title="HXQ ADE",
    summary="HXQ Automatic Depression Detection",
    docs_url=None,
    redoc_url=None,
)

executor = ThreadPoolExecutor(10)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

TEMP_PATH = Config.get_temp_path()


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/js/swagger-ui-bundle.js",
        swagger_css_url="/static/js/swagger-ui.css",
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    image_list = []

    return templates.TemplateResponse(
        "index.html", {"request": request, "image_list": image_list}
    )


@app.post("/uploadfile/")
async def uploadfile(file: UploadFile):
    resp = get_resp()
    url, path, name = await file_api.uploadfile(file)
    file_info = {"path": path, "url": url, "name": name}
    resp["data"] = {"file_info": file_info}
    return resp


@app.get("/get_file/{file_name}", summary="Get file by file name")
def get_file(file_name: str):
    file_path = os.path.isfile(os.path.join(TEMP_PATH, file_name))
    if file_path:
        return FileResponse(os.path.join(TEMP_PATH, file_name))
    else:
        return {"code": 404, "message": "file does not exist."}


@app.get("/wav/get_file/{file_name}", summary="Get file by file name")
def get_file(file_name: str):
    return StreamingResponse(
        content=requests.get(url=f"{settings.HXQ_WAV2LIP_DOMAIN}/get_file/{file_name}"),
        media_type=guess_type(file_name)[0],
    )


@app.get("/voice/get_file/{file_name}", summary="Get file by file name")
def get_file(file_name: str):
    return StreamingResponse(
        requests.get(url=f"{settings.HXQ_VC_DOMAIN}/get_file/{file_name}"),
        media_type=guess_type(file_name)[0],
    )


@app.post("/image/detect", summary="图片检测")
async def image_detect(
    batch_no: str = Form(),
    image1: UploadFile = File(),
    image2: UploadFile = File(),
    image3: UploadFile = File(),
):
    image_paths = []
    print(f"batch_no: {batch_no}")
    for image in [image1, image2, image3]:
        dir_path = Path(f"{TEMP_PATH}/img/{batch_no}")
        dir_path.mkdir(parents=True, exist_ok=True)
        url, path, name = await file_api.uploadfile(image, dir_path)
        image_paths.append(path)

    detect_dict = await detect_api.image_detect(image_paths, batch_no)
    return build_resp(0, {"detect": detect_dict})


@app.post("/image/batch_detect", summary="图片批量检测")
async def image_batch_detect(
    batch_no: str = Form(),
    files: list[UploadFile] = File(description="Multiple images as UploadFile"),
):
    image_paths = []
    print(f"batch_no: {batch_no}")
    for image in files:
        dir_path = Path(f"{TEMP_PATH}/img/{batch_no}")
        dir_path.mkdir(parents=True, exist_ok=True)
        url, path, name = await file_api.uploadfile(image, dir_path)
        image_paths.append(path)

    detect_dict = await detect_api.image_detect(image_paths, batch_no)
    return build_resp(0, {"detect": detect_dict})


if __name__ == "__main__":
    uvicorn.run(
        app="__main__:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.RELOAD,
    )