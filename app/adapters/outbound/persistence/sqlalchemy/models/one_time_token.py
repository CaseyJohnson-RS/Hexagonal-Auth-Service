from sqlalchemy import Boolean, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base_token import BaseToken


class OneTimeToken(BaseToken):
    __tablename__ = "one_time_tokens"

    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "User", back_populates="one_time_tokens"
    )
