import ssl,socket
import pytest
from backend.evaluators.ansiedad_semantic import cash_safe_transport as t

def test_preresolution_keeps_tls_hostname_and_host(monkeypatch):
    seen={}
    monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_CREDENTIAL')
    monkeypatch.setattr(t.socket,'getaddrinfo',lambda *a:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('192.0.2.1',443))])
    monkeypatch.setattr(t.socket,'create_connection',lambda addr,timeout,source:seen.update(tcp=addr))
    class Response:
        status=200
        def read(self):return b'{"ok":true}'
    class Connection:
        def __init__(self,host,port,timeout,context):
            seen.update(host=host,port=port,check_hostname=context.check_hostname,verify=context.verify_mode)
        def request(self,method,path,body,headers):
            seen.update(method=method,path=path);self._create_connection(('api.openai.com',443),120)
        def getresponse(self):return Response()
        def close(self):seen['closed']=True
    monkeypatch.setattr(t.http.client,'HTTPSConnection',Connection)
    assert t.prepared_https_transport()({'model':'test'})=={'ok':True}
    assert seen=={'host':'api.openai.com','port':443,'check_hostname':True,'verify':ssl.CERT_REQUIRED,
                 'method':'POST','path':'/v1/chat/completions','tcp':('192.0.2.1',443),'closed':True}

def test_dns_failure_never_constructs_https_request(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_CREDENTIAL')
    def fail(*a):raise socket.gaierror('controlled DNS failure')
    monkeypatch.setattr(t.socket,'getaddrinfo',fail)
    monkeypatch.setattr(t.http.client,'HTTPSConnection',lambda *a,**k:pytest.fail('No connection allowed'))
    with pytest.raises(socket.gaierror):t.prepared_https_transport()

def test_missing_key_fails_before_dns(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.setattr(t.socket,'getaddrinfo',lambda *a:pytest.fail('No DNS needed'))
    with pytest.raises(PermissionError):t.prepared_https_transport()
