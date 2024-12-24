CREATE SEQUENCE IF NOT EXISTS roles_id_seq;
CREATE SEQUENCE IF NOT EXISTS store_locations_id_seq;
CREATE SEQUENCE IF NOT EXISTS products_id_seq;
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE SEQUENCE IF NOT EXISTS audit_id_seq;

CREATE TABLE IF NOT EXISTS public.roles
(
    id integer NOT NULL DEFAULT nextval('roles_id_seq'::regclass),
    name text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT roles_pkey PRIMARY KEY (id),
    CONSTRAINT roles_name_key UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS public.store_locations
(
    id integer NOT NULL DEFAULT nextval('store_locations_id_seq'::regclass),
    city text COLLATE pg_catalog."default" NOT NULL,
    store integer NOT NULL,
    CONSTRAINT store_locations_pkey PRIMARY KEY (id),
    CONSTRAINT store_locations_city_store_number_key UNIQUE (city, store)
);

CREATE TABLE IF NOT EXISTS public.products
(
    id integer NOT NULL DEFAULT nextval('products_id_seq'::regclass),
    name text COLLATE pg_catalog."default" NOT NULL,
    quantity integer NOT NULL,
    purchase_price numeric(10,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    store_id integer NOT NULL,
    CONSTRAINT products_pkey PRIMARY KEY (id),
    CONSTRAINT products_store_id_fkey FOREIGN KEY (store_id)
        REFERENCES public.store_locations (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT products_quantity_check CHECK (quantity >= 0),
    CONSTRAINT products_purchase_price_check CHECK (purchase_price >= 0::numeric)
);

CREATE TABLE IF NOT EXISTS public.users
(
    id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    username text COLLATE pg_catalog."default" NOT NULL,
    password_hash text COLLATE pg_catalog."default" NOT NULL,
    role_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT unique_username UNIQUE (username),
    CONSTRAINT users_username_key UNIQUE (username),
    CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id)
        REFERENCES public.roles (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
);

CREATE TABLE audit (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    role_id INT NOT NULL,
    product_id INT NOT NULL,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_username FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    CONSTRAINT fk_audit_product_id FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_store_locations_city_store ON public.store_locations (city, store);
CREATE INDEX IF NOT EXISTS idx_products_store_id ON public.products (store_id);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON public.users (role_id);

INSERT INTO public.roles (name) VALUES ('admin')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.roles (name) VALUES ('moder')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.roles (name) VALUES ('Banned')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.store_locations (city, store) VALUES 
    ('Новосибирск', 1),
    ('Новосибирск', 2),
    ('Новосибирск', 3),
    ('Барнаул', 1),
    ('Барнаул', 2),
    ('Бийск', 1)
ON CONFLICT (city, store) DO NOTHING;