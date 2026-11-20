-- Local illustrative fixtures. Never point init at a real catalogue.
BEGIN;

CREATE TABLE foods (food_id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE nutrients (nutrient_id INTEGER PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL);
CREATE TABLE food_nutrients (
  food_id INTEGER NOT NULL REFERENCES foods(food_id),
  nutrient_id INTEGER NOT NULL REFERENCES nutrients(nutrient_id),
  amount_per_100g NUMERIC NOT NULL,
  PRIMARY KEY(food_id, nutrient_id)
);
INSERT INTO foods VALUES
(1, 'White rice, cooked, Long-grain, plain'),
(2, 'White rice, dry, Long-grain, uncooked'),
(3, 'Rolled oats, dry, Plain, uncooked'),
(4, 'Black beans, cooked, Boiled, unsalted'),
(5, 'Banana, raw, Peeled'),
(6, 'Green lentils, cooked, Boiled, unsalted'),
(7, 'Chickpeas, cooked, Boiled, unsalted'),
(8, 'Chicken breast, cooked, Roasted, skinless');
INSERT INTO nutrients VALUES (208,'Energy','kcal'),(203,'Protein','g'),(205,'Carbohydrate','g'),(204,'Fat','g');
INSERT INTO food_nutrients VALUES
(1, 208, 130),
(1, 203, 2.7),
(1, 205, 28.2),
(1, 204, 0.3),
(2, 208, 365),
(2, 203, 7.1),
(2, 205, 80),
(2, 204, 0.7),
(3, 208, 379),
(3, 203, 13),
(3, 205, 67.7),
(3, 204, 6.5),
(4, 208, 132),
(4, 203, 8.9),
(4, 205, 23.7),
(4, 204, 0.5),
(5, 208, 89),
(5, 203, 1.1),
(5, 205, 22.8),
(5, 204, 0.3),
(6, 208, 116),
(6, 203, 9),
(6, 205, 20.1),
(6, 204, 0.4),
(7, 208, 164),
(7, 203, 8.9),
(7, 205, 27.4),
(7, 204, 2.6),
(8, 208, 165),
(8, 203, 31),
(8, 205, 0),
(8, 204, 3.6);
CREATE ROLE macrochef_reader WITH LOGIN PASSWORD 'local-demo-read';
GRANT CONNECT ON DATABASE macrochef TO macrochef_reader;
GRANT USAGE ON SCHEMA public TO macrochef_reader;
GRANT SELECT ON foods, nutrients, food_nutrients TO macrochef_reader;
COMMIT;
