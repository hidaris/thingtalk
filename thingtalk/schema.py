from typing import Dict, Any, Type
from pydantic import BaseModel


class BaseModel(BaseModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type['P']) -> None:
            schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
