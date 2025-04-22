from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory = "templates")


class User (BaseModel):
    name : str
@app.get("/login_form",response_class = HTMLResponse)
async def login_form(request : Request):
    return templates.TemplateResponse("login_form.html", {"request" : request})


@app.post("/login", response_class = HTMLResponse)
async def submit_form(request : Request, name : str = Form(...)):
    return templates.TemplateResponse("login_form.html", {"request" : request, "name" : name, "submitted" : True})
 

 