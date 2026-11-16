from fastapi import APIRouter

from app.services import avg as avg_service

router = APIRouter(prefix="/api/avg", tags=["avg"])


@router.get("/options")
def get_avg_options():
    """The potato / vegetable / meat choices for an AVG meal. Shopping-list
    details stay server-side; the client only needs ids, emoji and labels."""
    return {
        category: [
            {"id": o["id"], "emoji": o["emoji"], "label": o["label"]}
            for o in options
        ]
        for category, options in avg_service.catalog().items()
    }
