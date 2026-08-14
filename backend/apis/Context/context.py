
# ==============================================================================
# File: backend/apis/Context/context.py
#
# Description:
# Context Engineering API routes for Delphi AI.
#
# Responsibilities:
#   - Receive and store conversation messages
#   - Retrieve session messages
#   - Retrieve long-term user context
#   - Retrieve complete context for an LLM request
# ==============================================================================

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import get_conn


# ==============================================================================
# Router
# ==============================================================================

router = APIRouter(
    prefix="/context",
    tags=["Context"]
)


# ==============================================================================
# Request / Response Models
# ==============================================================================

class ChatMessageRequest(BaseModel):
    """Request model for saving a chat message."""

    user_id: int = Field(
        ...,
        description="Delphi user ID"
    )

    session_id: str = Field(
        ...,
        min_length=1,
        description="Current chat session ID"
    )

    role: str = Field(
        ...,
        description="Message role: user, assistant, or system"
    )

    content: str = Field(
        ...,
        min_length=1,
        description="Chat message content"
    )


class ContextResponse(BaseModel):
    """Standard response for context operations."""

    status: str
    user_id: int
    session_id: Optional[str] = None
    message: Optional[str] = None


# ==============================================================================
# Health Check
# ==============================================================================

@router.get("/health")
def context_health():
    """
    Check whether the Context API is running.
    """

    return {
        "status": "success",
        "service": "context",
        "message": "Context service is running"
    }


# ==============================================================================
# Save Chat Message
# ==============================================================================

@router.post(
    "/message",
    response_model=ContextResponse
)
def save_message(request: ChatMessageRequest):
    """
    Store a single conversation message.

    This endpoint stores the raw conversation.

    Context extraction will be handled by context_builder.py.
    """

    # --------------------------------------------------------------------------
    # Validate role
    # --------------------------------------------------------------------------

    allowed_roles = {
        "user",
        "assistant",
        "system"
    }

    if request.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid role. "
                "Allowed values: user, assistant, system"
            )
        )

    conn = None
    cursor = None

    try:

        # ----------------------------------------------------------------------
        # Database connection
        # ----------------------------------------------------------------------

        conn = get_conn()

        cursor = conn.cursor()

        # ----------------------------------------------------------------------
        # Insert message
        # ----------------------------------------------------------------------

        cursor.execute(
            """
            INSERT INTO context_messages
            (
                user_id,
                session_id,
                role,
                content
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                request.user_id,
                request.session_id,
                request.role,
                request.content
            )
        )

        conn.commit()

        # ----------------------------------------------------------------------
        # Response
        # ----------------------------------------------------------------------

        return ContextResponse(
            status="success",
            user_id=request.user_id,
            session_id=request.session_id,
            message="Message saved successfully"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save context message: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==============================================================================
# Get Session Messages
# ==============================================================================

@router.get(
    "/session/{user_id}/{session_id}"
)
def get_session_messages(
    user_id: int,
    session_id: str
):
    """
    Retrieve all messages belonging to a session.
    """

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                session_id,
                role,
                content,
                created_at
            FROM context_messages
            WHERE user_id = %s
              AND session_id = %s
            ORDER BY
                created_at ASC,
                id ASC
            """,
            (
                user_id,
                session_id
            )
        )

        messages = cursor.fetchall()

        return {
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "message_count": len(messages),
            "messages": messages
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to retrieve session messages: {str(e)}"
            )
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==============================================================================
# Get User Long-Term Context
# ==============================================================================

@router.get(
    "/user/{user_id}"
)
def get_user_context(user_id: int):
    """
    Retrieve active long-term context for a user.

    Example:

        favorite_color = blue
        height = 5 ft
        weight = 60 kg
    """

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                context_key,
                context_value,
                context_category,
                confidence,
                source,
                status,
                created_at,
                updated_at
            FROM user_context
            WHERE user_id = %s
              AND status = 'active'
            ORDER BY updated_at DESC
            """,
            (user_id,)
        )

        context = cursor.fetchall()

        return {
            "status": "success",
            "user_id": user_id,
            "context_count": len(context),
            "context": context
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to retrieve user context: {str(e)}"
            )
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==============================================================================
# Get Complete Context
# ==============================================================================

@router.get(
    "/full/{user_id}/{session_id}"
)
def get_full_context(
    user_id: int,
    session_id: str
):
    """
    Retrieve the context required to build an LLM prompt.

    Returns:

        1. Long-term user context
        2. Current session messages
    """

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(
            dictionary=True
        )

        # ----------------------------------------------------------------------
        # Long-term user context
        # ----------------------------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                context_key,
                context_value,
                context_category,
                confidence,
                source,
                status,
                updated_at
            FROM user_context
            WHERE user_id = %s
              AND status = 'active'
            ORDER BY updated_at DESC
            """,
            (user_id,)
        )

        user_context = cursor.fetchall()

        # ----------------------------------------------------------------------
        # Current session messages
        # ----------------------------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                role,
                content,
                created_at
            FROM context_messages
            WHERE user_id = %s
              AND session_id = %s
            ORDER BY
                created_at ASC,
                id ASC
            """,
            (
                user_id,
                session_id
            )
        )

        session_messages = cursor.fetchall()

        # ----------------------------------------------------------------------
        # Return combined context
        # ----------------------------------------------------------------------

        return {
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "context": {
                "long_term": user_context,
                "current_session": session_messages
            }
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to build full context: {str(e)}"
            )
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

