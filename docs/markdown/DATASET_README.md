# 🏠 Rental Dataset Documentation

## UK Rental Property Market Dataset

This dataset contains comprehensive rental property information collected from the UK rental market through the Rightmove API.

## 📊 Dataset Overview

- **Data Source**: Rightmove API (Live Market Data)
- **Geographic Coverage**: London and surrounding areas
- **Total Properties**: 154 rental properties
- **Property Types**: Apartments, Houses, Studios, Shared Properties
- **Data Format**: JSON (Raw), Processed JSON, Analysis Reports (PDF)
- **Last Updated**: May 28, 2025

## 📋 Dataset Schema

### Basic Property Information

```json
{
  "property_id": 123456789,
  "bedrooms": 2,
  "bathrooms": 1,
  "display_address": "Camden, London NW1",
  "property_sub_type": "Flat",
  "price": {
    "amount": 2500,
    "currency": "GBP",
    "period": "monthly"
  },
  "location": {
    "latitude": 51.5394,
    "longitude": -0.1430
  },
  "summary": "Modern 2-bedroom flat in Camden..."
}
```

## 📁 Directory Structure

```text
dataset/
├── README.md                          # This documentation
└── rent_cast_data/                    # Main dataset directory
    ├── raw/                           # Raw API responses
    │   └── rightmove_data.json       # Original API data
    ├── processed/                     # Cleaned and structured data
    │   └── rightmove_data_processed.json
    └── analysis/                      # Analysis results
        ├── comprehensive_analysis_results.json
        ├── price_distribution/
        │   ├── price_distribution_analysis.pdf
        │   ├── histogram.pdf
        │   ├── boxplot_by_type.pdf
        │   └── outlier_detection.pdf
        ├── geographical_distribution/
        │   ├── geographical_distribution_analysis.pdf
        │   └── rental_properties_map.html
        └── property_type_vs_price/
            └── property_type_vs_price_analysis.pdf
```

## 🔍 Data Analysis Results

### 💰 Price Distribution Analysis

**Key Price Statistics:**

```text
Average Rental Price: £1,969 per month
Median Rental Price: £1,838 per month
Price Range: £340 - £7,250 per month
Standard Deviation: £1,182

Quartile Analysis:
Q1 (25th percentile): £901
Q2 (50th percentile): £1,838
Q3 (75th percentile): £2,588
```

**Price Insights:**

- Market Balance: The median (£1,838) is close to the mean (£1,969), indicating a relatively balanced market
- Affordability Range: 25% of properties are priced below £901/month
- Premium Market: Top 25% of properties exceed £2,588/month
- Outlier Detection: Only 0.6% of properties are statistical outliers

### 📍 Geographic Distribution Analysis

**Geographic Coverage:**

```text
Latitude Range: 51.458° N to 51.614° N
Longitude Range: -0.274° W to 0.080° E
Market Center: (51.5183° N, -0.1093° W)
```

**Geographic Insights:**

- Central Focus: Properties cluster around Central London (Camden/Bloomsbury area)
- Coverage Area: Spans from West London to East London
- North-South Range: Approximately 17.3km
- East-West Range: Approximately 28.1km

### 🏠 Property Type vs Price Analysis

**Feature-Price Correlations:**

```text
Bedroom-Price Correlation: 0.382 (moderate positive)
Bathroom-Price Correlation: 0.326 (moderate positive)
```

**Average Prices by Bedroom Count:**

```text
Studio (0 bed): £1,339/month (28 properties)
1 Bedroom: £1,656/month (37 properties)  
2 Bedroom: £2,198/month (38 properties)
3 Bedroom: £1,972/month (31 properties)
4 Bedroom: £2,913/month (16 properties)
5 Bedroom: £2,900/month (2 properties)
6+ Bedroom: £4,950/month (2 properties)
```

**Average Prices by Property Type:**

```text
House Share: £788/month (most affordable)
Flat Share: £1,000/month
Studio: £1,493/month
Flat: £1,840/month (most common: 70 properties)
Apartment: £2,087/month (second most common: 51 properties)
Maisonette: £2,077/month
Terraced: £3,150/month
House: £3,300/month
Town House: £3,700/month
Semi-Detached: £4,000/month (premium segment)
```

### 📈 Market Insights

**Market Segmentation:**

- **Budget Segment** (< £1,200): Studios and shared accommodations
- **Mid-Market** (£1,200 - £2,500): 1-2 bedroom flats and apartments
- **Premium Segment** (> £2,500): Houses, large apartments, and luxury properties

**Property Type Distribution:**

- Flats dominate the market (70 properties, 45.5%)
- Apartments are second most common (51 properties, 33.1%)
- Studios provide affordable options (15 properties, 9.7%)
- Houses represent premium segment (small count, high prices)

## 📊 Available Visualizations

The dataset generates comprehensive visualizations saved in the `analysis/` directory:

### Price Distribution Analysis

- `histogram.pdf` - Rental price distribution histogram
- `boxplot_by_type.pdf` - Property type price comparison
- `outlier_detection.pdf` - Statistical outlier analysis
- `price_distribution_analysis.pdf` - Complete price analysis report

### Geographic Distribution Analysis

- `rental_properties_map.html` - Interactive property map
- `geographical_distribution_analysis.pdf` - Geographic analysis report

### Property Type vs Price Analysis

- `property_type_vs_price_analysis.pdf` - Feature correlation analysis

## 📝 Data Limitations

1. **Geographic Scope**: Currently focused on London and surrounding areas
2. **Temporal Coverage**: Snapshot data (not historical trends)
3. **Property Types**: Limited to rental properties only
4. **API Constraints**: Subject to Rightmove API rate limits

---

**Last Updated**: May 28, 2025  
**Dataset Version**: 1.0  
**Maintainer**: Rental Agent Project Team