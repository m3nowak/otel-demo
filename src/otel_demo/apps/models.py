from pydantic import BaseModel


class Work(BaseModel):
    work_id: str
    cid: str
    repeat: int
    delay: float
    no_val1: int
    no_val2: int
    str_val1: str
    str_val2: str
