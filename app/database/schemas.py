from pydantic import BaseModel, Field, ConfigDict

class CreateUserSchema(BaseModel):
    name: str
    username: str = Field(..., min_length=3, max_length=32, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(
        min_length=8,
        max_length=255,
        description="Password must be between 8 and 255 characters",
    )


class UserResponseModel(BaseModel):
    name: str
    username:str
    
    model_config = ConfigDict(from_attributes=True)