#!/usr/bin/env python3
#####################################################
# Import time, decimal, serial, reg expr, sys
#
import sys
from time import *
import serial
import radar_actions

####################################################
#
# Description: OmniPreSense OPS24x RADAR Sensor generic signal processor
# 
#####################################################
# Modifiable parameters for this code (not the sensor's profile)
TARGET_MAX_SPEED_ALLOWED = 75  # max speed to be tracked; anything faster is ignored
TARGET_MIN_SPEED_ALLOWED = 10  # min speed to be tracked; anything slower is ignored
IDLE_NOTICE_INTERVAL = 10.0  # time in secs waiting to, um, take action on idle (in state of "not tracking" only)
TARGETLESS_MIN_INTERVAL_TIME = 0.75  # grace period for object to track again (hysteresis)
# note that a change in direction does not allow for this.  
MIN_TRACK_TO_ACQUIRED_TIME = 0.1  # min time in secs that object needs to be tracked for it to be counted


# OPS24x module setting initialization constants (
OPS24x_Units_Pref = 'UK'  # UK for Km/H 
OPS24x_Sampling_Frequency = 'SX'  # 10Ksps
OPS24x_Transmit_Power = 'PX'  # max power
OPS24x_Magnitude_Control = 'M>20\n'  # Magnitude must be > 20
OPS24x_SubInteger_Digits = 'F0'  # no decimal reporting
OPS24x_Module_Information = '??'
OPS24x_Send_Zeros = 'BZ'
OPS24x_MinToReport = 'R>10\n'  # 
OPS24x_MaxToReport = 'R<200\n'  # 

# This is for lab development only
OPS24x_Units_Pref = 'UC'  # "UC" for cm/s to make readings that a hand wave will show

# singleton resource
serial_OPS24x = serial.Serial()  # we will initialize it in main_init()

#
def send_OPS24x_cmd(console_msg_prefix, ops24x_command):
    """
    send commands to the OPS-24x module

    Note regarding debug print: console_msg_prefix is printed out prior to printing the command

    """
    data_for_send_str = ops24x_command
    data_for_send_bytes = str.encode(data_for_send_str)
    print(console_msg_prefix, ops24x_command)
    serial_OPS24x.write(data_for_send_bytes)
    # Initialize message verify checking
    ser_message_start = '{'
    ser_write_verify = False
    # Print out module response to command string
    while not ser_write_verify:
        data_rx_bytes = serial_OPS24x.readline()
        data_rx_length = len(data_rx_bytes)
        if data_rx_length != 0:
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start):
                print(data_rx_str)
                ser_write_verify = True
    return ser_write_verify



def read_velocity():
    """return velocity (signed speed) from OPS24x

    notes on return values:
        Positive speed -> object approaching sensor
        Negative speed -> object moving away from sensor
        None -> something else was returned (blank line, command reply)
    """
    global serial_OPS24x
    object_velocity = 0.0
    ops24x_rx_bytes = serial_OPS24x.readline()
    ops24x_rx_bytes_length = len(ops24x_rx_bytes)
    # a case can be made that if the length is 0, it's a newline char so try again
    if ops24x_rx_bytes_length != 0:
        ops24x_rx_str = str(ops24x_rx_bytes)
        if ops24x_rx_str.find('{') == -1:  # really, { would only be found in first char
            # Speed data found
            object_velocity = float(ops24x_rx_bytes)
            return object_velocity
    return None


def is_speed_in_allowed(object_velocity):
    """boolean function returns True if the argument is in acceptable range

    This uses static global const-variables 
    TARGET_MIN_SPEED_ALLOWED < object_speed_float < TARGET_MAX_SPEED_ALLOWED
    """
    object_speed_float = abs(object_velocity)
    if TARGET_MIN_SPEED_ALLOWED < object_speed_float < TARGET_MAX_SPEED_ALLOWED:
        return True
    else:
        return False


