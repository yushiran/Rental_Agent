from app.raw_data import get_rightmove_data, RentalDataset


if __name__ == "__main__":
    dataset = RentalDataset()
    print("Dataset initialized successfully!")
    
    # Print summary statistics
    stats = dataset.get_summary_stats()
    print(f"Dataset summary: {stats}")

    # Example usage
    data = dataset.get_data()
    print(f"Loaded {len(data)} processed properties")
    
    # Example filtering
    two_bedroom_props = dataset.filter_by_bedrooms(2, 2)
    print(f"Found {len(two_bedroom_props)} two-bedroom properties")
    
    print("\n" + "="*60)
    print("RUNNING COMPREHENSIVE RENTAL MARKET ANALYSIS")
    print("="*60)
    
    try:
        # Run comprehensive analysis (includes all three analyses)
        comprehensive_results = dataset.run_comprehensive_analysis(save_plots=True)
        
        print("\n📊 ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"Analysis date: {comprehensive_results['analysis_date']}")
        print(f"Total properties analyzed: {comprehensive_results['total_properties_analyzed']}")
        
        # Display key findings from price distribution analysis
        price_analysis = comprehensive_results['price_distribution_analysis']
        print(f"\n💰 PRICE DISTRIBUTION INSIGHTS:")
        print(f"  • Average rental price: £{price_analysis['price_mean']:.0f}")
        print(f"  • Median rental price: £{price_analysis['price_median']:.0f}")
        print(f"  • Price range: £{price_analysis['price_min']:.0f} - £{price_analysis['price_max']:.0f}")
        print(f"  • Outliers detected: {price_analysis['outlier_count']} ({price_analysis['outlier_percentage']:.1f}%)")
        
        # Display geographical insights
        geo_analysis = comprehensive_results['geographical_distribution_analysis']
        print(f"\n📍 GEOGRAPHICAL INSIGHTS:")
        print(f"  • Properties with location data: {geo_analysis['total_properties_with_location']}")
        print(f"  • Center coordinates: ({geo_analysis['center_lat']:.4f}, {geo_analysis['center_lon']:.4f})")
        
        # Display property type insights
        property_analysis = comprehensive_results['property_type_vs_price_analysis']
        print(f"\n🏠 PROPERTY TYPE INSIGHTS:")
        print(f"  • Bedrooms-Price correlation: {property_analysis['bedrooms_price_correlation']:.3f}")
        print(f"  • Bathrooms-Price correlation: {property_analysis['bathrooms_price_correlation']:.3f}")
        
        print(f"\n📁 All analysis results saved to: {dataset.analysis_results_path}")
        print("   Generated files:")
        print("   • price_distribution/price_distribution_analysis.pdf")
        print("   • geographical_distribution/geographical_distribution_analysis.pdf") 
        print("   • geographical_distribution/rental_properties_map.html")
        print("   • property_type_vs_price/property_type_vs_price_analysis.pdf")
        print("   • comprehensive_analysis_results.json")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print("Trying individual analyses...")
        
        # Try individual analyses if comprehensive fails
        try:
            print("\n1️⃣ Running price distribution analysis...")
            price_results = dataset.analyze_rental_price_distribution(save_plots=True)
            print(f"   ✅ Price analysis completed. Average price: £{price_results['price_mean']:.0f}")
            
            print("\n2️⃣ Running geographical distribution analysis...")
            geo_results = dataset.analyze_geographical_distribution(save_plots=True)
            print(f"   ✅ Geographical analysis completed. {geo_results['total_properties_with_location']} properties mapped.")
            
            print("\n3️⃣ Running property type vs price analysis...")
            property_results = dataset.analyze_property_type_vs_price(save_plots=True)
            print(f"   ✅ Property analysis completed. Bedroom correlation: {property_results['bedrooms_price_correlation']:.3f}")
            
        except Exception as individual_error:
            print(f"❌ Individual analysis also failed: {individual_error}")
    
    print("\n" + "="*60)
    print("ANALYSIS SCRIPT COMPLETED")
    print("="*60)