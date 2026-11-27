"""AI Intelligence Service: Structured parser, 7-factor recommendation engine, review summarizer."""

import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.ai_runtime.ollama_client import OllamaAIProvider
from app.modules.ai.models import RecommendationItem, RecommendationSession
from app.modules.ai.schemas import (
    PortfolioAnalysisResponse,
    RecommendationItemResponse,
    RecommendationResponse,
    ReviewSummaryResponse,
)
from app.modules.portfolios.models import Portfolio, Project
from app.modules.professionals.models import Category, ProfessionalProfile, Service
from app.modules.reviews.models import Review


class AIService:
    ollama_provider = OllamaAIProvider()

    @classmethod
    async def extract_query_requirements(cls, query: str) -> dict[str, Any]:
        """Extract structured query requirements using Ollama with deterministic rule fallback."""
        schema = {
            "type": "object",
            "properties": {
                "categories": {"type": "array", "items": {"type": "string"}},
                "category": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "object", "properties": {"city": {"type": "string"}}},
                "city": {"type": "string"},
                "style": {"type": "array", "items": {"type": "string"}},
                "budget_max_paise": {"type": "integer"},
                "duration_days": {"type": "integer"},
            },
        }

        # Try Ollama if enabled
        if settings.AI_ENABLED:
            try:
                res = await cls.ollama_provider.generate_structured_output(query, schema)
                if res and isinstance(res, dict):
                    # Normalize keys
                    cats = res.get("categories") or res.get("category") or []
                    if isinstance(cats, str):
                        cats = [cats]
                    city = res.get("city") or res.get("location", {}).get("city")
                    return {
                        "category": cats,
                        "location": {"city": city} if city else {},
                        "style": res.get("style", []),
                        "budget_max_paise": res.get("budget_max_paise"),
                        "duration_days": res.get("duration_days", 1),
                    }
            except Exception:
                pass  # Fall back to heuristic rule-based extraction

        # Robust regex fallback
        extracted: dict[str, Any] = {
            "category": [],
            "location": {},
            "style": [],
            "budget_max_paise": None,
            "duration_days": 1,
        }

        q_lower = query.lower()

        # Categories
        if "wedding" in q_lower:
            extracted["category"].append("wedding-photography")
        if "cinematic" in q_lower or "video" in q_lower or "film" in q_lower:
            extracted["category"].append("cinematic-films")
        if "candid" in q_lower:
            extracted["style"].append("candid")
        if "portrait" in q_lower:
            extracted["category"].append("portrait-fashion")

        # Cities
        for city in ["pune", "mumbai", "delhi", "bengaluru", "hyderabad", "jaipur", "goa", "chennai"]:
            if city in q_lower:
                extracted["location"]["city"] = city.capitalize()
                break

        # Budget extraction (e.g. ₹50,000 or 50000 or 50k)
        if "50,000" in q_lower or "50000" in q_lower or "50k" in q_lower:
            extracted["budget_max_paise"] = 5000000  # 50,000 INR = 5,000,000 paise
        elif "1,00,000" in q_lower or "100000" in q_lower or "1 lakh" in q_lower:
            extracted["budget_max_paise"] = 10000000

        # Duration
        days_match = re.search(r'(\d+)\s*(?:day|days)', q_lower)
        if days_match:
            extracted["duration_days"] = int(days_match.group(1))

        return extracted

    @classmethod
    async def get_recommendations(
        cls,
        db: AsyncSession,
        query: str,
        customer_id: uuid.UUID | None = None,
    ) -> RecommendationResponse:
        requirements = await cls.extract_query_requirements(query)
        city = requirements.get("location", {}).get("city")
        budget_max = requirements.get("budget_max_paise")
        target_cats = [c.lower() for c in requirements.get("category", [])]

        # Stage 1: Eligibility Filtering
        stmt = select(ProfessionalProfile).where(ProfessionalProfile.profile_visibility == "public")
        if city:
            stmt = stmt.where(func.lower(ProfessionalProfile.base_city) == city.lower())

        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        # If zero candidates match city exactly, broaden to all verified/public candidates
        if not candidates:
            stmt = select(ProfessionalProfile).where(ProfessionalProfile.profile_visibility == "public")
            res = await db.execute(stmt)
            candidates = list(res.scalars().all())

        # Stage 2: 7-Factor Weighted Relevance Ranking
        # Formula: Score = 0.25*S + 0.20*V + 0.15*R + 0.15*B + 0.10*A + 0.10*E + 0.05*T
        scored_candidates: list[tuple[ProfessionalProfile, float, str, list[str], int]] = []

        for p in candidates:
            # Query lowest starting price from active services (avoids crash on p.starting_price_minor)
            price_stmt = select(func.min(Service.starting_price_minor)).where(
                Service.professional_id == p.id, Service.is_active.is_(True)
            )
            price_res = await db.execute(price_stmt)
            cand_starting_price = price_res.scalar() or 0

            # 1. Skills / Category Match (S) [0-100]
            cat_stmt = (
                select(Category.slug)
                .join(Service, Service.category_id == Category.id)
                .where(Service.professional_id == p.id, Service.is_active.is_(True))
            )
            cat_res = await db.execute(cat_stmt)
            prof_cats = [cat.lower() for cat in cat_res.scalars().all()]
            if not target_cats:
                s_score = 80.0
            elif any(tc in pc or pc in tc for tc in target_cats for pc in prof_cats):
                s_score = 100.0
            else:
                s_score = 35.0

            # 2. Visual portfolio volume & depth (V) [0-100]
            proj_stmt = (
                select(func.count(Project.id))
                .join(Portfolio, Portfolio.id == Project.portfolio_id)
                .where(Portfolio.professional_id == p.id, Project.publication_status == "published")
            )
            proj_cnt_res = await db.execute(proj_stmt)
            proj_cnt = proj_cnt_res.scalar() or 0
            v_score = min(100.0, max(25.0, float(proj_cnt * 25.0)))

            # 3. Verified review quality (R) [0-100]
            # Combination of average rating and review volume
            r_score = min(100.0, (float(p.avg_rating) / 5.0) * 80.0 + min(20.0, float(p.total_reviews * 4.0)))

            # 4. Budget suitability (B) [0-100]
            if budget_max and cand_starting_price > 0:
                if cand_starting_price <= budget_max:
                    b_score = 100.0
                else:
                    ratio = budget_max / cand_starting_price
                    b_score = max(20.0, ratio * 100.0)
            else:
                b_score = 85.0

            # 5. Availability & Travel (A) [0-100]
            if city:
                if p.base_city.strip().lower() == city.strip().lower():
                    a_score = 100.0
                elif p.travel_available:
                    a_score = 75.0
                else:
                    a_score = 25.0
            else:
                a_score = 90.0

            # 6. Relevant experience (E) [0-100]
            e_score = min(100.0, max(20.0, float(p.years_experience) * 10.0))

            # 7. Trust & Verification (T) [0-100]
            t_score = 100.0 if p.verification_status == "verified" else (65.0 if p.verification_status == "in_review" else 40.0)

            # Final weighted composite
            composite = (
                0.25 * s_score
                + 0.20 * v_score
                + 0.15 * r_score
                + 0.15 * b_score
                + 0.10 * a_score
                + 0.10 * e_score
                + 0.05 * t_score
            ) / 100.0  # Normalize to 0.0 - 1.0

            # Grounded explanation (clean UTF-8 ★, no mojibake)
            rating_str = f"{p.avg_rating:.1f}★" if p.total_reviews > 0 else "New Professional"
            explanation = (
                f"Recommended based on {p.years_experience} years of {p.base_city} experience, "
                f"a {rating_str} verified rating across {p.total_reviews} reviews, "
                f"and active portfolio matching your creative requirements."
            )

            # Fetch representative project titles
            proj_title_stmt = (
                select(Project.title)
                .join(Portfolio, Portfolio.id == Project.portfolio_id)
                .where(Portfolio.professional_id == p.id, Project.publication_status == "published")
                .limit(2)
            )
            proj_title_res = await db.execute(proj_title_stmt)
            projects = list(proj_title_res.scalars().all())

            scored_candidates.append((p, composite, explanation, projects, cand_starting_price))

        # Sort descending by composite score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Record session
        session = RecommendationSession(
            customer_id=customer_id,
            query_text=query,
            extracted_requirements=requirements,
            ranking_version="v2.0-dynamic-7factor",
        )
        db.add(session)
        await db.flush()

        results: list[RecommendationItemResponse] = []
        for idx, (cand, score, explanation, projs, start_price) in enumerate(scored_candidates[:10], start=1):
            item = RecommendationItem(
                session_id=session.id,
                professional_id=cand.id,
                relevance_score=round(score, 4),
                ranking_position=idx,
                explanation_data={"explanation": explanation, "projects": projs},
            )
            db.add(item)

            results.append(
                RecommendationItemResponse(
                    professional_id=cand.id,
                    display_name=cand.display_name,
                    slug=cand.slug,
                    headline=cand.headline,
                    profile_image=cand.profile_image,
                    base_city=cand.base_city,
                    avg_rating=float(cand.avg_rating),
                    total_reviews=cand.total_reviews,
                    starting_price_minor=start_price,
                    verification_status=cand.verification_status,
                    relevance_score=round(score, 4),
                    ranking_position=idx,
                    match_explanation=explanation,
                    relevant_projects=projs,
                )
            )

        await db.commit()

        return RecommendationResponse(
            session_id=session.id,
            query=query,
            extracted_requirements=requirements,
            total_matches=len(results),
            recommendations=results,
        )

    @classmethod
    async def analyze_portfolio_asset(cls, db: AsyncSession, project_id: uuid.UUID) -> PortfolioAnalysisResponse:
        stmt = select(Project).where(Project.id == project_id)
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()

        categories = [project.style] if (project and project.style) else ["Commercial", "Creative Portfolio"]
        tags = project.tags if (project and project.tags) else ["natural-tones", "high-resolution", "cinematic"]
        title_context = project.title if project else "Portfolio Asset"
        desc_context = project.description if (project and project.description) else "Curated professional project asset."

        return PortfolioAnalysisResponse(
            detected_categories=categories,
            suggested_tags=tags,
            lighting_style="Balanced ambient lighting with natural falloff",
            composition="Rule of Thirds visual balance with subject focus",
            suggested_caption=f"{title_context}: {desc_context[:120]}",
        )

    @classmethod
    async def summarize_reviews(cls, db: AsyncSession, professional_id: uuid.UUID) -> ReviewSummaryResponse:
        stmt = select(Review).where(
            Review.professional_id == professional_id,
            Review.moderation_status == "approved",
        )
        res = await db.execute(stmt)
        reviews = list(res.scalars().all())

        if not reviews:
            return ReviewSummaryResponse(
                professional_id=professional_id,
                total_reviews_analyzed=0,
                sentiment_highlights=["No verified customer reviews have been submitted for this professional yet."],
                strengths_mentioned=[],
                areas_for_alignment=["Awaiting client feedback on newly completed bookings."],
            )

        # Dynamic sentiment analysis from actual stored reviews
        avg_quality = sum(float(r.work_quality_rating) for r in reviews) / len(reviews)
        avg_comm = sum(float(r.communication_rating) for r in reviews) / len(reviews)
        avg_punct = sum(float(r.punctuality_rating) for r in reviews) / len(reviews)
        avg_val = sum(float(r.value_rating) for r in reviews) / len(reviews)

        highlights = []
        strengths = []
        areas = []

        if avg_quality >= 4.5:
            strengths.append("Exceptional work quality and composition")
            highlights.append("Clients consistently praise the creative visual depth and final edits.")
        if avg_comm >= 4.5:
            strengths.append("Clear and responsive communication")
            highlights.append("Clients highlight transparent pre-shoot coordination and quick responses.")
        if avg_punct >= 4.5:
            strengths.append("Punctual arrival and on-schedule deliverables")
            highlights.append("Dependable on-time project handover within agreed timelines.")
        if avg_val >= 4.5:
            strengths.append("High value for money")

        if not highlights:
            highlights.append(f"Rated across {len(reviews)} bookings with solid overall client satisfaction.")

        if avg_punct < 4.0:
            areas.append("Timeline flexibility during peak festival and wedding seasons.")
        else:
            areas.append("Advance booking advised due to high calendar demand.")

        return ReviewSummaryResponse(
            professional_id=professional_id,
            total_reviews_analyzed=len(reviews),
            sentiment_highlights=highlights,
            strengths_mentioned=strengths if strengths else ["Reliable execution"],
            areas_for_alignment=areas,
        )
