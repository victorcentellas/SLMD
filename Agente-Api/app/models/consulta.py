from pydantic import BaseModel
from typing import List, Dict, Any

class VariableResponse(BaseModel):
    variable: str
    datos: List[Dict[str, Any]]

class GrupoResponse(BaseModel):
    grupo: str
    datos: List[Dict[str, Any]]

class VariablesInteresResponse(BaseModel):
    variables: List[str]
