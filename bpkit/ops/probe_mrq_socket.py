"""Live-fire: can a MoviePipeline executor instance receive TCP data at the
reflected layer (the same layer BP binds)?  Creates a MoviePipelinePythonHostExecutor,
binds socket_message_recieved_delegate to a python callable that appends to
_mrq_recv_log.txt in the repo root, connects to the local probe server, sends one
message.  Refs stashed in builtins so nothing is GC'd between ue_run calls."""
import unreal, builtins, os

# ue_run ships source as a string -- no __file__; hardcode the repo-root log path
LOG = r"C:\Users\sugar\devel\conan\_mrq_recv_log.txt"

state = getattr(builtins, "_mrq_probe", None)
if state is None:
    ex = unreal.new_object(unreal.MoviePipelinePythonHostExecutor)
    hits = []

    def on_msg(message):
        hits.append(message)
        with open(LOG, "a", encoding="utf8") as f:
            f.write("RECV: %r\n" % message)

    ex.socket_message_recieved_delegate.add_callable(on_msg)
    state = {"ex": ex, "on_msg": on_msg, "hits": hits}
    builtins._mrq_probe = state
    print("executor created + delegate bound:", ex)
    ok = ex.connect_socket("127.0.0.1", 9777)
    print("connect_socket ->", ok)
    if ok:
        sent = ex.send_socket_message("hello-mrq")
        print("send_socket_message ->", sent)
else:
    ex = state["ex"]
    print("existing executor:", ex)
    print("is_socket_connected:", ex.is_socket_connected())
    print("hits so far:", state["hits"])
    # manual pump attempt in case recv only polls during render frames
    for _ in range(5):
        ex.on_begin_frame()
    print("pumped on_begin_frame x5; hits now:", state["hits"])
