# =============================1st attempt===============================

# import os
# import json
# import datetime
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse
# from pydantic import BaseModel
# import logging

# from report_utils import generate_pdf_report, generate_docx_report, append_log

# # ------------ FastAPI Setup ------------
# app = FastAPI(title="Gemini Universal Backend")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# @app.get("/")
# def root():
#     return FileResponse("frontend/index.html")

# # ------------ API Keys ------------
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # YOU MUST SET THIS IN ENVIRONMENT
# MODEL = "gemini-2.5-flash"
# API_VERSION = "v1beta"

# class Prompt(BaseModel):
#     prompt: str

# # ------------ Try Google SDK ------------
# try:
#     import google.generativeai as genai
#     genai.configure(api_key=GEMINI_API_KEY)
#     SDK_AVAILABLE = True
# except Exception:
#     SDK_AVAILABLE = False


# @app.post("/generate")
# async def generate_text(payload: Prompt):
#     if not GEMINI_API_KEY:
#         raise HTTPException(status_code=500, detail="API key not set!")

#     user_prompt = payload.prompt

#     # -------- Try SDK First --------
#     if SDK_AVAILABLE:
#         try:
#             model = genai.GenerativeModel(MODEL)
#             response = model.generate_content(user_prompt)

#             # Extract text safely
#             if hasattr(response, "text"):
#                 text = response.text
#             else:
#                 text = str(response)

#         except Exception as e:
#             raise Exception(f"SDK failed: {str(e)}")

#     else:
#         # ---- REST FALLBACK ----
#         import requests
#         url = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"
#         body = {
#             "contents": [
#                 {"role": "user", "parts": [{"text": user_prompt}]}
#             ]
#         }
#         res = requests.post(url, json=body)
#         text = res.json()["candidates"][0]["content"][0]["text"]

#     # Save chat history
#     history = json.loads(open("chat_history.json", "r").read())
#     history.append({"prompt": user_prompt, "response": text, "time": str(datetime.datetime.now())})
#     open("chat_history.json", "w").write(json.dumps(history, indent=2))

#     # Append to logs
#     append_log(user_prompt, text)

#     return {"text": text}


# @app.get("/report/pdf")
# def create_pdf():
#     path = generate_pdf_report()
#     return FileResponse(path, filename="gemini_report.pdf")


# @app.get("/report/docx")
# def create_docx():
#     path = generate_docx_report()
#     return FileResponse(path, filename="gemini_report.docx")
# ================2nd attempt======================================
import json
import datetime
import logging
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()  # <-- loads .env variables


from backend.report_utils import generate_pdf_report, generate_docx_report, append_log

app = FastAPI(title="Medifusion Memory Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")


# -------------------------
# CONFIG
# -------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
API_VERSION = "v1beta"
CHAT_HISTORY_FILE = "backend/chat_history.json"
MAX_CONTEXT_MESSAGES = 8

session_history: List[Dict[str, str]] = []

# Load persistent history
if os.path.exists(CHAT_HISTORY_FILE):
    try:
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            persistent_history = json.load(f)
    except:
        persistent_history = []
else:
    persistent_history = []
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


# Try SDK
SDK_AVAILABLE = False
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
        except:
            pass
    SDK_AVAILABLE = True
except:
    SDK_AVAILABLE = False


class Prompt(BaseModel):
    prompt: str


# -------------------------
# STYLE PROMPT
# -------------------------
STYLE_INSTRUCTION = """
You are Medifusion Assistant.
Respond in a friendly, caring tone but with short, simple medical-style guidance.
Keep answers clear, supportive, and safe.
Never diagnose. Never prescribe medications.
Ask follow-up questions if necessary.
"""


# -------------------------
# BUILD PROMPT WITH MEMORY
# -------------------------
def build_prompt(user_prompt: str) -> str:
    combined = []

    for h in (persistent_history[-MAX_CONTEXT_MESSAGES:] + session_history[-MAX_CONTEXT_MESSAGES:]):
        if "prompt" in h and "response" in h:
            combined.append(f"User: {h['prompt']}\nAI: {h['response']}")
        elif "user" in h and "ai" in h:
            combined.append(f"User: {h['user']}\nAI: {h['ai']}")

    history_text = "\n".join(combined)
    final = STYLE_INSTRUCTION + "\nConversation so far:\n" + history_text + "\nUser: " + user_prompt
    return final


# -------------------------
# GEMINI CALL
# -------------------------
def call_gemini(prompt: str) -> dict:

    if SDK_AVAILABLE:
        try:
            model = genai.GenerativeModel(MODEL)

            if hasattr(model, "generate_content"):
                resp = model.generate_content(prompt)
            else:
                resp = model.generate(prompt)

            if hasattr(resp, "text"):
                return {"text": resp.text}

            return {"raw": resp}

        except Exception as e:
            logging.exception("SDK failed: %s", e)

    # REST fallback
    try:
        import requests

        url = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"
        body = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ]
        }

        r = requests.post(url, json=body)
        r.raise_for_status()
        data = r.json()

        if data.get("candidates"):
            parts = data["candidates"][0]["content"]
            text = "".join([p.get("text", "") for p in parts])
            return {"text": text}

        return {"raw": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# MAIN CHAT ENDPOINT
# -------------------------
@app.post("/generate")
async def generate_text(payload: Prompt):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    user_prompt = payload.prompt.strip()

    final_prompt = build_prompt(user_prompt)
    result = call_gemini(final_prompt)
    reply = clean_text(result.get("text") or json.dumps(result.get("raw"), ensure_ascii=False))

    session_history.append({"user": user_prompt, "ai": reply})
    persistent_history.append({"prompt": user_prompt, "response": reply})

    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(persistent_history, f, indent=2, ensure_ascii=False)

    append_log(user_prompt, reply)

    return JSONResponse({"text": reply})
def clean_text(text):
    cleaned = text.replace("■", "\n• ").replace("▪", "\n• ")
    cleaned = cleaned.replace("\n\n", "\n")
    return cleaned.strip()


# -------------------------
# HISTORY ENDPOINT
# -------------------------
@app.get("/history")
def get_history():
    return JSONResponse(persistent_history[-200:])


# -------------------------
# REPORT ENDPOINTS
# -------------------------
@app.get("/report/pdf")
def create_pdf():
    path = generate_pdf_report()
    return FileResponse(path, filename=os.path.basename(path))


@app.get("/report/docx")
def create_docx():
    path = generate_docx_report()
    return FileResponse(path, filename=os.path.basename(path))
