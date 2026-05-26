from pathlib import Path

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import FadeTransition, ScreenManager
from kivy.utils import platform

try:
    from kivymd.app import MDApp as AppBase
except ImportError:
    from kivy.app import App as AppBase

from skynet_app.config import load_app_config
from skynet_app.data import LocalRepository
from skynet_app.screens.helpdesk import (
    AdminScreen,
    ArticleScreen,
    KnowledgeScreen,
    LogsScreen,
    ProfileScreen,
    ReportsScreen,
    TicketDetailScreen,
    TicketsScreen,
    UsersScreen,
)
from skynet_app.screens.public import AuthScreen, HomeScreen, PasswordScreen, RegisterScreen
from skynet_app.theme import BACKGROUND, PRIMARY, TEXT
from skynet_app.widgets.drawer import DrawerView


class SkyNetApp(AppBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        projectRoot = Path(__file__).resolve().parent.parent
        self.configData = load_app_config(projectRoot)
        self.repository = LocalRepository(projectRoot / "storage" / "skynet_mobile.db", self.configData)
        self.selected_ticket_id = None
        self.selected_article_id = None
        self.selected_user_id = None
        self.last_reset_code = ""
        self.last_reset_email = ""
        self._drawer = None

    def build(self):
        self.title = "SkyNet Mobile"
        Clock.max_iteration = 200
        Builder.load_file(str(Path(__file__).resolve().parent.parent / "kv" / "skynet.kv"))
        if hasattr(self, "theme_cls"):
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.theme_style = "Light"
        if platform not in ("android", "ios"):
            Window.size = (430, 860)
        Window.clearcolor = BACKGROUND

        self.screen_manager = ScreenManager(transition=FadeTransition())
        for screen in (
            HomeScreen(name="home"),
            AuthScreen(name="auth"),
            RegisterScreen(name="register"),
            PasswordScreen(name="password"),
            ProfileScreen(name="profile"),
            TicketsScreen(name="tickets"),
            TicketDetailScreen(name="ticket_detail"),
            KnowledgeScreen(name="knowledge"),
            ArticleScreen(name="article"),
            AdminScreen(name="admin"),
            ReportsScreen(name="reports"),
            UsersScreen(name="users"),
            LogsScreen(name="logs"),
        ):
            self.screen_manager.add_widget(screen)
        self.refresh_screen("home", force=True)
        return self.screen_manager

    def switch_screen(self, name):
        self.screen_manager.current = name
        self.refresh_screen(name)

    def mark_screen_dirty(self, name):
        screen = self.screen_manager.get_screen(name)
        if hasattr(screen, "mark_dirty"):
            screen.mark_dirty()

    def refresh_screen(self, name, force=False):
        screen = self.screen_manager.get_screen(name)
        if hasattr(screen, "refresh") and (force or getattr(screen, "is_dirty", True)):
            screen.refresh()

    def refresh_current_screen(self, force=False):
        self.refresh_screen(self.screen_manager.current, force=force)

    def refresh_all_screens(self):
        for screen in self.screen_manager.screens:
            if hasattr(screen, "mark_dirty"):
                screen.mark_dirty()
        self.refresh_current_screen(force=True)
        self._drawer = None

    def open_ticket(self, ticket_id):
        self.selected_ticket_id = ticket_id
        self.mark_screen_dirty("ticket_detail")
        self.switch_screen("ticket_detail")

    def open_article(self, article_id):
        self.selected_article_id = article_id
        self.mark_screen_dirty("article")
        self.switch_screen("article")

    def open_user(self, user_id):
        self.selected_user_id = user_id
        self.mark_screen_dirty("users")
        self.switch_screen("users")

    def open_knowledge_category(self, category_code):
        knowledge_screen = self.screen_manager.get_screen("knowledge")
        knowledge_screen.current_category = category_code
        self.mark_screen_dirty("knowledge")
        self.switch_screen("knowledge")

    def open_drawer(self):
        self._drawer = DrawerView()
        self._drawer.open()

    def show_message(self, title, message):
        content = BoxLayout(orientation="vertical", padding=24, spacing=16)
        body = Label(text=message, color=TEXT, halign="left", valign="middle")
        body.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        content.add_widget(body)
        popup = Popup(title=title, content=content, size_hint=(0.86, None), height=240, separator_color=PRIMARY)
        popup.open()
