"""
=================================================
                  Blissful Nvidia Tool
=================================================
Description:
Simple CLI tool for monitoring and overclocking Nvidia Graphics Cards

Dependencies:
nvidia-ml-py - NOT pynvml which is the older, deprecated version and does not have the needed functionality for all features.
Nvidia Driver 555.xx or greater for all features.

License:
MIT License - See below for full text

=================================================
Copyright (c) 2024 Blyss Sarania

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

=================================================
Created on: Tue Oct 1, 2024
@author: Blyss Sarania
=================================================
"""
__VERSION__ = "1.20"
import os
import time
import argparse
import pynvml as nv
parser = argparse.ArgumentParser(description="Blissful Nvidia Tool")
parser.add_argument("--gpu-number", type=int, default=0, help="Specify the GPU index (default: 0)")
parser.add_argument("--refresh-rate", type=int, default=1000, help="Specify how often to refresh the monitor, in milliseconds. Default is 1000")
parser.add_argument("--reactive-color", action='store_true', help="Uses color to indicate the intensity of values")
parser.add_argument("--interactive", action='store_true', help="This and those below need root/superuser. Enable interactive mode for monitor. Type \"h\" for help")
parser.add_argument("--set-clocks", nargs=2, type=int, help="Needs root. Set core and memory clock offsets (in MHz) respectively. Example: --set-clocks -150 500")
parser.add_argument("--set-power-limit", type=int, help="Set the power limit (in watts). Example: --set-power-limit 300")
parser.add_argument("--set-max-fan", action='store_true', help="Set all fans to maximum speed")
parser.add_argument("--set-auto-fan", action='store_true', help="Reset fan control to automatic mode")
parser.add_argument("--set-custom-fan", type=int, help="Set a custom fan percentage. !BE CAREFUL! as this changes the fan control policy to manual!!! Only values 30-100 are accepted. ")
parser.add_argument("--set-profile", type=int, help="Apply on of the custom profiles you've created.")


def add_sign(offset):
    """
    Helper function to add a + sign to positive numbers and output them back
    """
    return f"+{offset}" if offset > 0 else offset


