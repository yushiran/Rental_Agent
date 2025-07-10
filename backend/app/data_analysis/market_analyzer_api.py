
"""
Market Analysis API Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
from loguru import logger
from app.data_analysis.market_analyzer import MarketAnalyzer

# Initialize router
analysis_router = APIRouter(prefix="/analysis", tags=["market_analysis"])

# Initialize analyzer
market_analyzer = MarketAnalyzer()

@analysis_router.get("/market/basic", response_model=Dict[str, Any])
async def get_basic_market_analysis() -> Dict[str, Any]:
    """
    📊 Get basic market analysis metrics
    
    Purpose: Provide essential market statistics for frontend dashboard
    
    Returns:
        Basic market metrics including supply/demand, pricing, occupancy rates
    """
    try:
        logger.info("📊 API: Fetching basic market analysis")
        
        analysis_result = await market_analyzer.get_basic_market_metrics()
        
        # Add API metadata
        analysis_result["api_metadata"] = {
            "endpoint": "/api/analysis/market/basic",
            "response_time": datetime.now().isoformat(),
            "data_type": "basic_metrics"
        }
        
        logger.info("✅ API: Basic market analysis completed")
        return analysis_result
        
    except Exception as e:
        logger.error(f"❌ API: Basic market analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")