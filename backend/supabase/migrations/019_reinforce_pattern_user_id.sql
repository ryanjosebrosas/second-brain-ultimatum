-- Migration 019: Add user_id parameter to reinforce_pattern RPC
-- Ensures pattern reinforcement is scoped to the owning user

CREATE OR REPLACE FUNCTION reinforce_pattern(
  p_pattern_id UUID,
  p_new_evidence TEXT[] DEFAULT '{}',
  p_user_id TEXT DEFAULT NULL
)
RETURNS SETOF patterns
LANGUAGE plpgsql
AS $$
DECLARE
  v_new_count INT;
  v_new_confidence TEXT;
BEGIN
  -- Verify ownership if user_id provided
  IF p_user_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM patterns WHERE id = p_pattern_id AND user_id = p_user_id
    ) THEN
      RAISE EXCEPTION 'Pattern % not found for user %', p_pattern_id, p_user_id;
    END IF;
  END IF;

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
VALUES ('019_reinforce_pattern_user_id', 'Add user_id parameter to reinforce_pattern RPC')
ON CONFLICT (version) DO NOTHING;
