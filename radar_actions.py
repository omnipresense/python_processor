
from datetime import datetime

def on_target_acquired(recent_speed):
    now = datetime.now()
    print(f'on_target_acquired called at {now.strftime("%d/%m/%Y %H:%M:%S")}')

def on_target_accelerating(recent_speed):
    now = datetime.now()
    print(f'on_target_accelerating called at {now.strftime("%d/%m/%Y %H:%M:%S")}')

def on_target_decelerating(recent_speed):
    now = datetime.now()
    print(f'on_target_decelerating called at {now.strftime("%d/%m/%Y %H:%M:%S")}')

def on_target_lost():
    now = datetime.now()
    print(f'on_target_lost called at {now.strftime("%d/%m/%Y %H:%M:%S")}')

def on_idle_notice_interval():
    now = datetime.now()
    print(f'on_target_lost called at {now.strftime("%d/%m/%Y %H:%M:%S")}')
