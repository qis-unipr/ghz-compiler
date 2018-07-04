APItoken = "19d9c94a929cf0d2eb9434c7ff41e0d7e6c0e4a5b7a50afc845d0952e0dd336bde2e83da2de82a4ea10b3feded5562668617753088f85f8d9149055bfe005a6c"

URL = 'https://quantumexperience.ng.bluemix.net/api'

if 'APItoken' not in locals():
    raise Exception("Please set up your api access token. See config.py.")
