CREATE SEQUENCE IF NOT EXISTS roles_id_seq;
CREATE SEQUENCE IF NOT EXISTS products_id_seq;
CREATE SEQUENCE IF NOT EXISTS users_id_seq;

CREATE TABLE IF NOT EXISTS public.roles
(
    id integer NOT NULL DEFAULT nextval('roles_id_seq'::regclass),
    name text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT roles_pkey PRIMARY KEY (id),
    CONSTRAINT roles_name_key UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS public.store_locations
(
    city text COLLATE pg_catalog."default" NOT NULL,
    store integer NOT NULL,
    CONSTRAINT unique_city_store UNIQUE (city, store)
);

CREATE TABLE IF NOT EXISTS public.products
(
    id integer NOT NULL DEFAULT nextval('products_id_seq'::regclass),
    name text COLLATE pg_catalog."default" NOT NULL,
    quantity integer NOT NULL,
    purchase_price numeric(10,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    city text COLLATE pg_catalog."default" NOT NULL,
    store integer NOT NULL,
    CONSTRAINT products_pkey PRIMARY KEY (id),
    CONSTRAINT fk_products_store_locations FOREIGN KEY (city, store)
        REFERENCES public.store_locations (city, store) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT products_purchase_price_check CHECK (purchase_price >= 0::numeric),
    CONSTRAINT products_quantity_check CHECK (quantity >= 0)
);

CREATE TABLE IF NOT EXISTS public.users
(
    id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    username text COLLATE pg_catalog."default" NOT NULL,
    password_hash text COLLATE pg_catalog."default" NOT NULL,
    role_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_username_key UNIQUE (username),
    CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id)
        REFERENCES public.roles (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_store_locations_city_store ON public.store_locations (city, store);
CREATE INDEX IF NOT EXISTS idx_products_city_store ON public.products (city, store);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON public.users (role_id);

INSERT INTO public.roles (name) VALUES ('admin')
ON CONFLICT (name) DO NOTHING;
