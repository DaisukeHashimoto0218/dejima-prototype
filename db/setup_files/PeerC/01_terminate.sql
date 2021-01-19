CREATE EXTENSION IF NOT EXISTS plsh;

CREATE OR REPLACE FUNCTION public.terminate_run_shell(text) RETURNS text AS $$
#!/bin/sh

result=$(curl -s -X POST -H "Content-Type: application/json" $DEJIMA_TERMINATION_ENDPOINT -d "$1")

$$ LANGUAGE plsh;

CREATE OR REPLACE FUNCTION public.terminate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
  DECLARE
  json_data text;
  result text;
  xid text;
  user_name text;
  BEGIN
  user_name := (SELECT session_user);
  IF NOT (user_name = 'dejima') THEN 
    IF NOT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = 'termination_flag') THEN
        -- RAISE LOG 'execute procedure dejima_b_c_delta_action';
        CREATE TEMPORARY TABLE termination_flag ON COMMIT DROP AS (SELECT true as finish);

        xid := (SELECT txid_current());
        json_data := concat('{"xid": "PeerC_', xid, '", "result": "commit"}');
        result := public.terminate_run_shell(json_data);
    END IF;
  END IF;
  RETURN null;
  END;
$$;

DROP TRIGGER IF EXISTS zzz_terminate_trigger ON public.bt;
CREATE CONSTRAINT TRIGGER zzz_terminate_trigger
    AFTER INSERT OR UPDATE OR DELETE ON
    public.bt DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.terminate();
