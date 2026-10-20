"""Free unauthenticated DNS/HTTPS diagnostics; no model or credential access."""
import json
import socket
from urllib.request import urlopen
from urllib.error import HTTPError

def probe():
    result={'billable_model_calls':0,'credentials_read':False,'https_reachable':False}
    try:
        result['dns_addresses']=len(socket.getaddrinfo('api.openai.com',443))
        try:
            with urlopen('https://api.openai.com',timeout=15) as response:
                result['status']=response.status
        except HTTPError as error:result['status']=error.code
        result['https_reachable']=True
    except Exception as error:result['error']=type(error).__name__+': '+str(error)
    return result

if __name__=='__main__':print(json.dumps(probe()))
