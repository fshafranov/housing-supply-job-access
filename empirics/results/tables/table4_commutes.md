Table 4. Actual commutes (LODES 2023) of residents of tracts, by decade built (means over 48 metros). Last column: metro-FE regression, SE clustered by metro.

| vintage      |   commute_median_km |   commute_share_le10km |   commute_median_close_pctile |   access10_mid_pctile | median km vs pre-1940 (s2)   |
|:-------------|--------------------:|-----------------------:|------------------------------:|----------------------:|:-----------------------------|
| 1939_earlier |               17.13 |                   0.39 |                         63.48 |                 64.16 | ref                          |
| 1940_1949    |               17.26 |                   0.36 |                         61.64 |                 62.74 | 1.1 (0.3)                    |
| 1950_1959    |               17.41 |                   0.34 |                         59.5  |                 60.13 | 2.0 (0.5)                    |
| 1960_1969    |               18.18 |                   0.32 |                         55.67 |                 55.95 | 2.7 (0.4)                    |
| 1970_1979    |               19.83 |                   0.3  |                         49.47 |                 49.77 | 4.1 (0.4)                    |
| 1980_1989    |               20.31 |                   0.28 |                         47.08 |                 47.19 | 4.7 (0.5)                    |
| 1990_1999    |               21.89 |                   0.26 |                         41.64 |                 41.61 | 6.2 (0.4)                    |
| 2000_2009    |               22.25 |                   0.26 |                         40.6  |                 40.36 | 6.7 (0.4)                    |
| 2010_2019    |               20.84 |                   0.28 |                         45.29 |                 44.86 | 5.1 (0.5)                    |
| 2020plus     |               21.63 |                   0.27 |                         42.5  |                 41.18 | 6.6 (0.6)                    |

How well potential access and centrality predict the commute percentile (tract level, metro FE):

| spec         | term                |   estimate |   std_error |   r2_within |
|:-------------|:--------------------|-----------:|------------:|------------:|
| m1_on_access | access10_mid_pctile |      0.903 |       0.009 |       0.816 |
| m2_on_center | dist_center_pctile  |      0.827 |       0.026 |       0.683 |
| m3_on_both   | access10_mid_pctile |      0.748 |       0.039 |       0.824 |
| m3_on_both   | dist_center_pctile  |      0.179 |       0.045 |       0.824 |
