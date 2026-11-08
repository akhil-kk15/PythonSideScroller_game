# Gamepad and joystick support across Linux, Windows, and macOS.
#
# Supports Xbox and generic controllers in both XInput and DirectInput modes:
# - "auto"        -> accepts both XInput and DirectInput (uses SDL2 GameController
#                    database when available, with automatic XInput / DirectInput
#                    fallback for unmapped controllers)
# - "xinput"      -> forces XInput SDL hints and standard Xbox XInput layout
# - "directinput" -> forces DirectInput SDL hints (on Windows) and DirectInput
#                    button/axis layouts (both Xbox DirectInput and 12-button HID)

import os
import sys
import pygame

try:
    from pygame._sdl2 import controller as sdl_controller
except Exception:
    sdl_controller = None

MODE_AUTO = "auto"
MODE_XINPUT = "xinput"
MODE_DIRECTINPUT = "directinput"
MODES = (MODE_AUTO, MODE_XINPUT, MODE_DIRECTINPUT)

MODE_LABELS = {
    MODE_AUTO: "Auto (XInput + DirectInput)",
    MODE_XINPUT: "XInput",
    MODE_DIRECTINPUT: "DirectInput",
}

MODE_BUTTON_LABELS = {
    MODE_AUTO: "Mode: Auto (Both)",
    MODE_XINPUT: "Mode: XInput",
    MODE_DIRECTINPUT: "Mode: DirectInput",
}

# Deadzones and thresholds.
# Vertical stick threshold is slightly higher than horizontal so natural thumb
# angle while running left/right does not accidentally grab ladders.
STICK_DEADZONE_X = 0.28
STICK_DEADZONE_Y = 0.48
MENU_STICK_THRESHOLD = 0.55
TRIGGER_THRESHOLD = 0.45
COMBINED_TRIGGER_THRESHOLD = 0.55

# Menu stick / D-pad hold repeat timing (in 60 FPS ticks).
MENU_REPEAT_DELAY = 22
MENU_REPEAT_INTERVAL = 8

_BUTTON_KEYS = (
    "south",
    "east",
    "west",
    "north",
    "lb",
    "rb",
    "rt",
    "back",
    "start",
)


def configure_sdl_hints(mode: str = MODE_AUTO) -> None:
    """Configure SDL2 joystick backend hints for Linux, Windows, and macOS."""
    if mode not in MODES:
        mode = MODE_AUTO

    # Do not process controller inputs while the game window is unfocused.
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "0"

    if mode in (MODE_AUTO, MODE_XINPUT):
        os.environ["SDL_XINPUT_ENABLED"] = "1"
        os.environ["SDL_JOYSTICK_HIDAPI"] = "1"
        os.environ["SDL_JOYSTICK_HIDAPI_XBOX"] = "1"
        os.environ["SDL_JOYSTICK_RAWINPUT"] = "1"
        os.environ["SDL_JOYSTICK_WGI"] = "1"
        os.environ["SDL_JOYSTICK_MFI"] = "1"
    elif mode == MODE_DIRECTINPUT:
        # On Windows, disabling XInput/RawInput/WGI/HIDAPI routes controllers
        # through DirectInput (dinput8). On Linux and macOS, keep OS drivers
        # active while disabling the Xbox HIDAPI override so DirectInput
        # mappings apply cleanly.
        os.environ["SDL_XINPUT_ENABLED"] = "0"
        os.environ["SDL_JOYSTICK_HIDAPI_XBOX"] = "0"
        if sys.platform == "win32":
            os.environ["SDL_JOYSTICK_RAWINPUT"] = "0"
            os.environ["SDL_JOYSTICK_WGI"] = "0"
            os.environ["SDL_JOYSTICK_HIDAPI"] = "0"
        else:
            os.environ["SDL_JOYSTICK_MFI"] = "1"


def _is_xbox_hardware(name: str, guid: str, num_axes: int, num_buttons: int) -> bool:
    """Return True if the device appears to be an Xbox-family controller."""
    lower = name.lower()
    if any(token in lower for token in ("xbox", "x-box", "xinput", "microsoft")):
        return True
    # SDL2 GUID encodes USB Vendor ID in little-endian at chars 8..12 (0x045e -> "5e04")
    # or ends with ASCII "xinput" ("78696e707574") / "rawinp" ("726177696e70").
    if len(guid) >= 12 and guid[8:12] == "5e04":
        return True
    if guid.endswith("78696e707574") or guid.endswith("726177696e70"):
        return True
    # Windows DirectInput exposes Xbox controllers with 5 axes (merged Z trigger) and 10 buttons.
    if num_axes == 5 and num_buttons == 10:
        return True
    return False


