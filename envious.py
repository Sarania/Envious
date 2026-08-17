#!/usr/bin/env python3
"""
=================================================
                  Envious
=================================================
Description:
Envious is a powerful terminal based tool for managing Nvidia graphics cards.
It supports overclocking, profiles, fan control, and more.

Dependencies:
nvidia-ml-py > 11.5 for all features. pynvml /may/ also work.
Nvidia Driver 555.xx or greater for all features.

License:
MIT License - See below for full text

=================================================
Copyright (c) 2024 Blyss Sarania

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

=================================================
Created on: Tue Oct 1, 2024
@author: Blyss Sarania
=================================================
"""

import argparse
import os
import sys
import textwrap
import time

import pynvml as nv

__VERSION__ = "1.60"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Envious")
    parser.add_argument(
        "--gpu-number",
        type=int,
        default=0,
        help="(offline)(interactive) Specify the GPU index (default: 0)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="(offline)(interactive) Disable the use of any color at all",
    )
    parser.add_argument(
        "--refresh-rate",
        type=int,
        default=1000,
        help="(interactive) Specify how often to refresh the monitor, in milliseconds. (Default: 1000)",
    )
    parser.add_argument(
        "--reactive-color",
        action="store_true",
        help="(interactive) Uses color to indicate the intensity of values",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help='(interactive)(root) Enable interactive mode for monitor so you can change clocks/fan/power/profile. Type "h" for help',
    )
    parser.add_argument(
        "--set-clocks",
        nargs=2,
        type=int,
        help="(offline)(root) Set core and memory clock offsets (in MHz) respectively. "
        "Example: --set-clocks -150 500",
    )
    parser.add_argument(
        "--set-power-limit",
        type=int,
        help="(offline)(root) Set the power limit (in watts). Example: --set-power-limit 300",
    )
    parser.add_argument(
        "--set-custom-fan",
        type=int,
        help="(offline)(root) Set a custom fan percentage for all fans. !BE CAREFUL! as this changes the fan control "
        "policy to manual!!! Only values 30-100 are accepted.",
    )
    parser.add_argument(
        "--set-profile",
        type=int,
        help="(offline)(root)(exclusive) Apply one of the custom profiles you've created - valid values are 1 through 4. Blocks other offline switches from processing!",
    )
    parser.add_argument(
        "--set-max-fan",
        action="store_true",
        help="(offline)(root) Set all fans to maximum speed",
    )
    parser.add_argument(
        "--set-auto-fan",
        action="store_true",
        help="(offline)(root) Restore fan control to automatic mode",
    )
    parser.add_argument(
        "--accept-risks",
        action="store_true",
        help="(offline) Suppress any warning messages normally printed in CLI mode(for making logging less noisy). User accepts ALL risks of overclocking/altering power limits/fan settings! No effect in interactive mode.",
    )
    return parser.parse_args()


def add_sign(offset) -> str:
    """Return a string with a '+' prefix for positive numbers."""
    return f"+{offset}" if offset > 0 else str(offset)


def rectify_nvml_overflow(offset_value) -> int:
    """Rectifies a potential bug/weirdness in the way some versions of NVML return offsets"""
    if offset_value > 100000:
        offset_value -= 4294966
    return offset_value


