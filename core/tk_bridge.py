from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class DialogState:
    dialog_queue: List[Any]
    confirm_queue: List[bool]


_state: contextvars.ContextVar[Optional[DialogState]] = contextvars.ContextVar("tk_bridge_state", default=None)


def set_state(dialog_queue: List[Any], confirm_queue: Optional[List[bool]] = None) -> None:
    confirm_queue = confirm_queue or []
    _state.set(DialogState(dialog_queue=dialog_queue, confirm_queue=confirm_queue))


def _next_dialog_item(default: Any = "") -> Any:
    state = _state.get()
    if not state or not state.dialog_queue:
        return default
    return state.dialog_queue.pop(0)


def _next_confirm(default: bool = False) -> bool:
    state = _state.get()
    if not state or not state.confirm_queue:
        return default
    return state.confirm_queue.pop(0)


def patch_tkinter() -> None:
    import tkinter.filedialog as filedialog
    from tkinter import messagebox

    def askopenfilename(*_args, **_kwargs):
        item = _next_dialog_item()
        if isinstance(item, list):
            return str(item[0]) if item else ""
        return str(item) if item else ""

    def askopenfilenames(*_args, **_kwargs):
        item = _next_dialog_item([])
        if isinstance(item, list):
            return item
        return [str(item)] if item else []

    def askdirectory(*_args, **_kwargs):
        item = _next_dialog_item()
        return str(item) if item else ""

    def showinfo(_title, message, **_kwargs):
        print(message)
        return "ok"

    def showwarning(_title, message, **_kwargs):
        print(message)
        return "ok"

    def showerror(_title, message, **_kwargs):
        print(message)
        raise ValueError(message)

    def askyesno(_title, _message, **_kwargs):
        return _next_confirm(False)

    filedialog.askopenfilename = askopenfilename
    filedialog.askopenfilenames = askopenfilenames
    filedialog.askdirectory = askdirectory
    messagebox.showinfo = showinfo
    messagebox.showwarning = showwarning
    messagebox.showerror = showerror
    messagebox.askyesno = askyesno
