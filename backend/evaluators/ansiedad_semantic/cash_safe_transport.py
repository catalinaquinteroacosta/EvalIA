"""Resolve before reservation, retain TLS hostname checks, never follow redirects."""
import http.client,json,os,socket,ssl
from .budgeted_reader import canonical

def prepared_https_transport():
    # Resolution failure occurs before Reader reserves or invokes transport.
    if not os.environ.get('OPENAI_API_KEY'):
        raise PermissionError('API key absent in environment; no credentials file access')
    addresses=socket.getaddrinfo('api.openai.com',443,socket.AF_INET,socket.SOCK_STREAM)
    if not addresses:raise OSError('No resolved API address; no request reserved')
    ip=addresses[0][4][0]
    context=ssl.create_default_context()
    if not context.check_hostname or context.verify_mode!=ssl.CERT_REQUIRED:
        raise ValueError('TLS validation must remain enabled')
    def send(body):
        connection=http.client.HTTPSConnection('api.openai.com',443,timeout=120,context=context)
        # HTTPSConnection still uses api.openai.com for SNI, certificate checks
        # and HTTP Host. Only TCP addressing uses the pre-resolved address.
        connection._create_connection=lambda address,timeout,source_address=None: socket.create_connection((ip,443),timeout,source_address)
        try:
            connection.request('POST','/v1/chat/completions',body=canonical(body).encode('utf-8'),
                headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json'})
            response=connection.getresponse();raw=response.read()
            if response.status!=200:raise ValueError('API HTTP '+str(response.status)+'; no automatic redirect/retry')
            return json.loads(raw)
        finally:connection.close()
    return send
