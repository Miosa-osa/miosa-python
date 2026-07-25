"""Desktop control mixin — screenshot, click, type, key, scroll, drag, etc."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..types import (
    ActionResponse,
    ClickRequest,
    CursorPosition,
    DesktopEnvironment,
    DoubleClickRequest,
    DragRequest,
    HotkeyRequest,
    KeyDownRequest,
    KeyRequest,
    KeyUpRequest,
    LaunchRequest,
    MouseButton,
    MouseDownRequest,
    MouseUpRequest,
    MoveCursorRequest,
    ScreenSize,
    ScrollDirection,
    ScrollRequest,
    TypeRequest,
    WaitRequest,
    WallpaperRequest,
    WindowFocusRequest,
    WindowInfo,
    WindowMoveRequest,
    WindowPosition,
    WindowResizeRequest,
    WindowSize,
)

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


class DesktopMixin:
    """Synchronous desktop control methods.

    Expects ``self._transport`` (``SyncTransport``) and
    ``self._computer_id`` (``str``) to be set by the owning class.
    """

    _transport: SyncTransport
    _computer_id: str

    def _desktop_path(self, action: str) -> str:
        return f"/computers/{self._computer_id}/desktop/{action}"

    def screenshot(self) -> bytes:
        """Capture a PNG screenshot of the desktop."""
        resp = self._transport.request(
            "GET", self._desktop_path("screenshot"), raw_response=True
        )
        if resp.status_code >= 400:
            from .._http import _parse_body
            from ..errors import _extract_request_id, raise_for_status
            body = _parse_body(resp)
            raise_for_status(resp.status_code, body, _extract_request_id(resp))
        return resp.content

    def screenshot_base64(self) -> str:
        """Capture a PNG screenshot encoded as a base64 string.

        Convenience for AI agents that pass screenshots to LLMs without
        writing to disk.
        """
        import base64
        return base64.b64encode(self.screenshot()).decode("ascii")

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
    ) -> ActionResponse:
        body = ClickRequest(x=x, y=y, button=MouseButton(button))
        data = self._transport.request(
            "POST", self._desktop_path("click"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def left_click(self, x: int, y: int) -> ActionResponse:
        """Explicit left-button click. Alias for :meth:`click(x, y)`."""
        return self.click(x, y, button="left")

    def right_click(self, x: int, y: int) -> ActionResponse:
        """Right-button click."""
        return self.click(x, y, button="right")

    def double_click(self, x: int, y: int) -> ActionResponse:
        body = DoubleClickRequest(x=x, y=y)
        data = self._transport.request(
            "POST", self._desktop_path("double-click"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def type(self, text: str, *, delay: Optional[int] = None) -> ActionResponse:
        body = TypeRequest(text=text, delay=delay)
        data = self._transport.request(
            "POST",
            self._desktop_path("type"),
            json_body=body.model_dump(exclude_none=True),
        )
        return ActionResponse.model_validate(data)

    def write(self, text: str, *, delay: Optional[int] = None) -> ActionResponse:
        """Alias for :meth:`type` used by simple computer-control loops."""
        return self.type(text, delay=delay)

    def key(self, key: str) -> ActionResponse:
        body = KeyRequest(key=key)
        data = self._transport.request(
            "POST", self._desktop_path("key"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def press(self, key: str) -> ActionResponse:
        """Alias for :meth:`key` used by simple computer-control loops."""
        return self.key(key)

    def hotkey(self, *keys: str) -> ActionResponse:
        """Press multiple keys simultaneously (e.g. ``hotkey("ctrl", "c")``).

        Keys are pressed together in the order given and released together.
        Common modifiers: ``"ctrl"``, ``"shift"``, ``"alt"``, ``"super"``.
        """
        body = HotkeyRequest(keys=list(keys))
        data = self._transport.request(
            "POST", self._desktop_path("hotkey"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def key_down(self, key: str) -> ActionResponse:
        """Press and hold a key without releasing it.

        Pair with :meth:`key_up` to release. Useful for modifier-held drag
        sequences or multi-step shortcuts.
        """
        body = KeyDownRequest(key=key)
        data = self._transport.request(
            "POST", self._desktop_path("key-down"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def key_up(self, key: str) -> ActionResponse:
        """Release a previously held key (see :meth:`key_down`)."""
        body = KeyUpRequest(key=key)
        data = self._transport.request(
            "POST", self._desktop_path("key-up"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def scroll(
        self,
        direction: str = "down",
        clicks: int = 3,
        *,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> ActionResponse:
        body = ScrollRequest(
            direction=ScrollDirection(direction), clicks=clicks, x=x, y=y
        )
        data = self._transport.request(
            "POST",
            self._desktop_path("scroll"),
            json_body=body.model_dump(exclude_none=True),
        )
        return ActionResponse.model_validate(data)

    def scroll_up(self, clicks: int = 3) -> ActionResponse:
        """Scroll up by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return self.scroll(direction="up", clicks=clicks)

    def scroll_down(self, clicks: int = 3) -> ActionResponse:
        """Scroll down by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return self.scroll(direction="down", clicks=clicks)

    def scroll_left(self, clicks: int = 3) -> ActionResponse:
        """Scroll left by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return self.scroll(direction="left", clicks=clicks)

    def scroll_right(self, clicks: int = 3) -> ActionResponse:
        """Scroll right by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return self.scroll(direction="right", clicks=clicks)

    def drag(
        self, from_x: int, from_y: int, to_x: int, to_y: int
    ) -> ActionResponse:
        body = DragRequest(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
        data = self._transport.request(
            "POST", self._desktop_path("drag"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def wait(self, seconds: float) -> ActionResponse:
        body = WaitRequest(seconds=seconds)
        data = self._transport.request(
            "POST", self._desktop_path("wait"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def cursor(self) -> CursorPosition:
        data = self._transport.request("GET", self._desktop_path("cursor"))
        return CursorPosition.model_validate(data)

    def get_cursor_position(self) -> CursorPosition:
        """Return the current cursor position. Alias for :meth:`cursor`."""
        return self.cursor()

    def cursor_position(self) -> CursorPosition:
        """Return the current cursor position. Alias for :meth:`cursor`."""
        return self.cursor()

    def get_screen_size(self) -> ScreenSize:
        """Return the screen resolution as ``{width, height}``."""
        data = self._transport.request("GET", self._desktop_path("screen-size"))
        return ScreenSize.model_validate(data)

    def screen_size(self) -> ScreenSize:
        """Return the screen resolution. Alias for :meth:`get_screen_size`."""
        return self.get_screen_size()

    def accessibility_tree(self) -> Dict[str, Any]:
        """Return the AT-SPI accessibility tree. Alias for :meth:`get_accessibility_tree`."""
        return self.get_accessibility_tree()

    def get_accessibility_tree(self) -> Dict[str, Any]:
        """Return the AT-SPI accessibility tree for the current desktop state.

        The tree is a nested JSON structure describing all visible UI elements —
        buttons, text fields, labels, their bounding boxes, roles, states, and
        parent/child relationships. AI agents use this for structured UI
        understanding without relying purely on vision.

        Returns the raw dict from envd. The exact schema depends on the envd
        version running inside the VM; callers should treat this as an opaque
        JSON object and inspect the ``role``, ``name``, ``bounds``, and
        ``children`` keys that AT-SPI exposes.
        """
        return self._transport.request("GET", self._desktop_path("accessibility-tree"))

    def windows(self) -> List[WindowInfo]:
        data = self._transport.request("GET", self._desktop_path("windows"))
        if isinstance(data, dict) and "data" in data:
            return [WindowInfo.model_validate(w) for w in data["data"]]
        if isinstance(data, list):
            return [WindowInfo.model_validate(w) for w in data]
        return []

    def focus_window(self, window_id: str) -> ActionResponse:
        body = WindowFocusRequest(window_id=window_id)
        data = self._transport.request(
            "POST",
            self._desktop_path("window/focus"),
            json_body=body.model_dump(),
        )
        return ActionResponse.model_validate(data)

    def launch(self, app_name: str) -> ActionResponse:
        body = LaunchRequest(app_name=app_name)
        data = self._transport.request(
            "POST", self._desktop_path("launch"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def get_desktop_environment(self) -> DesktopEnvironment:
        """Return information about the running desktop environment.

        Proxies to envd ``GET /desktop/environment`` and returns the name,
        resolution, and session type of the active desktop session.
        """
        data = self._transport.request("GET", self._desktop_path("environment"))
        return DesktopEnvironment.model_validate(data)

    def get_desktop_env(self) -> DesktopEnvironment:
        """Return desktop environment info. Short alias for :meth:`get_desktop_environment`."""
        return self.get_desktop_environment()

    def set_wallpaper(self, image_path_or_url: str) -> ActionResponse:
        """Set the desktop wallpaper to a local path or remote URL.

        Proxies to envd ``POST /desktop/wallpaper``.

        Args:
            image_path_or_url: Absolute path inside the VM (e.g.
                ``"/home/ubuntu/bg.png"``) or a ``https://`` URL that envd
                will fetch and apply.
        """
        body = WallpaperRequest(path=image_path_or_url)
        data = self._transport.request(
            "POST", self._desktop_path("wallpaper"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def get_clipboard(self) -> str:
        """Return the current clipboard text content."""
        data = self._transport.request("GET", self._desktop_path("clipboard"))
        if isinstance(data, dict):
            return data.get("text", "")
        return ""

    def clipboard_get(self) -> str:
        """Return clipboard text. Alias for :meth:`get_clipboard`."""
        return self.get_clipboard()

    def set_clipboard(self, text: str) -> ActionResponse:
        """Set the clipboard text content."""
        data = self._transport.request(
            "POST", self._desktop_path("clipboard"), json_body={"text": text}
        )
        return ActionResponse.model_validate(data)

    def clipboard_set(self, text: str) -> ActionResponse:
        """Set clipboard text. Alias for :meth:`set_clipboard`."""
        return self.set_clipboard(text)

    # ── Window management ──────────────────────────────────────────────────

    def get_window_size(self, window_id: str) -> WindowSize:
        """Return the width and height of the given window."""
        data = self._transport.request(
            "GET", self._desktop_path(f"window/{window_id}/size")
        )
        return WindowSize.model_validate(data)

    def get_window_position(self, window_id: str) -> WindowPosition:
        """Return the x/y screen position of the given window."""
        data = self._transport.request(
            "GET", self._desktop_path(f"window/{window_id}/position")
        )
        return WindowPosition.model_validate(data)

    def set_window_size(self, window_id: str, width: int, height: int) -> ActionResponse:
        """Resize the given window to *width* x *height* pixels."""
        body = WindowResizeRequest(width=width, height=height)
        data = self._transport.request(
            "POST",
            self._desktop_path(f"window/{window_id}/resize"),
            json_body=body.model_dump(),
        )
        return ActionResponse.model_validate(data)

    def set_window_position(self, window_id: str, x: int, y: int) -> ActionResponse:
        """Move the given window to screen coordinates (*x*, *y*)."""
        body = WindowMoveRequest(x=x, y=y)
        data = self._transport.request(
            "POST",
            self._desktop_path(f"window/{window_id}/move"),
            json_body=body.model_dump(),
        )
        return ActionResponse.model_validate(data)

    def maximize_window(self, window_id: str) -> ActionResponse:
        """Maximize the given window."""
        data = self._transport.request(
            "POST", self._desktop_path(f"window/{window_id}/maximize"), json_body={}
        )
        return ActionResponse.model_validate(data)

    def minimize_window(self, window_id: str) -> ActionResponse:
        """Minimize (iconify) the given window."""
        data = self._transport.request(
            "POST", self._desktop_path(f"window/{window_id}/minimize"), json_body={}
        )
        return ActionResponse.model_validate(data)

    def close_window(self, window_id: str) -> ActionResponse:
        """Close the given window."""
        data = self._transport.request(
            "POST", self._desktop_path(f"window/{window_id}/close"), json_body={}
        )
        return ActionResponse.model_validate(data)

    def move_cursor(self, x: int, y: int) -> ActionResponse:
        """Move the mouse cursor to (*x*, *y*) without clicking.

        Proxies to envd ``POST /desktop/move``.
        """
        body = MoveCursorRequest(x=x, y=y)
        data = self._transport.request(
            "POST", self._desktop_path("move"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def move_mouse(self, x: int, y: int) -> ActionResponse:
        """Alias for :meth:`move_cursor` used by simple computer-control loops."""
        return self.move_cursor(x, y)

    def mouse_down(self, x: int, y: int, button: str = "left") -> ActionResponse:
        """Press and hold a mouse button at (*x*, *y*).

        Use :meth:`mouse_up` to release. Together these enable custom drag
        sequences and long-press gestures.

        Proxies to envd ``POST /desktop/mouse-press``.

        Args:
            x: Horizontal screen coordinate (0-based pixels).
            y: Vertical screen coordinate (0-based pixels).
            button: ``"left"`` (default), ``"right"``, or ``"middle"``.
        """
        body = MouseDownRequest(x=x, y=y, button=MouseButton(button))
        data = self._transport.request(
            "POST", self._desktop_path("mouse-down"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    def mouse_up(self, x: int, y: int, button: str = "left") -> ActionResponse:
        """Release a held mouse button at (*x*, *y*).

        Complements :meth:`mouse_down` for custom drag and long-press sequences.

        Proxies to envd ``POST /desktop/mouse-release``.

        Args:
            x: Horizontal screen coordinate (0-based pixels).
            y: Vertical screen coordinate (0-based pixels).
            button: ``"left"`` (default), ``"right"``, or ``"middle"``.
        """
        body = MouseUpRequest(x=x, y=y, button=MouseButton(button))
        data = self._transport.request(
            "POST", self._desktop_path("mouse-up"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)


class AsyncDesktopMixin:
    """Asynchronous desktop control methods."""

    _transport: AsyncTransport
    _computer_id: str

    def _desktop_path(self, action: str) -> str:
        return f"/computers/{self._computer_id}/desktop/{action}"

    async def screenshot_base64(self) -> str:
        """Async base64-encoded PNG screenshot. See :meth:`DesktopMixin.screenshot_base64`."""
        import base64
        return base64.b64encode(await self.screenshot()).decode("ascii")

    async def left_click(self, x: int, y: int) -> ActionResponse:
        """Explicit left-button click. Alias for :meth:`click(x, y)`."""
        return await self.click(x, y, button="left")

    async def right_click(self, x: int, y: int) -> ActionResponse:
        """Right-button click."""
        return await self.click(x, y, button="right")

    async def screenshot(self) -> bytes:
        resp = await self._transport.request(
            "GET", self._desktop_path("screenshot"), raw_response=True
        )
        if resp.status_code >= 400:
            from .._http import _parse_body
            from ..errors import _extract_request_id, raise_for_status
            body = _parse_body(resp)
            raise_for_status(resp.status_code, body, _extract_request_id(resp))
        return resp.content

    async def click(
        self,
        x: int,
        y: int,
        button: str = "left",
    ) -> ActionResponse:
        body = ClickRequest(x=x, y=y, button=MouseButton(button))
        data = await self._transport.request(
            "POST", self._desktop_path("click"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def double_click(self, x: int, y: int) -> ActionResponse:
        body = DoubleClickRequest(x=x, y=y)
        data = await self._transport.request(
            "POST", self._desktop_path("double-click"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def type(self, text: str, *, delay: Optional[int] = None) -> ActionResponse:
        body = TypeRequest(text=text, delay=delay)
        data = await self._transport.request(
            "POST",
            self._desktop_path("type"),
            json_body=body.model_dump(exclude_none=True),
        )
        return ActionResponse.model_validate(data)

    async def write(self, text: str, *, delay: Optional[int] = None) -> ActionResponse:
        """Alias for :meth:`type` used by simple computer-control loops."""
        return await self.type(text, delay=delay)

    async def key(self, key: str) -> ActionResponse:
        body = KeyRequest(key=key)
        data = await self._transport.request(
            "POST", self._desktop_path("key"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def press(self, key: str) -> ActionResponse:
        """Alias for :meth:`key` used by simple computer-control loops."""
        return await self.key(key)

    async def hotkey(self, *keys: str) -> ActionResponse:
        """Press multiple keys simultaneously (e.g. ``hotkey("ctrl", "c")``).

        Keys are pressed together in the order given and released together.
        Common modifiers: ``"ctrl"``, ``"shift"``, ``"alt"``, ``"super"``.
        """
        body = HotkeyRequest(keys=list(keys))
        data = await self._transport.request(
            "POST", self._desktop_path("hotkey"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def key_down(self, key: str) -> ActionResponse:
        """Press and hold a key without releasing it.

        Pair with :meth:`key_up` to release. Useful for modifier-held drag
        sequences or multi-step shortcuts.
        """
        body = KeyDownRequest(key=key)
        data = await self._transport.request(
            "POST", self._desktop_path("key-down"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def key_up(self, key: str) -> ActionResponse:
        """Release a previously held key (see :meth:`key_down`)."""
        body = KeyUpRequest(key=key)
        data = await self._transport.request(
            "POST", self._desktop_path("key-up"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def scroll(
        self,
        direction: str = "down",
        clicks: int = 3,
        *,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> ActionResponse:
        body = ScrollRequest(
            direction=ScrollDirection(direction), clicks=clicks, x=x, y=y
        )
        data = await self._transport.request(
            "POST",
            self._desktop_path("scroll"),
            json_body=body.model_dump(exclude_none=True),
        )
        return ActionResponse.model_validate(data)

    async def scroll_up(self, clicks: int = 3) -> ActionResponse:
        """Scroll up by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return await self.scroll(direction="up", clicks=clicks)

    async def scroll_down(self, clicks: int = 3) -> ActionResponse:
        """Scroll down by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return await self.scroll(direction="down", clicks=clicks)

    async def scroll_left(self, clicks: int = 3) -> ActionResponse:
        """Scroll left by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return await self.scroll(direction="left", clicks=clicks)

    async def scroll_right(self, clicks: int = 3) -> ActionResponse:
        """Scroll right by *clicks* detents. Convenience wrapper for :meth:`scroll`."""
        return await self.scroll(direction="right", clicks=clicks)

    async def drag(
        self, from_x: int, from_y: int, to_x: int, to_y: int
    ) -> ActionResponse:
        body = DragRequest(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
        data = await self._transport.request(
            "POST", self._desktop_path("drag"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def wait(self, seconds: float) -> ActionResponse:
        body = WaitRequest(seconds=seconds)
        data = await self._transport.request(
            "POST", self._desktop_path("wait"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def cursor(self) -> CursorPosition:
        data = await self._transport.request("GET", self._desktop_path("cursor"))
        return CursorPosition.model_validate(data)

    async def get_cursor_position(self) -> CursorPosition:
        """Return the current cursor position. Async alias for :meth:`cursor`."""
        return await self.cursor()

    async def cursor_position(self) -> CursorPosition:
        """Return current cursor position. Async alias for :meth:`cursor`."""
        return await self.cursor()

    async def get_screen_size(self) -> ScreenSize:
        """Return the screen resolution as ``{width, height}``."""
        data = await self._transport.request("GET", self._desktop_path("screen-size"))
        return ScreenSize.model_validate(data)

    async def screen_size(self) -> ScreenSize:
        """Return screen resolution. Async alias for :meth:`get_screen_size`."""
        return await self.get_screen_size()

    async def accessibility_tree(self) -> Dict[str, Any]:
        """Return AT-SPI accessibility tree. Async alias for :meth:`get_accessibility_tree`."""
        return await self.get_accessibility_tree()

    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """Return the AT-SPI accessibility tree for the current desktop state.

        Async variant of :meth:`DesktopMixin.get_accessibility_tree`.
        """
        return await self._transport.request("GET", self._desktop_path("accessibility-tree"))

    async def windows(self) -> List[WindowInfo]:
        data = await self._transport.request("GET", self._desktop_path("windows"))
        if isinstance(data, dict) and "data" in data:
            return [WindowInfo.model_validate(w) for w in data["data"]]
        if isinstance(data, list):
            return [WindowInfo.model_validate(w) for w in data]
        return []

    async def focus_window(self, window_id: str) -> ActionResponse:
        body = WindowFocusRequest(window_id=window_id)
        data = await self._transport.request(
            "POST",
            self._desktop_path("window/focus"),
            json_body=body.model_dump(),
        )
        return ActionResponse.model_validate(data)

    async def launch(self, app_name: str) -> ActionResponse:
        body = LaunchRequest(app_name=app_name)
        data = await self._transport.request(
            "POST", self._desktop_path("launch"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def get_desktop_environment(self) -> DesktopEnvironment:
        """Return information about the running desktop environment.

        Proxies to envd ``GET /desktop/environment`` and returns the name,
        resolution, and session type of the active desktop session.
        """
        data = await self._transport.request("GET", self._desktop_path("environment"))
        return DesktopEnvironment.model_validate(data)

    async def get_desktop_env(self) -> DesktopEnvironment:
        """Return desktop env info. Short async alias for :meth:`get_desktop_environment`."""
        return await self.get_desktop_environment()

    async def set_wallpaper(self, image_path_or_url: str) -> ActionResponse:
        """Set the desktop wallpaper to a local path or remote URL.

        Proxies to envd ``POST /desktop/wallpaper``.

        Args:
            image_path_or_url: Absolute path inside the VM (e.g.
                ``"/home/ubuntu/bg.png"``) or a ``https://`` URL that envd
                will fetch and apply.
        """
        body = WallpaperRequest(path=image_path_or_url)
        data = await self._transport.request(
            "POST", self._desktop_path("wallpaper"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def get_clipboard(self) -> str:
        """Return the current clipboard text content."""
        data = await self._transport.request("GET", self._desktop_path("clipboard"))
        if isinstance(data, dict):
            return data.get("text", "")
        return ""

    async def clipboard_get(self) -> str:
        """Return clipboard text. Async alias for :meth:`get_clipboard`."""
        return await self.get_clipboard()

    async def set_clipboard(self, text: str) -> ActionResponse:
        """Set the clipboard text content."""
        data = await self._transport.request(
            "POST", self._desktop_path("clipboard"), json_body={"text": text}
        )
        return ActionResponse.model_validate(data)

    async def clipboard_set(self, text: str) -> ActionResponse:
        """Set clipboard text. Async alias for :meth:`set_clipboard`."""
        return await self.set_clipboard(text)

    # ── Window management ──────────────────────────────────────────────────

    async def get_window_size(self, window_id: str) -> WindowSize:
        """Return the width and height of the given window."""
        data = await self._transport.request(
            "GET", self._desktop_path(f"window/{window_id}/size")
        )
        return WindowSize.model_validate(data)

    async def get_window_position(self, window_id: str) -> WindowPosition:
        """Return the x/y screen position of the given window."""
        data = await self._transport.request(
            "GET", self._desktop_path(f"window/{window_id}/position")
        )
        return WindowPosition.model_validate(data)

    async def set_window_size(self, window_id: str, width: int, height: int) -> ActionResponse:
        """Resize the given window to *width* x *height* pixels."""
        body = WindowResizeRequest(width=width, height=height)
        data = await self._transport.request(
            "POST",
            self._desktop_path(f"window/{window_id}/resize"),
            json_body=body.model_dump(),
        )
        return ActionResponse.model_validate(data)

    async def set_window_position(self, window_id: str, x: int, y: int) -> ActionResponse:
        """Move the given window to screen coordinates (*x*, *y*)."""
        body = WindowMoveRequest(x=x, y=y)
        data = await self._transport.request(
            "POST",
            self._desktop_path(f"window/{window_id}/move"),
            json_body=body.model_dump(),
        )
        return ActionResponse.model_validate(data)

    async def maximize_window(self, window_id: str) -> ActionResponse:
        """Maximize the given window."""
        data = await self._transport.request(
            "POST", self._desktop_path(f"window/{window_id}/maximize"), json_body={}
        )
        return ActionResponse.model_validate(data)

    async def minimize_window(self, window_id: str) -> ActionResponse:
        """Minimize (iconify) the given window."""
        data = await self._transport.request(
            "POST", self._desktop_path(f"window/{window_id}/minimize"), json_body={}
        )
        return ActionResponse.model_validate(data)

    async def close_window(self, window_id: str) -> ActionResponse:
        """Close the given window."""
        data = await self._transport.request(
            "POST", self._desktop_path(f"window/{window_id}/close"), json_body={}
        )
        return ActionResponse.model_validate(data)

    async def move_cursor(self, x: int, y: int) -> ActionResponse:
        """Move the mouse cursor to (*x*, *y*) without clicking.

        Async variant of :meth:`DesktopMixin.move_cursor`.
        Proxies to envd ``POST /desktop/move``.
        """
        body = MoveCursorRequest(x=x, y=y)
        data = await self._transport.request(
            "POST", self._desktop_path("move"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def move_mouse(self, x: int, y: int) -> ActionResponse:
        """Alias for :meth:`move_cursor` used by simple computer-control loops."""
        return await self.move_cursor(x, y)

    async def mouse_down(self, x: int, y: int, button: str = "left") -> ActionResponse:
        """Press and hold a mouse button at (*x*, *y*).

        Async variant of :meth:`DesktopMixin.mouse_down`.
        Proxies to envd ``POST /desktop/mouse-press``.

        Args:
            x: Horizontal screen coordinate (0-based pixels).
            y: Vertical screen coordinate (0-based pixels).
            button: ``"left"`` (default), ``"right"``, or ``"middle"``.
        """
        body = MouseDownRequest(x=x, y=y, button=MouseButton(button))
        data = await self._transport.request(
            "POST", self._desktop_path("mouse-down"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)

    async def mouse_up(self, x: int, y: int, button: str = "left") -> ActionResponse:
        """Release a held mouse button at (*x*, *y*).

        Async variant of :meth:`DesktopMixin.mouse_up`.
        Proxies to envd ``POST /desktop/mouse-release``.

        Args:
            x: Horizontal screen coordinate (0-based pixels).
            y: Vertical screen coordinate (0-based pixels).
            button: ``"left"`` (default), ``"right"``, or ``"middle"``.
        """
        body = MouseUpRequest(x=x, y=y, button=MouseButton(button))
        data = await self._transport.request(
            "POST", self._desktop_path("mouse-up"), json_body=body.model_dump()
        )
        return ActionResponse.model_validate(data)
