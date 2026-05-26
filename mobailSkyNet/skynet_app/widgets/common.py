from kivy.app import App
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from skynet_app.theme import (
    APP_GAP,
    APP_GAP_LG,
    APP_PADDING,
    APP_PADDING_SM,
    BACKGROUND,
    BUTTON_HEIGHT,
    BUTTON_RADIUS,
    CARD_RADIUS,
    DANGER,
    HEADER_HEIGHT,
    INPUT_HINT,
    INPUT_TEXT,
    INPUT_HEIGHT,
    INPUT_RADIUS,
    OUTLINE,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    ROLE_LABELS,
    STATUS_COLORS,
    SURFACE,
    SURFACE_ALT,
    SURFACE_SOFT,
    TEXT,
    TEXT_MUTED,
)


class WrapLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(width=self._update_text_size, texture_size=self._update_height)
        self._update_text_size()

    def _update_text_size(self, *_):
        self.text_size = (self.width, None)

    def _update_height(self, *_):
        self.height = max(self.texture_size[1] + dp(4), dp(22))


class SectionTitle(WrapLabel):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", sp(20))
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)


class SubSectionTitle(WrapLabel):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", sp(16))
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)


class CaptionLabel(WrapLabel):
    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", sp(13))
        kwargs.setdefault("color", TEXT_MUTED)
        super().__init__(**kwargs)

class NumberBadge(Label):
    bg_color = ListProperty(PRIMARY)
    text_color = ListProperty(SURFACE)

    def __init__(self, text="", **kwargs):
        kwargs.setdefault("text", text)
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(34), dp(34)))
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("color", SURFACE)
        super().__init__(**kwargs)
        self.bind(size=self._sync_text_size)
        self._sync_text_size()

    def _sync_text_size(self, *_):
        self.text_size = self.size


class Card(BoxLayout):
    bg_color = ListProperty(SURFACE)
    border_color = ListProperty(OUTLINE)
    radius = ListProperty(CARD_RADIUS)
    tone = StringProperty("default")
    elevation = NumericProperty(1)
    shadow_color = ListProperty([0, 0, 0, 0.06])

    def __init__(self, **kwargs):
        tone = kwargs.pop("tone", "default")
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", APP_GAP)
        kwargs.setdefault("padding", APP_PADDING)
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.tone = tone
        self.bind(minimum_height=self.setter("height"))
        self.bind(tone=self._sync_tone)
        self._sync_tone()

    def _sync_tone(self, *_):
        palettes = {
            "default": (SURFACE, OUTLINE),
            "soft": (SURFACE_ALT, OUTLINE),
            "primary": (SURFACE_SOFT, PRIMARY_LIGHT),
            "danger": ([1, 0.96, 0.96, 1], [0.96, 0.84, 0.84, 1]),
        }
        self.bg_color, self.border_color = palettes.get(self.tone, palettes["default"])
        self.elevation = 0 if self.tone == "primary" else 1


class AppButton(Button):
    bg_color = ListProperty(PRIMARY)
    text_color = ListProperty(SURFACE)
    border_color = ListProperty(PRIMARY)
    radius = NumericProperty(BUTTON_RADIUS)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", BUTTON_HEIGHT)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("color", kwargs.get("text_color", SURFACE))
        kwargs.setdefault("font_size", sp(14))
        super().__init__(**kwargs)


class SecondaryButton(AppButton):
    def __init__(self, **kwargs):
        kwargs.setdefault("bg_color", SURFACE_ALT)
        kwargs.setdefault("text_color", TEXT)
        kwargs.setdefault("border_color", OUTLINE)
        kwargs.setdefault("color", TEXT)
        super().__init__(**kwargs)


class GhostButton(AppButton):
    def __init__(self, **kwargs):
        kwargs.setdefault("bg_color", PRIMARY_LIGHT)
        kwargs.setdefault("text_color", PRIMARY)
        kwargs.setdefault("border_color", PRIMARY_LIGHT)
        kwargs.setdefault("color", PRIMARY)
        super().__init__(**kwargs)


class DangerButton(AppButton):
    def __init__(self, **kwargs):
        kwargs.setdefault("bg_color", DANGER)
        kwargs.setdefault("text_color", SURFACE)
        kwargs.setdefault("border_color", DANGER)
        kwargs.setdefault("color", SURFACE)
        super().__init__(**kwargs)


