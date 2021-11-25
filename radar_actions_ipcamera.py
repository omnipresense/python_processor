
from datetime import datetime
import requests
from requests.auth import HTTPDigestAuth
import IPCamera


cam = IPCamera.IPCamera(overlay_url="http://127.0.0.1/test_url")

def on_target_acquired(recent_speed):
    now = datetime.now()
    tstamp = now.strftime("\n%d/%m/%Y\n%H:%M:%S")
    cam.update_overlay_payload_for_val(str(abs(round(recent_speed)))+" km/h" + tstamp)
    cam.send_overlay_payload()

def on_target_accelerating(recent_speed):
    now = datetime.now()
    tstamp = now.strftime("\n%d/%m/%Y\n%H:%M:%S")
    cam.update_overlay_payload_for_val(str(abs(round(recent_speed)))+" km/h" + tstamp)
    cam.send_overlay_payload()

def on_target_decelerating(recent_speed):
    pass

def on_target_lost():
    cam.update_overlay_payload_for_val("")
    cam.send_overlay_payload()

def on_idle_notice_interval():
    # cam.update_payload_for_val("", cam.payload)
    # cam.send_payload()
    pass
