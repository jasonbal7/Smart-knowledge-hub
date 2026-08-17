from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import engine, Base, get_db
import models
import schemas
import security
from rag import extract_text, chunk_text, embed_and_store, retrieve_context, delete_document_embeddings
from llm import generate_rag_answer

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Create SQLite database tables 
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Test", description="Test Description", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
def read_root_test():
    return {"status": "online", "message": "Smart Knowledge Hub API is connected to SQLite!!"}

# register post method
@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    
    """
    Registers a new user, hashes their password, and saves them to SQLite.
    Includes duplicate check and rollback protection.
    """
    
    # check if the username is already in use
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already registered.")
    
    # hash the raw password
    hashed_pwd = security.hash_password(user_data.password)
    
    # Create the SQLAlchemy ORM instance
    new_user = models.User(username=user_data.username, password_hash=hashed_pwd)
    
    # Update teh Database safely
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "Database error during registration.")
    
    
# login post method
@app.post("/login", response_model = schemas.TokenResponse)
@limiter.limit("5/minute")
def login_user(request: Request, login_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates a user by checking their username and verifying 
    their plain text password against the stored bcrypt hash.
    """
    user = db.query(models.User).filter(models.User.username == login_data.username).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    is_password_correct = security.verify_password(login_data.password, user.password_hash)
    if not is_password_correct:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalidusername or password")
    
    # Issue JWT containing user id as the subject claim ('sub')
    access_token = security.create_access_token(data={"sub": str(user.id)})
    
    return { 
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Login successful!",
        "user_id": user.id,
        "username": user.username
    }
    
@app.get("/users/me", response_model=schemas.UserResponse)
def get_my_profile(current_user: models.User = Depends(security.get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return current_user
    
# create note method
@app.post("/notes", response_model=schemas.NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(note_data: schemas.NoteCreate, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """
    Creates a new note tied to a specific user_id.
    """
    new_note = models.Note(title=note_data.title, content=note_data.content, user_id=current_user.id)
    
    try:
        db.add(new_note)
        db.commit() 
        db.refresh(new_note)
        
        return new_note
    
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save note.")
    
    
# Get all user notes
@app.get("/notes", response_model=list[schemas.NoteResponse])
def get_my_notes(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    
    return db.query(models.Note).filter(models.Note.user_id == current_user.id).all()

# Update a note method
@app.put("/notes/{note_id}", response_model=schemas.NoteResponse)
def update_user_note(note_id: int, note_data: schemas.NoteUpdate, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    
    # find note from note_id
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    
    # check ownership
    if note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this note.")
    
    
    note.title = note_data.title
    note.content = note_data.content

    # save changes safely
    try: 
        db.commit() 
        db.refresh(note)
        
        return note
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update note.")
    
    

# delete a note
@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """
    Deletes a note by its ID, ensuring it belongs to that user id
    """
    
    # find note based on the note id
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    
    # ensure that that note id belongs to that user
    if note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to do that.")
    
    try:
        db.delete(note)
        db.commit()
        return None
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete note.")
    
# Upload a document method
@app.post("/upload")
def upload_document(current_user: models.User = Depends(security.get_current_user), file: UploadFile = File(...), db : Session = Depends(get_db)):
    
    file_bytes = file.file.read()
    text = extract_text(file.filename, file_bytes)
    chunks = chunk_text(text)
    
    # save to SQLite
    doc = models.Document(filename=file.filename, user_id=current_user.id)
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Sync to ChromaDB 
        embed_and_store(chunks, current_user.id, doc.id, file.filename)
        
        return {"message": "Document uploaded and indexed successfully", "doc_id": doc.id}
    
    except Exception as e:
        db.rollback()
        print(f"Error: {e}") # Helpful for debugging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload document.")
    

@app.post("/ask")
def ask_question(request: schemas.AskRequest, current_user: models.User = Depends(security.get_current_user)):
    
    """
    RAG Pipeline:
    1. Retrieves top-k semantically relevant chunks from ChromaDB for the user.
    2. Sends context chunks + question to Groq (Llama 3.1).
    3. Returns the answer along with the source chunks.
    """
    
    # 1. Retrieve matching chunks from ChromaDB
    context_chunks = retrieve_context(request.question, user_id=current_user.id)
    
    # 2. Call the LLM to synthesize the final answer
    answer = generate_rag_answer(question=request.question, context_chunks=context_chunks)
    
    # 3. Return structured payload
    return {
        "question": request.question,
        "answer": answer,
        "retrieved_chunks": context_chunks
    }
    
    
@app.get("/documents", response_model=list[schemas.DocumentResponse])
def get_user_documents(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """
    Returns all metadata records of uploaded files belonging to the current user.
    """
    return db.query(models.Document).filter(models.Document.user_id == current_user.id).all()


@app.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):  
    """
    Cascade Deletion:
    1. Verifies the document exists and belongs to the authenticated user.
    2. Deletes associated vector embeddings from ChromaDB.
    3. Deletes the database record from SQLite.
    """
    
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    
    if not doc: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "Document not found.")
    
    if doc.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail = "You do not have permission to delete the documetn.")
    
    try:
        delete_document_embeddings(doc_id=doc.id, user_id=current_user.id)
        
        db.delete(doc)
        db.commit()
        return None
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Failed to delete document: {str(e)}")
          