"""Search and comparison service using PostgreSQL structured filtering & ranking."""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.professionals.models import ProfessionalProfile, Category, Service, ServicePackage
from app.modules.search.schemas import SearchFilterParams, SearchCandidateResult, SearchResponse, ComparisonMatrix


class SearchService:
    @staticmethod
    async def search_professionals(db: AsyncSession, params: SearchFilterParams) -> SearchResponse:
        query = select(ProfessionalProfile).where(
            ProfessionalProfile.profile_visibility == "public"
        )

        if params.city:
            query = query.where(func.lower(ProfessionalProfile.base_city) == params.city.strip().lower())

        if params.verified_only:
            query = query.where(ProfessionalProfile.verification_status == "verified")

        # Category filter via joins
        if params.category_slug:
            query = query.join(Service, Service.professional_id == ProfessionalProfile.id).join(
                Category, Category.id == Service.category_id
            ).where(Category.slug == params.category_slug)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        # Order by rating and reviews
        query = query.order_by(
            desc(ProfessionalProfile.avg_rating),
            desc(ProfessionalProfile.total_reviews),
        )

        # Pagination
        offset = (params.page - 1) * params.limit
        query = query.offset(offset).limit(params.limit)

        res = await db.execute(query)
        profiles = res.scalars().all()

        results = []
        for p in profiles:
            # Query lowest starting price across services
            price_q = select(func.min(Service.starting_price_minor)).where(
                Service.professional_id == p.id, Service.is_active == True
            )
            price_res = await db.execute(price_q)
            min_price = price_res.scalar() or 500000  # Default 5,000 INR

            results.append(
                SearchCandidateResult(
                    id=p.id,
                    display_name=p.display_name,
                    slug=p.slug,
                    headline=p.headline,
                    profile_image=p.profile_image,
                    cover_image=p.cover_image,
                    base_city=p.base_city,
                    state=p.state,
                    years_experience=p.years_experience,
                    avg_rating=float(p.avg_rating),
                    total_reviews=p.total_reviews,
                    starting_price_minor=min_price,
                    verification_status=p.verification_status,
                )
            )

        return SearchResponse(
            total_results=total,
            page=params.page,
            limit=params.limit,
            results=results,
        )

    @staticmethod
    async def compare_professionals(db: AsyncSession, professional_ids: List[uuid.UUID]) -> ComparisonMatrix:
        stmt = select(ProfessionalProfile).where(ProfessionalProfile.id.in_(professional_ids))
        res = await db.execute(stmt)
        profiles = res.scalars().all()

        prof_list = []
        for p in profiles:
            # Fetch services
            serv_q = select(Service).where(Service.professional_id == p.id, Service.is_active == True)
            serv_res = await db.execute(serv_q)
            services = serv_res.scalars().all()

            prof_list.append({
                "id": str(p.id),
                "display_name": p.display_name,
                "slug": p.slug,
                "headline": p.headline,
                "profile_image": p.profile_image,
                "base_city": p.base_city,
                "years_experience": p.years_experience,
                "avg_rating": float(p.avg_rating),
                "total_reviews": p.total_reviews,
                "verification_status": p.verification_status,
                "travel_available": p.travel_available,
                "services": [s.name for s in services],
            })

        feature_matrix = {
            "Experience (Years)": [p["years_experience"] for p in prof_list],
            "City": [p["base_city"] for p in prof_list],
            "Rating": [p["avg_rating"] for p in prof_list],
            "Verified": [p["verification_status"] == "verified" for p in prof_list],
            "Travel Outside City": [p["travel_available"] for p in prof_list],
        }

        return ComparisonMatrix(
            professionals=prof_list,
            feature_matrix=feature_matrix,
        )
