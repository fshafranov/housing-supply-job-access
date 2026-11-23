Table 5. Baum-Snow & Han tract supply elasticities (2011, units) and job access. Descriptive.

A. By within-metro job-access decile (10 = closest to jobs), unit-weighted:

|   access_decile |       units |   elast_units |   elast_newunits |   share_negative_elast |   bsh_frac_developed_2011 |   bsh_frac_flat |   bsh_frac_to_edge |
|----------------:|------------:|--------------:|-----------------:|-----------------------:|--------------------------:|----------------:|-------------------:|
|               1 | 6.24492e+06 |         0.567 |            0.382 |                  0.024 |                     0.12  |           0.375 |              0.509 |
|               2 | 6.9034e+06  |         0.491 |            0.31  |                  0.044 |                     0.207 |           0.377 |              0.411 |
|               3 | 7.13125e+06 |         0.425 |            0.254 |                  0.06  |                     0.277 |           0.415 |              0.357 |
|               4 | 7.3179e+06  |         0.382 |            0.217 |                  0.073 |                     0.329 |           0.445 |              0.31  |
|               5 | 7.37926e+06 |         0.33  |            0.171 |                  0.105 |                     0.378 |           0.454 |              0.273 |
|               6 | 7.38738e+06 |         0.291 |            0.134 |                  0.128 |                     0.412 |           0.442 |              0.244 |
|               7 | 7.40718e+06 |         0.255 |            0.101 |                  0.163 |                     0.449 |           0.446 |              0.208 |
|               8 | 7.38546e+06 |         0.208 |            0.059 |                  0.221 |                     0.492 |           0.455 |              0.18  |
|               9 | 7.39853e+06 |         0.147 |            0.003 |                  0.307 |                     0.552 |           0.456 |              0.127 |
|              10 | 7.39658e+06 |         0.125 |           -0.013 |                  0.354 |                     0.585 |           0.493 |              0.097 |

B. Homes built 2010+ by within-metro elasticity quintile (5 = most elastic):

|   elast_quintile |   share_of_all_homes |   share_of_new_homes |   elast_units |   access10_pctile |   access10_pctile_new_homes |   commute_median_km_new_homes |
|-----------------:|---------------------:|---------------------:|--------------:|------------------:|----------------------------:|------------------------------:|
|                1 |                  0.2 |                0.182 |        -0.024 |            70.495 |                      76.474 |                        12.701 |
|                2 |                  0.2 |                0.147 |         0.179 |            62.053 |                      62.805 |                        16.695 |
|                3 |                  0.2 |                0.167 |         0.313 |            53.298 |                      49.016 |                        20.652 |
|                4 |                  0.2 |                0.21  |         0.458 |            42.096 |                      36.917 |                        23.762 |
|                5 |                  0.2 |                0.294 |         0.656 |            27.494 |                      24.034 |                        27.16  |

C. Regressions (e1: tracts, metro FE, SE by metro; e2-e5: metros, robust SE):

| spec                 | term                  |   estimate |   std_error |   p_value |   nobs |    r2 |
|:---------------------|:----------------------|-----------:|------------:|----------:|-------:|------:|
| e1_elast_on_access   | access10_mid_pctile   |     -0.005 |       0.001 |     0     |  41724 | 0.495 |
| e1b_plus_center      | access10_mid_pctile   |     -0.006 |       0.001 |     0     |  41724 | 0.496 |
| e1b_plus_center      | dist_center_pctile    |      0.001 |       0.001 |     0.273 |  41724 | 0.496 |
| e2_access_gap        | Intercept             |     -9.06  |       2.236 |     0     |     48 | 0.026 |
| e2_access_gap        | elast_core_minus_edge |     -7.002 |       6.546 |     0.29  |     48 | 0.026 |
| e3_commute_gap       | Intercept             |      1.674 |       0.471 |     0.001 |     48 | 0.004 |
| e3_commute_gap       | elast_core_minus_edge |      0.662 |       1.503 |     0.662 |     48 | 0.004 |
| e4_growth_gap        | Intercept             |     -6.13  |       2.181 |     0.007 |     44 | 0.005 |
| e4_growth_gap        | elast_core_minus_edge |      2.662 |       6.448 |     0.682 |     44 | 0.005 |
| e5_access_gap_levels | Intercept             |     10.255 |       4.51  |     0.028 |     48 | 0.357 |
| e5_access_gap_levels | elast_near_jobs       |     -4.005 |       5.897 |     0.501 |     48 | 0.357 |
| e5_access_gap_levels | elast_far             |    -29.193 |       9.773 |     0.005 |     48 | 0.357 |