def draw_dashboard(stdscr):
    """
    Main function for drawing monitor, takes in a screen pointer
    """
    def set_color(value, threshold_caution, threshold_warn):
        """
        Helper function to return color values based on current readings, takes in the value and thresholds to check
        """
        if threshold_caution < value < threshold_warn:
            return RED
        elif value > threshold_warn:
            return YELLOW
        else:
            return GREEN

    def header():
        """
        Simple function to show the header
        """
        stdscr.addstr(0, 0, "                    Blissful Nvidia Tool", MAGENTA)
        stdscr.addstr(1, 0, "------------------------------------------------------------")

    def load_profile(profile_number):
        """
        Loads a profile and applies settings. Takes in which profile to load
        """
        stdscr.addstr(14, 0, f"Loading profile {profile_number}!")
        try:
            with open(os.path.join(source_dir, f"profile{profile_number}.bnt"), "r", encoding="utf-8") as file:
                new_core_offset = int(file.readline())
                new_mem_offset = int(file.readline())
                new_power_limit = int(file.readline())
                new_fan_policy = int(file.readline())
                new_fan_speed = int(file.readline())
                stdscr.addstr(15, 0, f"Setting core clock offset to {add_sign(new_core_offset)} Mhz...")
                nv.nvmlDeviceSetGpcClkVfOffset(gpu, new_core_offset)
                stdscr.addstr(16, 0, f"Setting mem clock offset to {add_sign(new_mem_offset)} Mhz...")
                nv.nvmlDeviceSetMemClkVfOffset(gpu, new_mem_offset * 2)
                stdscr.addstr(17, 0, f"Setting core power limit to {new_power_limit}...")
                nv.nvmlDeviceSetPowerManagementLimit(gpu, new_power_limit * 1000)
                if new_fan_policy == 1:
                    if 101 > new_fan_speed > 29:
                        stdscr.addstr(18, 0, f"Setting fan policy to manual and fan speed to {new_fan_speed}%...")
                        num_fans = nv.nvmlDeviceGetNumFans(gpu)
                        for i in range(0, num_fans):
                            nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_MANUAL)
                            nv.nvmlDeviceSetFanSpeed_v2(gpu, i, new_fan_speed)
                    else:
                        raise ValueError("Invalid fan speed setting in profile!")
                else:
                    stdscr.addstr(18, 0, "Setting fan policy to automatic control...")
                    num_fans = nv.nvmlDeviceGetNumFans(gpu)
                    for i in range(0, num_fans):
                        nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW)
                        nv.nvmlDeviceSetDefaultFanSpeed_v2(gpu, i)
            return profile_number
        except ValueError as e:
            stdscr.addstr(15, 0, f"Some kind of value error prevented the profile loading: {e}")
            return 66
        except nv.NVMLError as e:
            stdscr.addstr(15, 0, f"Some kind of NVML error prevented the profile loading: {e}")
            return 66
        except FileNotFoundError:
            stdscr.addstr(15, 0, "Profile was not found!")
            return 66

    def save_profile(profile_number):
        """
        Saves current settings to the specified profile number.
        """
        stdscr.addstr(14, 0, f"Current settings will be saved as profile {profile_number}!")
        with open(os.path.join(source_dir, f"profile{profile_number}.bnt"), "w", encoding="utf-8") as file:
            file.write(str(int(current_core_offset)) + "\n")
            file.write(str(int(current_mem_offset)) + "\n")
            file.write(str(int(current_power_limit)) + "\n")
            file.write(str(fan_policy.value) + "\n")
            file.write(str(fan_speed) + "\n")
            for i in range(1, 5):
                profile_exists[i] = False
                if os.path.exists(os.path.join(source_dir, f"profile{i}.bnt")):
                    profile_exists[i] = True

    def delete_profile(profile_number):
        """
        Simply deletes the specified profile
        """
        profile_path = os.path.join(source_dir, f"profile{profile_number}.bnt")
        if os.path.exists(profile_path):
            os.remove(profile_path)
            stdscr.addstr(14, 0, f"Deleted profile {profile_number}!")
        else:
            stdscr.addstr(14, 0, f"Nope, profile {profile_number} doesn't exist so we can't delete it, silly!")
        for i in range(1, 5):
            profile_exists[i] = False
            if os.path.exists(os.path.join(source_dir, f"profile{i}.bnt")):
                profile_exists[i] = True

    stdscr.clear()
    stdscr.nodelay(True)  # Non-blocking input
    curses.curs_set(0)    # Hide cursor
    curses.start_color()
    curses.echo()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    GREEN = curses.color_pair(1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    RED = curses.color_pair(2)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    CYAN = curses.color_pair(3)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    YELLOW = curses.color_pair(4)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    MAGENTA = curses.color_pair(5)
    curses.init_pair(6, curses.COLOR_BLUE, -1)
    BLUE = curses.color_pair(6)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    WHITE = curses.color_pair(7)
    curses.init_pair(8, 8, -1)
    GRAY = curses.color_pair(8)
    temp_color = WHITE
    power_color = WHITE
    clock_color = WHITE
    mem_clock_color = WHITE
    mem_util_color = WHITE
    util_color = WHITE
    vram_color = WHITE
    delay = 0
    active_profile = 0
    profile_exists = [False, False, False, False, False]  # We create this with an extra phantom element at position 0 to make the code easier to maintain, we only use 1-4
    if args.interactive:
        nv.nvmlDeviceSetPersistenceMode(gpu, 1)
        for i in range(1, 5):
            if os.path.exists(os.path.join(source_dir, f"profile{i}.bnt")):
                profile_exists[i] = True
    gpu_name = nv.nvmlDeviceGetName(gpu)
    default_power_limit = nv.nvmlDeviceGetPowerManagementDefaultLimit(gpu) / 1000
    while True:
        stdscr.clear()
        current_core_offset = nv.nvmlDeviceGetGpcClkVfOffset(gpu)
        current_mem_offset = nv.nvmlDeviceGetMemClkVfOffset(gpu) / 2
        #  If the offset is negative, pynvml may return a value that is munged by truncated overflow
        #  Since offsets will never legitimately be this large, this should be a safe fix.
        if current_core_offset > 100000:
            current_core_offset = current_core_offset - 4294966
        if current_mem_offset > 100000:
            current_mem_offset = current_mem_offset - 4294966
        core_offset_sign = add_sign(current_core_offset)
        mem_offset_sign = add_sign(current_mem_offset)
        fan_policy = ctypes.c_uint()
        nv.nvmlDeviceGetFanControlPolicy_v2(gpu, 0, ctypes.byref(fan_policy))
        fan_policy_str = "Manual" if fan_policy.value == 1 else "Auto"
        fan_speed = nv.nvmlDeviceGetFanSpeed(gpu)
        current_temperature = nv.nvmlDeviceGetTemperature(gpu, 0)
        current_power_usage = nv.nvmlDeviceGetPowerUsage(gpu) / 1000  # Convert mW to W
        utilization = nv.nvmlDeviceGetUtilizationRates(gpu)
        mem_info = nv.nvmlDeviceGetMemoryInfo(gpu)
        core_clock = nv.nvmlDeviceGetClockInfo(gpu, nv.NVML_CLOCK_GRAPHICS)
        core_clock_str = f"{core_clock} Mhz ({core_offset_sign} Mhz)" if current_core_offset != 0 else f"{core_clock} Mhz"
        max_core_clock = nv.nvmlDeviceGetMaxClockInfo(gpu, nv.NVML_CLOCK_GRAPHICS)
        max_mem_clock = nv.nvmlDeviceGetMaxClockInfo(gpu, nv.NVML_CLOCK_MEM)
        mem_clock = nv.nvmlDeviceGetClockInfo(gpu, nv.NVML_CLOCK_MEM)
        mem_clock_str = f"{mem_clock} Mhz ({mem_offset_sign} Mhz)" if current_mem_offset != 0 else f"{mem_clock} Mhz"
        current_power_limit = nv.nvmlDeviceGetPowerManagementLimit(gpu) / 1000
        current_power_offset = current_power_limit - default_power_limit
        power_offset_str = add_sign(current_power_offset)
        current_power_percentage = (current_power_usage / current_power_limit) * 100
        current_clock_percentage = (core_clock / max_core_clock) * 100
        current_mem_clock_percentage = (mem_clock / max_mem_clock) * 100
        current_vram_percentage = (mem_info.used / mem_info.total) * 100
        if args.reactive_color:
            temp_color = set_color(current_temperature, 65, 80)
            power_color = set_color(current_power_percentage, 70, 90)
            clock_color = set_color(current_clock_percentage, 70, 90)
            mem_clock_color = set_color(current_mem_clock_percentage, 70, 90)
            util_color = set_color(utilization.gpu, 70, 90)
            mem_util_color = set_color(utilization.memory, 70, 90)
            vram_color = set_color(current_vram_percentage, 70, 90)
        header()
        if args.interactive:
            for i in range(1, 5):
                profile_color = YELLOW if active_profile == i else BLUE if profile_exists[i] else GRAY
                stdscr.addstr(2, 23 + (4 * (i - 1)), f"{i}", profile_color)
        stdscr.addstr(3, 2, "GPU: ", YELLOW)
        stdscr.addstr(4, 2, "Core Clock Freq: ", YELLOW)
        stdscr.addstr(5, 2, "Mem Clock Freq: ", YELLOW)
        stdscr.addstr(6, 2, "Temp/Fan: ", YELLOW)
        stdscr.addstr(7, 2, "Power: ", YELLOW)
        stdscr.addstr(8, 2, "VRAM Usage: ", YELLOW)
        stdscr.addstr(9, 2, "Core Usage: ", YELLOW)
        stdscr.addstr(10, 2, "Mem Controller: ", YELLOW)
        stdscr.addstr(3, 22, f"{args.gpu_number} - {gpu_name}", GREEN)
        stdscr.addstr(4, 22, f"{core_clock_str}", clock_color)
        stdscr.addstr(5, 22, f"{mem_clock_str}", mem_clock_color)
        stdscr.addstr(6, 22, f"{current_temperature}°C | {fan_speed}% ({fan_policy_str})", temp_color)
        stdscr.addstr(7, 22, f"{current_power_usage:.2f} / {current_power_limit:.2f} W ({power_offset_str} W)", power_color)
        stdscr.addstr(8, 22, f"{mem_info.used / (1024**2):.2f} / {mem_info.total / (1024**2):.2f} MB", vram_color)
        stdscr.addstr(9, 22, f"{utilization.gpu}%", util_color)
        stdscr.addstr(10, 22, f"{utilization.memory}%", mem_util_color)
        stdscr.addstr(12, 2, "Press \"h\" for help or \"q\" to quit!")
        stdscr.refresh()
        stdscr.timeout(args.refresh_rate)
        key = stdscr.getch()
        if key == ord("q"):
            nv.nvmlShutdown()
            exit(1)
        elif key == ord("h"):
            stdscr.nodelay(False)
            stdscr.clear()
            header()
            stdscr.addstr(3, 0, "Blissful Legend:", BLUE)
            stdscr.addstr(5, 2, "h", YELLOW)
            stdscr.addstr(6, 2, "i", YELLOW)
            stdscr.addstr(5, 5, "- show this help screen.")
            stdscr.addstr(6, 5, "- switch to process monitor with extra info")
            if args.interactive:
                stdscr.addstr(7, 2, "c", YELLOW)
                stdscr.addstr(8, 2, "m", YELLOW)
                stdscr.addstr(9, 2, "p", YELLOW)
                stdscr.addstr(10, 2, "f", YELLOW)
                stdscr.addstr(11, 2, "a", YELLOW)
                stdscr.addstr(12, 2, "1", YELLOW)
                stdscr.addstr(13, 2, "F1", YELLOW)
                stdscr.addstr(7, 5, "- set new core clock offset")
                stdscr.addstr(8, 5, "- set new mem clock offset")
                stdscr.addstr(9, 5, "- set new power limit")
                stdscr.addstr(10, 5, "- set manual fan percentage (CAUTION: This sets your fan control policy to manual meaning it WON'T adapt to temperature!)")
                stdscr.addstr(11, 5, "- set fan control back to auto")
                stdscr.addstr(12, 5, "- load profile")
                stdscr.addstr(12, 19, "(also 2, 3, 4)", YELLOW)
                stdscr.addstr(13, 5, "- save profile")
                stdscr.addstr(13, 19, "(also F2, F3, F4)", YELLOW)
                stdscr.addstr(15, 0, "Press a key to return to the monitor!")
            else:
                stdscr.addstr(8, 0, "Press a key to return to the monitor!")
            stdscr.refresh()
            stdscr.getch()
            stdscr.nodelay(True)
        elif key == ord("i"):
            key = ""
            max_gen = nv.nvmlDeviceGetMaxPcieLinkGeneration(gpu)
            max_width = nv.nvmlDeviceGetMaxPcieLinkWidth(gpu)
            bar_size = nv.nvmlDeviceGetBAR1MemoryInfo(gpu)
            bar_size = str((bar_size.bar1Total / 1024) / 1024) + " MB"
            compute_version_major, compute_version_minor = nv.nvmlDeviceGetCudaComputeCapability(gpu)
            mem_bus_width = nv.nvmlDeviceGetMemoryBusWidth(gpu)
            while not key == ord("i"):
                stdscr.clear()
                link_gen = nv.nvmlDeviceGetCurrPcieLinkGeneration(gpu)
                link_width = nv.nvmlDeviceGetCurrPcieLinkWidth(gpu)
                compute_running_processes = nv.nvmlDeviceGetComputeRunningProcesses_v3(gpu)
                for process in compute_running_processes:
                    setattr(process, "type", "Compute")
                graphics_running_processes = nv.nvmlDeviceGetGraphicsRunningProcesses_v3(gpu)
                for process in graphics_running_processes:
                    setattr(process, "type", "Graphics")
                running_processes = graphics_running_processes + compute_running_processes
                running_processes = sorted(running_processes, key=lambda x: x.usedGpuMemory, reverse=True)
                header()
                stdscr.addstr(3, 0, "Extra info/Process Monitor:", BLUE)
                stdscr.addstr(5, 2, "Device Name: ", YELLOW)
                stdscr.addstr(6, 2, "Compute Capability: ", YELLOW)
                stdscr.addstr(7, 2, "BAR1 Size: ", YELLOW)
                stdscr.addstr(8, 2, "PCI Express: ", YELLOW)
                stdscr.addstr(9, 2, "Memory bus: ", YELLOW)
                stdscr.addstr(10, 2, "Top Processes by VRAM: ", YELLOW)
                stdscr.addstr(5, 26, f"{gpu_name}", GREEN)
                stdscr.addstr(6, 26, f"{compute_version_major}.{compute_version_minor}")
                stdscr.addstr(7, 26, f"{bar_size}")
                stdscr.addstr(8, 26, f"Gen {link_gen}@{link_width}x / Gen {max_gen}@{max_width}x")
                stdscr.addstr(9, 26, f"{mem_bus_width} bit")
                list_length = min(5, len(running_processes))
                if list_length == 0:
                    stdscr.addstr(12, 4, "0 -   None")
                    stdscr.addstr(14, 0, "Press \"i\" key to return to the monitor or \"q\" to quit!")
                else:
                    for i in range(0, list_length):
                        stdscr.addstr(12 + i, 4, f"{i + 1}", curses.color_pair(i + 1))
                        stdscr.addstr(12 + i, 5, f" -   {psutil.Process(running_processes[i].pid).name()} -- ({running_processes[i].usedGpuMemory / 1024} MB) ({running_processes[i].type}) ")
                        stdscr.addstr(13 + list_length, 0, "Press \"i\" key to return to the monitor or \"q\" to quit!")
                stdscr.timeout(args.refresh_rate)
                stdscr.refresh()
                key = stdscr.getch()
                if key == ord("q"):
                    nv.nvmlShutdown()
                    exit(1)
        elif args.interactive and key in [curses.KEY_F1, curses.KEY_F2, curses.KEY_F3, curses.KEY_F4, ord("1"), ord("2"), ord("3"), ord("4"), ord("!"), ord("@"), ord("#"), ord("$"), ord("c"), ord("m"), ord("p"), ord("f"), ord("a")]:
            active_profile = 0
            stdscr.nodelay(False)
            if key == ord("1"):
                save_profile(1)
                delay = 1
            elif key == curses.KEY_F1:
                active_profile = load_profile(1)
                delay = 2
            elif key == ord("!"):
                delete_profile(1)
                delay = 1
            elif key == ord("2"):
                save_profile(2)
                delay = 1
            elif key == curses.KEY_F2:
                active_profile = load_profile(2)
                delay = 2
            elif key == ord("@"):
                delete_profile(2)
                delay = 1
            elif key == ord("3"):
                save_profile(3)
                delay = 1
            elif key == curses.KEY_F3:
                active_profile = load_profile(3)
                delay = 2
            elif key == ord("#"):
                delete_profile(3)
                delay = 1
            elif key == ord("4"):
                save_profile(4)
                delay = 1
            elif key == curses.KEY_F4:
                active_profile = load_profile(4)
                delay = 2
            elif key == ord("$"):
                delete_profile(4)
                delay = 1
            elif key == ord("c"):
                stdscr.addstr(14, 0, "Enter new core clock offset in Mhz:")
                new_core_offset = stdscr.getstr(14, 36, 6)
                try:
                    new_core_offset = int(new_core_offset)
                    stdscr.addstr(15, 0, f"Setting core clock offset to {new_core_offset} MHz...")
                    nv.nvmlDeviceSetGpcClkVfOffset(gpu, new_core_offset)
                except ValueError:
                    stdscr.addstr(15, 0, "Invalid input! Please enter a valid number.")
                    delay = 2
                except nv.NVMLError as e:
                    stdscr.addstr(16, 0, f"Failed to set core clock offset: {str(e)}")
                    delay = 2
            elif key == ord("m"):
                stdscr.addstr(14, 0, "Enter new mem clock offset in Mhz:")
                new_mem_offset = stdscr.getstr(14, 35, 6)
                try:
                    new_mem_offset = int(new_mem_offset)
                    stdscr.addstr(15, 0, f"Setting mem clock offset to {new_mem_offset} MHz...")
                    nv.nvmlDeviceSetMemClkVfOffset(gpu, new_mem_offset * 2)
                except ValueError:
                    stdscr.addstr(15, 0, "Invalid input! Please enter a valid number.")
                    delay = 2
                except nv.NVMLError as e:
                    stdscr.addstr(16, 0, f"Failed to set mem clock offset: {str(e)}")
                    delay = 2
            elif key == ord("p"):
                stdscr.addstr(14, 0, "Enter new power limit in watts:")
                new_power_limit = stdscr.getstr(14, 32, 6)
                try:
                    new_power_limit = int(new_power_limit)
                    stdscr.addstr(15, 0, f"Setting power limit to {new_power_limit} W...")
                    nv.nvmlDeviceSetPowerManagementLimit(gpu, new_power_limit * 1000)
                except ValueError:
                    stdscr.addstr(15, 0, "Invalid input! Please enter a valid number.")
                    delay = 2
                except nv.NVMLError as e:
                    stdscr.addstr(16, 0, f"Failed to set power limit: {str(e)}")
                    delay = 2
            elif key == ord("f"):
                stdscr.addstr(14, 0, "Enter new fan percentage between 30 and 100:")
                new_fan_speed = stdscr.getstr(14, 45, 6)
                try:
                    new_fan_speed = int(new_fan_speed)
                    stdscr.addstr(15, 0, f"Setting fan speed to {new_fan_speed}%...")
                    if 101 > new_fan_speed > 29:
                        num_fans = nv.nvmlDeviceGetNumFans(gpu)
                        for i in range(0, num_fans):
                            nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_MANUAL)
                            nv.nvmlDeviceSetFanSpeed_v2(gpu, i, new_fan_speed)
                        stdscr.addstr(16, 0, "Fan control policy is now MANUAL... return it to AUTO with \"a\"", YELLOW)
                        delay = 2
                    else:
                        raise ValueError("Between 30 and 100!")
                except ValueError:
                    stdscr.addstr(15, 0, "Invalid input! Please enter a valid number.")
                    delay = 2
                except nv.NVMLError as e:
                    stdscr.addstr(15, 0, f"Failed to set fan speed: {str(e)}")
                    delay = 2
            elif key == ord("a"):
                try:
                    stdscr.addstr(14, 0, "Setting fans to automatic control...")
                    num_fans = nv.nvmlDeviceGetNumFans(gpu)
                    for i in range(0, num_fans):
                        nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW)
                        nv.nvmlDeviceSetDefaultFanSpeed_v2(gpu, i)
                except nv.NVMLError as e:
                    stdscr.addstr(15, 0, f"Failed to set fan speed: {str(e)}")
                    delay = 2
            stdscr.refresh()
            time.sleep(1 + delay)
            delay = 0
            stdscr.nodelay(True)