#
# If run from the command line (and there's no other way to run it)
# this will execute, optionalls looking for a serial port to use as the command line argument  
def main_init():
    global serial_OPS24x
    # Initialize the USB port to read from the OPS-24x module
    serial_OPS24x = serial.Serial(
        baudrate=57600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1,
        writeTimeout=2
    )
    if len(sys.argv) > 1:
        serial_OPS24x.port = sys.argv[1]
    else:
        serial_OPS24x.port = "/dev/ttyACM0"  # good for linux
    serial_OPS24x.open()
    serial_OPS24x.flushInput()
    serial_OPS24x.flushOutput()


    # Initialize and query Ops24x Module
    print("\nInitializing Ops24x Module")
    send_OPS24x_cmd("\nSet Sampling Frequency: ", OPS24x_Sampling_Frequency)
    send_OPS24x_cmd("\nSet Transmit Power: ", OPS24x_Transmit_Power)
    send_OPS24x_cmd("\nSet Magnitude Control: ", OPS24x_Magnitude_Control)
    send_OPS24x_cmd("\nSet \"Fractional\" digits: ", OPS24x_SubInteger_Digits)
    send_OPS24x_cmd("\nSet Min Speed To Report", OPS24x_MinToReport);
    send_OPS24x_cmd("\nSet Max Speed To Report", OPS24x_MaxToReport);
    send_OPS24x_cmd("\nSet Units Pref", OPS24x_Units_Pref)
    send_OPS24x_cmd("\nSet Zeros Pref", OPS24x_Send_Zeros)
    #send_OPS24x_cmd("\nAsk Module Information: ", OPS24x_Module_Information)

