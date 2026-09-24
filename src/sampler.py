import time


class FixedRateSampler:

    def __init__(self, fps):

        self.interval = 1.0 / float(fps)

        self.started = False

        self.start_time = 0.0

        self.next_sample_time = 0.0

        self.frame_id = 0

    def reset(self):

        self.started = False

        self.start_time = 0.0

        self.next_sample_time = 0.0

        self.frame_id = 0

    def update(self):

        now = time.perf_counter()

        if not self.started:

            self.started = True

            self.start_time = now

            self.next_sample_time = 0.0

            self.frame_id = 0

            return {
                "frame_id": 0,
                "time": 0.0,
            }

        elapsed = now - self.start_time

        if elapsed + 0.000001 < self.next_sample_time:
            return None

        frame_id = self.frame_id

        self.frame_id += 1

        self.next_sample_time = (
            self.frame_id * self.interval
        )

        return {
            "frame_id": frame_id,
            "time": frame_id * self.interval,
        }