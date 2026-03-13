import logging

try:
    import numpy as np
except ImportError:
    np = None

try:
    import xgboost as xgb
except ImportError:
    xgb = None

logger = logging.getLogger(__name__)


class AmplificationPredictor:
    def __init__(self, model_path: str = "ml-agent/models/amplification/xgb_virality.model"):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        if xgb is None:
            logger.warning("XGBoost is not installed. Using heuristic reach prediction.")
            return

        try:
            self.model = xgb.Booster()
            self.model.load_model(self.model_path)
            logger.info("XGBoost amplification model loaded.")
        except Exception as exc:
            logger.warning("Failed to load XGBoost model. File may not exist yet: %s", exc)
            self.model = None

    def _heuristic_prediction(self, features: dict) -> int:
        followers = float(features.get("account_followers", 100) or 100)
        engagement_volume = float(features.get("engagement_volume", 0) or 0)
        avg_rt_rate = float(features.get("avg_rt_rate", 0.0) or 0.0)
        centrality = float(features.get("centrality", 0.0) or 0.0)
        heuristic = followers * (1.2 + avg_rt_rate * 3.0 + centrality * 2.0) + engagement_volume * 8
        return int(max(50, heuristic))

    def predict(self, features: dict) -> int:
        if not self.model or xgb is None or np is None:
            return self._heuristic_prediction(features)

        try:
            x = np.array(
                [[
                    features.get("account_followers", 0),
                    features.get("avg_rt_rate", 0.0),
                    features.get("sentiment", 0.0),
                    features.get("time_of_day", 12),
                    features.get("centrality", 0.0),
                ]]
            )
            dmatrix = xgb.DMatrix(x)
            pred = self.model.predict(dmatrix)[0]
            return int(max(0, pred))
        except Exception as exc:
            logger.error("XGB prediction failed: %s", exc)
            return self._heuristic_prediction(features)


predictor = AmplificationPredictor()


def get_reach_prediction(features_dict: dict) -> int:
    return predictor.predict(features_dict)
