#!/usr/bin/env python3
#####################################################
# Import time, decimal, serial, reg expr, sys
#
import sys
import time
import serial
import radar_actions
import logging
logging.basicConfig(stream=sys.stderr, level=logging.WARN)
logging.debug('Welcome to ops_radar')

####################################################
#
# Description: OmniPreSense OPS24x RADAR Sensor generic velocity processor
# 
#####################################################
# Modifiable parameters for this code (not necessarily the sensor's profile)
TARGET_MAX_SPEED_ALLOWED = 75   # max speed to be tracked; anything faster is ignored
TARGET_MIN_SPEED_ALLOWED = 10   # min speed to be tracked; anything slower is ignored
IDLE_NOTICE_INTERVAL = 10.0     # time in secs waiting to, um, take action on idle (in state of "not tracking" only)
TARGETLESS_MIN_INTERVAL_TIME = 0.75  # grace period for object to track again (hysteresis)
# note that a change in direction does not allow for this.  
MIN_TRACK_TO_ACQUIRED_TIME = 0.1  # min time in secs that object needs to be tracked for it to be counted

OPS24X_INFO_QUERY_COMMAND = '??'

# OPS24x configuration parameters (sent to sensor)
OPS24X_UNITS_PREF = 'US'            # US for MPH , UK for Km/H 
OPS24X_SAMPLING_FREQUENCY = 'SX'    # 10Ksps
OPS24X_TRANSMIT_POWER = 'PX'        # max power
OPS24X_MAGNITUDE_MIN = 'M>20\n'     # Magnitude must be > this
OPS24X_DECIMAL_DIGITS = 'F0'        # F-zero for no decimal reporting
OPS24X_BLANKS_PREF = 'BZ'           # Blanks pref: send 0's not silence
OPS24X_LIVE_SPEED = 'O1OS'          # OS cancels 9243 mode, enables no-delay speeds.  O1 only one speed
OPS24X_MAX_REPORTABLE = 'R<200\n'   # Report only < than this speed
OPS24X_MIN_REPORTABLE = f'R>{TARGET_MIN_SPEED_ALLOWED}\n'       # Report only > this speed
OPS24X_BIDIRECTIONAL = "R|"
OPS24X_INBOUND_ONLY  = "R+"
OPS24X_OUTBOUND_ONLY = "R|"
OPS24X_DIRECTION_PREF = OPS24X_BIDIRECTIONAL

# These are for lab development only, so hand-waves are usable
OPS24X_UNITS_PREF = 'UC'  # "UC" for cm/s
TARGET_MAX_SPEED_ALLOWED = 150
OPS24X_DIRECTION_PREF = OPS24X_INBOUND_ONLY
# remove them when moving to actual vehicle testing.


# global singleton resource
serial_port = serial.Serial()  # we will initialize it in main_init()


def send_ops24x_cmd(logging_prefix,ops24x_command):
    """
    send commands to the OPS24x module

    Note regarding debug print: console_msg_prefix is printed out prior to printing the command

    """
    global serial_port
    data_for_send_str = ops24x_command
    data_for_send_bytes = str.encode(data_for_send_str)
    logging.info(f"{logging_prefix}{ops24x_command}")
    serial_port.write(data_for_send_bytes)
    # Initialize message verify checking
    ser_message_start = '{'
    ser_write_verify = False
    # Print out module response to command string
    while not ser_write_verify:
        data_rx_bytes = serial_port.readline()
        data_rx_length = len(data_rx_bytes)
        if data_rx_length != 0:
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start):
                logging.debug(data_rx_str)
                ser_write_verify = True
    return ser_write_verify


def read_velocity():
    """return the velocity (signed speed) from OPS24x

    notes on return values:
        Positive speed -> object approaching sensor
        Negative speed -> object moving away from sensor
        None -> something else was received (blank line, command reply, etc)
    """
    global serial_port
    object_velocity = 0.0
    ops24x_rx_bytes = serial_port.readline()
    ops24x_rx_bytes_length = len(ops24x_rx_bytes)
    # a case can be made that if the length is 0, it's a newline char so try again
    if ops24x_rx_bytes_length != 0:
        ops24x_rx_str = str(ops24x_rx_bytes)
        if ops24x_rx_str.find('{') == -1:  # really, { would only be found in first char
            try:
                # Speed data found (maybe)
                object_velocity = float(ops24x_rx_bytes)
                return object_velocity
            except ValueError:  # well just toss this line out
                return None
    return None


def is_speed_in_allowed(velocity):
    """boolean function returns True if the argument is in acceptable range

    Parameter:
    velocity -- value to compare against the constants.  abs() is applied to this
    return TARGET_MIN_SPEED_ALLOWED < abs(velocity) < TARGET_MAX_SPEED_ALLOWED
    """
    if TARGET_MIN_SPEED_ALLOWED < abs(velocity) < TARGET_MAX_SPEED_ALLOWED:
        return True
    else:
        return False


