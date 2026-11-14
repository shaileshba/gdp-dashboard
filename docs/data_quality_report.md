# Data quality report

Generated 2026-11-14 by `uv run python -m gdp_pipeline build`.

**Coverage:** 166 countries, 1500-2025, 87,316 country-years.
Units: GDP per person in **2011 international dollars (PPP)**; population in persons; borders as of today.

## How each value was produced

| Label | Meaning |
|---|---|
| observed | Value is in the Maddison Project Database |
| interpolated | Between two observed years, assuming steady growth |
| extended | After 2022, follows World Bank (GDP/head) or UN (population) growth rates |
| parent | Before the country appears, follows the former state it belonged to (USSR, Czechoslovakia, Yugoslavia) |
| regional | Outside the observed years, follows the median growth of other countries in its region |

A country-year's overall label is the weaker of its GDP/head and population labels.

Two adjustments apply to *regional* estimates only (real data is never changed):
- **Calibration to Maddison's regional totals.** Where Maddison publishes a total for a region
  (1820 onward), estimated countries in that region are scaled so the region adds up. The scaling
  is held flat before 1820, and fades out over 30 years as an estimate approaches a country's
  first real data point, so the two join without a jump.
- **Subsistence floor.** Estimated GDP per person never falls below $400.

| Label | Share of country-years |
|---|---|
| regional | 64.2% |
| observed | 17.8% |
| interpolated | 13.3% |
| parent | 4.0% |
| extended | 0.6% |

## How much of world GDP rests on real data

| Year | Countries with observed GDP/head | World GDP from real data (obs./interp.) | World GDP from estimates |
|---|---|---|---|
| 1500 | 11 | 54% | 46% |
| 1600 | 14 | 54% | 46% |
| 1700 | 16 | 55% | 45% |
| 1820 | 54 | 69% | 31% |
| 1870 | 66 | 77% | 23% |
| 1913 | 71 | 82% | 18% |
| 1950 | 143 | 95% | 5% |
| 1990 | 166 | 100% | 0% |
| 2022 | 166 | 100% | 0% |
| 2025 | 0 | 100% | 0% |

Before 1820, most of the world total is estimated. Charts should show this (e.g. dashed lines).

## Check against Maddison's own world totals

| Year | Maddison world GDP/head | Our world GDP/head | Maddison world pop (m) | Our world pop (m) | GDP/head gap |
|---|---|---|---|---|---|
| 1820 | 1128 | 1121 | 1042.0 | 1047.0 | -0.6% |
| 1850 | 1301 | 1247 | 1189.0 | 1215.0 | -4.2% |
| 1870 | 1543 | 1472 | 1272.0 | 1279.0 | -4.6% |
| 1900 | 2265 | 2081 | 1547.0 | 1587.0 | -8.1% |
| 1920 | 2493 | 2346 | 1935.0 | 1875.0 | -5.9% |
| 1940 | 3413 | 3078 | 2240.0 | 2307.0 | -9.8% |
| 1950 | 3360 | 3292 | 2518.0 | 2517.0 | -2.0% |
| 1960 | 4404 | 4344 | 3029.0 | 3029.0 | -1.4% |
| 1970 | 5971 | 5938 | 3675.0 | 3675.0 | -0.6% |
| 1980 | 7239 | 7259 | 4418.0 | 4418.0 | +0.3% |
| 1990 | 8211 | 8229 | 5241.0 | 5241.0 | +0.2% |
| 2000 | 9904 | 9921 | 6048.0 | 6048.0 | +0.2% |
| 2010 | 13122 | 13155 | 6844.0 | 6844.0 | +0.3% |
| 2015 | 14713 | 14754 | 7264.0 | 7264.0 | +0.3% |
| 2016 | 15029 | 15070 | 7346.0 | 7346.0 | +0.3% |
| 2017 | 15416 | 15459 | 7429.0 | 7429.0 | +0.3% |
| 2018 | 15815 | 15860 | 7510.0 | 7510.0 | +0.3% |
| 2019 | 16091 | 16138 | 7591.0 | 7591.0 | +0.3% |
| 2020 | 15461 | 15506 | 7670.0 | 7670.0 | +0.3% |
| 2021 | 16283 | 16331 | 7738.0 | 7738.0 | +0.3% |
| 2022 | 16677 | 16727 | 7802.0 | 7802.0 | +0.3% |

### By region

