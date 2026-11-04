from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")
