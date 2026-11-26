"""
ChargeSense Hardware & System Buzzer Service
Sounds loud audible hardware alarms through the laptop's physical speakers
using Windows system alarm media (winsound.PlaySound) and system beeps.
Runs asynchronously in daemon threads so it never blocks web requests.
"""

import sys
import threading
import time
import os

class BuzzerService:
    """Controls physical laptop speaker alarms and system buzzer."""

    def __init__(self):
        self._is_active = False
        self._lock = threading.Lock()
        self._alarm_file = r'C:\Windows\Media\Alarm01.wav'
        if not os.path.exists(self._alarm_file):
            self._alarm_file = r'C:\Windows\Media\notify.wav'

    @property
    def is_active(self) -> bool:
        return self._is_active

    def start_buzzer(self, max_duration_sec: int = 45):
        """
        Starts the continuous hardware alarm buzzer loop.
        Plays Windows system alarm wav through laptop speakers.
        Automatically stops after max_duration_sec if not manually muted.
        """
        with self._lock:
            if self._is_active:
                return  # Already ringing
            self._is_active = True

        def _alarm_worker():
            try:
                if sys.platform == 'win32':
                    import winsound
                    # SND_ASYNC (1) | SND_LOOP (8) | SND_FILENAME (0x20000) = 0x20009
                    flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
                    winsound.PlaySound(self._alarm_file, flags)

                    # Monitor duration or manual mute
                    start_time = time.time()
                    while self._is_active and (time.time() - start_time < max_duration_sec):
                        time.sleep(0.5)

                    # Purge / stop sound
                    winsound.PlaySound(None, winsound.SND_PURGE)
                else:
                    for _ in range(max(1, max_duration_sec * 2)):
                        if not self._is_active:
                            break
                        print("\a", end="", flush=True)
                        time.sleep(0.5)
            except Exception as e:
                print(f"[BuzzerService Error] {e}")
            finally:
                with self._lock:
                    self._is_active = False

        thread = threading.Thread(target=_alarm_worker, daemon=True)
        thread.start()
        print(f"[ChargeSense Buzzer] Hardware alarm started on laptop speakers (file: {self._alarm_file}).")

    def stop_buzzer(self):
        """Stops the active hardware buzzer immediately."""
        with self._lock:
            self._is_active = False

        if sys.platform == 'win32':
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        print("[ChargeSense Buzzer] Hardware alarm silenced.")

    def play_test_beep(self, duration_sec: float = 2.0):
        """Plays a brief 2-second test chime/buzzer through physical laptop speakers."""
        def _test_worker():
            try:
                if sys.platform == 'win32':
                    import winsound
                    # Play Alarm01 for test duration
                    winsound.PlaySound(self._alarm_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                    time.sleep(duration_sec)
                    winsound.PlaySound(None, winsound.SND_PURGE)
                else:
                    print("\a", end="", flush=True)
            except Exception as e:
                print(f"[BuzzerService Test Error] {e}")

        threading.Thread(target=_test_worker, daemon=True).start()


buzzer_service = BuzzerService()
