from pydantic import BaseModel

class OrganizationSchema(BaseModel):
    id: int
    org_name: str
    venue: str
    latitude: float
    longitude: float
    contact_info: str
    bio: str
    city: str

    class Config:
        from_attributes = True