def main_loop():
    global serial_OPS24x
    try:
        recent_velocity = 0.0
        prior_velocity = 0.0

        # main loop to the program
        while True:
            # Flush serial buffers
            serial_OPS24x.flushInput()
            serial_OPS24x.flushOutput()
            
            # state machine variables
            tracking = False
            target_acquired = False

            # Two principal states.  NotTracking and Tracking.
            # NotTracking and Tracking are split into two loops

            # The first time we get a speed report in range, we will move to tracking
            while not tracking:
                # Reset tracking
                target_acquired = False
                # Wait for numeric speed
                # Initialize wait timer
                idle_start_time = time()
                idle_current_time = idle_start_time
                idle_delta_time = 0.0
                is_valid_speed = False
                # tight loop looking for objects
                while not is_valid_speed:
                    # Get speed from OPS24x
                    speed = read_velocity()
                    if speed is not None:
                        recent_velocity = speed
                        is_valid_speed = is_speed_in_allowed(recent_velocity);
                        # import pdb
                        # pdb.set_trace()
                        # only if IDLE_NOTICE_INTERVAL do we do idle notices
                        if IDLE_NOTICE_INTERVAL>0 and not is_valid_speed:
                            idle_current_time = time() # start the current timer over
                            idle_delta_time = idle_current_time - idle_start_time
                            if idle_delta_time > IDLE_NOTICE_INTERVAL:
                                radar_actions.on_idle_notice_interval()
                                print('notice: still idle')
                                # Reset wait timer
                                idle_start_time = idle_current_time
                        # else:
                        #     print("!")
                # We left the 'while no activity' loop.  a Valid speed was received. move to tracking loop
                # Begin tracking
                tracking = True


            # Tracking has sub-conditions of acquiring ("just tracking") and target-acquired
            # if there's an object that has stayed consistent for a length of time,
            # it is called "target-acquired"
            targetless_start_time = tracking_current_time = tracking_start_time = time()
            tracking_delta_time = 0.0
            while tracking:
                # Initialize tracking timer
                # print('DEBUG: start tracking for acquire')
                # Save old and new speeds
                prior_velocity = recent_velocity
                speed = read_velocity()   
                if speed is not None:
                    recent_velocity = speed
                    tracking_current_time = time()

                    # states: not target_acquired and target_acquired
                    # transitions
                        # upon consistent reading (>MIN_TRACK_TO_ACQUIRED_TIME, no direction change),  not-acq to acq
                        # upon change of direction   if new speed is allowed, acq to not-acq. if out, tracking=false
                        # upon speed-out-of-range for more than an allowable time, tracking = false

                    if is_speed_in_allowed(recent_velocity):
                        # print('DEBUG: same direction maybe. confirm prior_velocity = ', prior_velocity, 'recent_velocity = ', recent_velocity)
                        # Test if directions are the same

                        # The instant the direction changes, old tracking ends
                        if (prior_velocity>0 and recent_velocity>0) or (prior_velocity<0 and recent_velocity<0):

                            # Direction is the same.  This is 
                            # "the common case" 
                            # when observing a target'

                            # Reset targetless wait timer
                            targetless_start_time = None # we most definitely have a target

                            # Check if tracking time is long enough to be valid
                            if (tracking_current_time - tracking_start_time) > MIN_TRACK_TO_ACQUIRED_TIME:
                                if not target_acquired:
                                    radar_actions.on_target_acquired(recent_velocity)
                                    # if we are to note the target acquisition as soon as possible, it goes here.
                                    if recent_velocity > 0:
                                        # motion inbound
                                        print(f"First acquire of inbound motion (speed {recent_velocity})")
                                    elif recent_velocity < 0:
                                        # motion outbound
                                        print(f"First acquire of outbound motion (speed {recent_velocity})")

                                    target_acquired = True # will be changed only first time tracking_delta_time > MIN_TRACK_TO_ACQUIRED_TIME
                                    # now Continue tracking and getting speeds until direction change or wait timeout
                                else:
                                    # target still acquired.
                                    # thats cool
                                    # hey, if there's a change (for not, increase only) in speed, do any actions needed
                                    if abs(recent_velocity) > abs(prior_velocity):
                                        print(f"Acceleration detected (speed {recent_velocity})")
                                        radar_actions.on_target_accelerating(recent_velocity)
                                    # elif abs(recent_velocity) < abs(prior_velocity):
                                    #     print(f"Deceleration detected (speed {recent_velocity})")
                                    #     radar_actions.on_target_decelerating(recent_velocity)
                                    # elif recent_velocity == 0:
                                    #     print(f"no motion detected")
                                    #     on_no_motion_detected()

                        else: # not the same sign (thus not the same direction)
                            # Direction changed!
                            # So, this immediately stops tracking one target and starts tracking another
                            # which has similar logic to going thru tracking/not-acquired and then acquired. 
                            if target_acquired:
                                # If we're seeing a different direction, then 
                                # therefore it must be a different object. 
                                #   
                                # possible cases:
                                #   Tracking was valid and object is going past us.  Simple choice: declare new object.
                                #   A new object is coming opposite direction.  Simple choice: immediately decree the old object is gone
                                
                                # So, now we have to enforce business policy.  
                                target_acquired = False # future policy improvement: don't do this immediately.
                                prior_velocity = 0

                                if recent_velocity > 0:
                                    # motion changed to inbound
                                    print('direction changed. motion now inbound')
                                elif recent_velocity < 0:
                                    # motion outbound
                                    print('direction changed. motion now outbound')
                                else:
                                    # Getting zeros.  No object seen
                                    print('Tracking no object')

                            else:
                                # Tracking time too short and wasn't not valid
                                print('Direction changed before tracking lock, restart tracking')
                                tracking_start_time = time()

                            # this cant happen, so no need to test: if recent_velocity != 0:
                            # Reset valid tracking and continue to track new object                            
                            targetless_start_time = time()  # it could be the start of targetless
                            tracking_start_time = time()    # or even the start of tracking

                    else: # speed is out of allowed range
                        targetless_current_time = time()
                        if targetless_start_time == None:
                            targetless_start_time = time()
                        else:
                            targetless_delta_time = targetless_current_time - targetless_start_time
                            # declare giving up on target if time expired
                            # JW - may want to do that if direction changes now, too
                            if targetless_delta_time > TARGETLESS_MIN_INTERVAL_TIME:
                                if target_acquired:
                                    radar_actions.on_target_lost()
                                    # some target was acquired, but apparently object went out of range
                                    # because now we have out-of-range speed
                                    # JW-observe: if target disappears (before direction switch), it will be counted here
                                    # JW-WARN: but it could be a very long time between reporting events if the target
                                    # goes out of range (like walks behind) so this is not the ideal way to report.
                                    if recent_velocity > 0:
                                        # just captured motion was inbound.  could have changed though, it's a low reading
                                        print('target lost.  seeing disallowed inbound')
                                    elif recent_velocity < 0:
                                        # just captured motion was outbound.  could have changed though, it's a low reading
                                        print('target lost.  seeing disallowed outbound')
                                    else:
                                        print('target lost.  seeing zeros')
                                target_acquired = False

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting.")
    finally:
        # clean up
        serial_OPS24x.close()


if __name__ == "__main__":
    main_init()
    main_loop()