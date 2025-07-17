from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from app.rag import get_retriever
from app.config import config
from app.utils import RentalLatex, RentalInfo
from typing import Dict, Any
import os
from datetime import datetime

retriever = get_retriever(
    embedding_model_id=config.rag.text_embedding_model_id,
    k=config.rag.top_k,
    device=config.rag.device
)

retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_rental_context",
    "Search and return information about rental properties, market data, landlord preferences, or tenant requirements. Use this tool when you need to access rental-related information from the knowledge base.",
)

@tool
def generate_rental_contract(
    agreement_date: str = "",
    landlord_name: str = "",
    tenant_name: str = "", 
    property_address: str = "",
    monthly_rent: str = "",
    security_deposit: str = "",
    start_date: str = "",
    tenancy_end_date: str = "",
    tenancy_duration: str = "",
    output_filename: str = "rental_agreement.pdf"
) -> str:
    """
    Generate a rental agreement PDF contract using LaTeX.
    
    This tool creates a professional rental agreement PDF by filling in the provided 
    rental information into a LaTeX template and compiling it to PDF.
    
    Use this tool when a tenant and landlord have reached an agreement and need to formalize
    the contract. The agent should extract all required information from the conversation 
    history before calling this tool.
    
    Args:
        agreement_date: Date when the agreement is signed (format: DD/MM/YYYY)
        landlord_name: Full name of the landlord
        tenant_name: Full name of the tenant  
        property_address: Complete address of the rental property
        monthly_rent: Monthly rent amount (e.g., "£1200")
        security_deposit: Security deposit amount (e.g., "£1200") 
        start_date: Tenancy start date (format: DD/MM/YYYY)
        tenancy_end_date: Tenancy end date (format: DD/MM/YYYY)
        tenancy_duration: Duration of tenancy (e.g., "12 months")
        output_filename: Name of the output PDF file (default: "rental_agreement.pdf")
        
    Returns:
        str: Success message with the path to the generated PDF file
    """
    # Validate required parameters
    required_params = {
        "landlord_name": landlord_name,
        "tenant_name": tenant_name,
        "property_address": property_address,
        "monthly_rent": monthly_rent,
    }
    
    missing_params = [key for key, value in required_params.items() if not value]
    if missing_params:
        return f"❌ Cannot generate contract: Missing required information: {', '.join(missing_params)}"
    
    # Set default values for optional parameters
    if not agreement_date:
        agreement_date = datetime.now().strftime("%d/%m/%Y")
    
    if not security_deposit:
        # Default security deposit to 5 weeks rent if not specified
        try:
            rent_value = monthly_rent.replace("£", "").replace(",", "")
            monthly_rent_value = float(rent_value)
            security_deposit = f"£{(monthly_rent_value * 5/4.3):.2f}"
        except:
            security_deposit = monthly_rent  # Fallback to same as monthly rent
            
    if not start_date:
        # Default to first day of next month
        next_month = datetime.now().replace(day=28) + datetime.timedelta(days=4)
        start_date = next_month.replace(day=1).strftime("%d/%m/%Y")
    
    if not tenancy_duration:
        tenancy_duration = "12 months"
        
    if not tenancy_end_date:
        # Try to calculate end date from start date and duration
        try:
            start = datetime.strptime(start_date, "%d/%m/%Y")
            months = int(tenancy_duration.split()[0])
            end = start.replace(month=((start.month - 1 + months) % 12) + 1, 
                              year=start.year + ((start.month - 1 + months) // 12))
            tenancy_end_date = end.strftime("%d/%m/%Y")
        except:
            # Fallback to one year later
            end_date = datetime.now().replace(year=datetime.now().year + 1)
            tenancy_end_date = end_date.strftime("%d/%m/%Y")
    
    try:
        # Create rental information object
        rental_info = RentalInfo(
            agreement_date=agreement_date,
            landlord_name=landlord_name,
            tenant_name=tenant_name,
            property_address=property_address,
            monthly_rent=monthly_rent,
            security_deposit=security_deposit,
            start_date=start_date,
            tenancy_end_date=tenancy_end_date,
            tenancy_duration=tenancy_duration,
            signature_mode="image",
            use_generated_signatures=True
        )
        
        # Initialize LaTeX generator
        latex_generator = RentalLatex()
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(latex_generator.workspace_dir, "generated_contracts")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename with timestamp if default is used
        if output_filename == "rental_agreement.pdf":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tenant_id = tenant_name.lower().replace(" ", "_")
            output_filename = f"rental_agreement_{tenant_id}_{timestamp}.pdf"
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Generate the PDF
        result_path = latex_generator.generate_pdf(rental_info, output_path)
        
        return f"✅ Rental agreement PDF successfully generated at: {result_path}\n\nThe contract includes:\n- Landlord: {landlord_name}\n- Tenant: {tenant_name}\n- Property: {property_address}\n- Monthly Rent: {monthly_rent}\n- Start Date: {start_date}\n- Duration: {tenancy_duration}"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Failed to generate rental agreement PDF: {str(e)}\n\nError details: {error_details}"

@tool
def analyze_rental_market_info(
    location: str = "",
    property_type: str = "",
    bedrooms: int = 0,
    budget_min: float = 0,
    budget_max: float = 0,
    analysis_type: str = "comprehensive"
) -> str:
    """
    Analyze current rental market information for a specific location and property criteria.
    
    This tool provides comprehensive rental market analysis including average prices,
    market trends, availability statistics, and competitive insights. Use this tool
    when you need to understand market conditions for negotiation strategy or 
    property evaluation.
    
    Args:
        location: Target location/district for market analysis (e.g., "Camden", "Zone 1")
        property_type: Type of property to analyze (e.g., "apartment", "house", "studio") 
        bedrooms: Number of bedrooms to focus analysis on (0 = any)
        budget_min: Minimum budget range for analysis (0 = no minimum)
        budget_max: Maximum budget range for analysis (0 = no maximum)
        analysis_type: Type of analysis ("comprehensive", "pricing", "availability", "trends")
        
    Returns:
        str: Detailed market analysis report with pricing, trends, and recommendations
    """
    try:
        from app.mongo import MongoClientWrapper
        from app.agents.models import PropertyModel
        from statistics import mean, median
        from collections import defaultdict, Counter
        
        # Initialize database connection
        properties_db = MongoClientWrapper(model=PropertyModel, collection_name="properties")
        
        # Build query filter
        query_filter = {}
        
        if location:
            # Case-insensitive location matching
            query_filter["district"] = {"$regex": location, "$options": "i"}
            
        if property_type:
            query_filter["property_type"] = {"$regex": property_type, "$options": "i"}
            
        if bedrooms > 0:
            query_filter["bedrooms"] = bedrooms
            
        if budget_min > 0 or budget_max > 0:
            price_filter = {}
            if budget_min > 0:
                price_filter["$gte"] = budget_min
            if budget_max > 0:
                price_filter["$lte"] = budget_max
            query_filter["monthly_rent"] = price_filter
        
        # Fetch matching properties
        properties = properties_db.fetch_documents(0, query_filter)  # 0 = no limit
        
        if not properties:
            return f"❌ No properties found matching criteria:\n- Location: {location or 'Any'}\n- Type: {property_type or 'Any'}\n- Bedrooms: {bedrooms or 'Any'}\n- Budget: £{budget_min}-£{budget_max or 'unlimited'}"
        
        # Extract data for analysis
        prices = []
        districts = []
        property_types = []
        bedroom_counts = []
        availability_status = []
        amenities_list = []
        
        for prop in properties:
            prop_dict = prop.to_dict() if hasattr(prop, 'to_dict') else prop
            
            prices.append(prop_dict.get("monthly_rent", 0))
            districts.append(prop_dict.get("district", "Unknown"))
            property_types.append(prop_dict.get("property_type", "Unknown"))
            bedroom_counts.append(prop_dict.get("bedrooms", 0))
            
            # Check availability based on rental status
            rental_status = prop_dict.get("rental_status", {})
            is_rented = rental_status.get("is_rented", False) if isinstance(rental_status, dict) else False
            availability_status.append("Available" if not is_rented else "Rented")
            
            # Collect amenities
            amenities = prop_dict.get("amenities", [])
            amenities_list.extend(amenities)
        
        # Calculate statistics
        avg_price = mean(prices) if prices else 0
        median_price = median(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        # Market analysis by type
        district_stats = Counter(districts)
        type_stats = Counter(property_types)
        bedroom_stats = Counter(bedroom_counts)
        availability_stats = Counter(availability_status)
        amenity_stats = Counter(amenities_list)
        
        # Calculate availability rate
        total_properties = len(properties)
        available_properties = availability_stats.get("Available", 0)
        availability_rate = (available_properties / total_properties * 100) if total_properties > 0 else 0
        
        # Generate price insights by bedrooms
        price_by_bedrooms = defaultdict(list)
        for prop in properties:
            prop_dict = prop.to_dict() if hasattr(prop, 'to_dict') else prop
            bedrooms = prop_dict.get("bedrooms", 0)
            price = prop_dict.get("monthly_rent", 0)
            price_by_bedrooms[bedrooms].append(price)
        
        bedroom_price_analysis = {}
        for beds, price_list in price_by_bedrooms.items():
            if price_list:
                bedroom_price_analysis[beds] = {
                    "average": mean(price_list),
                    "median": median(price_list),
                    "min": min(price_list),
                    "max": max(price_list),
                    "count": len(price_list)
                }
        
        # Build comprehensive report
        report = f"""
🏘️ **RENTAL MARKET ANALYSIS REPORT**
📍 **Search Criteria:**
   • Location: {location or 'All areas'}
   • Property Type: {property_type or 'All types'}
   • Bedrooms: {bedrooms or 'Any number'}
   • Budget Range: £{budget_min or 0} - £{budget_max or 'unlimited'}

📊 **MARKET OVERVIEW** ({total_properties} properties analyzed)
   • Average Rent: £{avg_price:.0f}/month
   • Median Rent: £{median_price:.0f}/month
   • Price Range: £{min_price:.0f} - £{max_price:.0f}
   • Availability Rate: {availability_rate:.1f}% ({available_properties}/{total_properties} available)

🏠 **PROPERTY TYPE BREAKDOWN:**"""
        
        for prop_type, count in type_stats.most_common(5):
            percentage = (count / total_properties * 100)
            report += f"\n   • {prop_type}: {count} properties ({percentage:.1f}%)"
        
        report += "\n\n🛏️ **BEDROOM DISTRIBUTION:**"
        for bedrooms, count in sorted(bedroom_stats.items()):
            percentage = (count / total_properties * 100)
            report += f"\n   • {bedrooms} bedroom(s): {count} properties ({percentage:.1f}%)"
        
        if bedroom_price_analysis:
            report += "\n\n💰 **PRICING BY BEDROOMS:**"
            for bedrooms in sorted(bedroom_price_analysis.keys()):
                stats = bedroom_price_analysis[bedrooms]
                report += f"\n   • {bedrooms} bedroom(s): £{stats['average']:.0f} avg (£{stats['min']:.0f}-£{stats['max']:.0f})"
        
        report += "\n\n📍 **TOP LOCATIONS:**"
        for district, count in district_stats.most_common(5):
            percentage = (count / total_properties * 100)
            report += f"\n   • {district}: {count} properties ({percentage:.1f}%)"
        
        if amenity_stats:
            report += "\n\n🎯 **POPULAR AMENITIES:**"
            for amenity, count in amenity_stats.most_common(8):
                percentage = (count / total_properties * 100)
                report += f"\n   • {amenity}: {count} properties ({percentage:.1f}%)"
        
        # Add market insights and recommendations
        report += "\n\n💡 **MARKET INSIGHTS:**"
        
        if availability_rate > 70:
            report += f"\n   • 🟢 High availability ({availability_rate:.1f}%) - Buyer's market"
        elif availability_rate > 40:
            report += f"\n   • 🟡 Moderate availability ({availability_rate:.1f}%) - Balanced market"
        else:
            report += f"\n   • 🔴 Low availability ({availability_rate:.1f}%) - Seller's market"
        
        if avg_price > 0:
            if budget_max > 0:
                if avg_price < budget_max * 0.8:
                    report += "\n   • 💚 Budget is above market average - Good negotiation position"
                elif avg_price < budget_max:
                    report += "\n   • 🟡 Budget aligns with market - Standard negotiation expected"
                else:
                    report += "\n   • 🔴 Budget below market average - Limited options"
        
        # Add negotiation recommendations
        report += "\n\n🎯 **NEGOTIATION STRATEGY:**"
        if availability_rate > 60:
            report += "\n   • Leverage high availability for rent reductions"
            report += "\n   • Request additional amenities or flexible terms"
        else:
            report += "\n   • Act quickly on suitable properties"
            report += "\n   • Be prepared to meet asking price"
        
        if analysis_type == "pricing":
            # Focus on price analysis only
            price_summary = "\n\n📈 **DETAILED PRICING ANALYSIS:**\n"
            price_summary += f"   • Market Average: £{avg_price:.0f}/month\n"
            price_summary += f"   • Market Median: £{median_price:.0f}/month\n"
            price_summary += f"   • Price Variance: {((max_price - min_price) / avg_price * 100):.1f}%\n"
            return price_summary
        
        elif analysis_type == "availability":
            # Focus on availability only
            return f"🏠 **AVAILABILITY ANALYSIS:**\n   • {available_properties} out of {total_properties} properties available ({availability_rate:.1f}%)\n   • Market Status: {'Buyer\'s Market' if availability_rate > 60 else 'Seller\'s Market' if availability_rate < 40 else 'Balanced Market'}"
        
        elif analysis_type == "trends":
            # Focus on trends (simplified for now)
            return f"📈 **MARKET TRENDS:**\n   • Average rent in {location or 'analyzed area'}: £{avg_price:.0f}\n   • Most common property type: {type_stats.most_common(1)[0][0] if type_stats else 'N/A'}\n   • Availability trend: {availability_rate:.1f}% available"
        
        return report
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Failed to analyze rental market: {str(e)}\n\nError details: {error_details}"
        
tools = [retriever_tool, generate_rental_contract, analyze_rental_market_info]
