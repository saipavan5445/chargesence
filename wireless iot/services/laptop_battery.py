"""
ChargeSense Real Hardware Laptop Battery Reader
Reads live physical laptop battery telemetry on Windows via kernel32.GetSystemPowerStatus.
No external drivers or admin permissions needed.
"""

import ctypes
import time
from datetime import datetime


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', ctypes.c_byte),
        ('BatteryFlag', ctypes.c_byte),
        ('BatteryLifePercent', ctypes.c_byte),
        ('SystemStatusFlag', ctypes.c_byte),
        ('BatteryLifeTime', ctypes.c_ulong),
        ('BatteryFullLifeTime', ctypes.c_ulong),
    ]


class LaptopBatteryReader:
    """Reads real laptop battery hardware statistics."""

    def __init__(self):
        self._last_reading_time = None
        self._last_percentage = None
        self._calculated_rate = 1.0  # % per minute default

    def read_battery(self) -> dict:
        """
        Queries Windows kernel for physical battery telemetry.
        Returns:
            dict containing percentage, charging status, AC connection,
            voltage estimate, and calculated rate.
        """
        status = SYSTEM_POWER_STATUS()
        success = False

        try:
            success = bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)))
        except Exception:
            success = False

        if not success or status.BatteryLifePercent == 255:
            # Fallback if desktop without battery or API error
            return {
                'available': False,
                'percentage': 50.0,
                'is_charging': True,
                'ac_plugged': True,
                'status': 'charging',
                'charging_rate': 1.0,
                'source': 'fallback'
            }

        pct = float(status.BatteryLifePercent)
        ac_plugged = (status.ACLineStatus == 1)
        # BatteryFlag: 1=High, 2=Low, 4=Critical, 8=Charging, 128=No system battery
        is_charging = (status.BatteryFlag & 8) != 0 or ac_plugged

        now = time.time()
        # Compute real charging speed if successive readings show delta
        if self._last_reading_time and self._last_percentage is not None:
            elapsed_min = (now - self._last_reading_time) / 60.0
            if elapsed_min >= 0.5:
                delta = pct - self._last_percentage
                if delta > 0:
                    self._calculated_rate = max(0.2, min(4.0, round(delta / elapsed_min, 2)))
                self._last_percentage = pct
                self._last_reading_time = now
        else:
            self._last_percentage = pct
            self._last_reading_time = now

        # Status string
        if is_charging:
            current_status = 'charging' if pct < 100 else 'completed'
        else:
            current_status = 'discharging'

        # Estimate voltage based on real chemistry curve (3.6V - 4.25V)
        voltage = round(3.60 + 0.55 * (pct / 100.0) + 0.10 * ((pct / 100.0) ** 3), 2)

        return {
            'available': True,
            'percentage': round(pct, 1),
            'is_charging': is_charging,
            'ac_plugged': ac_plugged,
            'battery_flag': int(status.BatteryFlag),
            'status': current_status,
            'voltage': voltage,
            'charging_rate': self._calculated_rate,
            'source': 'physical_laptop_hardware'
        }


# Singleton instance
laptop_reader = LaptopBatteryReader()
