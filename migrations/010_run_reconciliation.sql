-- Serialize v9-to-v10 reconciliation with any in-flight reservation or receipt.
SELECT pg_advisory_xact_lock(4197832742);
ALTER TABLE public.workforce_runs ALTER COLUMN reserved_microusd TYPE bigint;

-- Legacy runs predate this ledger. Repair only pooled runs; keep their state,
-- leases, journal and issued receipts (including historical corrections) intact.
WITH balances AS (
 SELECT r.id AS run, coalesce(sum(l.held + l.spent),0) AS exposure
 FROM public.workforce_runs r LEFT JOIN amc_ops.attempts a ON a.run=r.id
 LEFT JOIN amc_ops.ledger l ON l.id=a.id
 WHERE r.execution_mode='pool' GROUP BY r.id
)
UPDATE public.workforce_runs r SET reserved_microusd=b.exposure
 FROM balances b WHERE r.id=b.run AND r.execution_mode='pool'
 AND r.reserved_microusd IS DISTINCT FROM b.exposure;

CREATE OR REPLACE FUNCTION amc_ops.bill(t text,i uuid,amount bigint,ref text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a amc_ops.attempts; prior amc_ops.ledger; h bigint; s bigint;
BEGIN
 PERFORM amc_ops.authorize(t);
 IF amount IS NULL OR amount NOT BETWEEN 0 AND 100000000000000 OR ref IS NULL OR length(trim(ref)) NOT BETWEEN 1 AND 160 THEN
  RAISE check_violation;
 END IF;
 PERFORM pg_advisory_xact_lock(4197832742);
 SELECT * INTO a FROM amc_ops.attempts WHERE id=i AND tenant=t AND status='closed';
 IF NOT FOUND OR EXISTS(SELECT FROM amc_ops.ledger WHERE id=i AND event='unsent') THEN RETURN false; END IF;
 SELECT * INTO prior FROM amc_ops.ledger WHERE tenant=t AND receipt=ref;
 IF FOUND THEN RETURN prior.id=i AND prior.absolute_cost=amount; END IF;

 SELECT sum(held),sum(spent) INTO STRICT h,s FROM amc_ops.ledger WHERE id=i GROUP BY id;
 -- Release outstanding holds and replace the previous spend with the absolute
 -- invoice amount. Both balances commit or roll back together, including refunds.
 UPDATE public.workforce_runs SET reserved_microusd=reserved_microusd + (amount-s-h)
 WHERE id=a.run AND tenant_id=t AND execution_mode='pool';
 IF NOT FOUND THEN RAISE EXCEPTION 'Missing pooled run for receipt'; END IF;
 INSERT INTO amc_ops.ledger(id,tenant,month,event,receipt,actor,held,spent,absolute_cost)
 VALUES(i,t,a.month,'receipt',ref,current_setting('amc.user_id'),-h,amount-s,amount);
 RETURN true;
END $$;
