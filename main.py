from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import engine, Base, get_db
import models
import schemas
import security

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
@app.post("/login", response_model = schemas.LoginResponse)
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
    
    return { 
        "message": "Login successful!",
        "user_id": user.id,
        "username": user.username
    }
    
    
# create note method
@app.post("/notes", response_model=schemas.NoteResponse, status_code=status.HTTP_201_CREATED)
def create_node(note_data: schemas.NoteCreate, db: Session = Depends(get_db)):
    """
    Creates a new note tied to a specific user_id.
    """
    
    user = db.query(models.User).filter(models.User.id == note_data.user_id).first()
    if not user: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    new_note = models.Note(title=note_data.title, content=note_data.content, user_id=note_data.user_id)
    
    try:
        db.add(new_note)
        db.commit() 
        db.refresh(new_note)
        
        return new_note
    
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save note.")
    
    
# Get all notes in the database
@app.get("/notes", response_model=list[schemas.NoteResponse])
def get_all_notes(db: Session = Depends(get_db)):
    
    return db.query(models.Note).all()

# Get all user notes
@app.get("/notes/user/{user_id}", response_model=list[schemas.NoteResponse])
def get_user_notes(user_id: int, db: Session = Depends(get_db)):
    
    notes = db.query(models.Note).filter(models.Note.user_id == user_id).all()
    return notes

# delete a note
@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    """
    Deletes a note by its ID.
    """
    
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    
    try:
        db.delete(note)
        db.commit()
        return None
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete note.")