from pydantic import BaseModel, Field

class CreateUserSchema(BaseModel):
    name: str
    username: str = Field(..., min_length=3, max_length=32, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(
        min_length=8,
        max_length=255,
        description="Password must be between 8 and 255 characters",
    )
 
# The model will decide the chat_name. no need for user to do it. unless needed for more customizable view.    
#class CreateChat(BaseModel):
#    chat_name:str = Field(
#        min_length=8,
#        max_length=200
#    )


class UserMessageSchema(BaseModel):
    content: str = Field(
        max_length=600
    )