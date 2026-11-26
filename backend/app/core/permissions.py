"""Role-based access control dependencies and permission utilities."""

from typing import Callable, List
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.professionals.models import ProfessionalProfile


def require_role(*allowed_roles: str) -> Callable:
    """Dependency factory checking that current user has one of the allowed roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and not getattr(current_user, "is_superuser", False):
            raise ForbiddenException(
                f"Action requires one of the following roles: {', '.join(allowed_roles)}."
            )
        return current_user

    return role_checker


require_customer = require_role("customer", "admin")
require_professional = require_role("professional", "admin")
require_admin = require_role("admin")


async def get_current_professional_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfessionalProfile:
    """Dependency resolving the authenticated user's ProfessionalProfile."""
    stmt = select(ProfessionalProfile).where(ProfessionalProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    prof = res.scalar_one_or_none()
    if not prof:
        raise ForbiddenException("User does not have an active professional profile.")
    return prof
