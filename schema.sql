-- Schema for date
CREATE TABLE date (
    id BIGINT PRIMARY KEY,
    day TEXT NOT NULL,
    time INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Schema for potion_order_table
CREATE TABLE potion_order_table (
    potion_order_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Schema for cart_order_table
CREATE TABLE cart_order_table (
    id BIGINT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_class TEXT NOT NULL,
    customer_level BIGINT NOT NULL,
    time_id BIGINT,
    transaction_occurred BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (time_id) REFERENCES date3(id) ON DELETE SET NULL
);

-- Schema for global_inventory
CREATE TABLE global_inventory (
    id BIGINT PRIMARY KEY,
    num_blue_ml INTEGER NOT NULL DEFAULT 0,
    num_green_ml INTEGER NOT NULL DEFAULT 0,
    num_red_ml INTEGER NOT NULL DEFAULT 0,
    num_dark_ml INTEGER NOT NULL DEFAULT 0,
    gold INTEGER NOT NULL DEFAULT 100,
    potion_capacity INTEGER NOT NULL DEFAULT 50,
    ml_capacity INTEGER NOT NULL DEFAULT 10000,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Insert default row
INSERT INTO global_inventory3 (id, num_blue_ml, num_green_ml, num_red_ml, num_dark_ml, gold, potion_capacity, ml_capacity, created_at)
VALUES (1, 0, 0, 0, 0, 100, 50, 10000, NOW());

-- Schema for potion_info_table
CREATE TABLE potion_info_table (
    id SERIAL PRIMARY KEY,
    potion_sku TEXT NOT NULL,
    inventory INTEGER NOT NULL DEFAULT 0,
    price INTEGER NOT NULL DEFAULT 48,
    potion_distribution INTEGER[] NOT NULL
);

-- Insert data into potion_info_table3
INSERT INTO potion_info_table3 (potion_sku, potion_distribution)
VALUES 
    ('red', ARRAY[100, 0, 0, 0]),
    ('green', ARRAY[0, 100, 0, 0]),
    ('blue', ARRAY[0, 0, 100, 0]),
    ('dark', ARRAY[0, 0, 0, 100]),
    ('yellow', ARRAY[50, 0, 50, 0]),
    ('cyan', ARRAY[0, 50, 50, 0]);

-- Schema for carts
CREATE TABLE carts (
    id BIGINT PRIMARY KEY,
    cart_id BIGINT,
    potion_id BIGINT,
    FOREIGN KEY (cart_id) REFERENCES cart_order_table3(id) ON DELETE SET NULL,
    FOREIGN KEY (potion_id) REFERENCES potion_info_table3(id) ON DELETE SET NULL,
    quantity BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Schema for potions
CREATE TABLE potions (
    potion_id BIGINT PRIMARY KEY,
    quantity BIGINT NOT NULL,
    potion_type TEXT NOT NULL,
    potion_order_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    time_id BIGINT,
    FOREIGN KEY (time_id) REFERENCES date3(id) ON DELETE SET NULL,
    FOREIGN KEY (potion_order_id) REFERENCES potion_order_table3(potion_order_id) ON DELETE SET NULL  -- Corrected reference
);

-- Schema for barrel_order_table
CREATE TABLE barrel_order_table (
    barrel_order_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    gold_cost INTEGER NOT NULL
);

-- Schema for barrels
CREATE TABLE barrels (
    barrel_id BIGINT PRIMARY KEY,
    barrel_order_id INTEGER NOT NULL,
    barrel_type TEXT NOT NULL,
    quantity_ml BIGINT NOT NULL,
    time_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (time_id) REFERENCES date3(id) ON DELETE SET NULL,
    FOREIGN KEY (barrel_order_id) REFERENCES barrel_order_table3(barrel_order_id) ON DELETE SET NULL
);
