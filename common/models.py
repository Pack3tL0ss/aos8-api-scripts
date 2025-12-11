from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class AccessPoint(BaseModel):
    model: str = Field(..., alias='AP Type')
    flags: str = Field(..., alias='Flags')
    group: str = Field(..., alias='Group')
    ip: str = Field(..., alias='IP Address')
    name: str = Field(..., alias='Name')
    standby_ip: str = Field(..., alias='Standby IP')
    status: str = Field(..., alias='Status')
    switch_ip: str = Field(..., alias='Switch IP')


class APDBModel(BaseModel):
    ap_database: List[AccessPoint] = Field(..., alias='AP Database')
    _data: List[str]
    _meta: List[str]