def _is_directinput_hardware(name: str, guid: str, num_axes: int, num_buttons: int) -> bool:
    """Return True if the device appears to be running in DirectInput / generic HID mode."""
    lower = name.lower()
    if any(
        token in lower
        for token in (
            "directinput",
            "dinput",
            "dual action",
            "rumblepad",
            "generic usb",
            "usb joystick",
            "twin usb",
        )
    ):
        return True
    if guid.endswith("78696e707574") or guid.endswith("726177696e70"):
        return False
    # Classic DirectInput gamepads expose 4 axes (2 sticks) + digital triggers on buttons 6/7,
    # or 5 axes + 10 buttons when an Xbox controller is opened via Windows DirectInput.
    if num_axes <= 4 and num_buttons >= 10:
        return True
    if num_axes == 5 and num_buttons == 10:
        return True
    return False


def _detect_protocol_and_profile(
    name: str,
    guid: str,
    num_axes: int,
    num_buttons: int,
    has_sdl_ctrl: bool,
    mode: str,
) -> tuple[str, str]:
    """Return ``(protocol_label, mapping_profile)`` for a connected joystick."""
    xbox_hw = _is_xbox_hardware(name, guid, num_axes, num_buttons)
    dinput_hw = _is_directinput_hardware(name, guid, num_axes, num_buttons)

    if dinput_hw and not guid.endswith("78696e707574"):
        detected_protocol = "DirectInput"
    elif xbox_hw or num_axes >= 6:
        detected_protocol = "XInput"
    else:
        detected_protocol = "DirectInput"

    if mode == MODE_XINPUT:
        return ("XInput", "xinput")

    if mode == MODE_DIRECTINPUT:
        if xbox_hw:
            return ("DirectInput", "xbox_directinput")
        return ("DirectInput", "directinput_hid")

    # MODE_AUTO: accept both XInput and DirectInput.
    if has_sdl_ctrl:
        return (detected_protocol, "sdl_controller")
    if detected_protocol == "XInput":
        return ("XInput", "xinput")
    if xbox_hw:
        return ("DirectInput", "xbox_directinput")
    return ("DirectInput", "directinput_hid")


def _safe_btn(joy, index: int) -> bool:
    try:
        if 0 <= index < joy.get_numbuttons():
            return bool(joy.get_button(index))
    except pygame.error:
        pass
    return False


def _safe_axis(joy, index: int) -> float:
    try:
        if 0 <= index < joy.get_numaxes():
            return float(joy.get_axis(index))
    except pygame.error:
        pass
    return 0.0


def _safe_hat(joy, index: int = 0) -> tuple[int, int]:
    try:
        if 0 <= index < joy.get_numhats():
            hx, hy = joy.get_hat(index)
            return int(hx), int(hy)
    except pygame.error:
        pass
    return (0, 0)


def _read_dpad_from_joystick(joy) -> tuple[bool, bool, bool, bool]:
    """Read `(up, down, left, right)` from hat 0, or macOS HID D-pad buttons 11..14."""
    try:
        num_hats = joy.get_numhats()
        num_buttons = joy.get_numbuttons()
    except pygame.error:
        return (False, False, False, False)

    if num_hats > 0:
        hx, hy = _safe_hat(joy, 0)
        # Note: in pygame.joystick hats, +1 is UP and -1 is DOWN.
        return (hy > 0, hy < 0, hx < 0, hx > 0)

    # Some macOS / Bluetooth HID drivers expose the D-pad as buttons 11..14 with 0 hats.
    if num_buttons >= 15:
        return (
            _safe_btn(joy, 11),
            _safe_btn(joy, 12),
            _safe_btn(joy, 13),
            _safe_btn(joy, 14),
        )
    return (False, False, False, False)


