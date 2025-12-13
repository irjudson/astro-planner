"""API routes for saving and loading observation plans."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ObservingPlan
from app.models.plan_models import SavedPlan

router = APIRouter(prefix="/plans", tags=["plans"])


class SavePlanRequest(BaseModel):
    """Request to save an observing plan."""

    name: str = Field(description="Name for the saved plan")
    description: Optional[str] = Field(default=None, description="Optional description")
    plan: ObservingPlan = Field(description="The observing plan to save")


class SavedPlanSummary(BaseModel):
    """Summary of a saved plan (for list view)."""

    id: int
    name: str
    description: Optional[str]
    observing_date: str
    location_name: str
    total_targets: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SavedPlanDetail(BaseModel):
    """Full saved plan details (for single plan view)."""

    id: int
    name: str
    description: Optional[str]
    observing_date: str
    location_name: str
    plan: ObservingPlan
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=SavedPlanSummary)
async def save_plan(request: SavePlanRequest, db: Session = Depends(get_db)):
    """
    Save an observing plan.

    Args:
        request: Plan save request with name, description, and plan data

    Returns:
        Saved plan summary
    """
    try:
        # Extract metadata from the plan
        observing_date = request.plan.session.observing_date
        location_name = request.plan.location.name
        total_targets = request.plan.total_targets

        # Create the saved plan
        saved_plan = SavedPlan(
            name=request.name,
            description=request.description,
            observing_date=observing_date,
            location_name=location_name,
            plan_data=request.plan.model_dump(mode="json"),
        )

        db.add(saved_plan)
        db.commit()
        db.refresh(saved_plan)

        # Return summary
        return SavedPlanSummary(
            id=saved_plan.id,
            name=saved_plan.name,
            description=saved_plan.description,
            observing_date=saved_plan.observing_date,
            location_name=saved_plan.location_name,
            total_targets=total_targets,
            created_at=saved_plan.created_at,
            updated_at=saved_plan.updated_at,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving plan: {str(e)}")


@router.get("/", response_model=List[SavedPlanSummary])
async def list_plans(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    """
    List all saved plans.

    Args:
        limit: Maximum number of plans to return
        offset: Offset for pagination

    Returns:
        List of saved plan summaries
    """
    try:
        plans = db.query(SavedPlan).order_by(SavedPlan.created_at.desc()).limit(limit).offset(offset).all()

        return [
            SavedPlanSummary(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                observing_date=plan.observing_date,
                location_name=plan.location_name,
                total_targets=plan.plan_data.get("total_targets", 0),
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
            for plan in plans
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing plans: {str(e)}")


@router.get("/{plan_id}", response_model=SavedPlanDetail)
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """
    Get a specific saved plan by ID.

    Args:
        plan_id: The ID of the plan to retrieve

    Returns:
        The full saved plan details including metadata
    """
    try:
        plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id).first()

        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        # Return full plan details with metadata
        return SavedPlanDetail(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            observing_date=plan.observing_date,
            location_name=plan.location_name,
            plan=ObservingPlan(**plan.plan_data),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plan: {str(e)}")


@router.put("/{plan_id}", response_model=SavedPlanSummary)
async def update_plan(
    plan_id: int,
    request: SavePlanRequest,
    db: Session = Depends(get_db),
):
    """
    Update a saved plan.

    Args:
        plan_id: The ID of the plan to update
        request: Updated plan data

    Returns:
        Updated plan summary
    """
    try:
        plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id).first()

        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        # Update fields
        plan.name = request.name
        plan.description = request.description
        plan.observing_date = request.plan.session.observing_date
        plan.location_name = request.plan.location.name
        plan.plan_data = request.plan.model_dump(mode="json")
        plan.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(plan)

        return SavedPlanSummary(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            observing_date=plan.observing_date,
            location_name=plan.location_name,
            total_targets=request.plan.total_targets,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating plan: {str(e)}")


@router.delete("/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """
    Delete a saved plan.

    Args:
        plan_id: The ID of the plan to delete

    Returns:
        Success message
    """
    try:
        plan = db.query(SavedPlan).filter(SavedPlan.id == plan_id).first()

        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        db.delete(plan)
        db.commit()

        return {"message": f"Plan {plan_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Check if it's a foreign key constraint violation
        error_msg = str(e)
        if "foreign key constraint" in error_msg.lower() or "violates foreign key" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete plan {plan_id}: it is referenced by existing telescope executions",
            )
        raise HTTPException(status_code=500, detail=f"Error deleting plan: {error_msg}")
