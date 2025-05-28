#!/usr/bin/env python3
"""
RentalLatex Basic Usage Demo

Simple demonstration of how to use RentalLatex class to generate rental agreement PDFs
"""

import sys
import os
from datetime import datetime

from app.latex import RentalLatex, RentalInfo


def demo_basic_usage():
    """Demonstrate basic usage of RentalLatex"""
    print("=== Basic RentalLatex Usage Demo ===")
    
    # Rental agreement information
    rental_data = RentalInfo(
        agreement_date='28/05/2025',
        landlord_name='John Smith',
        tenant_name='Alice Johnson',
        property_address='123 Main Street, London SW1A 1AA',
        monthly_rent='£1200',
        security_deposit='£1200',
        start_date='01/06/2025',
        tenancy_end_date='31/05/2026',
        tenancy_duration='12 months',
        signature_mode='image',
        use_generated_signatures=True
    )

    rental_latex = RentalLatex()
    
    # Create output directory
    output_dir = "workspace/latex/demo"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate PDF
    output_file = os.path.join(output_dir, "basic_rental_agreement.pdf")
    
    try:
        result_path = rental_latex.generate_pdf(rental_data, output_file)
        print(f"✓ PDF generated successfully: {result_path}")
        
    except Exception as e:
        print(f"✗ Generation failed: {e}")


def main():
    """Main function - run basic usage demo"""
    print("RentalLatex Basic Usage Demo")
    print("=" * 40)
    
    # Run basic usage demonstration
    demo_basic_usage()
    
    print("\n" + "=" * 40)
    print("Demo complete! Generated PDF is located in workspace/latex/demo/")


if __name__ == "__main__":
    main()
