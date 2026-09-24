class PoseSmoother:

    def __init__(self, alpha=0.30):
        self.alpha = float(alpha)
        self.previous = None

    def reset(self):
        self.previous = None

    def update(self, keypoints):

        if self.previous is None:
            self.previous = self._copy(keypoints)
            return self._copy(self.previous)

        result = {}

        for name, current in keypoints.items():

            previous = self.previous.get(name)

            if previous is None:
                result[name] = dict(current)
                continue

            alpha = self.alpha

            x = (
                previous["x"] * (1.0 - alpha)
                + current["x"] * alpha
            )

            y = (
                previous["y"] * (1.0 - alpha)
                + current["y"] * alpha
            )

            result[name] = {
                "x": x,
                "y": y,
                "confidence": current["confidence"],
            }

        self.previous = self._copy(result)

        return result

    @staticmethod
    def _copy(keypoints):
        return {
            name: {
                "x": float(point["x"]),
                "y": float(point["y"]),
                "confidence": float(point["confidence"]),
            }
            for name, point in keypoints.items()
        }