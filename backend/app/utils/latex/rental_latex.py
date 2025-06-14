"""
Rental LaTeX Generator

This module provides a RentalLatex class that allows users to generate PDF rental agreements
by providing custom values for the template variables.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from app.config import config


@dataclass
class RentalInfo:
    """Data class to hold rental agreement information"""
    agreement_date: str = ""
    landlord_name: str = ""
    tenant_name: str = ""
    property_address: str = ""
    monthly_rent: str = ""
    security_deposit: str = ""
    start_date: str = ""
    tenancy_end_date: str = ""
    tenancy_duration: str = ""
    # Signature configuration
    signature_mode: str = "image"  # Options: 'image' or 'manual'
    landlord_signature_image: str = ""
    tenant_signature_image: str = ""
    use_generated_signatures: bool = True  # Whether to generate signatures using pywhatkit


class RentalLatex:
    """
    A class to generate rental agreement PDFs from LaTeX templates.
    
    This class takes custom rental information and generates a PDF using
    the predefined LaTeX template.
    """
    
    def __init__(self, template_path: Optional[str] = None, workspace_dir: Optional[str] = None):
        """
        Initialize the RentalLatex generator.
        
        Args:
            template_path: Path to the LaTeX template file. If None, uses the default template.
            workspace_dir: Directory to store generated files. If None, uses default workspace.
        """
        self.template_path = template_path or self._get_default_template_path()
        self.template_content = self._load_template()
        self.workspace_dir = workspace_dir or self._get_default_workspace_dir()
        os.makedirs(self.workspace_dir, exist_ok=True)
    
    def _get_default_template_path(self) -> str:
        """Get the default template path"""
        root_dir = config.root_path
        return str(root_dir / "dataset" / "rental_contract_template" / "tenancyAgreement.tex")
    
    def _get_default_workspace_dir(self) -> str:
        """Get the default workspace directory"""
        root_dir = config.root_path
        return str(root_dir / "workspace" / "latex")
    
    def _load_template(self) -> str:
        """Load the LaTeX template content"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {self.template_path}")
        except Exception as e:
            raise Exception(f"Error loading template: {e}")
    
    def _replace_variables(self, content: str, rental_info: RentalInfo) -> str:
        """
        Replace template variables with custom values.
        
        Args:
            content: LaTeX template content
            rental_info: Custom rental information
            
        Returns:
            LaTeX content with replaced variables
        """
        # Create replacement mapping - use format() to avoid f-string escape issues
        replacements = {
            r'\newcommand{\agreementDate}{\underline{\hspace{4cm}}}': 
                '\\newcommand{{\\agreementDate}}{{{}}}'.format(rental_info.agreement_date or "\\underline{\\hspace{4cm}}"),
            r'\newcommand{\landlordName}{Yu}': 
                '\\newcommand{{\\landlordName}}{{{}}}'.format(rental_info.landlord_name or "Yu"),
            r'\newcommand{\tenantName}{Shiran}': 
                '\\newcommand{{\\tenantName}}{{{}}}'.format(rental_info.tenant_name or "Shiran"),
            r'\newcommand{\propertyAddress}{Stapleton House, B607G N7 8FB}': 
                '\\newcommand{{\\propertyAddress}}{{{}}}'.format(rental_info.property_address or "Stapleton House, B607G N7 8FB"),
            r'\newcommand{\monthlyRent}{£150}': 
                '\\newcommand{{\\monthlyRent}}{{{}}}'.format(rental_info.monthly_rent or "£150"),
            r'\newcommand{\securityDeposit}{£100}': 
                '\\newcommand{{\\securityDeposit}}{{{}}}'.format(rental_info.security_deposit or "£100"),
            r'\newcommand{\startDate}{01/05/2025}': 
                '\\newcommand{{\\startDate}}{{{}}}'.format(rental_info.start_date or "01/05/2025"),
            r'\newcommand{\tenancyEndDate}{01/06/2025}': 
                '\\newcommand{{\\tenancyEndDate}}{{{}}}'.format(rental_info.tenancy_end_date or "01/06/2025"),
            r'\newcommand{\tenancyDuration}{1 month}': 
                '\\newcommand{{\\tenancyDuration}}{{{}}}'.format(rental_info.tenancy_duration or "1 month"),
            # Signature configuration replacements
            r'\newcommand{\signatureMode}{image}': 
                '\\newcommand{{\\signatureMode}}{{{}}}'.format(rental_info.signature_mode),
            r'\newcommand{\landlordSignatureImage}{}': 
                '\\newcommand{{\\landlordSignatureImage}}{{{}}}'.format(rental_info.landlord_signature_image),
            r'\newcommand{\tenantSignatureImage}{}': 
                '\\newcommand{{\\tenantSignatureImage}}{{{}}}'.format(rental_info.tenant_signature_image)
        }
        
        # Apply replacements
        for old_value, new_value in replacements.items():
            content = content.replace(old_value, new_value)
        
        return content
    
    def _compile_latex(self, latex_content: str, output_dir: str) -> str:
        """
        Compile LaTeX content to PDF.
        
        Args:
            latex_content: LaTeX content to compile
            output_dir: Directory to store output files
            
        Returns:
            Path to the generated PDF file
        """
        # Create temporary .tex file
        tex_file = os.path.join(output_dir, "rental_agreement.tex")
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        # Compile with xelatex (better unicode support)
        try:
            # First compilation
            subprocess.run([
                'xelatex', 
                '-interaction=nonstopmode',
                '-output-directory=' + output_dir,
                tex_file
            ], check=True, capture_output=True, text=True)
            
            # Second compilation for cross-references
            subprocess.run([
                'xelatex', 
                '-interaction=nonstopmode',
                '-output-directory=' + output_dir,
                tex_file
            ], check=True, capture_output=True, text=True)
            
        except subprocess.CalledProcessError as e:
            # Try with pdflatex as fallback
            try:
                subprocess.run([
                    'pdflatex', 
                    '-interaction=nonstopmode',
                    '-output-directory=' + output_dir,
                    tex_file
                ], check=True, capture_output=True, text=True)
                
                subprocess.run([
                    'pdflatex', 
                    '-interaction=nonstopmode',
                    '-output-directory=' + output_dir,
                    tex_file
                ], check=True, capture_output=True, text=True)
                
            except subprocess.CalledProcessError as fallback_error:
                raise Exception(f"LaTeX compilation failed: {fallback_error}")
        
        pdf_file = os.path.join(output_dir, "rental_agreement.pdf")
        if not os.path.exists(pdf_file):
            raise Exception("PDF generation failed - output file not found")
        
        return pdf_file
    
    def generate_pdf(self, rental_info: RentalInfo, output_path: str) -> str:
        """
        Generate a rental agreement PDF with custom information.
        
        Args:
            rental_info: Custom rental information
            output_path: Path where the PDF should be saved
            
        Returns:
            Path to the generated PDF file
        """
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Use temporary directory for compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate signature images if needed
            if rental_info.signature_mode == "image" and rental_info.use_generated_signatures:
                # Generate landlord signature if name provided and no image path specified
                if rental_info.landlord_name and not rental_info.landlord_signature_image:
                    landlord_sig_path = os.path.join(temp_dir, "landlord_signature.png")
                    self._generate_signature_image(rental_info.landlord_name, landlord_sig_path)
                    rental_info.landlord_signature_image = landlord_sig_path 
                
                # Generate tenant signature if name provided and no image path specified
                if rental_info.tenant_name and not rental_info.tenant_signature_image:
                    tenant_sig_path = os.path.join(temp_dir, "tenant_signature.png")
                    self._generate_signature_image(rental_info.tenant_name, tenant_sig_path)
                    rental_info.tenant_signature_image = tenant_sig_path
            
            # Replace variables in template
            customized_content = self._replace_variables(self.template_content, rental_info)
            
            # Compile to PDF
            temp_pdf = self._compile_latex(customized_content, temp_dir)
            
            # Copy to final destination
            shutil.copy2(temp_pdf, output_path)
        
        return output_path
    
    @staticmethod
    def format_date(date_obj: datetime) -> str:
        """Format a datetime object to DD/MM/YYYY string"""
        return date_obj.strftime("%d/%m/%Y")
    
    @staticmethod
    def format_currency(amount: float, currency: str = "£") -> str:
        """Format a float amount to currency string"""
        return "{}{:.0f}".format(currency, amount)

    def _generate_signature_image(self, name: str, output_path: str) -> str:
        """
        Generate a handwritten signature image using PIL and PatrickHand font.
        
        Args:
            name: The name to convert to signature
            output_path: Path where the signature image should be saved
            
        Returns:
            Path to the generated signature image
        """
        try:
            # Get font path
            root_dir = config.root_path
            font_path = str(root_dir / "dataset" / "rental_contract_template" / "PatrickHand-Regular.ttf")
            
            # Create image with transparent background
            img = Image.new('RGBA', (400, 150), color=(255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Load font
            font = ImageFont.truetype(font_path, size=48)
            
            # Draw text in black
            draw.text((20, 50), name, fill=(0, 0, 0, 255), font=font)
            
            # Crop to content
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            
            # Save as PNG
            img.save(output_path, "PNG")
            
            return output_path
        except Exception as e:
            raise Exception(f"Error generating signature for {name}: {e}")