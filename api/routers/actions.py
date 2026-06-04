"""Роутер домена actions (§3.4). prefix=/api/actions.

POST записывает действие в журнал (output/actions.csv) и возвращает обновлённый
рантайм-статус инцидента (actions_service, b5).
"""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter

from api.domain.common import Status
from api.domain.entities import Action, ActionType
from api.services import actions_service

router = APIRouter(prefix="/api/actions", tags=["actions"])


class ActionResult(BaseModel):
    """Ответ POST /api/actions: записанное действие + новый статус инцидента."""

    incident_id: str
    action: ActionType
    comment: str
    status: Status


@router.post("", response_model=ActionResult)
def record_action(action: Action) -> ActionResult:
    """Записать действие и вернуть обновлённый статус инцидента (§3.4)."""
    actions_service.record(action)
    return ActionResult(
        incident_id=action.incident_id,
        action=action.action,
        comment=action.comment,
        status=actions_service.status_for(action.incident_id),
    )
