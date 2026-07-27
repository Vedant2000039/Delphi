from fastapi import APIRouter
from pydantic import BaseModel
from apis.context_engine.cortex_service import query_cortex_analyst

# Router mounted under /intellegence — groups the raw Cortex chat endpoint
# (note: prefix/tag spelling "Intellegence" is kept exactly as in the original)
router = APIRouter(
    prefix="/intellegence",
    tags=["Intellegence"]
)


class ChatRequest(BaseModel):
    """Payload for POST /intellegence/chat — a raw natural-language query for Cortex Analyst."""
    message: str


@router.post("/chat")
def chat_with_cortex(request: ChatRequest):
    """
    Passes the user's message straight through to Cortex Analyst against
    the "leads" model and returns the resulting rows, along with a count.
    """
    try:
        # Forward the raw message directly to Cortex Analyst as the query
        results = query_cortex_analyst(request.message, model="leads")

        return {
            "data":      results,
            "row_count": len(results),
        }

    except Exception as e:
        # On any failure, return the error message instead of raising
        return {"error": str(e)}