class AppInput(TextInput):
    border_color = ListProperty(OUTLINE)
    background_color_inactive = ListProperty(SURFACE)
    background_color_active = ListProperty(SURFACE)
    radius = NumericProperty(INPUT_RADIUS)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", INPUT_HEIGHT)
        kwargs.setdefault("padding", [dp(16), dp(12), dp(16), dp(12)])
        kwargs.setdefault("font_size", sp(17))
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_color", [0, 0, 0, 0])
        kwargs.setdefault("foreground_color", [0, 0, 0, 1])
        kwargs.setdefault("disabled_foreground_color", [0.45, 0.45, 0.45, 1])
        kwargs.setdefault("cursor_color", PRIMARY)
        kwargs.setdefault("hint_text_color", [0.25, 0.25, 0.25, 0.95])
        kwargs.setdefault("selection_color", [PRIMARY[0], PRIMARY[1], PRIMARY[2], 0.3])
        super().__init__(**kwargs)


class PasswordField(BoxLayout):
    """Поле пароля с кнопкой показать/скрыть."""

    def __init__(self, hint_text="Пароль", text="", **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("spacing", dp(10))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", BUTTON_HEIGHT)
        super().__init__(**kwargs)

        self.input = AppInput(password=True, hint_text=hint_text, text=text, radius=INPUT_RADIUS)
        self.input.size_hint = (1, None)
        self.input.height = self.height

        self.toggle = GhostButton(text="Показать", size_hint=(None, None), size=(dp(100), self.height), radius=BUTTON_RADIUS)
        self.toggle.bind(on_release=lambda *_: self._toggle())

        self.add_widget(self.input)
        self.add_widget(self.toggle)

    def _toggle(self):
        self.input.password = not self.input.password
        self.toggle.text = "Показать" if self.input.password else "Скрыть"


class AppTextArea(AppInput):
    def __init__(self, **kwargs):
        kwargs.setdefault("multiline", True)
        kwargs.setdefault("height", dp(140))
        kwargs.setdefault("font_size", sp(16))
        kwargs.setdefault("radius", dp(16))
        super().__init__(**kwargs)


class AppSpinner(Spinner):
    border_color = ListProperty(OUTLINE)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", INPUT_HEIGHT)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_color", SURFACE)
        kwargs.setdefault("color", INPUT_TEXT)
        kwargs.setdefault("sync_height", True)
        super().__init__(**kwargs)