def main_init():
    """
    main program initialization: open the serial port, initialize the radar
    """
    # Initialize the USB port to read from the OPS-24x module.  
    # Baud rate will just lower the native USB speed.  
    global serial_port
    serial_port = serial.Serial(
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1,
        writeTimeout=2
    )
    if len(sys.argv) > 1:
        serial_port.port = sys.argv[1]
    else:
        serial_port.port = "/dev/ttyACM0"  # good for linux
    serial_port.open()
    serial_port.flushInput()
    serial_port.flushOutput()

    # Initialize and query Ops24x Module
    logging.info("Initializing Ops24x Module")
    send_ops24x_cmd("Send Sampling Frequency: ", OPS24X_SAMPLING_FREQUENCY)
    send_ops24x_cmd("Send Transmit Power: ", OPS24X_TRANSMIT_POWER)
    send_ops24x_cmd("Send Magnitude Control: ", OPS24X_MAGNITUDE_MIN)
    send_ops24x_cmd("Send Decimal digits: ", OPS24X_DECIMAL_DIGITS)
    send_ops24x_cmd("Send line of Min Speed To Report:", OPS24X_MIN_REPORTABLE)
    send_ops24x_cmd("Send line of Max Speed To Report: ", OPS24X_MAX_REPORTABLE)
    send_ops24x_cmd("Send Units Preference: ", OPS24X_UNITS_PREF)
    send_ops24x_cmd("Send Zeros Preference: ", OPS24X_BLANKS_PREF)
    send_ops24x_cmd("Send Force Instantaneous speeds: ", OPS24X_LIVE_SPEED)
    send_ops24x_cmd("Send Directional Preference: ", OPS24X_INBOUND_ONLY)
    #send_ops24x_cmd("Ask Module Information: ", OPS24X_INFO_QUERY_COMMAND)



