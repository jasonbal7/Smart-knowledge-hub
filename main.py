from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import engine, Base, get_db
import models
import schemas
import security
from rag import extract_text, chunk_text, embed_and_store, retrieve_context

# Create SQLite database tables 
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Test", description="Test Description", version="0.1.0")

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
def login_user(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
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
def create_node(note_data: schemas.NoteCreate, current_user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
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
def ask_question(question: str, current_user: models.User = Depends(security.get_current_user)):
    
    context_chunks = retrieve_context(question, user_id=current_user.id)
    context_text = "\n\n".join(context_chunks)
    
    prompt = f"""Answer the question using ONLY the context below. If the answer isn't in the context, say so.

Context:
{context_text}

Question: {question}"""

    # placeholder — swap in your LLM call here (next step)
    return {"prompt_sent_to_llm": prompt, "retrieved_chunks": context_chunks}