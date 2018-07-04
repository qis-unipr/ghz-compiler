APItoken = None

URL = 'https://quantumexperience.ng.bluemix.net/api'

if 'APItoken' not in locals():
    raise Exception("Please set up your api access token. See config.py.")
