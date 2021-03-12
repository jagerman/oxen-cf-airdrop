--
-- PostgreSQL database dump
--

-- Dumped from database version 13.2 (Debian 13.2-1)
-- Dumped by pg_dump version 13.2 (Debian 13.2-1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: shares_to_score(double precision, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.shares_to_score(shares double precision, shares_rank bigint) RETURNS double precision
    LANGUAGE sql IMMUTABLE STRICT
    AS $$SELECT shares * CASE WHEN shares_rank <= 30*24 THEN 1.0 WHEN shares_rank <= 60*24 THEN 1.2 ELSE 1.4 END;$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: wallet_snapshot_shares; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallet_snapshot_shares (
    wallet integer NOT NULL,
    height integer NOT NULL,
    shares double precision NOT NULL
);


--
-- Name: wallet_shares; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.wallet_shares AS
 SELECT x.wallet,
    x.height,
    x.shares,
    public.shares_to_score(x.shares, x.rank) AS score
   FROM ( SELECT wallet_snapshot_shares.wallet,
            wallet_snapshot_shares.height,
            wallet_snapshot_shares.shares,
            row_number() OVER (PARTITION BY wallet_snapshot_shares.wallet ORDER BY wallet_snapshot_shares.shares DESC, wallet_snapshot_shares.height) AS rank
           FROM public.wallet_snapshot_shares) x;


--
-- Name: aggregate_shares; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.aggregate_shares AS
 SELECT wallets.id AS wallet,
    count(wallet_shares.wallet) AS snapshots,
    coalesce(sum(wallet_shares.shares), 0.0) AS shares,
    coalesce(sum(wallet_shares.score), 0.0) AS score
   FROM wallets LEFT JOIN wallet_shares ON wallet_shares.wallet = wallets.id
  GROUP BY wallets.id
  WITH NO DATA;


--
-- Name: snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.snapshots (
    height integer NOT NULL,
    blockhash character varying NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: wallets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallets (
    id integer NOT NULL,
    address character varying NOT NULL,
    destination character varying NOT NULL,
    signature character varying NOT NULL
);


--
-- Name: wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.wallets_id_seq OWNED BY public.wallets.id;


--
-- Name: wallets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets ALTER COLUMN id SET DEFAULT nextval('public.wallets_id_seq'::regclass);


--
-- Name: snapshots snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.snapshots
    ADD CONSTRAINT snapshots_pkey PRIMARY KEY (height);


--
-- Name: wallet_snapshot_shares wallet_snapshot_shares_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_snapshot_shares
    ADD CONSTRAINT wallet_snapshot_shares_pkey PRIMARY KEY (wallet, height);


--
-- Name: wallets wallets_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_address_key UNIQUE (address);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: wallet_snapshot_shares_height_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX wallet_snapshot_shares_height_idx ON public.wallet_snapshot_shares USING btree (height);


--
-- Name: wallet_snapshot_shares_wallet_shares_height_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX wallet_snapshot_shares_wallet_shares_height_idx ON public.wallet_snapshot_shares USING btree (wallet, shares DESC, height);


--
-- Name: wallet_snapshot_shares wallet_snapshot_shares_height_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_snapshot_shares
    ADD CONSTRAINT wallet_snapshot_shares_height_fkey FOREIGN KEY (height) REFERENCES public.snapshots(height);


--
-- Name: wallet_snapshot_shares wallet_snapshot_shares_wallet_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallet_snapshot_shares
    ADD CONSTRAINT wallet_snapshot_shares_wallet_fkey FOREIGN KEY (wallet) REFERENCES public.wallets(id);


--
-- PostgreSQL database dump complete
--

