<div align="center">
  <h1>Envious</h1>
  <img src="screenshot.png?version=3" alt="Blissful Nvidia Tool" />
</div>

Envious is a friendly, feature-rich application for administering modern Nvidia GPUs (Maxwell or higher) directly from your Linux command line.

It only requires Python 3 and the nvidia-ml-py libraries along with up-to-date Nvidia drivers. Using envious, you can overclock or underclock your GPU, adjust power limits, control fan speeds, and view
real-time monitoring information through a built-in curses-based interface. Profiles can be saved and loaded for convenience, and the tool can operate non-interactively for scripting purposes.

While monitoring can be performed as a normal user, many of the overclocking, power management, and fan control operations will require root privileges. Use this tool responsibly, as you accept all risks
associated with making changes to your GPU’s settings.

License: MIT


## Usage

```
python envious.py  # Run a monitor for the GPU
python envious.py --reactive-color  # Run a colorful monitor for the GPU
# Any of the below need root/admin permissions!
python envious.py --interactive # Run the monitor in interactive mode. h for help!
python envious.py --set-clocks -150 1000  # Set the GPU core offset to -150Mhz and GPU memory offset to +1000Mhz. 
# Note the memory value is the same as that specified in GreenWithEnvy/MSI Afterburner, NOT the same as nvidia-settings!
python envious.py --set-power-limit 300  # Set the power limit in watts. nvidia-ml-py will reject invalid values. 
python envious.py --set-max-fan  # Set ALL fans to maximum speed.
python envious.py --set-auto-fan  # Set ALL fans back to automatic control.
# Additionally you can specify which GPU to monitor or control with --gpu-number:
python envious.py --gpu-number 1 --set-power-limit 280  # Set the power limit to 280 Watts on GPU 1 (0 is 1st, 1 is 2nd, etc...)
```
