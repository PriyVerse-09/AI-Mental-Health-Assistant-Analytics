import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def extract_regional_cmd_data(file_path, sheet_name='2.11'):
    #Extract CMD prevalence by UK region from APMS Table 2.11
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd', skiprows=4)

    regions = [
        'North East', 'North West', 'Yorkshire and The Humber',
        'East Midlands', 'West Midlands', 'East of England',
        'London', 'South East', 'South West'
    ]

    # Extract the "All adults" observed data (rows 20-26 in the cleaned data)
    regional_data = []

    # Defining disorder mapping
    disorders = {
        'Generalised Anxiety Disorder': 20,
        'Depressive Episode': 21,
        'All Phobias': 22,
        'Obsessive Compulsive Disorder': 23,
        'Panic Disorder': 24,
        'CMD-NOS': 25,
        'Any CMD': 26
    }

    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd')

    # Extract prevalence values for "All adults" (Observed data)
    all_adults_start = 23  

    disorder_names = [
        'Generalised Anxiety Disorder',
        'Depressive Episode',
        'All Phobias',
        'Obsessive Compulsive Disorder',
        'Panic Disorder',
        'CMD-NOS',
        'Any CMD'
    ]

    # Extract values for each disorder across regions
    for idx, disorder in enumerate(disorder_names):
        row_idx = all_adults_start + 1 + idx  

        for col_idx, region in enumerate(regions):
            prevalence = df_raw.iloc[row_idx, col_idx + 1]

            regional_data.append({
                'Region': region,
                'Disorder': disorder,
                'Prevalence_Percentage': prevalence,
                'Year': 2014,
                'Data_Type': 'Observed',
                'Population_Group': 'All Adults'
            })

   
    df_regional = pd.DataFrame(regional_data)
   
    df_regional['Prevalence_Percentage'] = pd.to_numeric(
        df_regional['Prevalence_Percentage'],
        errors='coerce'
    )

    df_regional = df_regional.dropna(subset=['Prevalence_Percentage'])

    return df_regional


def create_choropleth_dataset(df_regional):

    #Create a pivot table optimized for Power BI choropleth mapping

    df_choropleth = df_regional.pivot(
        index='Region',
        columns='Disorder',
        values='Prevalence_Percentage'
    ).reset_index()

    df_choropleth['Overall_CMD_Prevalence'] = df_choropleth['Any CMD']

    weights = {
        'Generalised Anxiety Disorder': 0.3,
        'Depressive Episode': 0.3,
        'All Phobias': 0.15,
        'Obsessive Compulsive Disorder': 0.15,
        'Panic Disorder': 0.1
    }

    df_choropleth['Severity_Score'] = sum(
        df_choropleth[disorder] * weight
        for disorder, weight in weights.items()
    )

    df_choropleth['Risk_Category'] = pd.cut(
        df_choropleth['Any CMD'],
        bins=[0, 15, 18, 25],
        labels=['Low Risk', 'Medium Risk', 'High Risk']
    )

    return df_choropleth


def create_long_format_dataset(df_regional):
    #Create long format dataset for flexible Power BI filtering

    df_long = df_regional.copy()

    national_avg = df_long.groupby('Disorder')['Prevalence_Percentage'].mean()
    df_long['National_Average'] = df_long['Disorder'].map(national_avg)

    df_long['Deviation_from_National'] = (
        df_long['Prevalence_Percentage'] - df_long['National_Average']
    )
    df_long['Deviation_Percentage'] = (
        (df_long['Prevalence_Percentage'] / df_long['National_Average'] - 1) * 100
    ).round(2)

    region_classification = {
        'London': 'Major Metropolitan',
        'North West': 'Urban Industrial',
        'West Midlands': 'Urban Industrial',
        'South East': 'Affluent Southeast',
        'East of England': 'Affluent Southeast',
        'South West': 'Rural/Coastal',
        'Yorkshire and The Humber': 'Northern Region',
        'North East': 'Northern Region',
        'East Midlands': 'Midlands'
    }

    df_long['Region_Type'] = df_long['Region'].map(region_classification)

    disorder_categories = {
        'Generalised Anxiety Disorder': 'Anxiety Disorders',
        'Panic Disorder': 'Anxiety Disorders',
        'All Phobias': 'Anxiety Disorders',
        'Depressive Episode': 'Mood Disorders',
        'Obsessive Compulsive Disorder': 'OCD & Related',
        'CMD-NOS': 'Mixed Disorders',
        'Any CMD': 'Overall Prevalence'
    }

    df_long['Disorder_Category'] = df_long['Disorder'].map(disorder_categories)

    # Calculate Risk_Category for 'Any CMD' and then map it to all rows in df_long
    any_cmd_prevalence_for_risk = df_long[df_long['Disorder'] == 'Any CMD'].set_index('Region')['Prevalence_Percentage']

    risk_category_mapping = pd.cut(
        any_cmd_prevalence_for_risk,
        bins=[0, 15, 18, 25],
        labels=['Low Risk', 'Medium Risk', 'High Risk'],
        include_lowest=True 
    )

    df_long['Risk_Category'] = df_long['Region'].map(risk_category_mapping)

    return df_long


