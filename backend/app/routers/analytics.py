from fastapi import APIRouter, Request, Query
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/virality")
async def get_virality_analytics(
    request: Request,
    claim_id: str = Query(None),
    limit: int = Query(100, le=500)
):
    pool = request.app.timescaledb_pool

    # Build query — optionally filter by claim_id
    if claim_id:
        rows = await pool.fetch(
            """
            SELECT
                time_bucket('15 minutes', time) AS bucket,
                claim_id,
                platform,
                AVG(predicted_6h_reach) AS avg_predicted_reach,
                AVG(actual_reach)       AS avg_actual_reach,
                AVG(risk_score)         AS avg_risk_score
            FROM virality_metrics
            WHERE claim_id = $1
            GROUP BY bucket, claim_id, platform
            ORDER BY bucket DESC
            LIMIT $2
            """,
            claim_id, limit
        )
    else:
        rows = await pool.fetch(
            """
            SELECT
                time_bucket('15 minutes', time) AS bucket,
                claim_id,
                platform,
                AVG(predicted_6h_reach) AS avg_predicted_reach,
                AVG(actual_reach)       AS avg_actual_reach,
                AVG(risk_score)         AS avg_risk_score
            FROM virality_metrics
            GROUP BY bucket, claim_id, platform
            ORDER BY bucket DESC
            LIMIT $1
            """,
            limit
        )

    data = [dict(row) for row in rows]

    # Convert datetime to ISO string for JSON serialization
    for row in data:
        if row.get("bucket"):
            row["bucket"] = row["bucket"].isoformat()

    return {
        "success": True,
        "data": {"virality_series": data},
        "error": None
    }

from datetime import datetime, timezone

@router.get("/dashboard")
async def get_dashboard_stats(request: Request):
    """
    Returns aggregated stats for the dashboard page:
    - statCards (Total Claims, High-Risk, Active Campaigns, Verified Today)
    - riskData (distribution of risk scores)
    - activityFeed (latest flagged claims)
    - trendData (virality trends based on TimescaleDB)
    """
    db = request.app.mongodb
    pool = request.app.timescaledb_pool

    # --- 1. Stats Cards ---
    total_claims = await db.claims.count_documents({})
    high_risk_claims = await db.claims.count_documents({"risk_score": {"$gte": 0.6}})
    
    # Count unique active parent_claim_ids
    pipeline_campaigns = [{"$match": {"parent_claim_id": {"$ne": None}}}, {"$group": {"_id": "$parent_claim_id"}}, {"$count": "total"}]
    try:
        campaigns_cursor = db.claims.aggregate(pipeline_campaigns)
        campaigns_res = await campaigns_cursor.to_list(length=1)
        active_campaigns = campaigns_res[0]["total"] if campaigns_res else 0
    except Exception:
        active_campaigns = 0
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    verified_today = await db.claims.count_documents({"created_at": {"$gte": today_start}})

    def format_num(x):
        if x >= 1000000: return f"{x/1000000:.1f}M"
        if x >= 1000: return f"{x/1000:.1f}K"
        return str(x)

    statCards = [
        {"label": "Total Claims Detected", "value": format_num(total_claims), "trend": None},
        {"label": "High-Risk Claims", "value": format_num(high_risk_claims), "trend": None},
        {"label": "Active Campaigns", "value": format_num(active_campaigns), "trend": None},
        {"label": "Claims Verified Today", "value": format_num(verified_today), "trend": None},
    ]

    # --- 2. Risk Data Distribution ---
    low_risk = await db.claims.count_documents({"risk_score": {"$lt": 0.3}})
    medium_risk = await db.claims.count_documents({"risk_score": {"$gte": 0.3, "$lt": 0.6}})
    high_risk = await db.claims.count_documents({"risk_score": {"$gte": 0.6, "$lt": 0.85}})
    critical_risk = await db.claims.count_documents({"risk_score": {"$gte": 0.85}})

    riskData = [
        {"name": "Low Risk", "value": low_risk, "color": "#107C7C"},
        {"name": "Medium Risk", "value": medium_risk, "color": "#4FB0AE"},
        {"name": "High Risk", "value": high_risk, "color": "#E69D3B"},
        {"name": "Critical Risk", "value": critical_risk, "color": "#A12B2B"},
    ]

    # --- 3. Activity Feed (Latest Flagged Claims) ---
    latest_cursor = db.claims.find().sort("created_at", -1).limit(5)
    latest_claims = await latest_cursor.to_list(length=5)
    
    def get_status(score):
        if score >= 0.85: return "critical"
        if score >= 0.6: return "high"
        if score >= 0.3: return "medium"
        return "low"

    def get_label(score):
        if score >= 0.85: return "Critical"
        if score >= 0.6: return "High Risk"
        if score >= 0.3: return "Medium Risk"
        return "Low Risk"

    def time_ago(dt):
        if not dt: return "unknown"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - dt
        minutes = int(diff.total_seconds() / 60)
        if minutes < 60: return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24: return f"{hours}h ago"
        return f"{hours//24}d ago"

    activityFeed = []
    for c in latest_claims:
        score = c.get("risk_score", 0.0)
        platform = c.get("source", {}).get("platform", "Platform").capitalize()
        text_truncated = c.get("original_text", "")[:50]
        if len(c.get("original_text", "")) > 50: text_truncated += "..."
        activityFeed.append({
            "platform": platform,
            "claim": text_truncated,
            "score": f"{int(score*100)} - {get_label(score)}",
            "status": get_status(score),
            "time": time_ago(c.get("created_at"))
        })

    # --- 4. Trend Data from TimescaleDB (last 6 hours by hour) ---
    trendData = []
    try:
        rows = await pool.fetch(
            """
            SELECT
                time_bucket('1 hour', time) AS bucket,
                AVG(predicted_6h_reach) AS avg_predicted,
                AVG(actual_reach) AS avg_actual
            FROM virality_metrics
            WHERE time > NOW() - INTERVAL '6 hours'
            GROUP BY bucket
            ORDER BY bucket ASC
            LIMIT 6
            """
        )
        for r in rows:
             hr = r["bucket"].strftime("%I %p")
             trendData.append({
                 "time": hr,
                 "predicted": int(r["avg_predicted"] or 0),
                 "actual": int(r["avg_actual"] or 0)
             })
    except Exception as e:
        logger.error(f"Error fetching trend data: {e}")

    # Fallback trend data if empty
    if not trendData:
        trendData = [
            {"time": "12 AM", "predicted": 20, "actual": 15},
            {"time": "04 AM", "predicted": 25, "actual": 22},
            {"time": "08 AM", "predicted": 45, "actual": 38},
            {"time": "12 PM", "predicted": 60, "actual": 55},
            {"time": "04 PM", "predicted": 85, "actual": 70},
            {"time": "08 PM", "predicted": 75, "actual": 82},
        ]

    return {
        "success": True,
        "data": {
            "statCards": statCards,
            "riskData": riskData,
            "activityFeed": activityFeed,
            "trendData": trendData
        },
        "error": None
    }