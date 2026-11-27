"""Search and comparison service using PostgreSQL structured filtering & ranking."""

import uuid
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.professionals.models import Category, ProfessionalProfile, Service
from app.modules.search.schemas import (
    ComparisonMatrix,
    SearchCandidateResult,
    SearchFilterParams,
    SearchResponse,
)


class SearchService:
    @staticmethod
    async def search_professionals(db: AsyncSession, params: SearchFilterParams) -> SearchResponse:
        # Lowest starting price subquery to eliminate N+1 queries
        price_subq = (
            select(
                Service.professional_id,
                func.min(Service.starting_price_minor).label("min_price"),
            )
            .where(Service.is_active.is_(True))
            .group_by(Service.professional_id)
            .subquery()
        )

        query = (
            select(ProfessionalProfile, price_subq.c.min_price)
            .outerjoin(price_subq, price_subq.c.professional_id == ProfessionalProfile.id)
            .where(ProfessionalProfile.profile_visibility == "public")
        )

        if params.city:
            query = query.where(func.lower(ProfessionalProfile.base_city) == params.city.strip().lower())

        if params.verified_only:
            query = query.where(ProfessionalProfile.verification_status == "verified")

        # Category filter via subquery to avoid inflating count or duplicating rows
        if params.category_slug:
            cat_subq = (
                select(Service.professional_id)
                .join(Category, Category.id == Service.category_id)
                .where(
                    Category.slug == params.category_slug.strip().lower(),
                    Service.is_active.is_(True),
                )
            )
            query = query.where(ProfessionalProfile.id.in_(cat_subq))

        # Style keyword filter across headline and bio
        if params.style:
            style_term = f"%{params.style.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(ProfessionalProfile.headline).like(style_term),
                    func.lower(ProfessionalProfile.biography).like(style_term),
                )
            )

        # Budget range filter on actual service price
        if params.budget_min_paise is not None:
            query = query.where(price_subq.c.min_price >= params.budget_min_paise)
        if params.budget_max_paise is not None:
            query = query.where(price_subq.c.min_price <= params.budget_max_paise)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        # Weighted ranking: balances verified rating & review count with recent registrations
        # Bayesian average: (avg_rating * total_reviews + 4.0 * 2) / (total_reviews + 2)
        bayesian_rank = (
            ProfessionalProfile.avg_rating * ProfessionalProfile.total_reviews + 8.0
        ) / (ProfessionalProfile.total_reviews + 2)

        query = query.order_by(
            desc(bayesian_rank),
            desc(ProfessionalProfile.created_at),
        )

        # Pagination
        offset = (params.page - 1) * params.limit
        query = query.offset(offset).limit(params.limit)

        res = await db.execute(query)
        rows = res.all()

        results = []
        for p, min_price in rows:
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
                    starting_price_minor=min_price or 0,
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
    async def compare_professionals(db: AsyncSession, professional_ids: list[uuid.UUID]) -> ComparisonMatrix:
        stmt = select(ProfessionalProfile).where(ProfessionalProfile.id.in_(professional_ids))
        res = await db.execute(stmt)
        profiles = res.scalars().all()

        prof_list = []
        for p in profiles:
            # Fetch services
            serv_q = select(Service).where(Service.professional_id == p.id, Service.is_active.is_(True))
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

        feature_matrix: dict[str, list[Any]] = {
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