def generate_summary_statistics(df_regional):
    #Generate summary statistics for the report

    # Overall CMD statistics
    any_cmd = df_regional[df_regional['Disorder'] == 'Any CMD']

    summary = {
        'highest_prevalence_region': any_cmd.loc[
            any_cmd['Prevalence_Percentage'].idxmax(), 'Region'
        ],
        'highest_prevalence_value': any_cmd['Prevalence_Percentage'].max(),
        'lowest_prevalence_region': any_cmd.loc[
            any_cmd['Prevalence_Percentage'].idxmin(), 'Region'
        ],
        'lowest_prevalence_value': any_cmd['Prevalence_Percentage'].min(),
        'national_average': any_cmd['Prevalence_Percentage'].mean(),
        'prevalence_range': (
            any_cmd['Prevalence_Percentage'].max() -
            any_cmd['Prevalence_Percentage'].min()
        )
    }

    # Top 3 regions by disorder type
    summary['top_regions_by_disorder'] = {}

    for disorder in df_regional['Disorder'].unique():
        if disorder != 'Any CMD':
            top_3 = df_regional[
                df_regional['Disorder'] == disorder
            ].nlargest(3, 'Prevalence_Percentage')[['Region', 'Prevalence_Percentage']]
            summary['top_regions_by_disorder'][disorder] = top_3.to_dict('records')

    return summary


def main():

    #Main execution function

    print("="*80)
    print("ANA-3: REGIONAL PREVALENCE MAPPING")
    print("Adult Psychiatric Morbidity Survey (APMS) 2014")
    print("="*80)
    print()

    file_path = "apms-2014-ch-02-tabs.xls"

    # Step 1: Extract regional data
    print("Step 1: Extracting regional CMD prevalence data...")
    df_regional = extract_regional_cmd_data(file_path)
    print(f"✓ Extracted {len(df_regional)} data points across {df_regional['Region'].nunique()} regions")
    print()

    # Step 2: Create choropleth dataset
    print("Step 2: Creating choropleth-optimized dataset...")
    df_choropleth = create_choropleth_dataset(df_regional)
    print(f"✓ Created wide-format dataset with {len(df_choropleth)} regions")
    print()

    # Step 3: Create long format dataset
    print("Step 3: Creating enhanced long-format dataset...")
    df_long = create_long_format_dataset(df_regional)
    print(f"✓ Enhanced dataset with calculated fields and categorizations")
    print()

    # Step 4: Generate summary statistics
    print("Step 4: Generating summary statistics...")
    summary = generate_summary_statistics(df_regional)
    print(f"✓ Calculated regional prevalence metrics")
    print()

    # Step 5: Save outputs
    print("Step 5: Saving output files...")

    df_choropleth.to_csv('regional_cmd_prevalence_wide.csv', index=False)
    print("✓ Saved: regional_cmd_prevalence_wide.csv")

    df_long.to_csv('regional_cmd_prevalence_long.csv', index=False)
    print("✓ Saved: regional_cmd_prevalence_long.csv")

    summary_df = pd.DataFrame([
        {
            'Metric': 'Highest Prevalence Region',
            'Value': summary['highest_prevalence_region'],
            'Percentage': f"{summary['highest_prevalence_value']:.1f}%"
        }, {
            'Metric': 'Lowest Prevalence Region',
            'Value': summary['lowest_prevalence_region'],
            'Percentage': f"{summary['lowest_prevalence_value']:.1f}%"
        }, {
            'Metric': 'National Average',
            'Value': 'All Regions',
            'Percentage': f"{summary['national_average']:.1f}%"
        }, {
            'Metric': 'Prevalence Range',
            'Value': 'Max - Min',
            'Percentage': f"{summary['prevalence_range']:.1f}%"
        }
    ])

    summary_df.to_csv('regional_summary_statistics.csv', index=False)
    print("✓ Saved: regional_summary_statistics.csv")
    print()

    print("="*80)
    print("SUMMARY FINDINGS")
    print("="*80)
    print(f"Highest Prevalence: {summary['highest_prevalence_region']} "
          f"({summary['highest_prevalence_value']:.1f}%)")
    print(f"Lowest Prevalence:  {summary['lowest_prevalence_region']} "
          f"({summary['lowest_prevalence_value']:.1f}%)")
    print(f"National Average:   {summary['national_average']:.1f}%")
    print(f"Regional Variation: {summary['prevalence_range']:.1f} percentage points")
    print()

    print("="*80)
    print("SAMPLE DATA (Any CMD by Region)")
    print("="*80)
    sample = df_long[df_long['Disorder'] == 'Any CMD'][
        ['Region', 'Prevalence_Percentage', 'National_Average',
         'Deviation_Percentage', 'Risk_Category']
    ].sort_values('Prevalence_Percentage', ascending=False)
    print(sample.to_string(index=False))
    print()

    print("="*80)
    print("✓ ANALYSIS COMPLETE - Files ready for Power BI import")
    print("="*80)


if __name__ == "__main__":
    main()