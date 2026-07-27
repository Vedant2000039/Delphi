# cortex_service.py
# ─────────────────────────────────────────────────────────────
# Snowflake Cortex Analyst wrapper.
#
# Supports TWO semantic models via the `model` parameter:
#   "leads"    → DELPHI_LEADS.yaml          (lead search pipeline)
#   "campaign" → CAMPAIGN_SUGGESTION.yaml   (campaign suggestion pipeline)
#
# Usage:
#   from .cortex_service import query_cortex_analyst
#   results = query_cortex_analyst(prompt)                  # leads (default)
#   results = query_cortex_analyst(prompt, model="campaign") # campaigns
# ─────────────────────────────────────────────────────────────

import os
import requests
import snowflake.connector

# ── Semantic model file paths in Snowflake stage ──────────────
_SEMANTIC_MODELS = {
    "leads":    "@DELPHI_DB.PUBLIC.DELPHI_STAGE/CAMPAIGN_DISCOVER.yaml",
    "campaign": "@DELPHI_DB.PUBLIC.DELPHI_STAGE/CAMPAIGN_DISCOVER.yaml",
}


def _get_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def query_cortex_analyst(prompt: str, model: str = "leads") -> list[dict]:
    """
    Send a natural-language prompt to Snowflake Cortex Analyst.

    Args:
        prompt: Natural language query
        model:  "leads" (default) or "campaign"

    Returns:
        List of result row dicts, or [] on any failure.
    """
    semantic_model_file = _SEMANTIC_MODELS.get(model)
    if not semantic_model_file:
        print(f"[Cortex] Unknown model '{model}'. Valid: {list(_SEMANTIC_MODELS)}")
        return []

    conn = _get_connection()

    try:
        token   = conn.rest.token
        account = os.getenv("SNOWFLAKE_ACCOUNT")
        url     = f"https://{account}.snowflakecomputing.com/api/v2/cortex/analyst/message"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "semantic_model_file": semantic_model_file,
        }

        headers = {
            "Authorization": f'Snowflake Token="{token}"',
            "Content-Type":  "application/json",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data     = response.json()

        print(f"[Cortex:{model}] Raw response:", data)

        # API-level error (wrong credentials, model not found, etc.)
        if "code" in data:
            print(f"[Cortex:{model}] API error:", data.get("message"))
            return []

        # Extract generated SQL
        sql_query = None
        for item in data.get("message", {}).get("content", []):
            if item.get("type") == "sql":
                sql_query = item["statement"]
                break

        if not sql_query:
            print(f"[Cortex:{model}] No SQL generated")
            return []

        print(f"[Cortex:{model}] Generated SQL:\n{sql_query}")

        # Execute the SQL
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            columns = [col[0] for col in cursor.description]
            rows    = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            print(f"[Cortex:{model}] Returned {len(results)} rows")
            return results
        finally:
            cursor.close()

    except Exception as e:
        print(f"[Cortex:{model}] Execution error: {e}")
        return []
    finally:
        conn.close()