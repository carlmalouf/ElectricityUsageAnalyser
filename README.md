# Electricity Usage and Cost Analysis

A Streamlit web application for analyzing electricity meter readings and comparing different electricity plans.

## Features

- 📊 **Interactive Visualizations**: View your electricity readings over time with Plotly charts
- 💰 **Cost Analysis**: Compare current vs. prospective electricity plans
- 📈 **Usage Trends**: Analyze daily usage patterns and statistics
- 🔮 **Annual Projections**: Estimate annual costs based on linear extrapolation of your data

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

Run the Streamlit app:
```bash
streamlit run app.py
```

The application will open in your default web browser.

## Usage

1. **Upload Your Data**: Click the file uploader and select your electricity readings CSV file
2. **View Readings**: Explore your meter readings over time in the "Readings Over Time" tab
3. **Analyze Costs**: 
   - Navigate to the "Cost Analysis" tab
   - Enter your current plan rates in the left column
   - Enter comparison plan rates in the right column
   - View the annual cost estimates and savings
4. **Review Trends**: Check the "Usage Trends" tab for detailed usage statistics

## CSV File Format

Your CSV file should have the following structure:

```csv
Date,Type,Reading,Reading Source
17 Dec 2024,anytime," 66,444 ",bill
17 Dec 2024,controlled load," 79,636 ",bill
17 Dec 2024,solar," 70,660 ",bill
```

### Columns:
- **Date**: Date of the reading (format: "DD Mon YYYY")
- **Type**: Reading type (`anytime`, `controlled load`, or `solar`)
- **Reading**: Meter reading in kWh (commas and spaces are handled automatically)
- **Reading Source**: Source of the reading (`bill` or leave empty for manual)

## Rate Inputs

The application requires the following rate information:

1. **Anytime Rate**: Cost per kWh for standard usage (in cents/kWh)
2. **Controlled Load Rate**: Cost per kWh for controlled load (in cents/kWh)
3. **Solar Feed In**: Credit per kWh for solar exports (in cents/kWh)
4. **Supply Daily Charge**: Daily supply charge (in $/day)
5. **Controlled Load Supply Daily Charge**: Daily charge for controlled load supply (in $/day)

## How Annual Costs are Calculated

1. The app calculates total usage across the entire data period
2. Usage is extrapolated to a full year (365 days) based on daily averages
3. Costs are calculated as:
   - Anytime Cost = Annual Usage × Rate
   - Controlled Load Cost = Annual Usage × Rate
   - Solar Credit = Annual Generation × Rate
   - Supply Charges = (Supply + CL Supply) × 365
   - **Total Annual Cost = Anytime + CL + Supply - Solar**

## Tips

- Include readings from different seasons for more accurate annual projections
- Use bill readings when available for the most accurate data
- Compare multiple plans by adjusting the rates in real-time
- Export your usage statistics for record keeping
