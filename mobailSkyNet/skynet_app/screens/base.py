from kivy.uix.boxlayout import BoxLayout

try:
    from kivymd.uix.screen import MDScreen as ScreenBase
except ImportError:
    from kivy.uix.screenmanager import Screen as ScreenBase

from skynet_app.widgets.common import HeaderBar, ScreenBody


class BaseScreen(ScreenBase):
    title = ""
    show_menu = True
    right_action = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_dirty = True
        root = BoxLayout(orientation="vertical")
        self.header = HeaderBar(title=self.title, show_menu=self.show_menu, right_action=self.right_action)
        self.body = ScreenBody()
        root.add_widget(self.header)
        root.add_widget(self.body)
        self.add_widget(root)

    def clear_body(self):
        self.body.layout.clear_widgets()

    def mark_dirty(self):
        self.is_dirty = True

    def refresh(self):
        self.header.set_context(self.title)
        self.clear_body()
        self.is_dirty = False

    def on_pre_enter(self, *_):
        if self.is_dirty:
            self.refresh()
