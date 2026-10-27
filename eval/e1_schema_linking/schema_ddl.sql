-- Raw relational schema (the "no semantic layer" context for E1's raw condition).
-- Deliberately hostile: column names only, no labels, no dictionary.
CREATE TABLE fact_inflation (
  time_period VARCHAR,
  geo_code VARCHAR,
  inflation_rate DOUBLE,
  unit VARCHAR
);
CREATE TABLE fact_poverty (
  time_period VARCHAR,
  geo_code VARCHAR,
  poverty_rate DOUBLE,
  poor_pop BIGINT
);
CREATE TABLE fact_min_wage (
  time_period VARCHAR,
  geo_code VARCHAR,
  min_wage BIGINT
);
