from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MetadataProviderRead(BaseModel):
    id: UUID
    name: str
    code: str
    base_url: str
    enabled: bool
    priority: int
    status: str
    latency: int
    fallback_count: int
    last_failure: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MetadataProviderUpdate(BaseModel):
    enabled: bool | None = None
    priority: int | None = None
    status: str | None = None
