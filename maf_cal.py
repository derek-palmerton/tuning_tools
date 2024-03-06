import pandas as pd
import numpy as np
import os

afr_error_tolerance = 0.01
throttle_error_tolerance = 1.0

# add full paths to any logs, they should have a specific format described below
# required columns:
#     'Time (s)'
#     'Actual equivalence/air to fuel ratio (λ)'
#     'Desired equivalence/air to fuel ratio (λ)'
#     'Long term fuel trim (%)'
#     'Mass airflow sensor voltage (V)'
#     'Relative throttle position (%)'
#     'Short term fuel trim (primary sensor) (%)'
downloads_dir = os.path.join("C:\\Users", "derek", "Downloads")
logs = [os.path.join(downloads_dir, "MAF Scaling Test 3 - 2024-03-04 17.46.26.csv"), 
        os.path.join(downloads_dir, "MAF Scaling Test 4 - 2024-03-04 20.41.41.csv")]

maf_voltage_buckets = [0, 0.039, 0.078, 0.117, 0.156, 0.195, 0.234, 0.273, 0.313, 0.352, 
                       0.391, 0.43, 0.469, 0.508, 0.547, 0.586, 0.625, 0.664, 0.703, 
                       0.742, 0.781, 0.82, 0.859, 0.898, 0.938, 0.977, 1.016, 1.055, 
                       1.094, 1.133, 1.172, 1.211, 1.25, 1.289, 1.328, 1.367, 1.406, 
                       1.445, 1.484, 1.523, 1.563, 1.602, 1.641, 1.68, 1.719, 1.758, 
                       1.797, 1.836, 1.875, 1.914, 1.953, 1.992, 2.031, 2.07, 2.109, 
                       2.148, 2.188, 2.227, 2.266, 2.305, 2.344, 2.383, 2.422, 2.461, 
                       2.5, 2.539, 2.578, 2.617, 2.656, 2.695, 2.734, 2.773, 2.813, 
                       2.852, 2.891, 2.93, 2.969, 3.008, 3.047, 3.086, 3.125, 3.164, 
                       3.203, 3.242, 3.281, 3.32, 3.359, 3.398, 3.438, 3.477, 3.516, 
                       3.555, 3.594, 3.633, 3.672, 3.711, 3.75, 3.789, 3.828, 3.867, 
                       3.906, 3.945, 3.984, 4.023, 4.063, 4.102, 4.141, 4.18, 4.219, 
                       4.258, 4.297, 4.336, 4.375, 4.414, 4.453, 4.492, 4.531, 4.57, 
                       4.609, 4.648, 4.688, 4.727, 4.766, 4.804, 4.844, 4.883, 4.921, 
                       4.961, 5]

def get_voltage_bucket(voltage):
     global maf_voltage_buckets
     np_maf_voltage_buckets = np.asarray(maf_voltage_buckets)
     idx = (np.abs(np_maf_voltage_buckets - voltage)).argmin()
     return np_maf_voltage_buckets[idx]

# maf voltage bucket sanity check
# for index, bucket in enumerate(maf_voltage_buckets):
#     # ignore 0 because we can mentally do that on our own
#     print(bucket - maf_voltage_buckets[index - 1])

valid_datapoints = {}
for log in logs:
    df = pd.read_csv(log)
    
    for index, row in df.iterrows():
        # ensure AFR is approximately the target
        actual_afr = row['Actual equivalence/air to fuel ratio (λ)']
        target_afr = row["Desired equivalence/air to fuel ratio (λ)"]
        if (actual_afr >= target_afr - afr_error_tolerance or 
            actual_afr <= target_afr + afr_error_tolerance):
            # get all rows within a second of the current row
            adjacent_rows = df[((df['Time (s)'] >= (row['Time (s)'] - 0.5)) & (df['Time (s)'] <= (row['Time (s)'] + 0.5)))]

            # check to make sure we have constant throttle across the time range
            throttle_pct = row["Relative throttle position (%)"]
            adjacent_throttle_pos = adjacent_rows["Relative throttle position (%)"]
            constant_throttle_rows = adjacent_rows[((adjacent_throttle_pos >= throttle_pct - throttle_error_tolerance) & 
                                                    (adjacent_throttle_pos <= throttle_pct + throttle_error_tolerance))]
            if adjacent_rows.equals(constant_throttle_rows):
                maf_voltage = row["Mass airflow sensor voltage (V)"]
                stft = row["Short term fuel trim (primary sensor) (%)"]
                ltft = row["Long term fuel trim (%)"]
                valid_datapoints.setdefault(get_voltage_bucket(maf_voltage), []).append(stft + ltft)

output = {}
for voltage_bucket in maf_voltage_buckets:
    ft_list = valid_datapoints.get(voltage_bucket)
    if ft_list is not None:
        ft_list_len = len(ft_list)
        avg_ft = np.average(ft_list)
    else:
        ft_list_len = 0
        avg_ft = 0
    output[voltage_bucket] = {
        "count" : ft_list_len,
        "avg_ft" : avg_ft,
        "maf_voltage_multiplier_adjustment" : (avg_ft / 100) + 1
    }

# now use google sheets to perform some multiplication on the current values and copy paste in the new
output_df = df.from_dict(output).to_csv("out.csv")
        
