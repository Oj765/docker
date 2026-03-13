CREATE TABLE IF NOT EXISTS virality_metrics (
    time        TIMESTAMPTZ NOT NULL,
    claim_id    TEXT NOT NULL,
    platform    TEXT,
    predicted_6h_reach  BIGINT,
    actual_reach        BIGINT,
    risk_score          FLOAT
);

SELECT create_hypertable('virality_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_virality_claim_id ON virality_metrics (claim_id, time DESC);