class FormRow(BoxLayout):
    def __init__(self, label_text, widget, hint_text="", **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", dp(4))
        kwargs.setdefault("padding", [0, 0, 0, dp(8)])
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.add_widget(CaptionLabel(text=label_text, color=TEXT, size_hint_y=None, height=dp(20)))
        self.add_widget(widget)
        if hint_text:
            self.add_widget(CaptionLabel(text=hint_text, color=TEXT_MUTED, size_hint_y=None, height=dp(18)))


class StatusBadge(Label):
    bg_color = ListProperty(PRIMARY)
    text_color = ListProperty(SURFACE)
    status_code = StringProperty("new")

    def __init__(self, status_code="new", **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("height", dp(28))
        kwargs.setdefault("padding", [dp(12), dp(6)])
        kwargs.setdefault("font_size", sp(12))
        kwargs.setdefault("color", SURFACE)
        super().__init__(**kwargs)
        self.status_code = status_code
        self.bind(status_code=self._sync_colors, texture_size=self._sync_size)
        self._sync_colors()
        self._sync_size()

    def _sync_colors(self, *_):
        text_color, bg_color = STATUS_COLORS.get(self.status_code, (SURFACE, PRIMARY))
        self.text_color = text_color
        self.bg_color = bg_color
        self.color = text_color

    def _sync_size(self, *_):
        self.width = max(self.texture_size[0] + dp(24), dp(96))


class ClickableCard(ButtonBehavior, Card):
    pass


class HeaderBar(BoxLayout):
    def __init__(self, title, show_menu=True, right_action=None, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("spacing", dp(12))
        kwargs.setdefault("padding", [APP_PADDING, dp(14), APP_PADDING, dp(14)])
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", HEADER_HEIGHT)
        super().__init__(**kwargs)

        if show_menu:
            menu_button = AppButton(
                text="☰",
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                bg_color=PRIMARY_DARK,
                border_color=PRIMARY_DARK,
                text_color=SURFACE,
            )
            menu_button.bind(on_release=lambda *_: App.get_running_app().open_drawer())
            self.add_widget(menu_button)
        else:
            self.add_widget(AnchorLayout(size_hint=(None, 1), width=dp(42)))

        title_box = BoxLayout(orientation="vertical", spacing=dp(2))
        self.title_label = WrapLabel(text=title, bold=True, font_size=sp(18), color=SURFACE)
        self.subtitle_label = CaptionLabel(text="", color=[1, 1, 1, 0.88])
        title_box.add_widget(self.title_label)
        title_box.add_widget(self.subtitle_label)
        self.add_widget(title_box)

        if right_action:
            action_button = SecondaryButton(text=right_action["text"], size_hint=(None, None), size=(dp(120), dp(42)))
            action_button.bind(on_release=lambda *_: right_action["callback"]())
            self.add_widget(action_button)
        else:
            self.add_widget(AnchorLayout(size_hint=(None, 1), width=dp(42)))
        self.set_context(title)

    def set_context(self, title):
        user = App.get_running_app().repository.get_current_user()
        self.title_label.text = title
        self.subtitle_label.text = f"Интернет-поддержка • {ROLE_LABELS.get(user['role_code'], user['role_name'])}"


class ScreenBody(ScrollView):
    def __init__(self, **kwargs):
        kwargs.setdefault("do_scroll_x", False)
        kwargs.setdefault("bar_width", dp(4))
        kwargs.setdefault("bar_color", PRIMARY_LIGHT)
        kwargs.setdefault("bar_inactive_color", [PRIMARY_LIGHT[0], PRIMARY_LIGHT[1], PRIMARY_LIGHT[2], 0.35])
        super().__init__(**kwargs)
        self.layout = BoxLayout(
            orientation="vertical",
            spacing=APP_GAP,
            padding=[APP_PADDING, APP_PADDING, APP_PADDING, APP_GAP_LG],
            size_hint_y=None,
        )
        self.layout.bind(minimum_height=self.layout.setter("height"))
        self.add_widget(self.layout)


def make_stat_line(label, value):
    line = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(28))
    left = Label(
        text=label,
        color=TEXT_MUTED,
        font_size=sp(13),
        halign="left",
        valign="middle",
    )
    right = Label(
        text=value,
        color=TEXT,
        font_size=sp(13),
        halign="right",
        valign="middle",
    )
    left.bind(size=lambda instance, value_size: setattr(instance, "text_size", value_size))
    right.bind(size=lambda instance, value_size: setattr(instance, "text_size", value_size))
    line.add_widget(left)
    line.add_widget(right)
    return line


def make_chip(text, on_release, active=False):
    widget_class = AppButton if active else SecondaryButton
    chip = widget_class(
        text=text,
        size_hint=(None, None),
        height=dp(36),
        width=max(dp(118), dp(28) + len(text) * dp(7)),
    )
    chip.bind(on_release=lambda *_: on_release())
    return chip


def make_chip_fill(text, on_release, active=False):
    chip = make_chip(text, on_release, active=active)
    chip.size_hint = (1, None)
    chip.width = 0
    chip.height = dp(40)
    return chip


def make_section(title, subtitle=""):
    box = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
    box.bind(minimum_height=box.setter("height"))
    box.add_widget(SectionTitle(text=title))
    if subtitle:
        box.add_widget(CaptionLabel(text=subtitle))
    return box


def make_info_card(title, subtitle="", button_text="", callback=None):
    card = Card(tone="soft", padding=[APP_PADDING, APP_PADDING_SM, APP_PADDING, APP_PADDING_SM])
    card.add_widget(SubSectionTitle(text=title))
    if subtitle:
        card.add_widget(WrapLabel(text=subtitle))
    if button_text and callback:
        button = GhostButton(text=button_text)
        button.bind(on_release=lambda *_: callback())
        card.add_widget(button)
    return card


def make_button_row(*buttons):
    row = BoxLayout(orientation="horizontal", spacing=APP_GAP, size_hint_y=None, height=BUTTON_HEIGHT)
    for button in buttons:
        button.size_hint = (1, None)
        button.height = BUTTON_HEIGHT
        row.add_widget(button)
    return row


def make_metric_card(value, label, tone="soft"):
    card = Card(tone=tone, padding=[APP_PADDING_SM, APP_PADDING_SM, APP_PADDING_SM, APP_PADDING_SM], spacing=dp(4))
    card.add_widget(SectionTitle(text=value, halign="center"))
    card.add_widget(CaptionLabel(text=label, halign="center"))
    return card


def make_stat_grid(items, cols=2):
    grid = GridLayout(cols=cols, spacing=APP_GAP, size_hint_y=None)
    grid.bind(minimum_height=grid.setter("height"))
    for value, label, *extra in items:
        tone = extra[0] if extra else "soft"
        grid.add_widget(make_metric_card(value, label, tone=tone))
    return grid


def make_list_card(title, rows, tone="default"):
    card = Card(tone=tone)
    card.add_widget(SubSectionTitle(text=title))
    for label, value in rows:
        card.add_widget(make_stat_line(label, value))
    return card
