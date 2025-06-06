from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from app.rag import get_retriever
from app.config import config
from app.latex import RentalLatex, RentalInfo
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
            output_filename = f"rental_agreement_{timestamp}.pdf"
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Generate the PDF
        result_path = latex_generator.generate_pdf(rental_info, output_path)
        
        return f"✅ Rental agreement PDF successfully generated at: {result_path}"
        
    except Exception as e:
        return f"❌ Failed to generate rental agreement PDF: {str(e)}"

tools = [retriever_tool, generate_rental_contract]
