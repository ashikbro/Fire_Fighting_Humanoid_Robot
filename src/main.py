from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from auth import authenticate_user, create_access_token, get_current_active_user
from datetime import timedelta
import uvicorn
import subprocess

app = FastAPI()
templates = Jinja2Templates(directory="templates")

ACCESS_TOKEN_EXPIRE_MINUTES = 30

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user({"admin": {"username": "admin", "hashed_password": "$2b$12$..." }}, form_data.username, form_data.password)
    if not user:
        return {"error": "Invalid credentials"}
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user=Depends(get_current_active_user)):
    # Run Streamlit dashboard as a subprocess or embed visualizations here
    # For simplicity, redirect to Streamlit dashboard URL or serve embedded content
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": current_user.username})

if __name__ == "__main__":
    # Optionally start Streamlit dashboard as subprocess
    subprocess.Popen(["d:\\Fire_Fighting_Humanoid_Robot\\.venv\\Scripts\\streamlit.exe", "run", "src/dashboard.py"])
    uvicorn.run(app, host="0.0.0.0", port=8000)