# Execution begins here
source_dir = os.path.dirname(os.path.abspath(__file__))
args = parser.parse_args()
nv.nvmlInit()
gpu = nv.nvmlDeviceGetHandleByIndex(args.gpu_number)

# If this check is true we run in offline mode, else we run in online mode
if args.set_clocks or args.set_power_limit or args.set_max_fan or args.set_auto_fan or args.set_custom_fan or args.set_profile:
    print("Blissful Nvidia Tool Offline Mode")
    print("_________________________________________")
    print("User accepts ALL risks of overclocking/altering power limits/fan settings!")
    print("Additionally, root permission is needed for these changes and the script will fail without it!")
    print()
    print("Enabling persistence...")
    print()
    nv.nvmlDeviceSetPersistenceMode(gpu, 1)
    if args.set_max_fan:
        num_fans = nv.nvmlDeviceGetNumFans(gpu)
        print(f"Found {num_fans} fans!")
        print("Attempting to set fans to max speed...")
        for i in range(0, num_fans):
            nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_MANUAL)
            nv.nvmlDeviceSetFanSpeed_v2(gpu, i, 100)
        print("Fans set to max speed!")
        print()
    elif args.set_auto_fan:
        num_fans = nv.nvmlDeviceGetNumFans(gpu)
        print(f"Found {num_fans} fans!")
        print("Attempting to restore fans to automatic control...")
        for i in range(0, num_fans):
            nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW)
            nv.nvmlDeviceSetDefaultFanSpeed_v2(gpu, i)
        print("Fans restored to automatic control!")
        print()
    elif args.set_custom_fan:
        new_speed = args.set_custom_fan
        if 101 > new_speed > 29:
            num_fans = nv.nvmlDeviceGetNumFans(gpu)
            print(f"Found {num_fans} fans!")
            print(f"Attempting to set fans to {new_speed}%...")
            for i in range(0, num_fans):
                nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_MANUAL)
                nv.nvmlDeviceSetFanSpeed_v2(gpu, i, new_speed)
            print(f"Fans set to {new_speed}%! Please monitor your temps as fan control policy is now MANUAL!")
            print()
        elif new_speed > 100:
            print(f"Value {new_speed} invalid for fan control!")
        else:
            print("Refusing to set fans below 30%! Sorry!")
            print()
    if args.set_clocks:
        core_offset, mem_offset = args.set_clocks
        print(f"Attempting to set core clock offset to {core_offset} MHz and memory clock offset to {mem_offset} MHz...")
        nv.nvmlDeviceSetGpcClkVfOffset(gpu, core_offset)
        nv.nvmlDeviceSetMemClkVfOffset(gpu, mem_offset * 2)  # Multiply memoffset by 2 so it's equivalent to offset in GWE and Windows
        print(f"Set core clock offset to {core_offset} MHz and memory clock offset to {mem_offset} MHz!")
        print()
    if args.set_power_limit:
        print(f"Attempting to set power limit to {args.set_power_limit} W...")
        nv.nvmlDeviceSetPowerManagementLimit(gpu, args.set_power_limit * 1000)
        print(f"Power limit set to {args.set_power_limit} W!")
        print()
    if args.set_profile:
        profile_number = args.set_profile
        print(f"Loading profile {profile_number}!")
        try:
            with open(os.path.join(source_dir, f"profile{profile_number}.bnt"), "r", encoding="utf-8") as file:
                new_core_offset = int(file.readline())
                new_mem_offset = int(file.readline())
                new_power_limit = int(file.readline())
                new_fan_policy = int(file.readline())
                new_fan_speed = int(file.readline())
                print(f"Setting core clock offset to {add_sign(new_core_offset)} Mhz...")
                nv.nvmlDeviceSetGpcClkVfOffset(gpu, new_core_offset)
                print(f"Setting mem clock offset to {add_sign(new_mem_offset)} Mhz...")
                nv.nvmlDeviceSetMemClkVfOffset(gpu, new_mem_offset * 2)
                print(f"Setting core power limit to {new_power_limit}...")
                nv.nvmlDeviceSetPowerManagementLimit(gpu, new_power_limit * 1000)
                if new_fan_policy == 1:
                    if 101 > new_fan_speed > 29:
                        print(f"Setting fan policy to manual and fan speed to {new_fan_speed}%...")
                        num_fans = nv.nvmlDeviceGetNumFans(gpu)
                        for i in range(0, num_fans):
                            nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_MANUAL)
                            nv.nvmlDeviceSetFanSpeed_v2(gpu, i, new_fan_speed)
                    else:
                        raise ValueError("Invalid fan speed setting in profile!")
                else:
                    print("Setting fan policy to automatic control...")
                    num_fans = nv.nvmlDeviceGetNumFans(gpu)
                    for i in range(0, num_fans):
                        nv.nvmlDeviceSetFanControlPolicy(gpu, i, nv.NVML_FAN_POLICY_TEMPERATURE_CONTINOUS_SW)
                        nv.nvmlDeviceSetDefaultFanSpeed_v2(gpu, i)
        except ValueError as e:
            print(f"Some kind of value error prevented the profile loading: {e}")
        except nv.NVMLError as e:
            print(f"Some kind of NVML error prevented the profile loading: {e}")
        except FileNotFoundError:
            print("Profile was not found!")
else:
    #  Interactive mode
    import ctypes
    import curses
    import psutil
    curses.wrapper(draw_dashboard)
nv.nvmlShutdown()
