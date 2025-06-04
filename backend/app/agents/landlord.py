from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseRentalAgent, AgentProfile, Property, MarketData
from .models import LandlordModel, PropertyModel
from loguru import logger


class LandlordAgent(BaseRentalAgent):
    """Landlord Agent - Professional property manager with market-driven decision making"""
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        properties: List[Property],
        pricing_strategy: str = "market_based",
        tenant_preferences: Dict[str, Any] = None,
        performance_metrics: Dict[str, Any] = None,
        **kwargs
    ):
        profile = AgentProfile(
            name=name,
            role="Professional Landlord",
            goals=[
                "Maximize property portfolio returns through optimal pricing",
                "Secure high-quality, long-term tenants",
                "Maintain high occupancy rates and property standards",
                "Build strong landlord reputation and tenant satisfaction"
            ],
            constraints=[
                "Comply with all rental market regulations",
                "Maintain minimum tenant qualification standards",
                "Ensure property maintenance and safety standards",
                "Operate within market-competitive pricing ranges"
            ],
            capabilities=[
                "Data-driven property pricing optimization",
                "Comprehensive tenant screening and risk assessment",
                "Professional contract negotiation",
                "Efficient property portfolio management",
                "Market trend analysis and adaptation"
            ]
        )
        
        system_message = f"""You are a professional landlord named {name} managing {len(properties)} properties.

Role and Expertise:
- Portfolio Size: {len(properties)} properties
- Pricing Strategy: {pricing_strategy}
- Tenant Requirements: {tenant_preferences or 'Standard market requirements'}
- Performance Metrics: {performance_metrics or 'Not available'}

Key Objectives:
1. Optimize rental income through data-driven pricing
2. Secure reliable, long-term tenants through thorough screening
3. Maintain high occupancy rates and tenant satisfaction
4. Build a professional reputation in the market

Communication Approach:
- Professional and data-informed
- Clear property specifications and requirements
- Market-based pricing justification
- Transparent negotiation process
- Direct response to tenant queries and concerns

Decision Framework:
- Use market data for pricing decisions
- Apply consistent tenant screening criteria
- Consider long-term portfolio value
- Balance occupancy rates with rental income
- Prioritize tenant quality over quick letting

Important: Focus on property details, terms, and conditions. All decisions must be based on data and market conditions."""
        
        super().__init__(
            name=name,
            profile=profile,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        
        self.properties = {str(prop.property_id): prop for prop in properties}
        self.pricing_strategy = pricing_strategy
        self.tenant_preferences = tenant_preferences or self._default_tenant_preferences()
        self.performance_metrics = performance_metrics or {}
        self.rental_applications: List[Dict] = []
        self.tenant_inquiries: List[Dict] = []
        
    def _default_tenant_preferences(self) -> Dict[str, Any]:
        """Default tenant qualification criteria"""
        return {
            "min_income_ratio": 2.5,
            "preferred_employment_status": ["employed", "self_employed"],
            "min_credit_score": 650,
            "lease_length_preference": "12 months",
            "additional_requirements": [
                "employment verification",
                "previous landlord references",
                "credit check"
            ]
        }
        
    def set_property_price(self, property_id: str, market_data: MarketData) -> float:
        """Set optimal property price based on market data and property features"""
        if property_id not in self.properties:
            raise ValueError(f"Property {property_id} not found in portfolio")
            
        property_data = self.properties[property_id]
        
        if self.pricing_strategy == "market_based":
            # Calculate base price from market data
            base_price = market_data.average_price
            
            # Property feature adjustments
            adjustments = {
                "location": self._calculate_location_premium(property_data.location, market_data),
                "condition": self._assess_property_condition(property_data),
                "features": self._evaluate_property_features(property_data),
                "market_trend": self._analyze_market_trend(market_data)
            }
            
            # Apply adjustments
            final_price = base_price
            for factor, adjustment in adjustments.items():
                final_price *= (1 + adjustment)
            
        elif self.pricing_strategy == "competitive":
            # Price slightly below market for faster letting
            similar_properties = self._find_similar_properties(property_data, market_data)
            final_price = self._calculate_competitive_price(similar_properties)
            
        elif self.pricing_strategy == "premium":
            # Premium pricing for high-end properties
            final_price = self._calculate_premium_price(property_data, market_data)
            
        else:
            final_price = market_data.average_price
            
        # Update property price
        self.properties[property_id].price["amount"] = round(final_price, 2)
        
        # Log price update
        self.log_interaction("price_update", {
            "property_id": property_id,
            "previous_price": property_data.price.get("amount"),
            "new_price": final_price,
            "market_average": market_data.average_price,
            "adjustments": adjustments if self.pricing_strategy == "market_based" else None,
            "strategy": self.pricing_strategy
        })
        
        return final_price
        
    def evaluate_tenant(self, tenant_info: Dict) -> Dict:
        """Comprehensive tenant evaluation based on multiple criteria"""
        evaluation = {
            "tenant_id": tenant_info.get("tenant_id", "Unknown"),
            "name": tenant_info.get("name", "Unknown"),
            "financial_assessment": self._assess_financial_capability(tenant_info),
            "rental_history": self._evaluate_rental_history(tenant_info),
            "employment_status": self._verify_employment(tenant_info),
            "compatibility": self._assess_tenant_compatibility(tenant_info),
            "risk_factors": [],
            "overall_score": 0,
            "recommendation": ""
        }
        
        # Calculate weighted score
        weights = {
            "financial": 0.4,
            "history": 0.25,
            "employment": 0.25,
            "compatibility": 0.1
        }
        
        scores = {
            "financial": evaluation["financial_assessment"]["score"],
            "history": evaluation["rental_history"]["score"],
            "employment": evaluation["employment_status"]["score"],
            "compatibility": evaluation["compatibility"]["score"]
        }
        
        evaluation["overall_score"] = sum(
            scores[key] * weights[key] for key in weights
        )
        
        # Risk assessment
        risk_factors = []
        if scores["financial"] < 60:
            risk_factors.append("Financial stability concerns")
        if scores["history"] < 60:
            risk_factors.append("Problematic rental history")
        if scores["employment"] < 60:
            risk_factors.append("Employment stability issues")
        
        evaluation["risk_factors"] = risk_factors
        
        # Final recommendation
        if evaluation["overall_score"] >= 80:
            evaluation["recommendation"] = "Strongly Recommended"
        elif evaluation["overall_score"] >= 70:
            evaluation["recommendation"] = "Recommended with standard deposit"
        elif evaluation["overall_score"] >= 60:
            evaluation["recommendation"] = "Consider with increased deposit"
        else:
            evaluation["recommendation"] = "Not recommended"
            
        self.log_interaction("tenant_evaluation", evaluation)
        return evaluation
        
    def _assess_financial_capability(self, tenant_info: Dict) -> Dict:
        """Detailed financial assessment"""
        income = tenant_info.get("profile", {}).get("annual_income", 0)
        desired_rent = tenant_info.get("budget", {}).get("preferred_amount", 0)
        credit_score = tenant_info.get("profile", {}).get("credit_score", 0)
        
        score = 0
        notes = []
        
        # Income ratio assessment
        if income > 0 and desired_rent > 0:
            monthly_income = income / 12
            income_ratio = monthly_income / desired_rent
            if income_ratio >= self.tenant_preferences["min_income_ratio"]:
                score += 40
                notes.append(f"Income ratio {income_ratio:.1f} meets requirements")
            else:
                notes.append(f"Income ratio {income_ratio:.1f} below minimum {self.tenant_preferences['min_income_ratio']}")
        
        # Credit score assessment
        if credit_score >= self.tenant_preferences["min_credit_score"]:
            score += 40
            notes.append("Credit score meets requirements")
        elif credit_score >= self.tenant_preferences["min_credit_score"] - 50:
            score += 20
            notes.append("Credit score marginally acceptable")
        else:
            notes.append("Credit score below requirements")
        
        # Additional financial factors
        if tenant_info.get("profile", {}).get("employment_status") in self.tenant_preferences["preferred_employment_status"]:
            score += 20
            notes.append("Employment status acceptable")
        
        return {
            "score": score,
            "notes": notes,
            "income_ratio": income_ratio if income > 0 and desired_rent > 0 else None,
            "credit_score": credit_score
        }
        
    def make_decision(self, context: Dict) -> Dict:
        """Make data-driven decisions based on context and market conditions"""
        if context["type"] == "rental_inquiry":
            return self._handle_rental_inquiry(context)
        elif context["type"] == "price_negotiation":
            return self._handle_price_negotiation(context)
        elif context["type"] == "application_review":
            return self._handle_application_review(context)
        else:
            return {"action": "need_more_info", "details": "Unrecognized decision context"}
            
    def _handle_rental_inquiry(self, context: Dict) -> Dict:
        """Process rental inquiry with comprehensive evaluation"""
        tenant_info = context["tenant_info"]
        property_id = context["property_id"]
        
        # Evaluate tenant
        evaluation = self.evaluate_tenant(tenant_info)
        
        # Check property availability and suitability
        property_check = self._check_property_suitability(
            property_id,
            tenant_info.get("requirements", {}),
            tenant_info.get("preferences", {})
        )
        
        if evaluation["overall_score"] >= 60 and property_check["suitable"]:
            response = {
                "action": "proceed_with_inquiry",
                "property_id": property_id,
                "requirements": self._get_application_requirements(),
                "viewing_options": self._get_viewing_options(property_id),
                "next_steps": self._generate_next_steps(evaluation["overall_score"]),
                "additional_notes": property_check["notes"]
            }
        else:
            response = {
                "action": "decline_inquiry",
                "reason": "Property not suitable or tenant requirements not met",
                "alternative_suggestions": self._suggest_alternatives(tenant_info)
            }
            
        self.log_interaction("inquiry_response", response)
        return response
        
    def _handle_price_negotiation(self, context: Dict) -> Dict:
        """Handle price negotiation based on market data and property metrics"""
        property_id = context["property_id"]
        offered_price = context["offered_price"]
        market_data = context.get("market_data")
        tenant_evaluation = context.get("tenant_evaluation", {})
        
        property_data = self.properties[property_id]
        current_price = property_data.price["amount"]
        
        # Calculate acceptable price range
        min_acceptable = self._calculate_minimum_acceptable_price(
            current_price,
            market_data,
            tenant_evaluation
        )
        
        if offered_price >= min_acceptable:
            return {
                "action": "accept_offer",
                "property_id": property_id,
                "accepted_price": offered_price,
                "terms": self._generate_lease_terms(offered_price),
                "next_steps": self._generate_acceptance_steps()
            }
        elif offered_price >= min_acceptable * 0.95:
            counter_price = self._calculate_counter_offer(
                offered_price,
                current_price,
                market_data
            )
            return {
                "action": "counter_offer",
                "property_id": property_id,
                "counter_price": counter_price,
                "justification": self._generate_price_justification(counter_price, market_data),
                "negotiation_terms": self._get_negotiation_terms()
            }
        else:
            return {
                "action": "decline_offer",
                "property_id": property_id,
                "reason": "Offer significantly below market value",
                "market_evidence": self._provide_market_evidence(market_data)
            }
            
    def _generate_lease_terms(self, agreed_price: float) -> Dict[str, Any]:
        """Generate comprehensive lease terms"""
        return {
            "lease_duration": self.tenant_preferences["lease_length_preference"],
            "rent_amount": agreed_price,
            "payment_frequency": "monthly",
            "deposit": agreed_price * 2,
            "payment_terms": {
                "due_date": "1st of each month",
                "payment_method": "bank transfer",
                "late_payment_penalties": "3% above base rate"
            },
            "utilities": {
                "tenant_responsible": [
                    "electricity",
                    "gas",
                    "water",
                    "council tax",
                    "internet"
                ],
                "landlord_responsible": [
                    "building insurance",
                    "structural repairs",
                    "common area maintenance"
                ]
            },
            "maintenance": {
                "tenant_responsibilities": "routine maintenance and minor repairs",
                "landlord_responsibilities": "major repairs and structural maintenance",
                "reporting_procedure": "online maintenance portal"
            },
            "special_conditions": self._get_special_conditions()
        }
        
    def process_message(self, message: str, sender: str) -> str:
        """Process received message"""
        self.log_interaction("message_received", {
            "from": sender,
            "content": message
        })
        
        # This will be processed by the autogen LLM, returning intelligent reply
        return message
