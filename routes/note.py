from fastapi import APIRouter, FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from passlib.context import CryptContext
from config.db import conn
from schemas.note import noteEntity, notesEntity
from models.note import ShowNote, conf, OTPRequest, OTPVerification
import random
import datetime
from pydantic import BaseModel
from fastapi_mail import FastMail, MessageSchema, MessageType


note = APIRouter()
templates = Jinja2Templates(directory="tem")


# show notes
@note.get("/", response_class=HTMLResponse)
async def read_item(request: Request): 
    user_id = request.cookies.get("user_id")
    user_logged_in = request.cookies.get("user_id") is not None
    user_name = request.cookies.get("user_name", "Guest")  # Retrieve username from cookies

    if user_id:
        # Fetch only the notes belonging to the logged-in user
        docs_cursor = conn.notes.notes.find({"user_id": user_id})
    else:
        docs_cursor = conn.notes.notes.find({"user_id": None})  # No user logged in, return empty

    docs = await docs_cursor.to_list(length=None)  
    newDocs = notesEntity(docs)

    return templates.TemplateResponse(
            "index.html",
        {
            "request": request,
            "newDocs": newDocs,
            "user_logged_in": user_logged_in,
            "user_name": user_name
        }
    )

# add note
@note.post("/")
async def create_item(request: Request):
    create_date = datetime.datetime.now()
    form = await request.form()
    formDict = dict(form)

     # Get the logged-in user ID from cookies
    user_id = request.cookies.get("user_id")
    if not user_id:
        response = RedirectResponse(url="/?error=Login or Signup to add your notes.", status_code=303)
        return response  # User must be logged in

    important_value = True if formDict.get("important") == "on" else False
    formDict.pop("important", None)
    note_data = {**formDict, "important": important_value, "user_id": user_id, "created_at": create_date, "updated_at": create_date}

    await conn.notes.notes.insert_one(note_data)
    return RedirectResponse(url="/", status_code=303) 

# edit note
@note.post("/update/{note_id}")
async def update_note(note_id: str, request: Request):
    update_date = datetime.datetime.now()
    user_id = request.cookies.get("user_id")
    if not user_id:
        response = RedirectResponse(url="/?error=First Login or Signup.", status_code=303)
        return response
    
    # Ensure only the owner can update their note
    note = await conn.notes.notes.find_one({"_id": ObjectId(note_id)})
    if not note or note["user_id"] != user_id:
        response = RedirectResponse(url="/?error=You are not authorised to edit it.", status_code=303)
        return response

    form = await request.form()
    formDict = dict(form)
    
    important_value = True if formDict.get("important") == "on" else False
    formDict.pop("important", None)

    note_data = {**formDict, "important": important_value, "updated_at": update_date}
    note_data.pop("id", None)

    await conn.notes.notes.update_one({"_id": ObjectId(note_id)}, {"$set": note_data})
    return RedirectResponse(url="/", status_code=303)

# remove note
@note.post("/delete/{note_id}")
async def delete_note(note_id: str, request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        response = RedirectResponse(url="/?error=First Login or Signup.", status_code=303)
        return response

    # Ensure only the owner can delete their note
    note = await conn.notes.notes.find_one({"_id": ObjectId(note_id)})
    if not note or note["user_id"] != user_id:
        response = RedirectResponse(url="/?error=You are not authorised to delete this.", status_code=303)
        return response
    
    await conn.notes.notes.delete_one({"_id": ObjectId(note_id)})
    return RedirectResponse(url="/", status_code=303)


# user login and signup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# signup route
@note.post("/signup")
async def signup(request: Request):
    user_data = dict(await request.form())
    existing_user = await conn.notes.users.find_one({"email": user_data.get("email")})
    
    if existing_user:
        response = RedirectResponse(url="/?error=Email already registered", status_code=303)
        return response  # Redirect to homepage with an error message
    
    hashed_password = pwd_context.hash(str(user_data.get("password")))
    new_user = {"name": user_data.get("name"), "email": user_data.get("email"), "password": hashed_password}
    
    await conn.notes.users.insert_one(new_user)
    
    response = RedirectResponse(url="/", status_code=303)
    return response

# send otp
otp_storage = {}

@note.post("/send-otp")
async def send_otp(request: OTPRequest):
    otp = str(random.randint(100000, 999999))
    otp_storage[request.email] = otp
    template = f"""
        <html>
        <body>    
        <p>Hii from MyNotes !!!
            <br>Your otp for email verification is - {otp}</p>
        </body>
        </html>
        """
 
    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=[request.email],  
        body=template,
        subtype=MessageType.html
        )
 
    fm = FastMail(conf)
    await fm.send_message(message)
 
    return {"message": f"OTP sent to {request.email}."}

# verify otp
@note.post("/verify-otp")
async def verify_otp(request: OTPVerification):
    if otp_storage.get(request.email) == request.otp:
        return {"success": True, "message": "OTP verified"}
    return {"success": False, "message": "Invalid otp"}

# login route
@note.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = await conn.notes.users.find_one({"email": email})

    if not user or not pwd_context.verify(password, user["password"]):
        response = RedirectResponse(url="/?error=Invalid email or password", status_code=303)
        return response  # Redirect to homepage with an error message
    
    response = RedirectResponse(url="/", status_code=303)

    # Store user ID and name in cookies 
    response.set_cookie(key="user_id", value=str(user["_id"]), httponly=True)
    response.set_cookie(key="user_name", value=user["name"]) 
    return response

# logout route
@note.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user_id")  # Remove user ID
    response.delete_cookie("user_name")  # Remove username
    return response
