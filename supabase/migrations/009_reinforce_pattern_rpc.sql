-- Atomic pattern reinforcement function
-- Replaces non-atomic SELECT + UPDATE in Python StorageService
-- Prevents race condition when two agents reinforce the same pattern concurrently

CREATE OR REPLACE FUNCTION reinforce_pattern(
  p_pattern_id UUID,
  p_new_evidence TEXT[] DEFAULT '{}'
)
RETURNS SETOF patterns
LANGUAGE plpgsql
AS $$
DECLARE
  v_new_count INT;
  v_new_confidence TEXT;
BEGIN
  -- Atomically increment use_count and get new value
  UPDATE patterns
  SET use_count = use_count + 1,
      date_updated = current_date,
      updated_at = now()
  WHERE id = p_pattern_id
  RETURNING use_count INTO v_new_count;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Pattern % not found', p_pattern_id;
  END IF;

  -- Compute confidence from new use_count
  IF v_new_count >= 5 THEN
    v_new_confidence := 'HIGH';
  ELSIF v_new_count >= 2 THEN
    v_new_confidence := 'MEDIUM';
  ELSE
    v_new_confidence := 'LOW';
  END IF;

  -- Update confidence and append evidence
  UPDATE patterns
  SET confidence = v_new_confidence,
      evidence = COALESCE(evidence, '{}') || p_new_evidence
  WHERE id = p_pattern_id;

  -- Return the updated row
  RETURN QUERY SELECT * FROM patterns WHERE id = p_pattern_id;
END;
$$;

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('009_reinforce_pattern_rpc', 'Atomic reinforce_pattern RPC function')
ON CONFLICT (version) DO NOTHING;
