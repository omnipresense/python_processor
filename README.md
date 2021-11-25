# python_processor 
A sample python program that reads data from the OmniPreSense RADAR and takes actions (as developed by the customer) 

### Required Libraries (with optional python virtual environment)
```
$ python -m venv my_env
$ my_env\Scripts\activate
$ pip install requests serial
```

### Execution
On Windows, the default /dev/ttyACM0 port is not he name of the USB port.  
So on Windows, if using the first available port, run the program by
```
python ops_radar.py COM3
```
Linux users do not need to supply an argument (if /dev/ttyACM0 is correct).
If using the UART pins, use /dev/ttyAMA0.  If using another Unix flavor, change the code or pass the correct serial port argument. 

## Concepts
The purpose of this program is 
to read radar data from an OPS24x RADAR (velocity) sensor and take action upon values (calling event handlers as appropriate).
The handlers should reside in a different file, which should be imported into ops_radar.py

The event handlers have a baseline implementation in radar_actions.py and include
```
on_target_acquired(recent_speed)
on_target_accelerating(recent_speed)
on_target_decelerating(recent_speed)
on_target_lost()
on_idle_notice_interval()
```
radar_actions_ipcamera.py is a different implementation which can use a web interface of an IP camera.  (This was originally developed to control an Axis camera)



## Development tips
- Change logging by setting the last value in the line
```logging.basicConfig(stream=sys.stderr, level=logging.INFO)```  
WARN will show only warnings of failures.  DEBUG gives information that might be helpful only when debugging.  INFO is somewhere inbetween.

- When first trying out the code ("in a lab") you will probably want different setting
so that you can wave at the sensor and see sensible results.
```
# These are for lab development only, so hand-waves are usable
OPS24X_UNITS_PREF = 'UC'  # "UC" for cm/s
TARGET_MAX_SPEED_ALLOWED = 150
OPS24X_DIRECTION_PREF = OPS24X_INBOUND_ONLY
```
Remove these when ready for road-side testing.