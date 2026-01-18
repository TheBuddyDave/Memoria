"""
Docstring for src.database.agent_state.base
This is the registry that sqlalchemy uses to find all models. so when we do class Model(Base) it will be registered under this Base.
All models that represent tables in the database should inherit from this Base class.
"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
    