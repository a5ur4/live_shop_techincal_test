from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

ClienteId = Annotated[int, Path(description="Id do cliente.", examples=[1])]
LojaId = Annotated[int, Path(description="Id da loja.", examples=[1])]