| Year | Region | GDP/head ours vs Maddison | Pop gap | GDP gap |
|---|---|---|---|---|
| 1820 | East Asia | 911 vs 911 | -0.0% | -0.0% |
| 1820 | Eastern Europe | 1,045 vs 1,045 | -0.0% | +0.0% |
| 1820 | Latin America | 949 vs 957 | +0.7% | -0.1% |
| 1820 | Middle East and North Africa | 883 vs 886 | +0.6% | +0.2% |
| 1820 | South and South East Asia | 904 vs 919 | +1.6% | +0.0% |
| 1820 | Sub Saharan Africa | 1,186 vs 1,188 | +0.0% | -0.2% |
| 1820 | Western Europe | 2,165 vs 2,171 | +0.1% | -0.2% |
| 1820 | Western Offshoots | 2,513 vs 2,513 | +0.0% | +0.0% |
| 1870 | East Asia | 994 vs 994 | +0.0% | +0.0% |
| 1870 | Eastern Europe | 1,181 vs 1,518 | +0.0% | -22.2% |
| 1870 | Latin America | 1,285 vs 1,293 | +0.6% | +0.0% |
| 1870 | Middle East and North Africa | 1,066 vs 1,085 | +2.5% | +0.6% |
| 1870 | South and South East Asia | 837 vs 850 | +1.6% | -0.0% |
| 1870 | Sub Saharan Africa | 1,176 vs 1,286 | +0.0% | -8.6% |
| 1870 | Western Europe | 3,290 vs 3,288 | +0.1% | +0.1% |
| 1870 | Western Offshoots | 4,647 vs 4,647 | -0.0% | -0.0% |
| 1950 | East Asia | 1,129 vs 1,109 | -0.0% | +1.7% |
| 1950 | Eastern Europe | 3,527 vs 4,133 | -0.3% | -14.9% |
| 1950 | Latin America | 3,678 vs 3,678 | +0.0% | +0.0% |
| 1950 | Middle East and North Africa | 2,288 vs 2,288 | -0.0% | -0.0% |
| 1950 | South and South East Asia | 1,070 vs 1,070 | -0.0% | -0.0% |
| 1950 | Sub Saharan Africa | 1,327 vs 1,327 | -0.0% | +0.0% |
| 1950 | Western Europe | 7,240 vs 7,240 | +0.0% | -0.0% |
| 1950 | Western Offshoots | 14,773 vs 14,773 | +0.0% | +0.0% |

Remaining gaps come from two places: the 30-year fade (estimates close to real data are scaled
less), and Eastern Europe, where Maddison's newer Russia series is lower than its own USSR total.
We keep the Russia series as published rather than force it to match.

## Largest economies (share of world GDP; * = estimated)

- **1500:** China 26%, India 17%*, Italy 6%, France 5%, Germany 4%, Japan 3%, Austria 2%*, Pakistan 2%*
- **1700:** China 28%, India 20%*, France 5%, Italy 4%, Japan 4%, Germany 3%, United Kingdom 3%, Pakistan 2%*
- **1820:** China 29%, India 14%*, United Kingdom 6%, France 5%, Italy 4%, Germany 4%, Japan 3%, United States 2%
- **1913:** United States 22%, China 10%, Germany 8%, United Kingdom 8%, India 6%*, France 5%, Italy 3%, Japan 3%
- **1950:** United States 28%, United Kingdom 7%, China 5%, Germany 5%, India 4%, France 4%, Russian Federation 4%, Italy 3%
- **2025:** China 22%, United States 15%, India 9%, Japan 3%, Russian Federation 3%, Indonesia 3%, Germany 3%, Brazil 2%

## Sanity checks

- Structural problems: none found
- Year-on-year GDP/head moves larger than 40% (usually wars, oil states or data breaks; review these):
  Romania 1948 (+174%), Iraq 1991 (-61%), Austria 1945 (-58%), Lebanon 1976 (-57%), Libya 2011 (-56%), Kuwait 1992 (+105%), Germany 1946 (-51%), Libya 2012 (+96%), Equatorial Guinea 1997 (+91%), Lebanon 1977 (+81%), Liberia 1990 (-45%), Georgia 1992 (-45%)
- Countries without a World Bank region/income group: Taiwan, Province of China

## Known gaps / next steps

- About 50 small economies in the World Bank list are not in Maddison and are not yet included
  (together well under 1% of world GDP).
- Before 1947, India, Pakistan and Bangladesh are split out of Maddison's British India total
  in proportion to their populations and incomes just after Partition.
- Ireland's series before 1921 includes Northern Ireland (about 1.3 million people double-counted
  with the UK); too small to matter at world level, noted for country views.
- Age structure (working-age share) from UN WPP is needed for the labour lever; it is added in the model milestone.

## Sources

- `maddison`: https://dataverse.nl/api/access/datafile/421302 (downloaded 2026-11-14, sha256 ecc5916ca127...)
- `pwt`: https://dataverse.nl/api/access/datafile/554105 (downloaded 2026-11-14, sha256 7b337e94f39d...)
- `wpp`: https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz (downloaded 2026-11-14, sha256 286ac36bb141...)
- `wdi_countries`: https://api.worldbank.org/v2/country (downloaded 2026-11-14, sha256 2d53f0c22ab2...)
- `wdi_gdp`: https://api.worldbank.org/v2/ NY.GDP.PCAP.PP.KD, NY.GDP.MKTP.PP.KD (downloaded 2026-11-14, sha256 856712316b13...)
