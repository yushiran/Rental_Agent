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

tools = [retriever_tool, generate_rental_contract]
