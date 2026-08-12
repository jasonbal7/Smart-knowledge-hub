from pydantic import BaseModel, Field


# Schema for incoming registration request
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8)
    
# Schema for outgoing user response froim registration
class UserResponse(BaseModel):
    id: int
    username: str
    
    class Config:
        from_attributes = True      # allows pydantic to read SQLAlchemy ORM objects
        
# Schema for incoming login payload
class UserLogin(BaseModel):
    username: str 
    password: str
    
    
# Schema for return response (outgoing payload)
class LoginResponse(BaseModel):
    message: str
    user_id: int
    username: str
    
# Schema for creating a note (incoming payload)
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    user_id: int 
    
# Schema for returning a note (outgoing payload)
class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    user_id: int
    
    class Config:
        from_attributes = True