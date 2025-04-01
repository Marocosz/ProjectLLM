from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pydantic import BaseModel
from typing import List
import uvicorn
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage


# API
chat_model = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key="OPENAI_API_KEY")

# Banco de dados SQLite
DATABASE_URL = "sqlite:///database.db"
engine = create_engine(DATABASE_URL, echo=True)

# Modelos SQLModel
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str  # Armazenar hashes de senha na produção

class Question(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    question: str
    answer: str = None  # Adicionado para armazenar a resposta do chatbot

# Criar tabelas
SQLModel.metadata.create_all(engine)

# FastAPI app
app = FastAPI()

# Configuração para templates e arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# Dependência de sessão

def get_session():
    with Session(engine) as session:
        yield session

# Inicializar LangChain com um modelo genérico
chat_model = ChatOpenAI(model_name="gpt-3.5-turbo")

# Rotas Web
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Rotas API
@app.post("/register/", response_model=User)
def register_user(user: User, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/ask/")
def ask_question(question: Question, session: Session = Depends(get_session)):
    # Gerar resposta do chatbot
    response = chat_model([HumanMessage(content=question.question)])
    question.answer = response.content
    
    # Salvar pergunta e resposta no banco de dados
    session.add(question)
    session.commit()
    session.refresh(question)
    return {"question": question.question, "answer": question.answer}

@app.get("/questions/{user_id}", response_model=List[Question])
def get_questions(user_id: int, session: Session = Depends(get_session)):
    return session.exec(select(Question).where(Question.user_id == user_id)).all()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
