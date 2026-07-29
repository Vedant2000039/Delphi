from fastapi import APIRouter, HTTPException
from openai import OpenAI
from db import get_conn
import os, json

router = APIRouter(prefix="/icp", tags=["ICP Insight"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/generate-insight")
def generate_icp_insight(payload: dict):
    product = payload.get("product")
    country_id = payload.get("country_id")
    industry_id = payload.get("industry_id")
    brand_id = payload.get("brand_id")

    if not (country_id and industry_id and brand_id):
        raise HTTPException(400, "country_id, industry_id, brand_id required")

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.callproc("Usp_get_icp_ideal_snapshot", [industry_id, brand_id, country_id])
    snapshot = []
    for r in cur.stored_results():
        rows = r.fetchall()
        if rows: snapshot.append(rows[0])
    cur.close(); conn.close()

    prompt = f"""
You are a B2B GTM analyst. Given this ideal customer snapshot data and product context, return STRICT JSON only, no markdown, matching this schema:
{{
  "icp_summary": "string",
  "top_industries": [{{"name": "string", "score": number}}],
  "top_job_titles": [{{"title": "string", "score": number}}],
  "firmographics": {{"employee_size": "string", "revenue_range": "string", "geography": "string"}},
  "recommended_next_steps": ["string"]
}}

Product: {product}
Snapshot data: {json.dumps(snapshot, default=str)}
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    try:
        structured = json.loads(resp.choices[0].message.content)
    except Exception:
        raise HTTPException(500, "Failed to parse AI response")

    return {"snapshot": snapshot, "insight": structured}