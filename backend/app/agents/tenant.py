from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseRentalAgent, AgentProfile, Property, MarketData
from .models import TenantModel, PropertyModel
from loguru import logger


class TenantAgent(BaseRentalAgent):
    """Tenant Agent - Intelligent property seeker with personalized preferences"""
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        budget: Dict[str, Any],
        preferred_areas: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        preferences: Dict[str, Any] = None,
        profile: Dict[str, Any] = None,
        **kwargs
    ):
        profile = AgentProfile(
            name=name,
            role="Property Seeker",
            goals=[
                "Find ideal property matching requirements and budget",
                "Optimize value for money through informed decisions",
                "Secure favorable rental terms through professional negotiation",
                "Ensure property meets all essential living needs"
            ],
            constraints=[
                f"Budget range: £{budget['min_amount']} - £{budget['max_amount']} {budget['frequency']}",
                "Location constraints based on preferred areas",
                "Must meet essential requirements and preferences",
                "Comply with rental market standards"
            ],
            capabilities=[
                "Property evaluation and comparison",
                "Budget optimization",
                "Location analysis",
                "Rental terms negotiation",
                "Market trend understanding"
            ]
        )
        
        system_message = f"""You are a sophisticated tenant agent named {name}.

Profile and Requirements:
- Budget Range: £{budget['min_amount']} - £{budget['max_amount']} {budget['frequency']}
- Preferred Areas: {', '.join(area['area_name'] for area in preferred_areas)}
- Essential Requirements: {requirements}
- Living Preferences: {preferences or 'Standard comfort requirements'}
- Tenant Profile: {profile or 'Not specified'}

Key Objectives:
1. Find properties matching exact specifications and budget
2. Analyze value proposition of each property
3. Negotiate optimal rental terms
4. Ensure all requirements are met

Decision Framework:
- Evaluate properties against detailed criteria
- Consider location convenience and accessibility
- Assess value for money and market position
- Verify property conditions and features
- Negotiate based on market data

Communication Style:
- Clear and specific about requirements
- Professional in negotiations
- Data-driven in property evaluation
- Direct about deal-breakers
- Transparent about preferences

Important: Focus on property details, terms, and value assessment. All decisions must be based on requirements and market data."""
        
        super().__init__(
            name=name,
            profile=profile,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        
        self.budget = budget
        self.preferred_areas = preferred_areas
        self.requirements = requirements
        self.preferences = preferences or {}
        self.profile = profile or {}
        self.viewed_properties: List[Dict[str, Any]] = []
        self.interested_properties: List[str] = []
        
    def evaluate_property(self, property_data: Property, market_data: MarketData) -> Dict:
        """Comprehensive property evaluation against requirements"""
        evaluation = {
            "property_id": property_data.property_id,
            "basic_criteria": self._evaluate_basic_criteria(property_data),
            "location_score": self._evaluate_location(property_data),
            "price_analysis": self._analyze_price(property_data, market_data),
            "features_match": self._evaluate_features(property_data),
            "overall_score": 0,
            "deal_breakers": [],
            "recommendation": ""
        }
        
        # Calculate weighted score
        weights = {
            "basic": 0.3,
            "location": 0.25,
            "price": 0.25,
            "features": 0.2
        }
        
        scores = {
            "basic": evaluation["basic_criteria"]["score"],
            "location": evaluation["location_score"]["score"],
            "price": evaluation["price_analysis"]["score"],
            "features": evaluation["features_match"]["score"]
        }
        
        evaluation["overall_score"] = sum(
            scores[key] * weights[key] for key in weights
        )
        
        # Check for deal breakers
        deal_breakers = []
        if not evaluation["basic_criteria"]["meets_minimum"]:
            deal_breakers.extend(evaluation["basic_criteria"]["failed_criteria"])
        if evaluation["price_analysis"]["over_budget"]:
            deal_breakers.append("Price exceeds maximum budget")
        if evaluation["location_score"]["too_far"]:
            deal_breakers.append("Location outside acceptable range")
            
        evaluation["deal_breakers"] = deal_breakers
        
        # Generate recommendation
        if not deal_breakers:
            if evaluation["overall_score"] >= 80:
                evaluation["recommendation"] = "Highly Recommended"
            elif evaluation["overall_score"] >= 70:
                evaluation["recommendation"] = "Worth Viewing"
            elif evaluation["overall_score"] >= 60:
                evaluation["recommendation"] = "Consider if No Better Options"
            else:
                evaluation["recommendation"] = "Not Recommended"
        else:
            evaluation["recommendation"] = "Not Suitable - Deal Breakers Present"
            
        self.log_interaction("property_evaluation", evaluation)
        return evaluation
        
    def _evaluate_basic_criteria(self, property_data: Property) -> Dict:
        """Evaluate basic property criteria"""
        score = 0
        failed_criteria = []
        
        # Check bedrooms
        if property_data.bedrooms < self.requirements.get("min_bedrooms", 1):
            failed_criteria.append("Insufficient bedrooms")
        else:
            score += 30
            
        # Check bathrooms
        if property_data.bathrooms < self.requirements.get("min_bathrooms", 1):
            failed_criteria.append("Insufficient bathrooms")
        else:
            score += 20
            
        # Check property type
        if (self.requirements.get("property_types") and 
            property_data.property_type not in self.requirements["property_types"]):
            failed_criteria.append("Wrong property type")
        else:
            score += 20
            
        # Additional basic checks
        if self.preferences.get("furnished") is not None:
            if "furnished" in property_data.summary.lower() == self.preferences["furnished"]:
                score += 15
            else:
                failed_criteria.append("Furnishing status mismatch")
                
        if self.preferences.get("pets") and "no pets" in property_data.summary.lower():
            failed_criteria.append("No pets allowed")
            
        return {
            "score": score,
            "meets_minimum": len(failed_criteria) == 0,
            "failed_criteria": failed_criteria
        }
        
    def _evaluate_location(self, property_data: Property) -> Dict:
        """Evaluate property location"""
        from math import radians, sin, cos, sqrt, atan2
        
        def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            R = 6371  # Earth's radius in kilometers
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
            
        score = 0
        too_far = False
        distances = []
        
        # Check distance to preferred areas
        for area in self.preferred_areas:
            distance = calculate_distance(
                property_data.location["latitude"],
                property_data.location["longitude"],
                area["latitude"],
                area["longitude"]
            )
            distances.append({
                "area": area["area_name"],
                "distance": distance,
                "within_range": distance <= area["max_distance"]
            })
            
            if distance <= area["max_distance"]:
                score += (40 / len(self.preferred_areas)) * (1 - distance/area["max_distance"])
                
        # Check if any preferred area is within range
        if not any(d["within_range"] for d in distances):
            too_far = True
            
        # Check commute if specified
        if "commute_destination" in self.requirements:
            commute_distance = calculate_distance(
                property_data.location["latitude"],
                property_data.location["longitude"],
                self.requirements["commute_destination"]["latitude"],
                self.requirements["commute_destination"]["longitude"]
            )
            
            if commute_distance <= self.requirements.get("max_commute_time", float("inf")):
                score += 30 * (1 - commute_distance/self.requirements["max_commute_time"])
            else:
                too_far = True
                
        return {
            "score": min(score, 100),
            "too_far": too_far,
            "distance_details": distances
        }
        
    def _analyze_price(self, property_data: Property, market_data: MarketData) -> Dict:
        """Analyze property price against budget and market data"""
        price = property_data.price["amount"]
        score = 0
        notes = []
        
        # Check against budget
        over_budget = price > self.budget["max_amount"]
        within_preferred = self.budget["min_amount"] <= price <= self.budget["preferred_amount"]
        
        if within_preferred:
            score += 50
            notes.append("Price within preferred range")
        elif not over_budget:
            score += 30
            notes.append("Price within maximum budget")
            
        # Compare to market average
        if market_data:
            market_ratio = price / market_data.average_price
            if market_ratio <= 0.9:
                score += 30
                notes.append("Below market average - good value")
            elif market_ratio <= 1.1:
                score += 20
                notes.append("Around market average")
            else:
                notes.append("Above market average")
                
        return {
            "score": score,
            "over_budget": over_budget,
            "market_comparison": market_ratio if market_data else None,
            "notes": notes
        }
        
    def _evaluate_features(self, property_data: Property) -> Dict:
        """Evaluate property features against requirements"""
        score = 0
        missing_essential = []
        has_nice_to_have = []
        
        # Check must-have features
        if "must_have_features" in self.requirements:
            for feature in self.requirements["must_have_features"]:
                if feature.lower() not in property_data.summary.lower():
                    missing_essential.append(feature)
                else:
                    score += 40 / len(self.requirements["must_have_features"])
                    
        # Check nice-to-have features
        if "nice_to_have_features" in self.requirements:
            for feature in self.requirements["nice_to_have_features"]:
                if feature.lower() in property_data.summary.lower():
                    has_nice_to_have.append(feature)
                    score += 20 / len(self.requirements["nice_to_have_features"])
                    
        return {
            "score": min(score, 100),
            "missing_essential": missing_essential,
            "has_nice_to_have": has_nice_to_have
        }
        
    def make_decision(self, context: Dict) -> Dict:
        """Make informed decisions based on property evaluation and market data"""
        if context["type"] == "property_viewing":
            return self._handle_property_viewing(context)
        elif context["type"] == "negotiation":
            return self._handle_negotiation(context)
        else:
            return {"action": "need_more_info", "details": "Unrecognized decision context"}
            
    def _handle_property_viewing(self, context: Dict) -> Dict:
        """Process property viewing decision"""
        property_data = context["property"]
        market_data = context["market_data"]
        
        evaluation = self.evaluate_property(property_data, market_data)
        
        if evaluation["deal_breakers"]:
            return {
                "action": "reject",
                "property_id": property_data.property_id,
                "reason": "Deal breakers present",
                "details": {
                    "deal_breakers": evaluation["deal_breakers"],
                    "evaluation": evaluation
                }
            }
            
        if evaluation["overall_score"] >= 60:
            max_offer = self._calculate_initial_offer(property_data, market_data)
            return {
                "action": "interested",
                "property_id": property_data.property_id,
                "max_offer": max_offer,
                "evaluation": evaluation,
                "next_steps": self._generate_next_steps(evaluation["overall_score"])
            }
        else:
            return {
                "action": "pass",
                "property_id": property_data.property_id,
                "reason": "Does not meet minimum requirements",
                "evaluation": evaluation
            }
            
    def _handle_negotiation(self, context: Dict) -> Dict:
        """Handle price negotiation"""
        property_data = context["property"]
        current_price = context["current_price"]
        market_data = context.get("market_data")
        
        max_offer = self._calculate_maximum_offer(
            property_data,
            market_data,
            context.get("negotiation_history", [])
        )
        
        if current_price <= max_offer:
            return {
                "action": "accept",
                "property_id": property_data.property_id,
                "accepted_price": current_price,
                "reason": "Price within acceptable range"
            }
        elif current_price <= max_offer * 1.1:
            counter_offer = self._calculate_counter_offer(current_price, max_offer)
            return {
                "action": "counter_offer",
                "property_id": property_data.property_id,
                "offer": counter_offer,
                "max_offer": max_offer,
                "reason": "Price negotiable within range"
            }
        else:
            return {
                "action": "reject",
                "property_id": property_data.property_id,
                "max_offer": max_offer,
                "reason": "Price too high for budget and value"
            }
            
    def _calculate_initial_offer(self, property_data: Property, market_data: MarketData) -> float:
        """Calculate initial offer based on property evaluation and market data"""
        asking_price = property_data.price["amount"]
        
        # Start with preferred amount as base
        max_offer = min(asking_price, self.budget["preferred_amount"])
        
        # Adjust based on market data
        if market_data:
            if asking_price > market_data.average_price * 1.1:
                max_offer = min(max_offer, market_data.average_price * 1.05)
            elif asking_price < market_data.average_price * 0.9:
                max_offer = asking_price  # Good deal, offer asking price
                
        # Never exceed maximum budget
        return min(max_offer, self.budget["max_amount"])
        
    def _calculate_maximum_offer(
        self,
        property_data: Property,
        market_data: MarketData,
        negotiation_history: List[Dict]
    ) -> float:
        """Calculate maximum offer considering all factors"""
        asking_price = property_data.price["amount"]
        
        # Start with maximum budget
        max_offer = self.budget["max_amount"]
        
        # Adjust based on market position
        if market_data:
            market_position = asking_price / market_data.average_price
            if market_position > 1.1:  # Overpriced
                max_offer = min(max_offer, market_data.average_price * 1.05)
            elif market_position < 0.9:  # Good deal
                max_offer = min(asking_price, max_offer)
                
        # Consider negotiation history
        if negotiation_history:
            lowest_counter = min(
                offer["counter_price"] 
                for offer in negotiation_history 
                if "counter_price" in offer
            )
            max_offer = min(max_offer, lowest_counter * 1.05)
            
        return max_offer
        
    def _calculate_counter_offer(self, current_price: float, max_offer: float) -> float:
        """Calculate counter offer during negotiation"""
        # Offer 90-95% of current price, but never exceed max_offer
        return min(current_price * 0.925, max_offer)