class EnviousApp:
    """Main application class for both offline and interactive modes."""

    def __init__(self, args: argparse.Namespace, gpu):
        self.args = args
        self.gpu = gpu
        self.gpu_name = nv.nvmlDeviceGetName(gpu)
        self.num_gpus = nv.nvmlDeviceGetCount()
        self.default_power_limit = (
            nv.nvmlDeviceGetPowerManagementDefaultLimit(gpu) / 1000
        )
        self.profile_dir = self._determine_profile_dir()

        self.use_color = not args.no_color and (
            os.getenv("TERM") != "dumb" and os.getenv("TERM") is not None
        )

        # ANSI color codes for offline mode
        self.ansi_warn = "\033[0;33;40m" if self.use_color else ""
        self.ansi_yellow = "\033[0;33m" if self.use_color else ""
        self.ansi_magenta = "\033[0;35m" if self.use_color else ""
        self.ansi_green = "\033[0;32m" if self.use_color else ""
        self.nc = "\033[0m" if self.use_color else ""

        # Curses state (initialised in interactive mode)
        self.curses = None
        self.psutil = None
        self.input_start = 14
        self.profile_exists = [False] * 5
        self.active_profile = 0
        self.last_active_profile = []
        self.fan_policy = None
        self.fan_warning_done = False
        self.max_text_width = 59
        self.mid_ref = 0

    @staticmethod
    def _determine_profile_dir() -> str:
        """Return the directory where profiles are stored."""
        exec_path = os.path.dirname(os.path.realpath(__file__))
        return "/var/lib/envious" if exec_path == "/usr/bin" else exec_path

    # ----------------------------------------------------------------------
    # Offline / CLI mode
    # ----------------------------------------------------------------------
    def run_offline(self) -> None:
        """Execute the non‑interactive (offline) commands."""

        def print_space_or_dont() -> None:
            """Adds a blank line in the more verbose mode else not"""
            if not self.args.accept_risks:
                print()

        if not self.args.accept_risks:
            print(f"{self.ansi_magenta}Envious Offline Mode{self.nc}")
            print("_________________________________________")
            print(
                f"{self.ansi_yellow}User accepts ALL risks of overclocking/altering power limits/fan settings!{self.nc}"
            )
            print(
                "Additionally, root permission is needed for these changes and they will fail to apply without it."
            )
            print()
            print("Enabling persistence...")
        try:
            nv.nvmlDeviceSetPersistenceMode(self.gpu, 1)
        except nv.NVMLError as e:
            print(
                f"{self.ansi_warn}Some kind of NVML error prevented applying the requested change: {e}{self.nc}"
            )
        print_space_or_dont()

        if self.args.set_profile is not None:
            self._offline_load_profile(self.args.set_profile)
        else:
            if self.args.set_max_fan:
                self._offline_set_max_fan()
            elif self.args.set_auto_fan:
                self._offline_set_auto_fan()
            elif self.args.set_custom_fan is not None:
                self._offline_set_custom_fan()
            print_space_or_dont()
            if self.args.set_clocks is not None:
                self._offline_set_clocks()
            if self.args.set_power_limit is not None:
                self._offline_set_power_limit()

        print_space_or_dont()

    def _offline_set_max_fan(self) -> None:
        num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
        print(f"Found {num_fans} fans!")
        print("Attempting to set fans to max speed...")
        for i in range(num_fans):
            try:
                nv.nvmlDeviceSetFanControlPolicy(self.gpu, i, nv.NVML_FAN_POLICY_MANUAL)
                nv.nvmlDeviceSetFanSpeed_v2(self.gpu, i, 100)
                print(f"{self.ansi_green}Fan {i} set to max speed!{self.nc}")
            except nv.NVMLError as e:
                print(
                    f"{self.ansi_warn}Some kind of NVML error prevented applying the requested change: {e}{self.nc}"
                )

    def _offline_set_auto_fan(self) -> None:
        num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
        print(f"Found {num_fans} fans!")
        print("Attempting to restore fans to automatic control...")
        for i in range(num_fans):
            try:
                nv.nvmlDeviceSetFanControlPolicy(
                    self.gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW
                )
                nv.nvmlDeviceSetDefaultFanSpeed_v2(self.gpu, i)
                print(
                    f"{self.ansi_green}Fan {i} restored to automatic control!{self.nc}"
                )
            except nv.NVMLError as e:
                print(
                    f"{self.ansi_warn}Some kind of NVML error prevented applying the requested change: {e}{self.nc}"
                )

    def _offline_set_custom_fan(self) -> None:
        new_speed = self.args.set_custom_fan
        if 101 > new_speed > 29:
            num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
            print(f"Found {num_fans} fans!")
            print(f"Attempting to set fans to {new_speed}%...")
            for i in range(num_fans):
                try:
                    nv.nvmlDeviceSetFanControlPolicy(
                        self.gpu, i, nv.NVML_FAN_POLICY_MANUAL
                    )
                    nv.nvmlDeviceSetFanSpeed_v2(self.gpu, i, new_speed)
                    print(
                        f"{self.ansi_green}Fan {i} set to {new_speed}%! "
                        f"{self.ansi_yellow}Fan control policy is now MANUAL!{self.nc}"
                    )
                except nv.NVMLError as e:
                    print(
                        f"{self.ansi_warn}Some kind of NVML error prevented applying the requested change: {e}{self.nc}"
                    )
        elif new_speed > 100:
            print(
                f"{self.ansi_warn}Value {new_speed} invalid for fan control!{self.nc}"
            )
        else:
            print(f"{self.ansi_warn}Refusing to set fans below 30%! Sorry!{self.nc}")

    def _offline_set_clocks(self) -> None:
        core_offset, mem_offset = self.args.set_clocks
        print(
            f"Attempting to set core clock offset to {core_offset} MHz and "
            f"memory clock offset to {mem_offset} MHz..."
        )
        try:
            nv.nvmlDeviceSetGpcClkVfOffset(self.gpu, core_offset)
            nv.nvmlDeviceSetMemClkVfOffset(
                self.gpu, mem_offset * 2
            )  # Convert to NVML units
            print(
                f"{self.ansi_green}Set core clock offset to {core_offset} MHz and "
                f"memory clock offset to {mem_offset} MHz!{self.nc}"
            )
        except nv.NVMLError as e:
            print(
                f"{self.ansi_warn}Some kind of NVML error prevented applying the requested change: {e}{self.nc}"
            )

    def _offline_set_power_limit(self) -> None:
        print(f"Attempting to set power limit to {self.args.set_power_limit} W...")
        try:
            nv.nvmlDeviceSetPowerManagementLimit(
                self.gpu, self.args.set_power_limit * 1000
            )
            print(
                f"{self.ansi_green}Power limit set to {self.args.set_power_limit} W!{self.nc}"
            )
        except nv.NVMLError as e:
            print(
                f"{self.ansi_warn}Some kind of NVML error prevented applying the requested change: {e}{self.nc}"
            )

    def _offline_load_profile(self, profile_number: int) -> None:
        print(f"Loading profile {profile_number} for GPU {self.args.gpu_number}!")
        profile_path = os.path.join(
            self.profile_dir, f"profile{profile_number}_{self.args.gpu_number}.bnt"
        )
        try:
            if not 0 < profile_number < 5:
                print(f"{self.ansi_warn}Valid profiles are those in the range 1 to 4!")
                sys.exit(4)
            with open(profile_path, "r", encoding="utf-8") as f:
                new_core_offset = int(f.readline())
                new_mem_offset = int(f.readline())
                new_power_limit = int(f.readline())
                new_fan_policy = int(f.readline())
                new_fan_speed = int(f.readline())

            print(f"Setting core clock offset to {add_sign(new_core_offset)} Mhz...")
            nv.nvmlDeviceSetGpcClkVfOffset(self.gpu, new_core_offset)
            print(f"Setting mem clock offset to {add_sign(new_mem_offset)} Mhz...")
            nv.nvmlDeviceSetMemClkVfOffset(self.gpu, new_mem_offset * 2)
            print(f"Setting core power limit to {new_power_limit}...")
            nv.nvmlDeviceSetPowerManagementLimit(self.gpu, new_power_limit * 1000)

            if new_fan_policy == 1:
                if 101 > new_fan_speed > 29:
                    print(
                        f"Setting fan policy to manual and fan speed to {new_fan_speed}%..."
                    )
                    num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
                    for i in range(num_fans):
                        nv.nvmlDeviceSetFanControlPolicy(
                            self.gpu, i, nv.NVML_FAN_POLICY_MANUAL
                        )
                        nv.nvmlDeviceSetFanSpeed_v2(self.gpu, i, new_fan_speed)
                else:
                    raise ValueError("Invalid fan speed setting in profile!")
            else:
                print("Setting fan policy to automatic control...")
                num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
                for i in range(num_fans):
                    nv.nvmlDeviceSetFanControlPolicy(
                        self.gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW
                    )
                    nv.nvmlDeviceSetDefaultFanSpeed_v2(self.gpu, i)

            print(
                f"{self.ansi_green}Profile {profile_number} successfully applied!{self.nc}"
            )
        except ValueError as e:
            print(
                f"{self.ansi_warn}Some kind of value error prevented the profile loading: {e}{self.nc}"
            )
        except nv.NVMLError as e:
            print(
                f"{self.ansi_warn}Some kind of NVML error prevented the profile loading: {e}{self.nc}"
            )
        except FileNotFoundError:
            print(f"{self.ansi_warn}Profile was not found!{self.nc}")

    # ----------------------------------------------------------------------
    # Interactive (curses) mode
    # ----------------------------------------------------------------------
    def run_interactive(self) -> None:
        """Start the interactive terminal UI."""
        import curses

        self.curses = curses
        curses.wrapper(self._dashboard)

    def _dashboard(self, stdscr) -> None:
        """Main curses dashboard loop."""
        import ctypes

        import psutil

        self.psutil = psutil
        self.ctypes = ctypes

        self._init_colors()
        stdscr.clear()
        self.curses.curs_set(0)
        self.curses.echo()
        stdscr.nodelay(True)

        # Enable persistence for interactive mode
        if self.args.interactive:
            try:
                nv.nvmlDeviceSetPersistenceMode(self.gpu, 1)
            except nv.NVMLError as e:
                stdscr.addstr(
                    1,
                    2,
                    f"Unable to set driver to persistent for interactive mode: {e}",
                )
                for i in range(4, 0, -1):
                    stdscr.addstr(2, 2, f"Shutting down in {i}s...")
                    stdscr.refresh()
                    time.sleep(1)
                return

        self._refresh_profile_exists()
        self.last_active_profile = [0] * self.num_gpus
        self.active_profile = 0
        self.fan_policy = ctypes.c_uint()

        while True:
            stdscr.clear()

            # Read current sensor / clock values

            nv.nvmlDeviceGetFanControlPolicy_v2(
                self.gpu, 0, ctypes.byref(self.fan_policy)
            )
            fan_policy_str = "Manual" if self.fan_policy.value == 1 else "Auto"
            fan_speed = nv.nvmlDeviceGetFanSpeed(self.gpu)
            current_temperature = nv.nvmlDeviceGetTemperature(self.gpu, 0)
            current_power_usage = nv.nvmlDeviceGetPowerUsage(self.gpu) / 1000  # mW -> W
            utilization = nv.nvmlDeviceGetUtilizationRates(self.gpu)
            mem_info = nv.nvmlDeviceGetMemoryInfo(self.gpu)
            vram_str = (
                f"{mem_info.used / (1024**2):.2f} / {mem_info.total / (1024**2):.2f} MB"
            )
            temp_str = f"{current_temperature}°C | {fan_speed}% ({fan_policy_str})"

            current_core_offset = rectify_nvml_overflow(
                nv.nvmlDeviceGetGpcClkVfOffset(self.gpu)
            )
            core_offset_sign = add_sign(current_core_offset)
            core_clock = nv.nvmlDeviceGetClockInfo(self.gpu, nv.NVML_CLOCK_GRAPHICS)
            max_core_clock = nv.nvmlDeviceGetMaxClockInfo(
                self.gpu, nv.NVML_CLOCK_GRAPHICS
            )
            core_clock_str = (
                f"{core_clock} Mhz ({core_offset_sign} Mhz)"
                if current_core_offset != 0
                else f"{core_clock} Mhz"
            )

            current_mem_offset = (
                rectify_nvml_overflow(nv.nvmlDeviceGetMemClkVfOffset(self.gpu)) / 2
            )
            mem_offset_sign = add_sign(current_mem_offset)
            mem_clock = nv.nvmlDeviceGetClockInfo(self.gpu, nv.NVML_CLOCK_MEM)
            max_mem_clock = nv.nvmlDeviceGetMaxClockInfo(self.gpu, nv.NVML_CLOCK_MEM)
            mem_clock_str = (
                f"{mem_clock} Mhz ({mem_offset_sign} Mhz)"
                if current_mem_offset != 0
                else f"{mem_clock} Mhz"
            )

            current_power_limit = nv.nvmlDeviceGetPowerManagementLimit(self.gpu) / 1000
            current_power_offset = current_power_limit - self.default_power_limit
            power_offset_str = add_sign(current_power_offset)
            power_str = f"{current_power_usage:.2f} / {current_power_limit:.2f} W ({power_offset_str} W)"

            current_power_percentage = (current_power_usage / current_power_limit) * 100
            current_clock_percentage = (core_clock / max_core_clock) * 100
            current_mem_clock_percentage = (mem_clock / max_mem_clock) * 100
            current_vram_percentage = (mem_info.used / mem_info.total) * 100

            # 24 is the width of the label text plus spaces for justification
            gpu_text_width = len(f"{self.args.gpu_number} - {self.gpu_name}") + 24
            core_text_width = len(core_clock_str) + 24
            mem_text_width = len(mem_clock_str) + 24
            power_text_width = len(power_str) + 24
            vram_text_width = len(vram_str) + 24
            self.max_text_width = max(
                gpu_text_width,
                core_text_width,
                mem_text_width,
                power_text_width,
                vram_text_width,
            )

            if self.args.reactive_color:
                temp_color = self._set_color(current_temperature, 65, 80)
                power_color = self._set_color(current_power_percentage, 70, 90)
                clock_color = self._set_color(current_clock_percentage, 70, 90)
                mem_clock_color = self._set_color(current_mem_clock_percentage, 70, 90)
                util_color = self._set_color(utilization.gpu, 70, 90)
                mem_util_color = self._set_color(utilization.memory, 70, 90)
                vram_color = self._set_color(current_vram_percentage, 70, 90)
            else:
                temp_color = self.WHITE
                power_color = self.WHITE
                clock_color = self.WHITE
                mem_clock_color = self.WHITE
                mem_util_color = self.WHITE
                util_color = self.WHITE
                vram_color = self.WHITE

            # Draw UI
            self._draw_header(stdscr)
            if self.args.interactive:
                self._draw_profile_indicators(stdscr)

            self.safe_addstr(stdscr, 3, 2, "GPU: ", self.YELLOW)
            self.safe_addstr(stdscr, 4, 2, "Core Clock Freq: ", self.YELLOW)
            self.safe_addstr(stdscr, 5, 2, "Mem Clock Freq: ", self.YELLOW)
            self.safe_addstr(stdscr, 6, 2, "Temp/Fan: ", self.YELLOW)
            self.safe_addstr(stdscr, 7, 2, "Power: ", self.YELLOW)
            self.safe_addstr(stdscr, 8, 2, "VRAM Usage: ", self.YELLOW)
            self.safe_addstr(stdscr, 9, 2, "GPU Core Usage: ", self.YELLOW)
            self.safe_addstr(stdscr, 10, 2, "Mem Controller: ", self.YELLOW)

            self.safe_addstr(
                stdscr, 3, 22, f"{self.args.gpu_number} - {self.gpu_name}", self.GREEN
            )
            self.safe_addstr(stdscr, 4, 22, core_clock_str, clock_color)
            self.safe_addstr(stdscr, 5, 22, mem_clock_str, mem_clock_color)
            self.safe_addstr(
                stdscr,
                6,
                22,
                temp_str,
                temp_color,
            )
            self.safe_addstr(
                stdscr,
                7,
                22,
                power_str,
                power_color,
            )
            self.safe_addstr(
                stdscr,
                8,
                22,
                vram_str,
                vram_color,
            )
            self.safe_addstr(stdscr, 9, 22, f"{utilization.gpu}%", util_color)
            self.safe_addstr(stdscr, 10, 22, f"{utilization.memory}%", mem_util_color)

            self.safe_addstr(stdscr, 12, 2, 'Press "h" for help or "q" to quit!')

            stdscr.refresh()
            stdscr.timeout(self.args.refresh_rate)
            key = stdscr.getch()

            if key == ord("q"):
                return
            elif key == ord("h"):
                self._show_help(stdscr)
            elif key == ord("i"):
                self._process_monitor(stdscr)
            elif self.args.interactive and key in (
                self.curses.KEY_F1,
                self.curses.KEY_F2,
                self.curses.KEY_F3,
                self.curses.KEY_F4,
                self.curses.KEY_RIGHT,
                self.curses.KEY_LEFT,
                ord("1"),
                ord("2"),
                ord("3"),
                ord("4"),
                ord("!"),
                ord("@"),
                ord("#"),
                ord("$"),
                ord("c"),
                ord("m"),
                ord("p"),
                ord("f"),
                ord("a"),
            ):
                current_profile = self.active_profile
                self.active_profile = 0
                stdscr.nodelay(False)
                delay = 0

                if key == self.curses.KEY_RIGHT and self.num_gpus > 1:
                    delay = self._switch_gpu(stdscr, 1)
                elif key == self.curses.KEY_LEFT and self.num_gpus > 1:
                    delay = self._switch_gpu(stdscr, -1)
                elif key == ord("1"):
                    self._save_profile(
                        stdscr,
                        1,
                        current_core_offset,
                        current_mem_offset,
                        current_power_limit,
                        self.fan_policy.value,
                        fan_speed,
                    )
                    self.active_profile = 1
                    delay = 1
                elif key == self.curses.KEY_F1:
                    self.active_profile = self._load_profile(stdscr, 1)
                    delay = 2
                elif key == ord("!"):
                    self._delete_profile(stdscr, 1)
                    self.active_profile = current_profile if current_profile != 1 else 0
                    delay = 1
                elif key == ord("2"):
                    self._save_profile(
                        stdscr,
                        2,
                        current_core_offset,
                        current_mem_offset,
                        current_power_limit,
                        self.fan_policy.value,
                        fan_speed,
                    )
                    self.active_profile = 2
                    delay = 1
                elif key == self.curses.KEY_F2:
                    self.active_profile = self._load_profile(stdscr, 2)
                    delay = 2
                elif key == ord("@"):
                    self._delete_profile(stdscr, 2)
                    self.active_profile = current_profile if current_profile != 2 else 0
                    delay = 1
                elif key == ord("3"):
                    self._save_profile(
                        stdscr,
                        3,
                        current_core_offset,
                        current_mem_offset,
                        current_power_limit,
                        self.fan_policy.value,
                        fan_speed,
                    )
                    self.active_profile = 3
                    delay = 1
                elif key == self.curses.KEY_F3:
                    self.active_profile = self._load_profile(stdscr, 3)
                    delay = 2
                elif key == ord("#"):
                    self._delete_profile(stdscr, 3)
                    self.active_profile = current_profile if current_profile != 3 else 0
                    delay = 1
                elif key == ord("4"):
                    self._save_profile(
                        stdscr,
                        4,
                        current_core_offset,
                        current_mem_offset,
                        current_power_limit,
                        self.fan_policy.value,
                        fan_speed,
                    )
                    self.active_profile = 4
                    delay = 1
                elif key == self.curses.KEY_F4:
                    self.active_profile = self._load_profile(stdscr, 4)
                    delay = 2
                elif key == ord("$"):
                    self._delete_profile(stdscr, 4)
                    self.active_profile = current_profile if current_profile != 4 else 0
                    delay = 1
                elif key == ord("c"):
                    delay = self._set_core_offset(stdscr)
                elif key == ord("m"):
                    delay = self._set_mem_offset(stdscr)
                elif key == ord("p"):
                    delay = self._set_power_limit(stdscr)
                elif key == ord("f"):
                    delay = self._set_fan_speed(stdscr)
                elif key == ord("a"):
                    delay = self._set_auto_fan(stdscr)

                stdscr.refresh()
                time.sleep(1 + delay)
                stdscr.nodelay(True)
                # Clear any queued input
                while stdscr.getch() != -1:
                    pass

    # ------------------------------------------------------------------
    # Curses helper methods
    # ------------------------------------------------------------------
    def _init_colors(self) -> None:
        """Initialise colour pairs and set the colour attributes used by the UI."""
        self.GREEN = self.RED = self.CYAN = self.YELLOW = self.MAGENTA = self.BLUE = (
            self.WHITE
        ) = self.GRAY = self.curses.A_NORMAL

        if self.curses.has_colors():
            self.curses.use_default_colors()
            if self.use_color:
                self.curses.start_color()
                self.curses.init_pair(1, self.curses.COLOR_GREEN, -1)
                self.GREEN = self.curses.color_pair(1)
                self.curses.init_pair(2, self.curses.COLOR_RED, -1)
                self.RED = self.curses.color_pair(2)
                self.curses.init_pair(3, self.curses.COLOR_CYAN, -1)
                self.CYAN = self.curses.color_pair(3)
                self.curses.init_pair(4, self.curses.COLOR_YELLOW, -1)
                self.YELLOW = self.curses.color_pair(4)
                self.curses.init_pair(5, self.curses.COLOR_MAGENTA, -1)
                self.MAGENTA = self.curses.color_pair(5)
                self.curses.init_pair(6, self.curses.COLOR_BLUE, -1)
                self.BLUE = self.curses.color_pair(6)
                self.curses.init_pair(7, self.curses.COLOR_WHITE, -1)
                self.WHITE = self.curses.color_pair(7)
                try:
                    self.curses.init_pair(8, 8, -1)
                    self.GRAY = self.curses.color_pair(8)
                except ValueError:
                    self.GRAY = self.CYAN
            else:
                self.GRAY = self.CYAN = self.RED = self.GREEN = self.WHITE = (
                    self.curses.A_NORMAL
                )
                self.YELLOW = self.BLUE = self.MAGENTA = self.curses.A_BOLD
        else:
            self.GRAY = self.CYAN = self.RED = self.GREEN = self.WHITE = (
                self.curses.A_NORMAL
            )
            self.YELLOW = self.BLUE = self.MAGENTA = self.curses.A_BOLD

    def safe_addstr(
        self, stdscr, y: int, x: int, text: str, attr=0, wrap: bool = False
    ) -> int:
        """
        Add a string to the screen without raising curses.error.

        If wrap is False, the string is truncated with an ellipsis if it would
        exceed the screen width. If wrap is True, the text is wrapped to
        multiple lines. Returns the number of lines used.
        """
        max_y, max_x = stdscr.getmaxyx()
        if (
            max_x > self.max_text_width
        ):  # If the terminal window is greater than max app width
            self.mid_ref = (max_x // 2) - (self.max_text_width // 2)
            x += self.mid_ref

        if y < 0 or y >= max_y or x < 0 or x >= max_x:
            return 0

        if wrap:
            available_width = (
                self.max_text_width
            )  # Wrap text and whatever our max length point already is.
            if available_width <= 0:
                return 0
            lines = textwrap.wrap(text, width=available_width) or [""]
            used = 0
            for line in lines:
                if y + used >= max_y:
                    break
                try:
                    stdscr.addstr(y + used, x, line, attr)
                except self.curses.error:
                    pass
                used += 1
            return used
        else:
            available_width = max_x - x
            if len(text) > available_width:
                if available_width <= 3:
                    text = text[:available_width]
                else:
                    text = text[: available_width - 3] + "..."
            try:
                stdscr.addstr(y, x, text, attr)
            except self.curses.error:
                pass
            return 1

    def _draw_header(self, stdscr) -> None:
        self.safe_addstr(
            stdscr, 0, (self.max_text_width // 2) - 3, "Envious", self.MAGENTA
        )
        self.safe_addstr(stdscr, 1, 0, "-" * self.max_text_width)

    def _draw_profile_indicators(self, stdscr) -> None:
        for i in range(1, 5):
            if self.use_color:
                if self.active_profile == i:
                    color = self.YELLOW
                elif self.profile_exists[i]:
                    color = self.BLUE
                else:
                    color = self.GRAY
            else:
                if self.active_profile == i:
                    color = self.curses.A_BOLD
                elif self.profile_exists[i]:
                    color = self.curses.A_NORMAL
                else:
                    color = None
            if color is not None:
                self.safe_addstr(
                    stdscr,
                    2,
                    ((self.max_text_width // 2) - 6) + (4 * (i - 1)),
                    str(i),
                    color,
                )

    def _set_color(self, value, caution: int, warn: int):
        """Return a colour attribute based on threshold values."""
        if caution < value < warn:
            return self.YELLOW
        if value > warn:
            return self.RED
        return self.GREEN

    # ------------------------------------------------------------------
    # Interactive actions
    # ------------------------------------------------------------------
    def _refresh_profile_exists(self) -> None:
        self.profile_exists = [False] * 5
        for i in range(1, 5):
            path = os.path.join(
                self.profile_dir, f"profile{i}_{self.args.gpu_number}.bnt"
            )
            if os.path.exists(path):
                self.profile_exists[i] = True

    def _save_profile(
        self,
        stdscr,
        profile_number: int,
        current_core_offset,
        current_mem_offset,
        current_power_limit,
        fan_policy_value,
        fan_speed,
    ) -> None:
        self.safe_addstr(
            stdscr,
            self.input_start,
            0,
            f"Current settings will be saved as profile {profile_number} for GPU {self.args.gpu_number}!",
        )
        path = os.path.join(
            self.profile_dir, f"profile{profile_number}_{self.args.gpu_number}.bnt"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{int(current_core_offset)}\n")
            f.write(f"{int(current_mem_offset)}\n")
            f.write(f"{int(current_power_limit)}\n")
            f.write(f"{fan_policy_value}\n")
            f.write(f"{fan_speed}\n")
        self.profile_exists[profile_number] = True

    def _load_profile(self, stdscr, profile_number: int) -> int:
        """Load a profile; returns the profile number on success, 66 on failure."""
        self.safe_addstr(
            stdscr,
            self.input_start,
            0,
            f"Loading profile {profile_number} for GPU {self.args.gpu_number}!",
        )
        path = os.path.join(
            self.profile_dir, f"profile{profile_number}_{self.args.gpu_number}.bnt"
        )
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_core_offset = int(f.readline())
                new_mem_offset = int(f.readline())
                new_power_limit = int(f.readline())
                new_fan_policy = int(f.readline())
                new_fan_speed = int(f.readline())

            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Setting core clock offset to {add_sign(new_core_offset)} Mhz...",
            )
            nv.nvmlDeviceSetGpcClkVfOffset(self.gpu, new_core_offset)
            self.safe_addstr(
                stdscr,
                self.input_start + 2,
                0,
                f"Setting mem clock offset to {add_sign(new_mem_offset)} Mhz...",
            )
            nv.nvmlDeviceSetMemClkVfOffset(self.gpu, new_mem_offset * 2)
            self.safe_addstr(
                stdscr,
                self.input_start + 3,
                0,
                f"Setting core power limit to {new_power_limit}...",
            )
            nv.nvmlDeviceSetPowerManagementLimit(self.gpu, new_power_limit * 1000)

            if new_fan_policy == 1:
                if 101 > new_fan_speed > 29:
                    self.safe_addstr(
                        stdscr,
                        self.input_start + 4,
                        0,
                        f"Setting fan policy to manual and fan speed to {new_fan_speed}%...",
                    )
                    num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
                    for i in range(num_fans):
                        nv.nvmlDeviceSetFanControlPolicy(
                            self.gpu, i, nv.NVML_FAN_POLICY_MANUAL
                        )
                        nv.nvmlDeviceSetFanSpeed_v2(self.gpu, i, new_fan_speed)
                else:
                    raise ValueError("Invalid fan speed setting in profile!")
            else:
                self.safe_addstr(
                    stdscr,
                    self.input_start + 4,
                    0,
                    "Setting fan policy to automatic control...",
                )
                num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
                for i in range(num_fans):
                    nv.nvmlDeviceSetFanControlPolicy(
                        self.gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW
                    )
                    nv.nvmlDeviceSetDefaultFanSpeed_v2(self.gpu, i)

            return profile_number
        except ValueError as e:
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Some kind of value error prevented the profile loading: {e}",
            )
            return 66
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Some kind of NVML error prevented the profile loading: {e}",
            )
            return 66
        except FileNotFoundError:
            self.safe_addstr(stdscr, self.input_start + 1, 0, "Profile was not found!")
            return 66

    def _delete_profile(self, stdscr, profile_number: int) -> None:
        path = os.path.join(
            self.profile_dir, f"profile{profile_number}_{self.args.gpu_number}.bnt"
        )
        if os.path.exists(path):
            os.remove(path)
            self.safe_addstr(
                stdscr,
                self.input_start,
                0,
                f"Deleted profile {profile_number} for GPU {self.args.gpu_number}!",
            )
            self.profile_exists[profile_number] = False
        else:
            self.safe_addstr(
                stdscr,
                self.input_start,
                0,
                f"Nope, profile {profile_number} doesn't exist so we can't delete it, silly!",
            )

    def _set_core_offset(self, stdscr) -> int:
        self.safe_addstr(
            stdscr, self.input_start, 0, "Enter new core clock offset in Mhz:"
        )
        new_core_offset = stdscr.getstr(self.input_start, 36 + self.mid_ref, 6)
        try:
            new_core_offset = int(new_core_offset)
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Setting core clock offset to {new_core_offset} MHz...",
            )
            nv.nvmlDeviceSetGpcClkVfOffset(self.gpu, new_core_offset)
            return 0
        except ValueError:
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                "Invalid input! Please enter a valid number.",
            )
            return 2
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr, self.input_start + 2, 0, f"Failed to set core clock offset: {e}"
            )
            return 2

    def _set_mem_offset(self, stdscr) -> int:
        self.safe_addstr(
            stdscr, self.input_start, 0, "Enter new mem clock offset in Mhz:"
        )
        new_mem_offset = stdscr.getstr(self.input_start, 35 + self.mid_ref, 6)
        try:
            new_mem_offset = int(new_mem_offset)
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Setting mem clock offset to {new_mem_offset} MHz...",
            )
            nv.nvmlDeviceSetMemClkVfOffset(self.gpu, new_mem_offset * 2)
            return 0
        except ValueError:
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                "Invalid input! Please enter a valid number.",
            )
            return 2
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr, self.input_start + 2, 0, f"Failed to set mem clock offset: {e}"
            )
            return 2

    def _set_power_limit(self, stdscr) -> int:
        self.safe_addstr(stdscr, self.input_start, 0, "Enter new power limit in watts:")
        new_power_limit = stdscr.getstr(self.input_start, 32 + self.mid_ref, 6)
        try:
            new_power_limit = int(new_power_limit)
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Setting power limit to {new_power_limit} W...",
            )
            nv.nvmlDeviceSetPowerManagementLimit(self.gpu, new_power_limit * 1000)
            return 0
        except ValueError:
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                "Invalid input! Please enter a valid number.",
            )
            return 2
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr, self.input_start + 2, 0, f"Failed to set power limit: {e}"
            )
            return 2

    def _set_fan_speed(self, stdscr) -> int:
        self.safe_addstr(
            stdscr, self.input_start, 0, "Enter new fan percentage between 30 and 100:"
        )
        new_fan_speed = stdscr.getstr(self.input_start, 45 + self.mid_ref, 6)
        try:
            new_fan_speed = int(new_fan_speed)
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                f"Setting fan speed to {new_fan_speed}%...",
            )
            if 101 > new_fan_speed > 29:
                num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
                for i in range(num_fans):
                    nv.nvmlDeviceSetFanControlPolicy(
                        self.gpu, i, nv.NVML_FAN_POLICY_MANUAL
                    )
                    nv.nvmlDeviceSetFanSpeed_v2(self.gpu, i, new_fan_speed)
                if not self.fan_warning_done:
                    self.safe_addstr(
                        stdscr,
                        self.input_start + 2,
                        0,
                        'Fan control policy is now MANUAL - this means it will not automatically change with temperature. You can return it to AUTO with "a"',
                        self.YELLOW,
                        wrap=True,
                    )
                    self.fan_warning_done = True
                    return 5  # Longer delay to allow warning to be read
                return 0
            else:
                raise ValueError("Between 30 and 100!")
        except ValueError:
            self.safe_addstr(
                stdscr,
                self.input_start + 1,
                0,
                "Invalid input! Please enter a valid number.",
            )
            return 2
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr, self.input_start + 1, 0, f"Failed to set fan speed: {e}"
            )
            return 2

    def _set_auto_fan(self, stdscr) -> int:
        try:
            self.safe_addstr(
                stdscr, self.input_start, 0, "Setting fans to automatic control..."
            )
            num_fans = nv.nvmlDeviceGetNumFans(self.gpu)
            for i in range(num_fans):
                nv.nvmlDeviceSetFanControlPolicy(
                    self.gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW
                )
                nv.nvmlDeviceSetDefaultFanSpeed_v2(self.gpu, i)
            return 0
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr, self.input_start + 1, 0, f"Failed to set fan speed: {e}"
            )
            return 2

    def _switch_gpu(self, stdscr, direction: int) -> int:
        """direction: 1 = right, -1 = left."""
        try:
            self.last_active_profile[self.args.gpu_number] = self.active_profile
            if direction == 1:
                self.args.gpu_number = (self.args.gpu_number + 1) % self.num_gpus
            else:
                self.args.gpu_number = (self.args.gpu_number - 1) % self.num_gpus

            self.gpu = nv.nvmlDeviceGetHandleByIndex(self.args.gpu_number)
            self.gpu_name = nv.nvmlDeviceGetName(self.gpu)
            self.default_power_limit = (
                nv.nvmlDeviceGetPowerManagementDefaultLimit(self.gpu) / 1000
            )
            self._refresh_profile_exists()
            self.active_profile = self.last_active_profile[self.args.gpu_number]
            return 0
        except nv.NVMLError as e:
            self.safe_addstr(
                stdscr,
                self.input_start,
                0,
                f"An NVMLError prevented the operation: {e}",
            )
            return 2

    # ------------------------------------------------------------------
    # Help and process monitor screens
    # ------------------------------------------------------------------
    def _show_help(self, stdscr) -> None:
        """Display the help screen and wait for a key press."""
        stdscr.nodelay(False)
        stdscr.clear()
        self.max_text_width = 60 if self.args.interactive else 54
        self._draw_header(stdscr)

        row = 3
        self.safe_addstr(stdscr, row, 2, "Blissful Legend:", self.BLUE)
        row += 2

        self.safe_addstr(stdscr, row, 4, "h", self.YELLOW)
        self.safe_addstr(stdscr, row, 8, "- show this help screen.")
        row += 1

        self.safe_addstr(stdscr, row, 4, "i", self.YELLOW)
        self.safe_addstr(stdscr, row, 8, "- switch to process monitor with extra info")
        row += 1

        if self.args.interactive:
            self.safe_addstr(stdscr, row, 4, "c", self.YELLOW)
            self.safe_addstr(stdscr, row, 8, "- set new core clock offset")
            row += 1

            self.safe_addstr(stdscr, row, 4, "m", self.YELLOW)
            self.safe_addstr(stdscr, row, 8, "- set new mem clock offset")
            row += 1

            self.safe_addstr(stdscr, row, 4, "p", self.YELLOW)
            self.safe_addstr(stdscr, row, 8, "- set new power limit")
            row += 1

            self.safe_addstr(stdscr, row, 4, "f", self.YELLOW)
            self.safe_addstr(
                stdscr, row, 8, "- set fan control to MANUAL and set fan percentage"
            )
            row += 1

            self.safe_addstr(stdscr, row, 4, "a", self.YELLOW)
            self.safe_addstr(
                stdscr, row, 8, "- set fan control to automatic based on temperatue"
            )
            row += 1

            if self.num_gpus > 1:
                self.safe_addstr(stdscr, row, 4, "<->", self.YELLOW)
                self.safe_addstr(stdscr, row, 8, "- switch between available GPUs")
                row += 1

            self.safe_addstr(stdscr, row, 4, "1", self.YELLOW)
            self.safe_addstr(stdscr, row, 8, "- save profile (also 2, 3, 4)")
            row += 1

            self.safe_addstr(stdscr, row, 4, "F1", self.YELLOW)
            self.safe_addstr(stdscr, row, 8, "- load profile (also F2, F3, F4)")
            row += 1

            self.safe_addstr(stdscr, row, 4, "!", self.YELLOW)
            self.safe_addstr(stdscr, row, 8, "- delete profile (also @, #, $)")
            row += 1
        row += 1
        self.safe_addstr(stdscr, row, 2, "Press a key to return to the monitor!")
        stdscr.refresh()
        stdscr.getch()
        stdscr.nodelay(True)

    def _process_monitor(self, stdscr) -> None:
        """Show extended GPU information and running processes."""
        self.max_text_width = 62
        key = ""

        # Static info
        try:
            nvml_version = nv.nvmlSystemGetNVMLVersion()
        except nv.NVMLError:
            nvml_version = "Unknown"
        try:
            max_gen = nv.nvmlDeviceGetMaxPcieLinkGeneration(self.gpu)
            max_width = nv.nvmlDeviceGetMaxPcieLinkWidth(self.gpu)
        except nv.NVMLError:
            max_gen = "?"
            max_width = "?"
        try:
            bar_size = nv.nvmlDeviceGetBAR1MemoryInfo(self.gpu)
            bar_size = f"{(bar_size.bar1Total / 1024) / 1024:.2f} MB"
        except nv.NVMLError:
            bar_size = "Unknown"
        try:
            compute_major, compute_minor = nv.nvmlDeviceGetCudaComputeCapability(
                self.gpu
            )
        except nv.NVMLError:
            compute_major = "?"
            compute_minor = "?"
        try:
            cuda_version = nv.nvmlSystemGetCudaDriverVersion_v2()
            cuda_major = cuda_version // 1000
            cuda_minor = (cuda_version % 1000) // 10
        except nv.NVMLError:
            cuda_major = "?"
            cuda_minor = "?"
        try:
            driver_version = nv.nvmlSystemGetDriverVersion()
        except nv.NVMLError:
            driver_version = "Unknown"
        try:
            mem_bus_width = nv.nvmlDeviceGetMemoryBusWidth(self.gpu)
        except nv.NVMLError:
            mem_bus_width = "Unknown"

        while key != ord("i"):
            stdscr.clear()

            # Dynamic info
            try:
                link_gen = nv.nvmlDeviceGetCurrPcieLinkGeneration(self.gpu)
                link_width = nv.nvmlDeviceGetCurrPcieLinkWidth(self.gpu)
            except nv.NVMLError:
                link_gen = "?"
                link_width = "?"

            try:
                compute_procs = nv.nvmlDeviceGetComputeRunningProcesses_v3(self.gpu)
                for proc in compute_procs:
                    proc.type = "Compute"
                graphics_procs = nv.nvmlDeviceGetGraphicsRunningProcesses_v3(self.gpu)
                for proc in graphics_procs:
                    proc.type = "Graphics"
                running_procs = graphics_procs + compute_procs
                running_procs.sort(key=lambda p: p.usedGpuMemory, reverse=True)
            except nv.NVMLError:
                running_procs = "Unknown"

            self._draw_header(stdscr)
            self.safe_addstr(stdscr, 3, 2, "Extra info/Process Monitor:", self.BLUE)

            self.safe_addstr(stdscr, 5, 4, "Device Name:", self.YELLOW)
            self.safe_addstr(stdscr, 6, 4, "Driver/NVML Version:", self.YELLOW)
            self.safe_addstr(stdscr, 7, 4, "Compute:", self.YELLOW)
            self.safe_addstr(stdscr, 8, 4, "BAR1 Size:", self.YELLOW)
            self.safe_addstr(stdscr, 9, 4, "PCI Express:", self.YELLOW)
            self.safe_addstr(stdscr, 10, 4, "Memory bus:", self.YELLOW)
            self.safe_addstr(stdscr, 11, 4, "Top Processes by VRAM:", self.YELLOW)

            self.safe_addstr(stdscr, 5, 28, self.gpu_name, self.GREEN)
            self.safe_addstr(stdscr, 6, 28, f"{driver_version} / {nvml_version}")
            self.safe_addstr(
                stdscr,
                7,
                28,
                f"CC: {compute_major}.{compute_minor} | CUDA: {cuda_major}.{cuda_minor}",
            )
            self.safe_addstr(stdscr, 8, 28, bar_size)
            self.safe_addstr(
                stdscr,
                9,
                28,
                f"Gen {link_gen}@{link_width}x / Gen {max_gen}@{max_width}x",
            )
            self.safe_addstr(stdscr, 10, 28, f"{mem_bus_width} bit")

            if running_procs != "Unknown":
                list_length = min(5, len(running_procs))
                if list_length == 0:
                    self.safe_addstr(stdscr, 13, 6, "0 -   None")
                    self.safe_addstr(
                        stdscr,
                        15,
                        2,
                        'Press "i" key to return to the monitor or "q" to quit!',
                    )
                else:
                    for i in range(list_length):
                        color = (
                            self.curses.color_pair(i + 1)
                            if self.use_color
                            else self.WHITE
                        )
                        self.safe_addstr(stdscr, 13 + i, 4, f"{i + 1}", color)
                        try:
                            proc_name = self.psutil.Process(running_procs[i].pid).name()
                        except (self.psutil.NoSuchProcess, self.psutil.AccessDenied):
                            proc_name = "?"
                        self.safe_addstr(
                            stdscr,
                            13 + i,
                            7,
                            f" -   {proc_name} -- ({(running_procs[i].usedGpuMemory / (1024**2)):.2f} MB) "
                            f"({running_procs[i].type}) ",
                        )
                    self.safe_addstr(
                        stdscr,
                        14 + list_length,
                        2,
                        'Press "i" key to return to the monitor or "q" to quit!',
                    )
            else:
                self.safe_addstr(stdscr, 13, 6, "Unable to retrieve running processes!")
                self.safe_addstr(
                    stdscr,
                    15,
                    2,
                    'Press "i" key to return to the monitor or "q" to quit!',
                )

            stdscr.timeout(self.args.refresh_rate)
            stdscr.refresh()
            key = stdscr.getch()
            if key == ord("q"):
                return


def main() -> None:
    """Entry point."""
    args = parse_args()

    try:
        nv.nvmlInit()
    except nv.NVMLError as e:
        print(f"Could not initialize NVML! The library reported: {e}")
        sys.exit(8)

    try:
        gpu = nv.nvmlDeviceGetHandleByIndex(args.gpu_number)
    except nv.NVMLError as e:
        print(
            f"Could not initialize for GPU {args.gpu_number}! The library reported: {e}"
        )
        nv.nvmlShutdown()
        sys.exit(8)

    app = EnviousApp(args, gpu)

    offline_requested = any(
        (
            args.set_clocks is not None,
            args.set_power_limit is not None,
            args.set_max_fan,
            args.set_auto_fan,
            args.set_custom_fan is not None,
            args.set_profile is not None,
        )
    )

    if offline_requested:
        app.run_offline()
    else:
        app.run_interactive()

    nv.nvmlShutdown()


if __name__ == "__main__":
    main()
