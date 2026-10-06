from __future__ import annotations

from nicegui import ui

from gotify2apprise.config.manager import ConfigError
from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.layout import page_frame, require_auth

SMTP_SNIPPET = """
  - id: smtp-local
    type: smtp
    enabled: true
    tags: [mail]
    options:
      host: 0.0.0.0
      port: 2525
      default_priority: 5
""".strip(
    "\n"
)


@ui.page("/config")
async def config_page() -> None:
    if not require_auth():
        return
    page_frame("Config")
    bridge = get_runtime().bridge
    current = ""
    if bridge.config_manager.path.exists():
        current = bridge.config_manager.path.read_text(encoding="utf-8")
    elif bridge.config is not None:
        current = bridge.config_manager.dumps(bridge.config)

    ui.label("YAML is the source of truth. Validate, save, then reload listeners.").classes(
        "q-px-md q-pt-md text-grey"
    )
    editor = ui.textarea(value=current).classes("w-full q-px-md").props("outlined rows=28")
    status = ui.label("").classes("q-px-md")

    async def validate() -> None:
        try:
            bridge.config_manager.validate_text(editor.value or "")
        except ConfigError as exc:
            status.set_text(str(exc))
            status.classes(replace="q-px-md text-negative")
            return
        status.set_text("Valid")
        status.classes(replace="q-px-md text-positive")

    async def save() -> None:
        try:
            await bridge.save_and_reload(editor.value or "")
        except Exception as exc:
            status.set_text(str(exc))
            status.classes(replace="q-px-md text-negative")
            return
        status.set_text("Saved and reloaded")
        status.classes(replace="q-px-md text-positive")

    async def reload_only() -> None:
        try:
            await bridge.reload()
        except Exception as exc:
            status.set_text(str(exc))
            status.classes(replace="q-px-md text-negative")
            return
        if bridge.config_manager.path.exists():
            editor.value = bridge.config_manager.path.read_text(encoding="utf-8")
        status.set_text("Reloaded from disk")
        status.classes(replace="q-px-md text-positive")

    def insert_smtp() -> None:
        text = editor.value or ""
        if "type: smtp" in text:
            ui.notify("An SMTP listener is already in the YAML")
            return
        needle = "listeners:"
        if needle in text:
            editor.value = text.replace(needle, needle + "\n" + SMTP_SNIPPET, 1)
        else:
            editor.value = text + "\nlisteners:\n" + SMTP_SNIPPET + "\n"
        ui.notify("SMTP listener snippet inserted — save to apply")

    with ui.row().classes("q-pa-md gap-2"):
        ui.button("Validate", on_click=validate)
        ui.button("Save & reload", on_click=save).props("unelevated")
        ui.button("Reload from disk", on_click=reload_only).props("flat")
        ui.button("Insert SMTP listener", on_click=insert_smtp).props("flat")
