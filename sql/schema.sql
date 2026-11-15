
CREATE TABLE foods (
    food_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE nutrients (
    nutrient_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL
);

CREATE TABLE food_nutrients (
    food_id INTEGER NOT NULL REFERENCES foods(food_id),
    nutrient_id INTEGER NOT NULL REFERENCES nutrients(nutrient_id),
    amount_per_100g NUMERIC NOT NULL,
    PRIMARY KEY (food_id, nutrient_id)
);
