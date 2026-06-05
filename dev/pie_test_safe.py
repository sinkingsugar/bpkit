import sys; sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import pie
print("is_in_pie:", pie.is_in_pie())
print("dialogs_suppressed (before):", pie.dialogs_suppressed())
prior = pie.suppress_dialogs(True)
print("set True; prior was:", prior, "| now reads:", pie.dialogs_suppressed())
pie.suppress_dialogs(prior)
print("restored to:", pie.dialogs_suppressed())
les = pie._les()
print("begin_play resolves:", hasattr(les, "editor_request_begin_play"),
      "| end_play resolves:", hasattr(les, "editor_request_end_play"))
