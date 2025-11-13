from pydantic import BaseModel

def to_camel(s: str) -> str:
    p = s.split("_")
    return p[0] + "".join(x.capitalize() for x in p[1:])

class CamelModel(BaseModel):
    class Config:
        orm_mode = True
        alias_generator = to_camel
        allow_population_by_field_name = True

class LabelOut(CamelModel):
    id: int
    name: str
    color: str

class LabelCreate(CamelModel):
    name: str
    color: str

class LabelUpdate(CamelModel):
    name: str | None = None
    color: str | None = None

# ↓ minimalni odgovori za create/ok
class LabelCreateOut(CamelModel):
    id: int

class OkOut(CamelModel):
    ok: bool = True
