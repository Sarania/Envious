<div align="center">
  <h1>Envious</h1>
  <img src="screenshot.png?version=3" alt="Blissful Nvidia Tool" />
</div>

Envious is a friendly, feature-rich application for administering modern Nvidia GPUs (Maxwell or higher) directly from your Linux command line.

It only requires Python 3 and the nvidia-ml-py libraries along with up-to-date Nvidia drivers. Using envious, you can overclock or underclock your GPU, adjust power limits, control fan speeds, and view
real-time monitoring information through a built-in curses-based interface, with support for multiple GPUs! Profiles can be saved and loaded for convenience, and the tool can operate non-interactively for scripting purposes.

While monitoring can be performed as a normal user, many of the overclocking, power management, and fan control operations will require root privileges. Use this tool responsibly, as you accept all risks
associated with making changes to your GPU’s settings.

License: MIT


## Usage
Profiles will be stored within the local directory unless envious is installed with the script in which case they are stored in /var/lib/envious. You need nvidia-ml-py > 11.5 installed at the system level or in an active venv.  

```
# From within the Envious directory:
python envious.py --reactive-color  # Run a colorful monitor for the GPU
# Any of the below need root/admin permissions!
python envious.py --interactive # Run the monitor in interactive mode to enable clock, power and fan control. h for help!
python envious.py --set-clocks -150 1000  # Set the GPU core offset to -150Mhz and GPU memory offset to +1000Mhz. 
# Note the memory value is the same as that specified in GreenWithEnvy/MSI Afterburner, NOT the same as nvidia-settings!
python envious.py --set-power-limit 300 # Set the power limit in watts(nvidia-ml-py will reject invalid values)
# Additionally you can specify which GPU to monitor or control with --gpu-number and combine commands:
python envious.py --gpu-number 1 --set-power-limit 280 --set-max-fan  # Set the power limit and fan speed on GPU 1 (0 is 1st, 1 is 2nd, etc...)
# Additionally, an optional install script can be used to install the tool:
sudo ./install.sh
# Then you can:
sudo envious --interactive
# And also
man envious  # For full command list!
```
