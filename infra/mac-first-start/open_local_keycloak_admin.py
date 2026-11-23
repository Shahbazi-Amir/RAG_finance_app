"""Open the temporary localhost-only Keycloak admin listener in isolated Chrome."""

import argparse
import base64
import hashlib
import socket
import ssl
import subprocess
import tempfile

name='rag-mac-keycloak-admin-local'
host='idp-staging.ragfinance.ir'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ca", required=True, help="Trusted local ingress CA certificate")
args = parser.parse_args()
binding=subprocess.check_output([
    'docker','inspect','-f','{{with (index .NetworkSettings.Ports "8443/tcp")}}{{(index . 0).HostIp}}:{{(index . 0).HostPort}}{{end}}',name
],text=True).strip()
address,port=binding.split(':')
if address != '127.0.0.1' or not port.isdecimal():
    raise SystemExit('ADMIN_LISTENER_NOT_LOOPBACK')
with socket.create_connection((address,int(port)),timeout=12) as sock:
    with ssl.create_default_context(cafile=args.ca).wrap_socket(sock,server_hostname=host) as tls:
        pem=ssl.DER_cert_to_PEM_cert(tls.getpeercert(binary_form=True))
key=subprocess.check_output(['openssl','x509','-pubkey','-noout'],input=pem.encode())
der=subprocess.check_output(['openssl','pkey','-pubin','-outform','DER'],input=key)
pin=base64.b64encode(hashlib.sha256(der).digest()).decode()
profile=tempfile.mkdtemp(prefix='rag-private-keycloak-admin-')
subprocess.run([
    'open','-na','Google Chrome','--args',
    '--user-data-dir='+profile,'--no-first-run','--no-proxy-server',
    '--disable-sync','--disable-background-networking','--disable-extensions',
    f'--host-resolver-rules=MAP {host} {binding},MAP * ~NOTFOUND',
    '--ignore-certificate-errors-spki-list='+pin,
    f'https://{host}/admin/master/console/',
],check=True)
print('PRIVATE_CHROME_WINDOW_LAUNCHED')
