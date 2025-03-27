import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import folium_static
from data_calc import load_data

st.set_page_config(layout="wide", page_title="India District Wealth Dashboard")

# Function to format values
def format_value(value, col_name, pct_cols):
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        num_value = float(value)
        if col_name in pct_cols:
            return f"{num_value:.1f}%"  # Assumes cd_ratio is already a ratio, not a percentage
        return f"{num_value:,.0f}"
    except (ValueError, TypeError):
        return str(value)

def main():
    # Load data
    data = load_data()
    st.title("India District Wealth Dashboard")
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Filters")
        
        # Dropdowns
        states = ['All'] + sorted(data['state'].dropna().unique().tolist())
        selected_state = st.selectbox("Select State", states)
        
        wealth_bins = sorted(data['wealth_bin'].dropna().unique().tolist())
        selected_wealth_bin = st.selectbox("Select Wealth Bin", ['All'] + wealth_bins)
        
        params = {
            'cd_ratio': 'Credit-Deposit %',
            'casa_ratio': 'CASA %',
            'rwi': 'Relative Wealth Index',
            'housing_loan': 'Housing Loan (₹ Cr)',
            'auto_loan': 'Auto Loan (₹ Cr)',
            'education_loan': 'Education Loan (₹ Cr)',
            'con_durable_loan': 'Consumer Durable Loan (₹ Cr)',
            'other_loan': 'Other Loan (₹ Cr)',
            'wealth_score': 'Wealth Score (Normalized)'
        }
        selected_param = st.selectbox("Select Parameter for Heatmap", list(params.keys()), index=8)

        # Slider for selected parameter
        min_val = float(data[selected_param].min())
        max_val = float(data[selected_param].max())
        step = (max_val - min_val) / 100 if max_val > min_val else 0.01
        param_range = st.slider(
            f"{params[selected_param]} Range",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val),
            step=step,
            key=selected_param
        )

        # District counts
        total_districts = len(data['district'].unique())
        filtered_data = data.copy()
        if selected_state != 'All':
            filtered_data = filtered_data[filtered_data['state'] == selected_state]
        if selected_wealth_bin != 'All':
            filtered_data = filtered_data[filtered_data['wealth_bin'] == selected_wealth_bin]
        filtered_data = filtered_data[
            (filtered_data[selected_param] >= param_range[0]) & 
            (filtered_data[selected_param] <= param_range[1])
        ]
        filtered_district_count = len(filtered_data['district'].unique())
        
        st.metric("Total Districts", total_districts)
        st.metric("Filtered Districts", filtered_district_count)

    # Formatting for tooltip
    pct_cols = ['cd_ratio']  # Add others if they’re percentages in your data
    filtered_data[f'{selected_param}_formatted'] = filtered_data[selected_param].apply(
        lambda x: format_value(x, selected_param, pct_cols)
    )

    with col2:
        st.subheader(f"Heatmap of {params[selected_param]}")
        m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
        folium.TileLayer('CartoDB positron', name="Light Map", control=False).add_to(m)
        
        choropleth = folium.Choropleth(
            geo_data=filtered_data,
            name='choropleth',
            data=filtered_data,
            columns=['district', selected_param],
            key_on='feature.properties.district',  # Adjust if GeoJSON uses 'dt_code'
            fill_color='YlGnBu',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=f'{params[selected_param]} by District'
        ).add_to(m)
        
        tooltip = folium.GeoJsonTooltip(
            fields=['state', 'district', f'{selected_param}_formatted'],
            aliases=['State:', 'District:', f'{params[selected_param]}:'],
            labels=True,
            localize=True,
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"),
            sticky=True
        )
        choropleth.geojson.add_child(tooltip)
        folium.LayerControl().add_to(m)
        folium_static(m, width=900, height=600)

    # Filtered data table
    st.subheader("Filtered Data - 10 Districts")
    display_columns = ['state', 'district', 'cd_ratio', 'housing_loan', 'auto_loan', 'education_loan', 'con_durable_loan', 'other_loan']
    st.dataframe(filtered_data[display_columns].set_index('state').round(0).sort_values(by='housing_loan', ascending=False).head(10))

if __name__ == "__main__":
    main()