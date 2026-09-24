import numpy as np


class KeyframeReducer:

    def __init__(
        self,
        tolerance=0.4,
    ):

        self.tolerance = float(
            tolerance
        )

    def reduce(self, frames):

        if not frames:
            return []

        if len(frames) <= 2:
            return list(frames)

        result = []

        # Primer frame SIEMPRE.
        result.append(frames[0])

        last_saved = frames[0]

        for current in frames[1:-1]:

            difference = self._difference(
                last_saved,
                current,
            )

            if difference >= self.tolerance:

                result.append(current)

                last_saved = current

        # Último frame SIEMPRE.
        if result[-1] is not frames[-1]:
            result.append(frames[-1])

        return result

    def _difference(
        self,
        a,
        b,
    ):

        points_a = a.get(
            "keypoints",
            {},
        )

        points_b = b.get(
            "keypoints",
            {},
        )

        differences = []

        for name in points_a:

            if name not in points_b:
                continue

            pa = points_a[name]
            pb = points_b[name]

            if (
                pa["confidence"] < 0.35
                or pb["confidence"] < 0.35
            ):
                continue

            dx = (
                pb["x"]
                - pa["x"]
            )

            dy = (
                pb["y"]
                - pa["y"]
            )

            differences.append(
                np.sqrt(
                    dx * dx
                    + dy * dy
                )
            )

        if not differences:
            return 0.0

        # El cambio más grande decide si merece keyframe.
        return float(
            max(differences)
        )