def main_loop():
    """
    main program loop:
    there are two important states in this code, not-tracking and tracking.
    when not tracking, read data until there's an object worth tracking
    when tracking, analyze, and when appropriate, call an event handler.

    The event handlers have a baseline implementation in radar_actions.py and include
    on_target_acquired(recent_speed)
    on_target_accelerating(recent_speed)
    on_target_decelerating(recent_speed)
    on_target_lost()
    on_idle_notice_interval()
    """
    global serial_port
    recent_velocity = 0.0
    prior_velocity = 0.0

    # main loop to the program
    while True:
        # Flush serial buffers
        serial_port.flushInput()
        serial_port.flushOutput()
        
        # state machine variables
        tracking = False
        target_acquired = False

        # Two principal states.  NotTracking and Tracking.
        # NotTracking and Tracking are split into two loops and this goes between the two

        # The first time we get a speed report in range, we will move to tracking
        while not tracking:
            # Reset tracking
            target_acquired = False
            # Wait for numeric speed
            # Initialize wait timer
            idle_start_time = time.time()
            idle_current_time = idle_start_time
            idle_delta_time = 0.0
            is_valid_speed = False
            # tight loop looking for objects
            while not is_valid_speed:
                # Get speed from OPS24x
                velocity = read_velocity()
                if velocity is not None:
                    recent_velocity = velocity
                    is_valid_speed = is_speed_in_allowed(recent_velocity)
                    logging.debug(f'not tracking.  received speed:{abs(velocity)} ({is_valid_speed}) ')

                    # only if IDLE_NOTICE_INTERVAL do we do idle notices
                    if IDLE_NOTICE_INTERVAL>0 and not is_valid_speed:
                        idle_current_time = time.time() # start the current timer over
                        idle_delta_time = idle_current_time - idle_start_time
                        if idle_delta_time > IDLE_NOTICE_INTERVAL:
                            radar_actions.on_idle_notice_interval()
                            logging.debug('notice: still idle')
                            # Reset wait timer
                            idle_start_time = idle_current_time
                    # else:
                    #     print("!")
            # We left the 'while no activity' loop.  a Valid speed was received. move to tracking loop
            # Begin tracking
            tracking = True
            logging.debug(f'NOW move to tracking.  received speed:{abs(velocity)}')


        # Tracking has sub-conditions of acquiring ("just tracking") and target-acquired
        # if there's an object that has stayed consistent for a length of time,
        # it is called "target-acquired"
        targetless_start_time = tracking_current_time = tracking_start_time = time.time()
        while tracking:
            # Initialize tracking timer
            # logging.info('start tracking for acquire')
            # Save old and new speeds
            prior_velocity = recent_velocity
            velocity = read_velocity()   
            if velocity is None:
                continue

            recent_velocity = velocity
            logging.debug(f'analyze received speed:{abs(recent_velocity)}')
            tracking_current_time = time.time()

            # states: not target_acquired and target_acquired
            # transitions
                # upon consistent reading (>MIN_TRACK_TO_ACQUIRED_TIME, no direction change),  not-acq to acq
                # upon change of direction   if new speed is allowed, acq to not-acq. if out, tracking=false
                # upon speed-out-of-range for more than an allowable time, tracking = false

            if is_speed_in_allowed(recent_velocity):
                # logging.debug('look for direction changes. confirm prior_velocity = ', prior_velocity, 'recent_velocity = ', recent_velocity)
                # The instant the direction changes, old tracking ends

                if (prior_velocity>0 and recent_velocity>0) or \
                        (prior_velocity<0 and recent_velocity<0):
                    # This should be the most common case when observing a target

                    # Reset targetless wait timer
                    targetless_start_time = None # we most definitely have a target

                    # Check if tracking time is long enough to be valid
                    if (tracking_current_time - tracking_start_time) > MIN_TRACK_TO_ACQUIRED_TIME:
                        if not target_acquired:
                            radar_actions.on_target_acquired(recent_velocity)
                            # if we are to note the target acquisition as soon as possible, it goes here.
                            if recent_velocity > 0:  # motion inbound
                                logging.info(f"First acquire of inbound motion (speed {recent_velocity})")
                            elif recent_velocity < 0: # motion outbound
                                logging.info(f"First acquire of outbound motion (speed {recent_velocity})")

                            target_acquired = True # will be changed only first time tracking_delta_time > MIN_TRACK_TO_ACQUIRED_TIME
                            # now Continue tracking and getting speeds until direction change or wait timeout
                        else:
                            # target still acquired. that's great
                            # hey, if there's a change in speed, do any desired actions
                            if abs(recent_velocity) > abs(prior_velocity):
                                logging.info(f"Acceleration detected (speed {recent_velocity})")
                                radar_actions.on_target_accelerating(recent_velocity)
                            # elif abs(recent_velocity) < abs(prior_velocity):
                            #     logging.info(f"Deceleration detected (speed {recent_velocity})")
                            #     radar_actions.on_target_decelerating(recent_velocity)

                else: # not the same sign (thus not the same direction)
                    # Direction changed!
                    # So, this immediately stops tracking one target and starts tracking another
                    # which has similar logic to going thru tracking/not-acquired and then acquired. 
                    if target_acquired:  # well, it is not acquired now
                        # possible cases:
                        #   Tracking was valid and object is going past us.  Simple choice: declare new object.
                        #   A new object is coming opposite direction.  Simple choice: immediately decree the old object is gone
                        
                        # So, now we have to enforce business policy.  
                        target_acquired = False # future policy improvement: don't do this immediately?
                        prior_velocity = 0

                        if recent_velocity > 0: # motion changed to inbound
                            logging.info('direction changed. motion now inbound')
                        elif recent_velocity < 0:# motion outbound
                            logging.info('direction changed. motion now outbound')
                        else:
                            # Getting zeros.  No object seen
                            logging.info('Tracking no object')
                    else:
                        # Tracking time too short and wasn't not valid
                        logging.info('Direction changed before tracking lock, restart tracking')

                    # Reset valid tracking and continue to track new object                            
                    targetless_start_time = time.time()  # it could be the start of targetless
                    tracking_start_time = time.time()    # or even the start of tracking

            else: # velocity is out of allowed range
                logging.debug(f'speed {abs(velocity)} outside of allowed range')
                targetless_current_time = time.time()
                if targetless_start_time == None:
                    targetless_start_time = time.time()
                else:
                    targetless_delta_time = targetless_current_time - targetless_start_time
                    # declare giving up on target if time expired
                    # todo?: may want to do that if direction changes now, too
                    if targetless_delta_time > TARGETLESS_MIN_INTERVAL_TIME:
                        if target_acquired:
                            radar_actions.on_target_lost()
                            # some target was acquired, but apparently object went out of range
                            # because now we have out-of-range speed
                            # OBSERVE: if target disappears (before direction switch), it will be counted here
                            # WARN: but it could be a very long time between reporting events if the target
                            # goes out of range (like walks behind) so this is not the ideal way to report.
                            if recent_velocity > 0:
                                # just captured motion was inbound.  could have changed though, it's a low reading
                                logging.info('target lost.  seeing disallowed inbound')
                            elif recent_velocity < 0:
                                # just captured motion was outbound.  could have changed though, it's a low reading
                                logging.info('target lost.  seeing disallowed outbound')
                            else:
                                logging.info('target lost.  seeing zeros')
                        target_acquired = False
                        tracking = False
        # end if tracking
    # end the not-tracking -> tracking loop.  do it again


if __name__ == "__main__":
    """
    The purpose of this program is 
    to read radar data from an OPS24x RADAR (velocity) sensor 
    and take action upon values (calling event handlers as appropriate) 
    """
    main_init()
    try:
        main_loop()
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting.")
    finally:
        # clean up
        serial_port.close()
