"""
Market Analysis Service - Standalone analysis functionality for rental market insights
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from app.mongo import MongoClientWrapper
from app.agents.models import TenantModel, PropertyModel, LandlordModel
from app.agents.models.tenant_model import RentalStatus
from app.agents.models.property_model import PropertyRentalStatus
from app.agents.models.landlord_model import LandlordRentalStatus

class MarketAnalyzer:
    """
    Market Analysis Service - Provides comprehensive rental market analysis
    
    Purpose: Analyze current market status without visualization dependencies
    Focus: Basic market metrics, supply/demand analysis, pricing insights
    """
    
    def __init__(self):
        """Initialize market analyzer with database connections"""
        self.tenants_db = MongoClientWrapper(
            model=TenantModel,
            collection_name="tenants"
        )
        self.properties_db = MongoClientWrapper(
            model=PropertyModel,
            collection_name="properties"
        )
        self.landlords_db = MongoClientWrapper(
            model=LandlordModel,
            collection_name="landlords"
        )
        
        logger.info("🔍 Market Analyzer initialized")
    
    async def get_basic_market_metrics(self) -> Dict[str, Any]:
        """
        📊 Get basic market metrics for dashboard display
        
        Purpose: Provide essential market statistics without complex calculations
        
        Returns:
            Dict containing basic market metrics
        """
        try:
            logger.info("📊 Fetching basic market metrics")
            
            # Get all data from database
            all_tenants = await self._fetch_all_tenants()
            all_properties = await self._fetch_all_properties()
            all_landlords = await self._fetch_all_landlords()
            
            # Calculate basic tenant metrics
            tenant_metrics = self._calculate_tenant_metrics(all_tenants)
            
            # Calculate basic property metrics
            property_metrics = self._calculate_property_metrics(all_properties)
            
            # Calculate basic landlord metrics
            landlord_metrics = self._calculate_landlord_metrics(all_landlords)
            
            # Calculate supply-demand metrics
            supply_demand_metrics = self._calculate_supply_demand_metrics(
                tenant_metrics, property_metrics
            )
            
            # Calculate price metrics
            price_metrics = self._calculate_price_metrics(all_properties)
            
            # Compile results
            market_metrics = {
                "timestamp": datetime.now().isoformat(),
                "tenant_metrics": tenant_metrics,
                "property_metrics": property_metrics,
                "landlord_metrics": landlord_metrics,
                "supply_demand": supply_demand_metrics,
                "price_metrics": price_metrics,
                "market_health_indicator": self._calculate_market_health(
                    tenant_metrics, property_metrics, supply_demand_metrics
                )
            }
            
            logger.info("✅ Basic market metrics calculated successfully")
            return market_metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get market metrics: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "failed"
            }
    
    def _calculate_tenant_metrics(self, tenants: List[TenantModel]) -> Dict[str, Any]:
        """Calculate basic tenant-related metrics"""
        total_tenants = len(tenants)
        
        if total_tenants == 0:
            return {
                "total_tenants": 0,
                "waiting_tenants": 0,
                "rented_tenants": 0,
                "rental_rate_percentage": 0.0,
                "average_budget": 0.0,
                "budget_distribution": {}
            }
        
        # Categorize tenants by rental status
        rented_tenants = [t for t in tenants if t.rental_status.is_rented]
        waiting_tenants = [t for t in tenants if not t.rental_status.is_rented]
        
        # Calculate budget statistics for waiting tenants
        waiting_budgets = [t.max_budget for t in waiting_tenants] if waiting_tenants else [0]
        avg_budget = sum(waiting_budgets) / len(waiting_budgets) if waiting_budgets else 0
        
        # Budget distribution
        budget_distribution = self._create_budget_distribution(waiting_budgets)
        
        return {
            "total_tenants": total_tenants,
            "waiting_tenants": len(waiting_tenants),
            "rented_tenants": len(rented_tenants),
            "rental_rate_percentage": round((len(rented_tenants) / total_tenants) * 100, 2),
            "average_budget": round(avg_budget, 2),
            "budget_distribution": budget_distribution
        }
    
    def _calculate_property_metrics(self, properties: List[PropertyModel]) -> Dict[str, Any]:
        """Calculate basic property-related metrics"""
        total_properties = len(properties)
        
        if total_properties == 0:
            return {
                "total_properties": 0,
                "available_properties": 0,
                "rented_properties": 0,
                "occupancy_rate_percentage": 0.0,
                "average_rent": 0.0,
                "property_type_distribution": {}
            }
        
        # Categorize properties by rental status
        rented_properties = [p for p in properties if p.rental_status.is_rented]
        available_properties = [p for p in properties if not p.rental_status.is_rented]
        
        # Calculate rent statistics for available properties
        available_rents = [p.monthly_rent for p in available_properties if p.monthly_rent > 0]
        avg_rent = sum(available_rents) / len(available_rents) if available_rents else 0
        
        # Property type distribution
        property_types = [p.property_sub_type for p in available_properties]
        type_distribution = self._create_type_distribution(property_types)
        
        return {
            "total_properties": total_properties,
            "available_properties": len(available_properties),
            "rented_properties": len(rented_properties),
            "occupancy_rate_percentage": round((len(rented_properties) / total_properties) * 100, 2),
            "average_rent": round(avg_rent, 2),
            "property_type_distribution": type_distribution
        }
    
    def _calculate_landlord_metrics(self, landlords: List[LandlordModel]) -> Dict[str, Any]:
        """Calculate basic landlord-related metrics"""
        total_landlords = len(landlords)
        
        if total_landlords == 0:
            return {
                "total_landlords": 0,
                "active_landlords": 0,
                "total_portfolio_properties": 0,
                "total_rented_properties": 0,
                "average_portfolio_size": 0.0,
                "total_rental_income": 0.0
            }
        
        # Calculate portfolio statistics
        active_landlords = [l for l in landlords if l.rental_stats.total_properties > 0]
        total_portfolio = sum(l.rental_stats.total_properties for l in landlords)
        total_rented = sum(l.rental_stats.rented_properties for l in landlords)
        total_income = sum(l.rental_stats.total_rental_income for l in landlords)
        
        avg_portfolio_size = total_portfolio / len(active_landlords) if active_landlords else 0
        
        return {
            "total_landlords": total_landlords,
            "active_landlords": len(active_landlords),
            "total_portfolio_properties": total_portfolio,
            "total_rented_properties": total_rented,
            "average_portfolio_size": round(avg_portfolio_size, 2),
            "total_rental_income": round(total_income, 2)
        }
    
    def _calculate_supply_demand_metrics(self, tenant_metrics: Dict, property_metrics: Dict) -> Dict[str, Any]:
        """Calculate supply-demand balance metrics"""
        waiting_tenants = tenant_metrics["waiting_tenants"]
        available_properties = property_metrics["available_properties"]
        
        # Supply-demand ratio
        if waiting_tenants > 0:
            supply_demand_ratio = available_properties / waiting_tenants
        else:
            supply_demand_ratio = float('inf') if available_properties > 0 else 0
        
        # Market condition classification
        if supply_demand_ratio > 1.5:
            market_condition = "Buyer's Market"
            condition_score = 3
        elif supply_demand_ratio < 0.7:
            market_condition = "Seller's Market"
            condition_score = 1
        else:
            market_condition = "Balanced Market"
            condition_score = 2
        
        return {
            "supply_demand_ratio": round(supply_demand_ratio, 2),
            "market_condition": market_condition,
            "condition_score": condition_score,
            "waiting_tenants": waiting_tenants,
            "available_properties": available_properties,
            "market_tension": self._calculate_market_tension(supply_demand_ratio)
        }
    
    def _calculate_price_metrics(self, properties: List[PropertyModel]) -> Dict[str, Any]:
        """Calculate basic price metrics"""
        # All property prices
        all_prices = [p.monthly_rent for p in properties if p.monthly_rent > 0]
        
        # Available property prices
        available_prices = [p.monthly_rent for p in properties 
                          if not p.rental_status.is_rented and p.monthly_rent > 0]
        
        # Rented property prices (from rental_status)
        rented_prices = [p.rental_status.rental_price for p in properties 
                        if p.rental_status.is_rented and p.rental_status.rental_price]
        
        if not all_prices:
            return {
                "all_properties": {"count": 0, "average": 0, "median": 0, "min": 0, "max": 0},
                "available_properties": {"count": 0, "average": 0, "median": 0},
                "rented_properties": {"count": 0, "average": 0, "median": 0},
                "price_ranges": {}
            }
        
        # Calculate statistics
        all_stats = self._calculate_price_stats(all_prices)
        available_stats = self._calculate_price_stats(available_prices)
        rented_stats = self._calculate_price_stats(rented_prices)
        
        # Price range distribution
        price_ranges = self._create_price_range_distribution(available_prices)
        
        return {
            "all_properties": all_stats,
            "available_properties": available_stats,
            "rented_properties": rented_stats,
            "price_ranges": price_ranges
        }
    
    def _calculate_market_health(self, tenant_metrics: Dict, property_metrics: Dict, 
                               supply_demand: Dict) -> Dict[str, Any]:
        """Calculate overall market health indicator"""
        # Health score components (0-100 scale)
        occupancy_score = property_metrics["occupancy_rate_percentage"]
        rental_score = tenant_metrics["rental_rate_percentage"]
        balance_score = 50 + (supply_demand["condition_score"] - 2) * 25  # Balanced=50, Buyer's=75, Seller's=25
        
        # Overall health score (weighted average)
        health_score = (occupancy_score * 0.4 + rental_score * 0.3 + balance_score * 0.3)
        
        # Health classification
        if health_score >= 75:
            health_status = "Healthy"
        elif health_score >= 50:
            health_status = "Moderate"
        else:
            health_status = "Concerning"
        
        return {
            "health_score": round(health_score, 2),
            "health_status": health_status,
            "components": {
                "occupancy_score": round(occupancy_score, 2),
                "rental_score": round(rental_score, 2),
                "balance_score": round(balance_score, 2)
            }
        }
    
    # Helper methods for calculations
    def _create_budget_distribution(self, budgets: List[float]) -> Dict[str, int]:
        """Create budget range distribution"""
        if not budgets:
            return {}
        
        ranges = {
            "under_1000": len([b for b in budgets if b < 1000]),
            "1000_1500": len([b for b in budgets if 1000 <= b < 1500]),
            "1500_2000": len([b for b in budgets if 1500 <= b < 2000]),
            "2000_3000": len([b for b in budgets if 2000 <= b < 3000]),
            "over_3000": len([b for b in budgets if b >= 3000])
        }
        return ranges
    
    def _create_type_distribution(self, property_types: List[str]) -> Dict[str, int]:
        """Create property type distribution"""
        if not property_types:
            return {}
        
        type_counts = {}
        for prop_type in property_types:
            type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
        
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _create_price_range_distribution(self, prices: List[float]) -> Dict[str, int]:
        """Create price range distribution"""
        if not prices:
            return {}
        
        ranges = {
            "under_1000": len([p for p in prices if p < 1000]),
            "1000_1500": len([p for p in prices if 1000 <= p < 1500]),
            "1500_2000": len([p for p in prices if 1500 <= p < 2000]),
            "2000_3000": len([p for p in prices if 2000 <= p < 3000]),
            "over_3000": len([p for p in prices if p >= 3000])
        }
        return ranges
    
    def _calculate_price_stats(self, prices: List[float]) -> Dict[str, Any]:
        """Calculate basic price statistics"""
        if not prices:
            return {"count": 0, "average": 0, "median": 0, "min": 0, "max": 0}
        
        sorted_prices = sorted(prices)
        count = len(prices)
        average = sum(prices) / count
        median = sorted_prices[count // 2] if count % 2 == 1 else (sorted_prices[count // 2 - 1] + sorted_prices[count // 2]) / 2
        
        return {
            "count": count,
            "average": round(average, 2),
            "median": round(median, 2),
            "min": round(min(prices), 2),
            "max": round(max(prices), 2)
        }
    
    def _calculate_market_tension(self, supply_demand_ratio: float) -> str:
        """Calculate market tension level"""
        if supply_demand_ratio > 2.0:
            return "Low"
        elif supply_demand_ratio > 1.0:
            return "Moderate"
        elif supply_demand_ratio > 0.5:
            return "High"
        else:
            return "Critical"
    
    # Database access methods
    async def _fetch_all_tenants(self) -> List[TenantModel]:
        """Fetch all tenants from database"""
        try:
            return self.tenants_db.fetch_documents(0, {})
        except Exception as e:
            logger.error(f"Failed to fetch tenants: {str(e)}")
            return []
    
    async def _fetch_all_properties(self) -> List[PropertyModel]:
        """Fetch all properties from database"""
        try:
            return self.properties_db.fetch_documents(0, {})
        except Exception as e:
            logger.error(f"Failed to fetch properties: {str(e)}")
            return []
    
    async def _fetch_all_landlords(self) -> List[LandlordModel]:
        """Fetch all landlords from database"""
        try:
            return self.landlords_db.fetch_documents(0, {})
        except Exception as e:
            logger.error(f"Failed to fetch landlords: {str(e)}")
            return []

    async def get_detailed_market_analysis(self) -> Dict[str, Any]:
        """
        📊 Get detailed market analysis with additional insights
        
        Purpose: Provide comprehensive market analysis for business intelligence
        
        Returns:
            Detailed market analysis with trends and insights
        """
        try:
            logger.info("📊 Starting detailed market analysis")
            
            # Get basic metrics first
            basic_metrics = await self.get_basic_market_metrics()
            
            if "error" in basic_metrics:
                return basic_metrics
            
            # Get all raw data for additional analysis
            all_tenants = await self._fetch_all_tenants()
            all_properties = await self._fetch_all_properties()
            all_landlords = await self._fetch_all_landlords()
            
            # Additional analysis
            matching_analysis = self._analyze_matching_potential(all_tenants, all_properties)
            geographic_analysis = self._analyze_geographic_distribution(all_properties)
            temporal_analysis = self._analyze_temporal_trends(all_tenants, all_properties)
            
            # Combine all analysis
            detailed_analysis = {
                **basic_metrics,
                "matching_analysis": matching_analysis,
                "geographic_analysis": geographic_analysis,
                "temporal_analysis": temporal_analysis,
                "analysis_type": "detailed",
                "recommendations": self._generate_market_recommendations(basic_metrics)
            }
            
            logger.info("✅ Detailed market analysis completed")
            return detailed_analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get detailed market analysis: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "failed",
                "analysis_type": "detailed"
            }
    
    def _analyze_matching_potential(self, tenants: List[TenantModel], properties: List[PropertyModel]) -> Dict[str, Any]:
        """Analyze potential matches between tenants and properties"""
        waiting_tenants = [t for t in tenants if not t.rental_status.is_rented]
        available_properties = [p for p in properties if not p.rental_status.is_rented]
        
        if not waiting_tenants or not available_properties:
            return {
                "potential_matches": 0,
                "match_rate_percentage": 0.0,
                "budget_property_alignment": "No data available"
            }
        
        # Simple matching logic
        potential_matches = 0
        for tenant in waiting_tenants:
            for property in available_properties:
                if (property.monthly_rent <= tenant.max_budget and 
                    tenant.min_bedrooms <= property.bedrooms <= tenant.max_bedrooms):
                    potential_matches += 1
                    break  # Count each tenant only once
        
        match_rate = (potential_matches / len(waiting_tenants)) * 100
        
        return {
            "potential_matches": potential_matches,
            "match_rate_percentage": round(match_rate, 2),
            "total_waiting_tenants": len(waiting_tenants),
            "total_available_properties": len(available_properties),
            "matching_efficiency": round((potential_matches / min(len(waiting_tenants), len(available_properties))) * 100, 2)
        }
    
    def _analyze_geographic_distribution(self, properties: List[PropertyModel]) -> Dict[str, Any]:
        """Analyze geographic distribution of properties"""
        available_properties = [p for p in properties if not p.rental_status.is_rented]
        
        if not available_properties:
            return {"district_distribution": {}, "top_districts": []}
        
        # District distribution
        districts = [p.district for p in available_properties if p.district]
        district_counts = {}
        for district in districts:
            district_counts[district] = district_counts.get(district, 0) + 1
        
        # Top districts by availability
        top_districts = sorted(district_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "district_distribution": district_counts,
            "top_districts": [{"district": d[0], "count": d[1]} for d in top_districts],
            "total_districts": len(district_counts)
        }
    
    def _analyze_temporal_trends(self, tenants: List[TenantModel], properties: List[PropertyModel]) -> Dict[str, Any]:
        """Analyze temporal trends (simplified without historical data)"""
        # Since we don't have historical data, provide current snapshot analysis
        current_time = datetime.now()
        
        # Recent activity analysis (based on last_updated timestamps)
        recent_rentals = 0
        for tenant in tenants:
            if tenant.rental_status.is_rented and tenant.rental_status.last_updated:
                try:
                    update_time = datetime.fromisoformat(tenant.rental_status.last_updated.replace('Z', '+00:00'))
                    # Count as recent if updated in last 7 days
                    if (current_time - update_time).days <= 7:
                        recent_rentals += 1
                except:
                    pass
        
        return {
            "recent_rentals_7d": recent_rentals,
            "analysis_timestamp": current_time.isoformat(),
            "trend_direction": "stable",  # Placeholder - would require historical data
            "note": "Temporal analysis limited without historical data"
        }
    
    def _generate_market_recommendations(self, basic_metrics: Dict[str, Any]) -> List[str]:
        """Generate market recommendations based on analysis"""
        recommendations = []
        
        # Supply-demand recommendations
        supply_demand = basic_metrics.get("supply_demand", {})
        ratio = supply_demand.get("supply_demand_ratio", 1.0)
        
        if ratio > 1.5:
            recommendations.append("High property supply: Consider competitive pricing strategies")
        elif ratio < 0.7:
            recommendations.append("High tenant demand: Market favorable for landlords")
        
        # Occupancy recommendations
        property_metrics = basic_metrics.get("property_metrics", {})
        occupancy_rate = property_metrics.get("occupancy_rate_percentage", 0)
        
        if occupancy_rate < 60:
            recommendations.append("Low occupancy rate: Review pricing and property quality")
        elif occupancy_rate > 85:
            recommendations.append("High occupancy rate: Market performing well")
        
        # Health recommendations
        health = basic_metrics.get("market_health_indicator", {})
        health_status = health.get("health_status", "Unknown")
        
        if health_status == "Concerning":
            recommendations.append("Market health concerning: Monitor trends closely")
        elif health_status == "Healthy":
            recommendations.append("Market performing well: Good conditions for growth")
        
        return recommendations if recommendations else ["Market analysis complete - no specific recommendations"]