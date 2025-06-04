import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
from shapely.geometry import Point

from app.raw_data import get_rightmove_data
from app.config import config
from app.utils import SCIPlotStyle

@dataclass
class ProcessedRentalProperty:
    """Processed rental property data structure"""
    bathrooms: int
    bedrooms: int
    customer: Dict[str, Any]
    display_address: str
    formatted_branch_name: str
    property_id: int
    location: Dict[str, float]
    price: Dict[str, Any]
    property_images: Dict[str, Any]
    property_sub_type: str
    property_type_full_description: str
    summary: str


class RentalDataset:
    """
    A class to manage rental property dataset with automatic loading and processing
    """
    
    def __init__(self):
        """Initialize the RentalDataset with configuration from config"""
        raw_rental_data_api = config.raw_rental_data_api
        if not raw_rental_data_api:
            raise ValueError("Raw rental data API configuration not found")
        
        self.dataset_path = Path(raw_rental_data_api.data_path)
        self.raw_dataset_path = self.dataset_path / "raw" / "rightmove_data.json"
        self.processed_dataset_path = self.dataset_path / "processed" / "rightmove_data_processed.json"
        self.analysis_results_path = self.dataset_path / "analysis" 
        
        # Ensure directories exist
        self.raw_dataset_path.parent.mkdir(parents=True, exist_ok=True)
        self.processed_dataset_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize data structures
        self.raw_data: Optional[Dict[str, Any]] = None
        self.processed_data: Optional[List[ProcessedRentalProperty]] = None
        
        # Load data with automatic fallback
        self._load_data()
    
    def _load_data(self):
        """Load data with automatic fallback: local files -> API -> processing"""
        # Try to load processed data first
        if self.processed_dataset_path.exists():
            try:
                self._load_processed_data()
                return
            except Exception as e:
                print(f"Failed to load processed data: {e}")
        
        # Try to load raw data
        if self.raw_dataset_path.exists():
            try:
                self._load_raw_data()
                self._process_raw_data()
                self._save_processed_data()
                return
            except Exception as e:
                print(f"Failed to load raw data: {e}")
        
        # Fetch from API as last resort
        print("No local data found. Fetching from API...")
        self._fetch_from_api()
        self._load_raw_data()
        self._process_raw_data()
        self._save_processed_data()
    
    def _load_raw_data(self):
        """Load raw data from JSON file"""
        with open(self.raw_dataset_path, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)
    
    def _load_processed_data(self):
        """Load processed data from JSON file"""
        with open(self.processed_dataset_path, 'r', encoding='utf-8') as f:
            processed_json = json.load(f)
            self.processed_data = [
                ProcessedRentalProperty(**item) for item in processed_json
            ]
    
    def _fetch_from_api(self):
        """Fetch data from API using the existing function"""
        try:
            get_rightmove_data()
            print("Data successfully fetched from API")
        except Exception as e:
            raise Exception(f"Failed to fetch data from API: {e}")
    
    def _process_raw_data(self):
        """Process raw data and extract only the required attributes"""
        if not self.raw_data:
            raise ValueError("No raw data available to process")
        
        processed_properties = []
        raw_properties = self.raw_data.get('data', [])
        
        for property_data in raw_properties:
            try:
                processed_property = ProcessedRentalProperty(
                    bathrooms=property_data.get('bathrooms', 0),
                    bedrooms=property_data.get('bedrooms', 0),
                    customer=property_data.get('customer', {}),
                    display_address=property_data.get('displayAddress', ''),
                    formatted_branch_name=property_data.get('formattedBranchName', ''),
                    property_id=property_data.get('id', 0),
                    location=property_data.get('location', {}),
                    price=property_data.get('price', {}),
                    property_images=property_data.get('propertyImages', {}),
                    property_sub_type=property_data.get('propertySubType', ''),
                    property_type_full_description=property_data.get('propertyTypeFullDescription', ''),
                    summary=property_data.get('summary', '')
                )
                processed_properties.append(processed_property)
            except Exception as e:
                print(f"Error processing property {property_data.get('id', 'unknown')}: {e}")
                continue
        
        self.processed_data = processed_properties
        print(f"Processed {len(processed_properties)} properties")
    
    def _save_processed_data(self):
        """Save processed data to JSON file"""
        if not self.processed_data:
            raise ValueError("No processed data to save")
        
        # Convert dataclass objects to dictionaries
        processed_json = [
            {
                'bathrooms': prop.bathrooms,
                'bedrooms': prop.bedrooms,
                'customer': prop.customer,
                'display_address': prop.display_address,
                'formatted_branch_name': prop.formatted_branch_name,
                'property_id': prop.property_id,
                'location': prop.location,
                'price': prop.price,
                'property_images': prop.property_images,
                'property_sub_type': prop.property_sub_type,
                'property_type_full_description': prop.property_type_full_description,
                'summary': prop.summary
            }
            for prop in self.processed_data
        ]
        
        with open(self.processed_dataset_path, 'w', encoding='utf-8') as f:
            json.dump(processed_json, f, indent=4, ensure_ascii=False)
        
        print(f"Processed data saved to {self.processed_dataset_path}")
    
    def get_data(self) -> List[ProcessedRentalProperty]:
        """Get the processed rental data"""
        if self.processed_data is None:
            raise ValueError("No processed data available")
        return self.processed_data
    
    def get_raw_data(self) -> Optional[Dict[str, Any]]:
        """Get the raw rental data"""
        return self.raw_data
    
    def refresh_data(self):
        """Force refresh data from API"""
        print("Refreshing data from API...")
        self._fetch_from_api()
        self._load_raw_data()
        self._process_raw_data()
        self._save_processed_data()
    
    def filter_by_bedrooms(self, min_bedrooms: int, max_bedrooms: Optional[int] = None) -> List[ProcessedRentalProperty]:
        """Filter properties by number of bedrooms"""
        if not self.processed_data:
            return []
        
        filtered = [prop for prop in self.processed_data if prop.bedrooms >= min_bedrooms]
        if max_bedrooms:
            filtered = [prop for prop in filtered if prop.bedrooms <= max_bedrooms]
        return filtered
    
    def filter_by_price_range(self, min_price: float, max_price: float) -> List[ProcessedRentalProperty]:
        """Filter properties by price range"""
        if not self.processed_data:
            return []
        
        filtered = []
        for prop in self.processed_data:
            price_amount = prop.price.get('amount', 0)
            if min_price <= price_amount <= max_price:
                filtered.append(prop)
        return filtered
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of the dataset"""
        if not self.processed_data:
            return {}
        
        total_properties = len(self.processed_data)
        prices = [prop.price.get('amount', 0) for prop in self.processed_data if prop.price.get('amount', 0) > 0]
        bedrooms = [prop.bedrooms for prop in self.processed_data]
        
        return {
            'total_properties': total_properties,
            'price_stats': {
                'min': min(prices) if prices else 0,
                'max': max(prices) if prices else 0,
                'avg': sum(prices) / len(prices) if prices else 0
            },
            'bedroom_distribution': {
                str(i): bedrooms.count(i) for i in range(0, max(bedrooms) + 1) if bedrooms.count(i) > 0
            }
        }
    
    def _to_dataframe(self) -> pd.DataFrame:
        """Convert processed data to pandas DataFrame for analysis"""
        if not self.processed_data:
            raise ValueError("No processed data available")
        
        data_list = []
        for prop in self.processed_data:
            data_dict = {
                'property_id': prop.property_id,
                'bathrooms': prop.bathrooms,
                'bedrooms': prop.bedrooms,
                'display_address': prop.display_address,
                'formatted_branch_name': prop.formatted_branch_name,
                'property_sub_type': prop.property_sub_type,
                'property_type_full_description': prop.property_type_full_description,
                'summary': prop.summary,
                'price_amount': prop.price.get('amount', 0),
                'price_currency': prop.price.get('currency', 'GBP'),
                'location_latitude': prop.location.get('latitude', 0),
                'location_longitude': prop.location.get('longitude', 0),
            }
            data_list.append(data_dict)
        
        return pd.DataFrame(data_list)
    
    def _setup_sci_style(self, color_palette: str = 'colorblind') -> SCIPlotStyle:
        """Setup SCI-standard plotting style using SCIPlotStyle class"""
        return SCIPlotStyle(
            color_palette=color_palette,
            figure_size='double_column',
            dpi=300
        )
    
    def analyze_rental_price_distribution(self, save_plots: bool = True) -> Dict[str, Any]:
        """
        📊 Rental Price Distribution Analysis
        
        Purpose: Analyze overall rental market price concentration and identify outliers
        
        Args:
            save_plots: Whether to save plots to analysis_results_path
            
        Returns:
            Dict containing analysis results and statistics
        """
        if not self.processed_data:
            raise ValueError("No processed data available for analysis")
        
        df = self._to_dataframe()
        # Filter out zero prices
        df_filtered = df[df['price_amount'] > 0].copy()
        
        if df_filtered.empty:
            raise ValueError("No valid price data found")
        
        # Setup SCI style
        sci_style = self._setup_sci_style('vibrant')  # Use vibrant colors instead of default
        
        # Create analysis directory
        analysis_dir = self.analysis_results_path / "price_distribution"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics
        stats = {
            'total_properties': len(df_filtered),
            'price_mean': df_filtered['price_amount'].mean(),
            'price_median': df_filtered['price_amount'].median(),
            'price_std': df_filtered['price_amount'].std(),
            'price_min': df_filtered['price_amount'].min(),
            'price_max': df_filtered['price_amount'].max(),
            'price_q25': df_filtered['price_amount'].quantile(0.25),
            'price_q75': df_filtered['price_amount'].quantile(0.75),
        }
        
        # Identify outliers using IQR method
        Q1 = stats['price_q25']
        Q3 = stats['price_q75']
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = df_filtered[(df_filtered['price_amount'] < lower_bound) | 
                              (df_filtered['price_amount'] > upper_bound)]
        stats['outlier_count'] = len(outliers)
        stats['outlier_percentage'] = (len(outliers) / len(df_filtered)) * 100
        
        if save_plots:
            # Create PDF report
            pdf_path = analysis_dir / "price_distribution_analysis.pdf"
            with PdfPages(str(pdf_path)) as pdf:
                # 1. Histogram of price distribution
                plt.figure(figsize=sci_style.figure_size)
                plt.hist(df_filtered['price_amount'], bins=30, 
                       alpha=0.7, edgecolor='black', linewidth=0.5)
                plt.xlabel('Rental Price (GBP)')
                plt.ylabel('Frequency')
                plt.title('Rental Price Distribution')
                
                # Add statistics text
                stats_text = f'Mean: £{stats["price_mean"]:.0f}\nMedian: £{stats["price_median"]:.0f}\nStd: £{stats["price_std"]:.0f}'
                plt.text(0.75, 0.95, stats_text, transform=plt.gca().transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                sci_style.save_figure(analysis_dir / "histogram", format='pdf')
                pdf.savefig(plt.gcf(), bbox_inches='tight')
                plt.close()
                
                # 2. Box plot by property sub type
                plt.figure(figsize=(12, 6))
                property_types = df_filtered['property_sub_type'].value_counts().head(8).index
                df_top_types = df_filtered[df_filtered['property_sub_type'].isin(property_types)]
                
                sns.boxplot(data=df_top_types, x='property_sub_type', y='price_amount')
                plt.xlabel('Property Sub Type')
                plt.ylabel('Rental Price (GBP)')
                plt.title('Price Distribution by Property Sub Type')
                plt.xticks(rotation=45, ha='right')
                
                sci_style.save_figure(analysis_dir / "boxplot_by_type", format='pdf')
                pdf.savefig(plt.gcf(), bbox_inches='tight')
                plt.close()
                
                # 3. Price outliers visualization
                plt.figure(figsize=(10, 6))
                plt.scatter(range(len(df_filtered)), df_filtered['price_amount'].sort_values(), 
                          alpha=0.6, s=20)
                plt.axhline(y=upper_bound, color='red', linestyle='--', linewidth=1, label=f'Upper Outlier Threshold (£{upper_bound:.0f})')
                plt.axhline(y=lower_bound, color='red', linestyle='--', linewidth=1, label=f'Lower Outlier Threshold (£{lower_bound:.0f})')
                plt.xlabel('Property Index (sorted by price)')
                plt.ylabel('Rental Price (GBP)')
                plt.title('Price Outlier Detection')
                plt.legend()
                
                sci_style.save_figure(analysis_dir / "outlier_detection", format='pdf')
                pdf.savefig(plt.gcf(), bbox_inches='tight')
                plt.close()
            
            print(f"Price distribution analysis saved to {pdf_path}")
        
        return stats
    
    def analyze_geographical_distribution(self, save_plots: bool = True) -> Dict[str, Any]:
        """
        📍 Geographical Distribution Analysis
        
        Purpose: Visualize property locations and analyze geographical clustering
        
        Args:
            save_plots: Whether to save plots and interactive map
            
        Returns:
            Dict containing geographical analysis results
        """
        if not self.processed_data:
            raise ValueError("No processed data available for analysis")
        
        df = self._to_dataframe()
        # Filter out invalid coordinates and prices
        df_filtered = df[(df['location_latitude'] != 0) & 
                        (df['location_longitude'] != 0) & 
                        (df['price_amount'] > 0)].copy()
        
        if df_filtered.empty:
            raise ValueError("No valid geographical data found")
        
        # Setup SCI style
        sci_style = self._setup_sci_style('nature')  # Use nature colors for geo data
        
        # Create analysis directory
        analysis_dir = self.analysis_results_path / "geographical_distribution"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate geographical statistics
        stats = {
            'total_properties_with_location': len(df_filtered),
            'latitude_range': [df_filtered['location_latitude'].min(), df_filtered['location_latitude'].max()],
            'longitude_range': [df_filtered['location_longitude'].min(), df_filtered['location_longitude'].max()],
            'center_lat': df_filtered['location_latitude'].mean(),
            'center_lon': df_filtered['location_longitude'].mean(),
        }
        
        if save_plots:
            # Create interactive map with Folium
            center_lat = stats['center_lat']
            center_lon = stats['center_lon']
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12, 
                          tiles='OpenStreetMap')
            # Add markers for each property
            price_quartiles = pd.qcut(df_filtered['price_amount'], q=4, labels=['Low', 'Medium-Low', 'Medium-High', 'High'])
            color_map = {'Low': 'green', 'Medium-Low': 'blue', 'Medium-High': 'orange', 'High': 'red'}           
            for idx, (_, row) in enumerate(df_filtered.iterrows()):
                color = color_map[str(pd.Series(price_quartiles).iloc[idx])]
                popup_text = f"""
                Price: £{row['price_amount']:.0f} {row['price_currency']}
                Bedrooms: {row['bedrooms']}
                Bathrooms: {row['bathrooms']}
                Type: {row['property_sub_type']}
                Address: {row['display_address']}
                """
                
                folium.Marker(
                    location=[row['location_latitude'], row['location_longitude']],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color=color, icon='home')
                ).add_to(m)
            legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 150px; height: 90px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; ">
            <p style="margin: 10px;"><strong>Price Quartiles</strong></p>
            <p style="margin: 5px;"><i class="fa fa-map-marker" style="color:green"></i> Low</p>
            <p style="margin: 5px;"><i class="fa fa-map-marker" style="color:blue"></i> Medium-Low</p>
            <p style="margin: 5px;"><i class="fa fa-map-marker" style="color:orange"></i> Medium-High</p>
            <p style="margin: 5px;"><i class="fa fa-map-marker" style="color:red"></i> High</p>
            </div>
            '''
            m.get_root().add_child(folium.Element(legend_html))
            map_path = analysis_dir / "rental_properties_map.html"
            m.save(str(map_path))
            
            # 2. 构造 GeoDataFrame（转换为 Web Mercator 坐标系）
            gdf = gpd.GeoDataFrame(
                df_filtered,
                geometry=gpd.points_from_xy(df_filtered['location_longitude'], df_filtered['location_latitude']),
                crs='EPSG:4326'  # 原始为 WGS84 经纬度
            ).to_crs(epsg=3857)  # 转换为 Web Mercator 适配底图
            fig, ax = plt.subplots(figsize=(12, 10))
            gdf.plot(
                ax=ax,
                column='price_amount',  # 用价格着色
                cmap='viridis',
                markersize=50,
                alpha=0.7,
                legend=True,
                legend_kwds={'label': 'Price (GBP)', 'shrink': 0.8}
            )
            try:
                ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf.crs, zoom='auto')  # type: ignore
            except Exception as e:
                print(f"Warning: Could not add basemap due to zoom level issue: {e}")
                try:
                    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf.crs, zoom=12)  # type: ignore
                except Exception as e2:
                    print(f"Warning: Could not add basemap with manual zoom: {e2}")
            
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_title('Property Locations by Price')
            ax.ticklabel_format(style='sci', axis='both', scilimits=(0,0))
            scatter_pdf_path = analysis_dir / "property_locations_map_overlay.pdf"
            sci_style.save_figure(scatter_pdf_path.with_suffix(''), format='pdf')
            plt.close()
            print(f"Property map overlay plot saved to {scatter_pdf_path}")
            
            # 3. Price distribution by geographical regions (simplified)
            # Divide into quadrants based on center
            df_filtered['region'] = 'Unknown'
            df_filtered.loc[(df_filtered['location_latitude'] >= center_lat) & 
                           (df_filtered['location_longitude'] >= center_lon), 'region'] = 'Northeast'
            df_filtered.loc[(df_filtered['location_latitude'] >= center_lat) & 
                           (df_filtered['location_longitude'] < center_lon), 'region'] = 'Northwest'
            df_filtered.loc[(df_filtered['location_latitude'] < center_lat) & 
                           (df_filtered['location_longitude'] >= center_lon), 'region'] = 'Southeast'
            df_filtered.loc[(df_filtered['location_latitude'] < center_lat) & 
                           (df_filtered['location_longitude'] < center_lon), 'region'] = 'Southwest'
            
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.boxplot(data=df_filtered, x='region', y='price_amount', ax=ax)
            ax.set_xlabel('Geographical Region')
            ax.set_ylabel('Rental Price (GBP)')
            ax.set_title('Price Distribution by Geographical Region')
            plt.xticks(rotation=45)
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save second plot as separate PDF
            region_pdf_path = analysis_dir / "price_by_region_boxplot.pdf"
            sci_style.save_figure(region_pdf_path.with_suffix(''), format='pdf')
            plt.close()
            
            print(f"Property locations scatter plot saved to {scatter_pdf_path}")
            print(f"Price by region boxplot saved to {region_pdf_path}")
            print(f"Interactive map saved to {map_path}")
        
        return stats
    
    def analyze_property_type_vs_price(self, save_plots: bool = True) -> Dict[str, Any]:
        """
        🏠 Property Type vs Price Analysis
        
        Purpose: Analyze the relationship between property characteristics and price
        
        Args:
            save_plots: Whether to save plots to analysis_results_path
            
        Returns:
            Dict containing property type analysis results
        """
        if not self.processed_data:
            raise ValueError("No processed data available for analysis")
        
        df = self._to_dataframe()
        # Filter out zero prices
        df_filtered = df[df['price_amount'] > 0].copy()
        
        if df_filtered.empty:
            raise ValueError("No valid price data found")
        
        # Setup SCI style
        sci_style = self._setup_sci_style('science')  # Use science colors for property analysis
        
        # Create analysis directory
        analysis_dir = self.analysis_results_path / "property_type_vs_price"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate correlations and statistics
        stats = {
            'bedrooms_price_correlation': df_filtered['bedrooms'].corr(df_filtered['price_amount']),
            'bathrooms_price_correlation': df_filtered['bathrooms'].corr(df_filtered['price_amount']),
            'avg_price_by_bedrooms': df_filtered.groupby('bedrooms')['price_amount'].agg(['mean', 'count']).to_dict(),
            'avg_price_by_bathrooms': df_filtered.groupby('bathrooms')['price_amount'].agg(['mean', 'count']).to_dict(),
            'avg_price_by_property_type': df_filtered.groupby('property_sub_type')['price_amount'].agg(['mean', 'count']).to_dict(),
        }
        
        if save_plots:
            pdf_path = analysis_dir / "property_type_vs_price_analysis.pdf"
            with PdfPages(str(pdf_path)) as pdf:
                # 1. Box plot: bedrooms vs price
                fig, ax = plt.subplots(figsize=(10, 6))
                bedroom_counts = df_filtered['bedrooms'].value_counts()
                valid_bedrooms = bedroom_counts[bedroom_counts >= 5].index  # Only show categories with >= 5 properties
                df_bedrooms = df_filtered[df_filtered['bedrooms'].isin(valid_bedrooms)]
                
                sns.boxplot(data=df_bedrooms, x='bedrooms', y='price_amount', ax=ax)
                ax.set_xlabel('Number of Bedrooms')
                ax.set_ylabel('Rental Price (GBP)')
                ax.set_title('Price Distribution by Number of Bedrooms')
                ax.grid(True, alpha=0.3)
                
                # Add sample size annotations
                for i, bedroom in enumerate(sorted(valid_bedrooms)):
                    count = bedroom_counts[bedroom]
                    ax.text(i, ax.get_ylim()[1]*0.95, f'n={count}', ha='center', va='top', fontsize=8)
                
                plt.tight_layout()
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()
                
                # 2. Scatter plot: bedrooms vs price with bathrooms as size
                fig, ax = plt.subplots(figsize=(10, 6))
                scatter = ax.scatter(df_filtered['bedrooms'], df_filtered['price_amount'], 
                                   s=df_filtered['bathrooms']*50, alpha=0.6)
                ax.set_xlabel('Number of Bedrooms')
                ax.set_ylabel('Rental Price (GBP)')
                ax.set_title('Price vs Bedrooms (Bubble size = Bathrooms)')
                ax.grid(True, alpha=0.3)
                
                # Add correlation text
                corr_text = f'Correlation (Bedrooms-Price): {stats["bedrooms_price_correlation"]:.3f}\nCorrelation (Bathrooms-Price): {stats["bathrooms_price_correlation"]:.3f}'
                ax.text(0.05, 0.95, corr_text, transform=ax.transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                plt.tight_layout()
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()
                
                # 3. Box plot: property sub type vs price (top categories only)
                fig, ax = plt.subplots(figsize=(12, 6))
                property_counts = df_filtered['property_sub_type'].value_counts()
                top_property_types = property_counts.head(8).index
                df_top_properties = df_filtered[df_filtered['property_sub_type'].isin(top_property_types)]
                
                sns.boxplot(data=df_top_properties, x='property_sub_type', y='price_amount', ax=ax)
                ax.set_xlabel('Property Sub Type')
                ax.set_ylabel('Rental Price (GBP)')
                ax.set_title('Price Distribution by Property Sub Type (Top 8 Categories)')
                plt.xticks(rotation=45, ha='right')
                ax.grid(True, alpha=0.3)
                
                # Add sample size annotations
                for i, prop_type in enumerate(top_property_types):
                    count = property_counts[prop_type]
                    ax.text(i, ax.get_ylim()[1]*0.95, f'n={count}', ha='center', va='top', fontsize=8)
                
                plt.tight_layout()
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()
                
                # 4. Average price by bedrooms (bar chart)
                fig, ax = plt.subplots(figsize=(8, 6))
                bedroom_avg = df_filtered.groupby('bedrooms')['price_amount'].mean().reset_index()
                bedroom_avg = bedroom_avg[bedroom_avg['bedrooms'] <= 6]  # Limit to reasonable bedroom counts
                
                bars = ax.bar(bedroom_avg['bedrooms'], bedroom_avg['price_amount'], 
                             alpha=0.7, edgecolor='black', linewidth=0.5)
                ax.set_xlabel('Number of Bedrooms')
                ax.set_ylabel('Average Rental Price (GBP)')
                ax.set_title('Average Price by Number of Bedrooms')
                ax.grid(True, alpha=0.3, axis='y')
                
                # Add value labels on bars
                for bar, value in zip(bars, bedroom_avg['price_amount']):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + value*0.01,
                           f'£{value:.0f}', ha='center', va='bottom', fontsize=9)
                
                plt.tight_layout()
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()
            
            print(f"Property type vs price analysis saved to {pdf_path}")
        
        return stats
    
    def run_comprehensive_analysis(self, save_plots: bool = True) -> Dict[str, Any]:
        """
        Run all three analyses and generate a comprehensive report
        
        Args:
            save_plots: Whether to save all plots and reports
            
        Returns:
            Dict containing all analysis results
        """
        print("Starting comprehensive rental market analysis...")
        
        # Ensure analysis directory exists
        self.analysis_results_path.mkdir(parents=True, exist_ok=True)
        
        # Run all analyses
        try:
            print("1/3 Analyzing rental price distribution...")
            price_analysis = self.analyze_rental_price_distribution(save_plots)
            
            print("2/3 Analyzing geographical distribution...")
            geo_analysis = self.analyze_geographical_distribution(save_plots)
            
            print("3/3 Analyzing property type vs price relationship...")
            property_analysis = self.analyze_property_type_vs_price(save_plots)
            
            # Combine all results
            comprehensive_results = {
                'analysis_date': pd.Timestamp.now().isoformat(),
                'total_properties_analyzed': len(self.processed_data) if self.processed_data else 0,
                'price_distribution_analysis': price_analysis,
                'geographical_distribution_analysis': geo_analysis,
                'property_type_vs_price_analysis': property_analysis
            }
            
            if save_plots:
                # Save comprehensive results as JSON
                results_path = self.analysis_results_path / "comprehensive_analysis_results.json"
                with open(results_path, 'w', encoding='utf-8') as f:
                    json.dump(comprehensive_results, f, indent=4, ensure_ascii=False, default=str)
                
                print(f"Comprehensive analysis completed and saved to {self.analysis_results_path}")
                print(f"Results summary saved to {results_path}")
            
            return comprehensive_results
            
        except Exception as e:
            print(f"Error during comprehensive analysis: {e}")
            raise