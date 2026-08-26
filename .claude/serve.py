import http.server, pathlib

OUT = pathlib.Path("/private/tmp/claude-501/-Users-fynnj-Documents-Claude-Projects-AutoTuneTrend/575f1a33-aca3-4984-bd4e-3506022d2004/scratchpad")

class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        name = pathlib.Path(self.path).name or "out.bin"
        data = self.rfile.read(int(self.headers["Content-Length"]))
        (OUT / name).write_bytes(data)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

http.server.ThreadingHTTPServer(("127.0.0.1", 8321), H).serve_forever()
