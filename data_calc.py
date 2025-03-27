import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

@st.cache_data
def load_data():
    df_rbi = pd.read_csv("raw_data/rbi_data_dec_24.csv")
    df_rbi.dropna(subset=['dt_code'], inplace=True)
    df_rbi['st_code'] = df_rbi['st_code'].fillna(0).apply(lambda x: str(int(x)).zfill(2))
    df_rbi['dt_code'] = df_rbi['dt_code'].fillna(0).apply(lambda x: str(int(x)).zfill(3))

    # Load GeoJSON
    geojson_url = "https://gist.github.com/curran/49fa25fc44c84fcbebb51e60946145a4/raw/d7a115cc604b1e7fdc0afec874babd1025b86215/INDIA_DISTRICTS_TOPO.json"
    gdf_districts = gpd.read_file(geojson_url)
    print(gdf_districts.head())
    gdf_districts.rename(columns={'dtname': 'district', 'stname': 'state', 'stcode11': 'st_code', 'dtcode11': 'dt_code'}, inplace=True)
    gdf_districts.set_crs(epsg=4326, inplace=True)

    # Load RWI
    df_rwi = pd.read_csv("https://github.com/worldbank/RWI/raw/refs/heads/main/Input/ind_pak_relative_wealth_index.csv")
    gdf_rwi = gpd.GeoDataFrame(df_rwi, geometry=gpd.points_from_xy(df_rwi.longitude, df_rwi.latitude))
    gdf_rwi.set_crs(epsg=4326, inplace=True)
    gdf_rwi_joined = gpd.sjoin(gdf_rwi, gdf_districts, how="inner", predicate="within")
    df_rwi_district = gdf_rwi_joined.groupby(['st_code', 'dt_code']).agg({'rwi': 'mean'}).reset_index()

    # Merge data
    df_merged = df_rbi.merge(df_rwi_district, on=['st_code', 'dt_code'], how='left')
    df_merged.dropna(subset='rwi', inplace=True)

    data_gpd_df = pd.merge(
        gdf_districts[['st_code', 'dt_code', 'geometry']],
        df_merged,
        on=['st_code', 'dt_code'], how='left'
    )
    data_gpd_df.dropna(subset=['state'], inplace=True)

    data_gpd_df['cd_ratio'] = (data_gpd_df['credit_cr'] / data_gpd_df['deposit_cr']) * 100
    data_gpd_df['per_capita_deposit'] = data_gpd_df['deposit_cr'] * 10000000 / data_gpd_df['population']
    data_gpd_df['per_capita_credit'] = data_gpd_df['credit_cr'] * 10000000 / data_gpd_df['population']
    data_gpd_df['per_capita_curr_ac_deposit'] = data_gpd_df['current_ac_cr'] * 10000000 / data_gpd_df['population']
    data_gpd_df['casa_ratio'] = ((data_gpd_df['current_ac_cr'] + data_gpd_df['savings_ac_cr']) / data_gpd_df['deposit_cr']) * 100

    data_gpd_df = data_gpd_df.rename(columns={
        'housing_loan_cr': 'housing_loan',
        'auto_loan_cr': 'auto_loan',
        'education_loan_cr': 'education_loan',
        'con_durable_loan_cr': 'con_durable_loan',
        'others_loan_cr': 'other_loan'
    })

    features = ['cd_ratio', 'rwi', 'housing_loan', 'auto_loan', 'education_loan', 'con_durable_loan', 'other_loan']
    scaler = MinMaxScaler()
    normalized_features = [f"{f}_norm" for f in features]
    data_gpd_df[normalized_features] = scaler.fit_transform(data_gpd_df[features].fillna(0))


    weights = {
        'cd_ratio_norm': 0.25,
        'rwi_norm': 0.25,
        'housing_loan_norm': 0.15,
        'auto_loan_norm': 0.1,
        'education_loan_norm': 0.05,
        'con_durable_loan_norm': 0.1,
        'other_loan_norm': -0.1  # Negative weight
    }

    # Calculate wealth_score
    data_gpd_df['wealth_score'] = sum(data_gpd_df[f] * w for f, w in weights.items())

    data_gpd_df['wealth_bin'] = pd.qcut(data_gpd_df['wealth_score'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])

    
    return data_gpd_df


