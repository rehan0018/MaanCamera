"""Enquiry HTTP endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.enquiries.schemas import EnquiryCreateRequest, EnquiryResponse
from app.modules.enquiries.service import EnquiryService

router = APIRouter(prefix="", tags=["Enquiries"])


@router.post("/enquiries", status_code=status.HTTP_201_CREATED)
async def create_enquiry(
    req: EnquiryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enquiry = await EnquiryService.create_enquiry(db, current_user.id, req)
    return success_response(
        data=EnquiryResponse.model_validate(enquiry).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/enquiries/me")
async def get_my_enquiries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enquiries = await EnquiryService.list_customer_enquiries(db, current_user.id)
    return success_response(
        data=[EnquiryResponse.model_validate(e).model_dump(mode="json") for e in enquiries]
    )


@router.get("/enquiries/{id}")
async def get_enquiry(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enquiry = await EnquiryService.get_enquiry_by_id(db, id)
    return success_response(data=EnquiryResponse.model_validate(enquiry).model_dump(mode="json"))
