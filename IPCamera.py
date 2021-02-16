from sys import argv
import json
import requests
from requests.auth import HTTPDigestAuth

class IPCamera:
    payload = {}
    overlay_url = "http://4.3.2.1/webcall.cgi"
    headers = {"Content-Type": "application/json"}
    auth = HTTPDigestAuth('user','password')

    def __init__(self, **kwargs):
        for key,value in kwargs.items():
            if key == "overlay_url":
                self.overlay_url = value
            # elif key == any others, then set
            # note that text and colors are set via update....

        self.overlay_payload = {
            "apiVersion": "1.0",
            "context": "321",
            "method": "setText",
            "params": {
                "camera": 1,
                "identity":3,
                "fontSize":108,
                "text":" ",
                "textBGColor": "red",
                "position": "bottomLeft",
                "textColor": "white",
                "text": "Radar by OmniPreSense"
            }
        }

        # https://www.axis.com/vapix-library/subjects/t10037719/section/t10004596/display?section=t10004596-t10047558
        # self.record_payload = {
        #     "apiVersion": "1.0",
        #     "context": "321",
        #     "method": "setText",
        #     "params": {
        #     "camera": 1,
        #     "identity":2,
        #     "text":"python overlay",
        #     "textBGColor": "red",
        #     "position": "topRight",
        #     "textColor": "white",
        #     "params":{"textColor":"white","textBGColor":"black","text":""}
        #     }
        # }

    def update_overlay_payload_for_val(self, val):
        try:
            val_as_num = float(val)
            if val_as_num > 35:
                self.overlay_payload["params"]["textColor"] = "red"
                self.overlay_payload["params"]["textBGColor"] = "white"
            else:
                self.overlay_payload["params"]["textColor"] = "black"
                self.overlay_payload["params"]["textBGColor"] = "white"
        except ValueError:  # fine, just text
            self.overlay_payload["params"]["textColor"] = "red"
            self.overlay_payload["params"]["textBGColor"] = "transparent"
        #now just update the actual text
        self.overlay_payload["params"]["text"] = val
        return self.overlay_payload

    def send_overlay_payload(self):
        r = requests.post(self.overlay_url, 
            auth = self.auth, 
            headers = self.headers, 
            json = self.overlay_payload)
        return r

if __name__ == "__main__":
    cam = IPCamera()
    if len(argv)==1:
        cam.overlay_payload["params"]["text"] = "python was here"
    elif len(argv) > 1:
        print("calling update with:",argv[1])
        cam.update_overlay_payload_for_val(argv[1])
        
    r = requests.post(cam.overlay_url, 
        auth = cam.auth, 
        headers = cam.headers, 
        json = cam.overlay_payload)
    import pdb; pdb.set_trace()
    print("camera returned:",r)

