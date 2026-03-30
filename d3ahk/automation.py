from __future__ import annotations

import threading
import time

from d3ahk.models import TriggerConfig
from d3ahk.win32_input import execute_trigger


class TriggerWorker(threading.Thread):
    def __init__(self, trigger: TriggerConfig, stop_event: threading.Event) -> None:
        super().__init__(daemon=True)
        self.trigger = trigger
        self.stop_event = stop_event

    def run(self) -> None:
        interval_seconds = max(self.trigger.interval_ms, 1) / 1000.0
        next_run = time.perf_counter()

        while not self.stop_event.is_set():
            execute_trigger(self.trigger)
            next_run += interval_seconds
            remaining = next_run - time.perf_counter()
            if remaining <= 0:
                next_run = time.perf_counter()
                continue
            self.stop_event.wait(remaining)


class AutomationController:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._workers: list[TriggerWorker] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self, triggers: list[TriggerConfig]) -> None:
        self.stop()
        active_triggers = [trigger for trigger in triggers if trigger.enabled]
        self._stop_event = threading.Event()
        self._workers = [TriggerWorker(trigger, self._stop_event) for trigger in active_triggers]

        for worker in self._workers:
            worker.start()

        self._running = bool(self._workers)

    def stop(self) -> None:
        self._stop_event.set()
        for worker in self._workers:
            worker.join(timeout=0.2)
        self._workers = []
        self._running = False