class Gamepad:
    """Polls connected XInput / DirectInput controllers and exposes clean game actions."""

    def __init__(self, mode: str = MODE_AUTO):
        self.mode = mode if mode in MODES else MODE_AUTO
        self.devices: dict[int, dict] = {}
        self._sdl_ctrl_ready = False

        # Continuous held state (used by Player.update).
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
        self.jump_held = False

        # One-frame edge-triggered actions (used by gameplay, menus, and story).
        self.jump = False
        self.attack = False
        self.pause = False
        self.restart = False
        self.confirm = False
        self.back = False
        self.nav_up = False
        self.nav_down = False

        self._prev_buttons = {key: False for key in _BUTTON_KEYS}
        self._prev_menu_up = False
        self._prev_menu_down = False
        self._repeat_timer = 0

        self._init_subsystems()
        self.scan_devices()

    def _init_subsystems(self) -> None:
        configure_sdl_hints(self.mode)
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
        except pygame.error:
            return

        self._sdl_ctrl_ready = False
        if sdl_controller is not None:
            try:
                if not sdl_controller.get_init():
                    sdl_controller.init()
                self._sdl_ctrl_ready = True
            except Exception:
                self._sdl_ctrl_ready = False

    def quit(self) -> None:
        """Release all opened controller and joystick handles."""
        for entry in list(self.devices.values()):
            ctrl = entry.get("controller")
            if ctrl is not None:
                try:
                    ctrl.quit()
                except Exception:
                    pass
            joy = entry.get("joystick")
            if joy is not None:
                try:
                    joy.quit()
                except Exception:
                    pass
        self.devices.clear()

        if sdl_controller is not None and self._sdl_ctrl_ready:
            try:
                sdl_controller.quit()
            except Exception:
                pass
            self._sdl_ctrl_ready = False

        try:
            if pygame.joystick.get_init():
                pygame.joystick.quit()
        except pygame.error:
            pass

    def set_mode(self, mode: str) -> None:
        """Switch between ``auto``, ``xinput``, and ``directinput`` at runtime."""
        if mode not in MODES:
            return
        self.mode = mode
        self.quit()
        self._reset_state()
        self._init_subsystems()
        self.scan_devices()

    def cycle_mode(self) -> str:
        """Advance to the next input mode and return its name."""
        next_index = (MODES.index(self.mode) + 1) % len(MODES)
        self.set_mode(MODES[next_index])
        return self.mode

    def _reset_state(self) -> None:
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
        self.jump_held = False
        self.jump = False
        self.attack = False
        self.pause = False
        self.restart = False
        self.confirm = False
        self.back = False
        self.nav_up = False
        self.nav_down = False
        for key in self._prev_buttons:
            self._prev_buttons[key] = False
        self._prev_menu_up = False
        self._prev_menu_down = False
        self._repeat_timer = 0

    def _open_device(self, device_index: int) -> None:
        try:
            joy = pygame.joystick.Joystick(device_index)
            if not joy.get_init():
                joy.init()
            instance_id = joy.get_instance_id()
            if instance_id in self.devices:
                return

            num_buttons = joy.get_numbuttons()
            num_axes = joy.get_numaxes()
            # Ignore non-gamepad pseudo-joysticks such as laptop accelerometers (0 buttons).
            if num_buttons < 4:
                return

            name = (joy.get_name() or "Controller").strip()
            try:
                guid = (joy.get_guid() or "").lower()
            except Exception:
                guid = ""
        except pygame.error:
            return

        ctrl = None
        if self._sdl_ctrl_ready and sdl_controller is not None:
            try:
                if sdl_controller.is_controller(device_index):
                    ctrl = sdl_controller.Controller(device_index)
                    if not ctrl.get_init():
                        ctrl.init()
            except Exception:
                ctrl = None

        protocol, profile = _detect_protocol_and_profile(
            name=name,
            guid=guid,
            num_axes=num_axes,
            num_buttons=num_buttons,
            has_sdl_ctrl=ctrl is not None,
            mode=self.mode,
        )

        self.devices[instance_id] = {
            "instance_id": instance_id,
            "joystick": joy,
            "controller": ctrl,
            "name": name,
            "guid": guid,
            "protocol": protocol,
            "profile": profile,
        }

    def scan_devices(self) -> None:
        """Open any currently connected gamepads."""
        try:
            if not pygame.joystick.get_init():
                return
            count = pygame.joystick.get_count()
        except pygame.error:
            return

        for idx in range(count):
            self._open_device(idx)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle hot-plug events. Returns True if device list changed."""
        if event.type == pygame.JOYDEVICEADDED:
            before = set(self.devices.keys())
            device_index = getattr(event, "device_index", None)
            if device_index is not None:
                self._open_device(device_index)
            else:
                self.scan_devices()
            return set(self.devices.keys()) != before

        if event.type == pygame.JOYDEVICEREMOVED:
            instance_id = getattr(event, "instance_id", getattr(event, "joy", None))
            entry = self.devices.pop(instance_id, None)
            if entry is not None:
                ctrl = entry.get("controller")
                if ctrl is not None:
                    try:
                        ctrl.quit()
                    except Exception:
                        pass
                joy = entry.get("joystick")
                if joy is not None:
                    try:
                        joy.quit()
                    except Exception:
                        pass
                if not self.devices:
                    self._reset_state()
                return True
        return False

    def is_connected(self) -> bool:
        return len(self.devices) > 0

    def status_line(self) -> str:
        """Short controller status line for the Controls menu."""
        if not self.devices:
            return "Gamepad: Not connected (plug in anytime)"
        first = next(iter(self.devices.values()))
        name = first["name"]
        if len(name) > 28:
            name = name[:25].rstrip() + "..."
        extra = f" (+{len(self.devices) - 1})" if len(self.devices) > 1 else ""
        return f"Gamepad: {name}{extra} [{first['protocol']}]"

    def mode_line(self) -> str:
        """Descriptive line showing the active XInput / DirectInput setting."""
        return f"Input API: {MODE_LABELS[self.mode]}"

    def mode_button_text(self) -> str:
        """Short label that fits inside a menu button."""
        return MODE_BUTTON_LABELS[self.mode]

    def _read_single_device(self, entry: dict) -> dict:
        profile = entry["profile"]
        joy = entry["joystick"]
        ctrl = entry["controller"]

        if profile == "sdl_controller" and ctrl is not None:
            try:
                stick_x = ctrl.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32768.0
                stick_y = ctrl.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32768.0
                rt_val = ctrl.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) / 32767.0
                dpad_up = bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_DPAD_UP))
                dpad_down = bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_DPAD_DOWN))
                dpad_left = bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_DPAD_LEFT))
                dpad_right = bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_DPAD_RIGHT))
                return {
                    "stick_x": stick_x,
                    "stick_y": stick_y,
                    "dpad_up": dpad_up,
                    "dpad_down": dpad_down,
                    "dpad_left": dpad_left,
                    "dpad_right": dpad_right,
                    "south": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_A)),
                    "east": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_B)),
                    "west": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_X)),
                    "north": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_Y)),
                    "lb": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_LEFTSHOULDER)),
                    "rb": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER)),
                    "rt": rt_val > TRIGGER_THRESHOLD,
                    "back": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_BACK)),
                    "start": bool(ctrl.get_button(pygame.CONTROLLER_BUTTON_START)),
                }
            except Exception:
                # Fall through to raw joystick profile if SDL controller read fails.
                profile = "xinput" if entry["protocol"] == "XInput" else "directinput_hid"

        stick_x = _safe_axis(joy, 0)
        stick_y = _safe_axis(joy, 1)
        dpad_up, dpad_down, dpad_left, dpad_right = _read_dpad_from_joystick(joy)

        try:
            num_axes = joy.get_numaxes()
            num_buttons = joy.get_numbuttons()
        except pygame.error:
            num_axes = 0
            num_buttons = 0

        if profile == "xinput":
            # Standard Xbox XInput layout across Windows, Linux (xpad), and macOS:
            # A=0, B=1, X=2, Y=3, LB=4, RB=5, Back=6, Start=7; Right Trigger on axis 5.
            rt_pressed = (_safe_axis(joy, 5) > TRIGGER_THRESHOLD) if num_axes >= 6 else _safe_btn(joy, 7)
            return {
                "stick_x": stick_x,
                "stick_y": stick_y,
                "dpad_up": dpad_up,
                "dpad_down": dpad_down,
                "dpad_left": dpad_left,
                "dpad_right": dpad_right,
                "south": _safe_btn(joy, 0),
                "east": _safe_btn(joy, 1),
                "west": _safe_btn(joy, 2),
                "north": _safe_btn(joy, 3),
                "lb": _safe_btn(joy, 4),
                "rb": _safe_btn(joy, 5),
                "rt": rt_pressed,
                "back": _safe_btn(joy, 6),
                "start": _safe_btn(joy, 7),
            }

        if profile == "xbox_directinput":
            # Xbox controller via DirectInput:
            # A=0, B=1, X=2, Y=3, LB=4, RB=5, Back=6, Start=7.
            # On Windows DirectInput (5 axes), axis 2 is a combined Z trigger (< -0.55 = RT).
            if num_axes == 5:
                rt_pressed = _safe_axis(joy, 2) < -COMBINED_TRIGGER_THRESHOLD
            elif num_axes >= 6:
                rt_pressed = _safe_axis(joy, 5) > TRIGGER_THRESHOLD
            else:
                rt_pressed = False
            return {
                "stick_x": stick_x,
                "stick_y": stick_y,
                "dpad_up": dpad_up,
                "dpad_down": dpad_down,
                "dpad_left": dpad_left,
                "dpad_right": dpad_right,
                "south": _safe_btn(joy, 0),
                "east": _safe_btn(joy, 1),
                "west": _safe_btn(joy, 2),
                "north": _safe_btn(joy, 3),
                "lb": _safe_btn(joy, 4),
                "rb": _safe_btn(joy, 5),
                "rt": rt_pressed,
                "back": _safe_btn(joy, 6),
                "start": _safe_btn(joy, 7),
            }

        # Standard 12-button DirectInput HID layout (e.g. Logitech F310/F710 in D-mode,
        # 8BitDo D-Input, generic USB/Bluetooth HID pads on Windows, Linux, and macOS):
        # 0=West(X), 1=South(A), 2=East(B), 3=North(Y), 4=LB, 5=RB, 6=LT, 7=RT, 8=Back, 9=Start.
        back_idx = 8 if num_buttons >= 10 else 6
        start_idx = 9 if num_buttons >= 10 else 7
        rt_pressed = _safe_btn(joy, 7) if num_buttons >= 10 else False
        return {
            "stick_x": stick_x,
            "stick_y": stick_y,
            "dpad_up": dpad_up,
            "dpad_down": dpad_down,
            "dpad_left": dpad_left,
            "dpad_right": dpad_right,
            "south": _safe_btn(joy, 1),
            "east": _safe_btn(joy, 2),
            "west": _safe_btn(joy, 0),
            "north": _safe_btn(joy, 3),
            "lb": _safe_btn(joy, 4),
            "rb": _safe_btn(joy, 5),
            "rt": rt_pressed,
            "back": _safe_btn(joy, back_idx),
            "start": _safe_btn(joy, start_idx),
        }

    def update(self) -> None:
        """Poll connected controllers once per frame and compute edge-triggered actions."""
        if not self.devices:
            self._reset_state()
            return

        move_left = False
        move_right = False
        move_up = False
        move_down = False
        menu_up_now = False
        menu_down_now = False
        buttons_now = {key: False for key in _BUTTON_KEYS}

        for entry in list(self.devices.values()):
            state = self._read_single_device(entry)
            sx = state["stick_x"]
            sy = state["stick_y"]

            if sx < -STICK_DEADZONE_X or state["dpad_left"]:
                move_left = True
            if sx > STICK_DEADZONE_X or state["dpad_right"]:
                move_right = True
            if sy < -STICK_DEADZONE_Y or state["dpad_up"]:
                move_up = True
            if sy > STICK_DEADZONE_Y or state["dpad_down"]:
                move_down = True

            if sy < -MENU_STICK_THRESHOLD or state["dpad_up"]:
                menu_up_now = True
            if sy > MENU_STICK_THRESHOLD or state["dpad_down"]:
                menu_down_now = True

            for key in _BUTTON_KEYS:
                if state[key]:
                    buttons_now[key] = True

        self.move_left = move_left
        self.move_right = move_right
        self.move_up = move_up
        self.move_down = move_down
        self.jump_held = buttons_now["south"] or buttons_now["lb"]

        just_pressed = {
            key: buttons_now[key] and not self._prev_buttons[key]
            for key in _BUTTON_KEYS
        }

        self.jump = just_pressed["south"] or just_pressed["lb"]
        self.attack = (
            just_pressed["west"]
            or just_pressed["east"]
            or just_pressed["north"]
            or just_pressed["rb"]
            or just_pressed["rt"]
        )
        self.pause = just_pressed["start"]
        self.restart = just_pressed["back"]
        self.confirm = just_pressed["south"]
        self.back = just_pressed["east"]

        # Menu up/down navigation with comfortable hold-to-repeat.
        self.nav_up = False
        self.nav_down = False
        if menu_up_now and not menu_down_now:
            if not self._prev_menu_up:
                self.nav_up = True
                self._repeat_timer = MENU_REPEAT_DELAY
            else:
                self._repeat_timer -= 1
                if self._repeat_timer <= 0:
                    self.nav_up = True
                    self._repeat_timer = MENU_REPEAT_INTERVAL
        elif menu_down_now and not menu_up_now:
            if not self._prev_menu_down:
                self.nav_down = True
                self._repeat_timer = MENU_REPEAT_DELAY
            else:
                self._repeat_timer -= 1
                if self._repeat_timer <= 0:
                    self.nav_down = True
                    self._repeat_timer = MENU_REPEAT_INTERVAL
        else:
            self._repeat_timer = 0

        self._prev_buttons = buttons_now
        self._prev_menu_up = menu_up_now
        self._prev_menu_down = menu_down_now
