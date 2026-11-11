"""Small client for the VICE text remote monitor."""
import atexit, re, socket, subprocess, time

PROMPT = re.compile(rb"\(C:\$[0-9a-f]{4}\) $")

class Vice:
    def __init__(self, d64, extra=(), port=6510):
        self.p = subprocess.Popen(
            ["x64sc", "-default", "-minimized", "-warp", "-remotemonitor",
             "-remotemonitoraddress", "ip4://127.0.0.1:%d" % port,
             "-autostart", d64] + list(extra),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(self.p.kill)    # never leave VICE running
        for _ in range(100):
            try:
                self.s = socket.create_connection(("127.0.0.1", port)); break
            except OSError:
                time.sleep(0.2)
        self.stop()

    def wait(self, timeout=300):
        buf = b""
        self.s.settimeout(timeout)
        while not PROMPT.search(buf):
            d = self.s.recv(65536)
            if not d:
                raise EOFError(buf.decode(errors="replace"))
            buf += d
        return buf.decode(errors="replace")

    def cmd(self, line, timeout=300):
        self.s.sendall(line.encode() + b"\n")
        return self.wait(timeout)

    def go(self, timeout=300):
        """Continue until the next breakpoint; returns the monitor text."""
        return self.cmd("x", timeout)

    def run_free(self):
        self.s.sendall(b"x\n")

    def stop(self):
        """Enter the monitor while the emulation runs."""
        self.s.sendall(b"\n")
        out = self.wait()
        time.sleep(0.5)                 # drop any extra prompts
        self.s.setblocking(False)
        try:
            while self.s.recv(65536):
                pass
        except OSError:
            pass
        self.s.setblocking(True)
        return out

    def peek(self, addr, n=1):
        out = self.cmd("m %04x %04x" % (addr, addr + n - 1))
        b = []
        for l in out.splitlines():
            m = re.match(r">C:[0-9a-f]{4}\s+((?:[0-9a-f]{2}\s+)+)", l)
            if m:
                b += [int(x, 16) for x in m.group(1).split()]
        return b[:n]

    def poke(self, addr, data):
        self.cmd("> %04x %s" % (addr, " ".join("%02x" % v for v in data)))

    def quit(self):
        try:
            self.s.sendall(b"quit\n")
        except OSError:
            pass
        try:
            self.p.wait(10)
        except subprocess.TimeoutExpired:
            self.p.kill()

def labels(path):
    return {l.split()[2][1:]: int(l.split()[1], 16) for l in open(path) if l.startswith("al ")}
