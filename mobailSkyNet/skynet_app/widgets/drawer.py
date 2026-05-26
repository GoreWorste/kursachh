from kivy.app import App
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.modalview import ModalView

from skynet_app.theme import APP_GAP, APP_PADDING, DRAWER_WIDTH, ROLE_LABELS, TEXT_MUTED
from skynet_app.widgets.common import CaptionLabel, Card, DangerButton, GhostButton, SectionTitle, SecondaryButton, SubSectionTitle


class DrawerView(ModalView):
    def __init__(self, **kwargs):
        kwargs.setdefault("auto_dismiss", True)
        kwargs.setdefault("background", "")
        kwargs.setdefault("background_color", [0, 0, 0, 0.35])
        super().__init__(**kwargs)

        app = App.get_running_app()
        user = app.repository.get_current_user()

        anchor = AnchorLayout(anchor_x="left", anchor_y="top")
        panel = Card(tone="default", size_hint=(None, 1), width=DRAWER_WIDTH, spacing=APP_GAP, padding=[APP_PADDING, dp(24), APP_PADDING, dp(24)])
        anchor.add_widget(panel)
        self.add_widget(anchor)

        panel.add_widget(SectionTitle(text="SkyNet"))
        panel.add_widget(CaptionLabel(text=f"Роль: {ROLE_LABELS.get(user['role_code'], user['role_name'])}"))
        panel.add_widget(CaptionLabel(text="Автономная Android-версия сайта", color=TEXT_MUTED))
        panel.add_widget(SubSectionTitle(text="Навигация"))

        for item in self._build_items(user):
            button = SecondaryButton(text=item["label"])
            button.bind(on_release=lambda *_args, name=item["screen"]: self._go(name))
            panel.add_widget(button)

        if user["is_authenticated"]:
            logout_button = DangerButton(text="Выйти")
            logout_button.bind(on_release=lambda *_: self._logout())
            panel.add_widget(logout_button)
        else:
            auth_button = GhostButton(text="Войти или зарегистрироваться")
            auth_button.bind(on_release=lambda *_: self._go("auth"))
            panel.add_widget(auth_button)

    def _build_items(self, user):
        items = [{"label": "Главная", "screen": "home"}, {"label": "База знаний", "screen": "knowledge"}]
        if user["is_authenticated"]:
            items.extend(
                [
                    {"label": "Кабинет", "screen": "auth"},
                    {"label": "Профиль", "screen": "profile"},
                    {"label": "Заявки", "screen": "tickets"},
                ]
            )
        else:
            items.append({"label": "Вход", "screen": "auth"})
            items.append({"label": "Регистрация", "screen": "register"})
        if user["is_operator"] or user["is_admin"]:
            items.extend(
                [
                    {"label": "Панель", "screen": "admin"},
                    {"label": "Отчёты", "screen": "reports"},
                ]
            )
        if user["is_admin"]:
            items.extend(
                [
                    {"label": "Пользователи", "screen": "users"},
                    {"label": "Журнал", "screen": "logs"},
                ]
            )
        return items

    def _go(self, screen_name):
        App.get_running_app().switch_screen(screen_name)
        self.dismiss()

    def _logout(self):
        app = App.get_running_app()
        app.repository.logout()
        app.refresh_all_screens()
        app.switch_screen("home")
        self.dismiss()
