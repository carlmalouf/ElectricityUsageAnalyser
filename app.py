import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import json
import os

# Page configuration
st.set_page_config(page_title="Electricity Analysis", layout="wide")

st.title("⚡ Electricity Usage and Cost Analysis")

# Load current plan configuration
def load_current_plan():
    config_file = 'current_plan.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Default values if file doesn't exist
        return {
            "anytime_rate": 25.0,
            "controlled_load_rate": 18.0,
            "solar_feed_in": 8.0,
            "supply_daily_charge": 1.20,
            "controlled_load_supply_daily_charge": 0.50
        }

current_plan = load_current_plan()

# Load data
def load_data(file_path):
    df = pd.read_csv(file_path)
    # Clean the data - remove commas and spaces from readings
    df['Reading'] = df['Reading'].str.replace(',', '').str.strip().astype(float)
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    df['Reading Source'] = df['Reading Source'].fillna('manual')
    df = df.sort_values(by='Date', ascending=True)
    return df

# File uploader
uploaded_file = st.file_uploader("Upload your electricity readings CSV file", type=['csv'])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    st.success(f"Loaded {len(df)} readings from {df['Date'].min().strftime('%d %b %Y')} to {df['Date'].max().strftime('%d %b %Y')}")
    
    # Display the data
    with st.expander("📊 View Raw Data"):
        st.dataframe(df, use_container_width=True)
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["📈 Readings Over Time", "💰 Cost Analysis", "📉 Usage Trends"])
    
    with tab1:
        st.subheader("Electricity Readings Over Time")
        
        # Line chart showing all readings with different symbols for bill vs manual
        fig_readings = go.Figure()
        
        # Add traces for each reading type
        for reading_type in df['Type'].unique():
            type_data = df[df['Type'] == reading_type].sort_values('Date')
            
            # Create symbol list based on Reading Source
            symbols = ['triangle-up' if source == 'bill' else 'circle' 
                      for source in type_data['Reading Source']]
            
            fig_readings.add_trace(go.Scatter(
                x=type_data['Date'],
                y=type_data['Reading'],
                mode='lines+markers',
                name=reading_type,
                marker=dict(size=8, symbol=symbols),
                line=dict(width=2)
            ))
        
        fig_readings.update_layout(
            title='Electricity Meter Readings',
            xaxis_title='Date',
            yaxis_title='Meter Reading (kWh)',
            height=500,
            hovermode='x unified'
        )
        st.plotly_chart(fig_readings, use_container_width=True)
        
        # Calculate daily usage distributed across each day in the period
        st.subheader("Total Usage by Month")
        
        daily_usage_data = []
        for reading_type in df['Type'].unique():
            type_df = df[df['Type'] == reading_type].sort_values('Date')
            for i in range(1, len(type_df)):
                start_date = type_df.iloc[i-1]['Date']
                end_date = type_df.iloc[i]['Date']
                days_diff = (end_date - start_date).days
                reading_diff = type_df.iloc[i]['Reading'] - type_df.iloc[i-1]['Reading']
                daily_avg = reading_diff / days_diff if days_diff > 0 else 0
                
                # Create an entry for each day in the period (excluding the end date)
                for day in range(days_diff):
                    current_date = start_date + pd.Timedelta(days=day)
                    daily_usage_data.append({
                        'Date': current_date,
                        'Type': reading_type,
                        'Daily Usage (kWh)': daily_avg
                    })
        
        daily_usage_df = pd.DataFrame(daily_usage_data)
        
        if not daily_usage_df.empty:
            # Add year-month column for grouping
            daily_usage_df['Year-Month'] = daily_usage_df['Date'].dt.to_period('M').astype(str)
            
            # Calculate monthly totals
            monthly_total = daily_usage_df.groupby(['Year-Month', 'Type'])['Daily Usage (kWh)'].sum().reset_index()
            monthly_total.columns = ['Month', 'Type', 'Total Usage (kWh)']
            
            # Sort by month
            monthly_total['Sort_Date'] = pd.to_datetime(monthly_total['Month'])
            monthly_total = monthly_total.sort_values('Sort_Date')
            
            # Calculate number of days in each month from the data
            days_per_month = daily_usage_df.groupby('Year-Month')['Date'].nunique().reset_index()
            days_per_month.columns = ['Month', 'Days']
            monthly_total = monthly_total.merge(days_per_month, on='Month')
            
            # Create the bar chart
            fig_monthly = go.Figure()
            
            # Add bars for each type
            types = monthly_total['Type'].unique()
            for reading_type in types:
                type_data = monthly_total[monthly_total['Type'] == reading_type]
                fig_monthly.add_trace(go.Bar(
                    name=reading_type,
                    x=type_data['Month'],
                    y=type_data['Total Usage (kWh)'],
                    text=type_data['Total Usage (kWh)'].round(0),
                    textposition='auto'
                ))
            
            # Calculate and add monthly cost annotations
            # Group by month to calculate total cost per month
            monthly_costs = []
            for month in monthly_total['Month'].unique():
                month_data = monthly_total[monthly_total['Month'] == month]
                days_in_month = month_data['Days'].iloc[0]
                
                anytime_usage = month_data[month_data['Type'] == 'anytime']['Total Usage (kWh)'].sum()
                cl_usage = month_data[month_data['Type'] == 'controlled load']['Total Usage (kWh)'].sum()
                solar_usage = month_data[month_data['Type'] == 'solar']['Total Usage (kWh)'].sum()
                
                # Use current plan rates from above (will be defined when we're in tab2 context)
                # For now, use the loaded plan values
                anytime_cost = anytime_usage * (current_plan["anytime_rate"] / 100)
                cl_cost = cl_usage * (current_plan["controlled_load_rate"] / 100)
                solar_credit = solar_usage * (current_plan["solar_feed_in"] / 100)
                supply_cost = (current_plan["supply_daily_charge"] + current_plan["controlled_load_supply_daily_charge"]) * days_in_month
                
                total_cost = anytime_cost + cl_cost + supply_cost - solar_credit
                monthly_costs.append({'Month': month, 'Cost': total_cost})
            
            monthly_costs_df = pd.DataFrame(monthly_costs)
            monthly_total = monthly_total.merge(monthly_costs_df, on='Month')
            
            # Add cost annotations above the bars
            max_usage = monthly_total.groupby('Month')['Total Usage (kWh)'].sum().reset_index()
            max_usage = max_usage.merge(monthly_costs_df, on='Month')
            
            for _, row in max_usage.iterrows():
                fig_monthly.add_annotation(
                    x=row['Month'],
                    y=row['Total Usage (kWh)'],
                    text=f"${row['Cost']:.0f}",
                    showarrow=False,
                    yshift=10,
                    font=dict(size=10, color='red', weight='bold')
                )
            
            fig_monthly.update_layout(
                title='Total Usage by Month',
                xaxis_title='Month',
                yaxis_title='Total Usage (kWh)',
                barmode='group',
                height=400
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
    
    with tab2:
        st.subheader("💰 Annual Cost Estimation")
        
        # Create two columns for current and comparison rates
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔵 Current Plan")
            current_anytime = st.number_input("Anytime Rate (c/kWh)", value=current_plan["anytime_rate"], step=0.1, key='curr_anytime')
            current_cl = st.number_input("Controlled Load Rate (c/kWh)", value=current_plan["controlled_load_rate"], step=0.1, key='curr_cl')
            current_solar = st.number_input("Solar Feed In (c/kWh)", value=current_plan["solar_feed_in"], step=0.1, key='curr_solar')
            current_supply = st.number_input("Supply Daily Charge ($/day)", value=current_plan["supply_daily_charge"], step=0.01, key='curr_supply')
            current_cl_supply = st.number_input("Controlled Load Supply Daily Charge ($/day)", value=current_plan["controlled_load_supply_daily_charge"], step=0.01, key='curr_cl_supply')
        
        with col2:
            st.markdown("#### 🟢 Comparison Plan")
            comp_anytime = st.number_input("Anytime Rate (c/kWh)", value=23.0, step=0.1, key='comp_anytime')
            comp_cl = st.number_input("Controlled Load Rate (c/kWh)", value=17.0, step=0.1, key='comp_cl')
            comp_solar = st.number_input("Solar Feed In (c/kWh)", value=10.0, step=0.1, key='comp_solar')
            comp_supply = st.number_input("Supply Daily Charge ($/day)", value=1.10, step=0.01, key='comp_supply')
            comp_cl_supply = st.number_input("Controlled Load Supply Daily Charge ($/day)", value=0.45, step=0.01, key='comp_cl_supply')
        
        st.markdown("---")
        
        # Calculate annual usage based on linear extrapolation
        def calculate_annual_costs(anytime_rate, cl_rate, solar_rate, supply_charge, cl_supply_charge):
            # Get the date range with data
            min_date = df['Date'].min()
            max_date = df['Date'].max()
            days_in_data = (max_date - min_date).days
            
            if days_in_data == 0:
                return None
            
            annual_usage = {}
            for reading_type in df['Type'].unique():
                type_df = df[df['Type'] == reading_type].sort_values('Date')
                if len(type_df) >= 2:
                    # Calculate total usage across the entire period
                    total_usage = type_df.iloc[-1]['Reading'] - type_df.iloc[0]['Reading']
                    # Extrapolate to annual usage
                    annual_usage[reading_type] = (total_usage / days_in_data) * 365
            
            # Calculate costs (rates are in c/kWh, convert to $/kWh)
            anytime_cost = annual_usage.get('anytime', 0) * (anytime_rate / 100)
            cl_cost = annual_usage.get('controlled load', 0) * (cl_rate / 100)
            solar_credit = annual_usage.get('solar', 0) * (solar_rate / 100)
            supply_cost = (supply_charge + cl_supply_charge) * 365
            
            total_cost = anytime_cost + cl_cost + supply_cost - solar_credit
            
            return {
                'anytime_usage': annual_usage.get('anytime', 0),
                'cl_usage': annual_usage.get('controlled load', 0),
                'solar_usage': annual_usage.get('solar', 0),
                'anytime_cost': anytime_cost,
                'cl_cost': cl_cost,
                'solar_credit': solar_credit,
                'supply_cost': supply_cost,
                'total_cost': total_cost,
                'days_in_data': days_in_data
            }
        
        current_calc = calculate_annual_costs(current_anytime, current_cl, current_solar, 
                                             current_supply, current_cl_supply)
        comp_calc = calculate_annual_costs(comp_anytime, comp_cl, comp_solar, 
                                          comp_supply, comp_cl_supply)
        
        if current_calc:
            st.markdown("### 📊 Annual Usage Estimates")
            st.info(f"Based on {current_calc['days_in_data']} days of data (extrapolated to 365 days)")
            
            # Display usage estimates
            usage_col1, usage_col2, usage_col3 = st.columns(3)
            with usage_col1:
                st.metric("Anytime Usage", f"{current_calc['anytime_usage']:,.0f} kWh/year")
            with usage_col2:
                st.metric("Controlled Load Usage", f"{current_calc['cl_usage']:,.0f} kWh/year")
            with usage_col3:
                st.metric("Solar Generation", f"{current_calc['solar_usage']:,.0f} kWh/year")
            
            st.markdown("### 💵 Annual Cost Comparison")
            
            # Create comparison metrics
            cost_col1, cost_col2, cost_col3 = st.columns(3)
            
            with cost_col1:
                st.markdown("#### 🔵 Current Plan")
                st.metric("Total Annual Cost", f"${current_calc['total_cost']:,.2f}")
                st.write(f"- Anytime: ${current_calc['anytime_cost']:,.2f}")
                st.write(f"- Controlled Load: ${current_calc['cl_cost']:,.2f}")
                st.write(f"- Supply Charges: ${current_calc['supply_cost']:,.2f}")
                st.write(f"- Solar Credit: -${current_calc['solar_credit']:,.2f}")
            
            with cost_col2:
                st.markdown("#### 🟢 Comparison Plan")
                st.metric("Total Annual Cost", f"${comp_calc['total_cost']:,.2f}")
                st.write(f"- Anytime: ${comp_calc['anytime_cost']:,.2f}")
                st.write(f"- Controlled Load: ${comp_calc['cl_cost']:,.2f}")
                st.write(f"- Supply Charges: ${comp_calc['supply_cost']:,.2f}")
                st.write(f"- Solar Credit: -${comp_calc['solar_credit']:,.2f}")
            
            with cost_col3:
                st.markdown("#### 📊 Difference")
                savings = current_calc['total_cost'] - comp_calc['total_cost']
                st.metric("Annual Savings", f"${savings:,.2f}", 
                         delta=f"{savings:,.2f}",
                         delta_color="normal" if savings > 0 else "inverse")
                st.write(f"Monthly: ${savings/12:,.2f}")
                st.write(f"Percentage: {(savings/current_calc['total_cost']*100):.1f}%")
            
            # Visualization of cost breakdown
            st.markdown("### 📊 Cost Breakdown Comparison")
            
            breakdown_data = pd.DataFrame({
                'Category': ['Anytime', 'Controlled Load', 'Supply Charges', 'Solar Credit'],
                'Current Plan': [
                    current_calc['anytime_cost'],
                    current_calc['cl_cost'],
                    current_calc['supply_cost'],
                    -current_calc['solar_credit']
                ],
                'Comparison Plan': [
                    comp_calc['anytime_cost'],
                    comp_calc['cl_cost'],
                    comp_calc['supply_cost'],
                    -comp_calc['solar_credit']
                ]
            })
            
            fig_breakdown = go.Figure()
            fig_breakdown.add_trace(go.Bar(
                name='Current Plan',
                x=breakdown_data['Category'],
                y=breakdown_data['Current Plan'],
                marker_color='#1f77b4'
            ))
            fig_breakdown.add_trace(go.Bar(
                name='Comparison Plan',
                x=breakdown_data['Category'],
                y=breakdown_data['Comparison Plan'],
                marker_color='#2ca02c'
            ))
            
            fig_breakdown.update_layout(
                title='Annual Cost Breakdown by Category',
                xaxis_title='Category',
                yaxis_title='Annual Cost ($)',
                barmode='group',
                height=400
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)
    
    with tab3:
        st.subheader("📉 Usage Trends and Insights")
        
        # Calculate period-by-period trends
        if not daily_usage_df.empty:
            st.markdown("### Usage Statistics by Type")
            
            for reading_type in daily_usage_df['Type'].unique():
                type_usage = daily_usage_df[daily_usage_df['Type'] == reading_type]
                
                with st.expander(f"📊 {reading_type.title()} Statistics"):
                    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                    
                    with stat_col1:
                        st.metric("Average Daily Usage", 
                                 f"{type_usage['Daily Usage (kWh)'].mean():.2f} kWh/day")
                    with stat_col2:
                        st.metric("Maximum Daily Usage", 
                                 f"{type_usage['Daily Usage (kWh)'].max():.2f} kWh/day")
                    with stat_col3:
                        st.metric("Minimum Daily Usage", 
                                 f"{type_usage['Daily Usage (kWh)'].min():.2f} kWh/day")
                    with stat_col4:
                        st.metric("Total Days", f"{len(type_usage)}")
                    
                    # Line chart of usage trends
                    fig_trend = px.line(type_usage, x='Date', y='Daily Usage (kWh)',
                                       title=f'{reading_type.title()} - Daily Usage Trend',
                                       markers=True)
                    fig_trend.update_layout(height=300)
                    st.plotly_chart(fig_trend, use_container_width=True)
            
            # Overall usage trend
            st.markdown("### 📈 Overall Usage Patterns")
            pivot_usage = daily_usage_df.pivot_table(
                index='Date',
                columns='Type',
                values='Daily Usage (kWh)',
                aggfunc='mean'
            ).reset_index()
            
            fig_combined = go.Figure()
            for col in pivot_usage.columns:
                if col != 'Date':
                    fig_combined.add_trace(go.Scatter(
                        x=pivot_usage['Date'],
                        y=pivot_usage[col],
                        name=col.title(),
                        mode='lines+markers'
                    ))
            
            fig_combined.update_layout(
                title='All Usage Types - Daily Usage Comparison',
                xaxis_title='Date',
                yaxis_title='Daily Usage (kWh/day)',
                height=500,
                hovermode='x unified'
            )
            st.plotly_chart(fig_combined, use_container_width=True)

else:
    st.info("👆 Please upload your electricity readings CSV file to begin the analysis.")
    st.markdown("""
    ### Expected CSV Format:
    The CSV file should have the following columns:
    - **Date**: Date of the reading (e.g., "17/12/2024")
    - **Type**: Type of reading (anytime, controlled load, solar)
    - **Reading**: Meter reading value (can include commas)
    - **Reading Source**: Source of reading (bill, manual, etc.)
    
    Example:
    ```
    Date,Type,Reading,Reading Source
    17/12/2024,anytime," 66,444 ",bill
    17/12/2024,controlled load," 79,636 ",bill
    17/12/2024,solar," 70,660 ",bill
    ```
    """)
