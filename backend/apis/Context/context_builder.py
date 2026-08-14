# ==============================================================================
# File: backend/apis/Context/context.py
#
# Description:
# Context Engineering API for Delphi AI.
#
# Responsibilities:
#   1. Store user conversation messages
#   2. Retrieve user context
#   3. Retrieve session messages
#   4. Provide a foundation for context building
#
# Context extraction / OpenAI logic will be handled separately.
# ==============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from db import get_conn


# ==============================================================================
# Router
# ==============================================================================

router = APIRouter(
    prefix="/context",
    tags=["Context"]
)


# ==============================================================================
# Pydantic Models
# ==============================================================================

class ChatMessageRequest(BaseModel):
    """
    Request model for storing a user/assistant message.
    """

    user_id: int = Field(..., description="Delphi user ID")
    session_id: str = Field(..., min_length=1, description="Current chat session ID")
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., min_length=1, description="Chat message")


class ContextResponse(BaseModel):
    """
    Basic response returned by context APIs.
    """

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
    Check whether Context API is running.
    """

    return {
        "status": "success",
        "service": "context",
        "message": "Context service is running"
    }


# ==============================================================================
# Save Chat Message
# ==============================================================================

@router.post("/message", response_model=ContextResponse)
def save_message(request: ChatMessageRequest):
    """
    Save a chat message for the current session.

    This is the first step of Context Engineering.

    Example:

    POST /context/message

    {
        "user_id": 10,
        "session_id": "session_001",
        "role": "user",
        "content": "My favorite color is blue."
    }
    """

    # --------------------------------------------------------------------------
    # Validate role
    # --------------------------------------------------------------------------

    allowed_roles = {"user", "assistant", "system"}

    if request.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Allowed values: user, assistant, system"
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
        # Store message
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

@router.get("/session/{user_id}/{session_id}")
def get_session_messages(
    user_id: int,
    session_id: str
):
    """
    Retrieve all messages from a particular session.
    """

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(dictionary=True)

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
            ORDER BY created_at ASC, id ASC
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
            detail=f"Failed to retrieve session messages: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==============================================================================
# Get User Context
# ==============================================================================

@router.get("/{user_id}")
def get_user_context(user_id: int):
    """
    Retrieve the long-term context/memory of a user.

    This is different from session messages.

    Example:

        User:
        My favorite color is blue.

    Context:

        favorite_color = blue

    This context can be used in future sessions.
    """

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(dictionary=True)

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
            detail=f"Failed to retrieve user context: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==============================================================================
# Get Complete Context
# ==============================================================================

@router.get("/full/{user_id}/{session_id}")
def get_full_context(
    user_id: int,
    session_id: str
):
    """
    Retrieve everything required to build the LLM context.

    Returns:

        1. Long-term user context
        2. Current session messages

    Later this endpoint will also retrieve:
        - relevant semantic memories
        - previous session summaries
        - decisions
        - preferences
        - goals
    """

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(dictionary=True)

        # ----------------------------------------------------------------------
        # 1. Long-term user context
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
        # 2. Current session messages
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
            ORDER BY created_at ASC, id ASC
            """,
            (
                user_id,
                session_id
            )
        )

        session_messages = cursor.fetchall()

        # ----------------------------------------------------------------------
        # Response
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
            detail=f"Failed to build full context: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()