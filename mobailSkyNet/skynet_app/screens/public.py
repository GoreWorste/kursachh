from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox

from skynet_app.screens.base import BaseScreen
from skynet_app.widgets.common import (
    AppButton,
    AppInput,
    AppSpinner,
    AppTextArea,
    CaptionLabel,
    Card,
    DangerButton,
    FormRow,
    GhostButton,
    NumberBadge,
    PasswordField,
    SectionTitle,
    SubSectionTitle,
    WrapLabel,
    make_button_row,
    make_info_card,
    make_stat_line,
    make_stat_grid,
)
from skynet_app.theme import TEXT


class HomeScreen(BaseScreen):
    title = "SkyNet"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        repo = app.repository
        user = repo.get_current_user()
        categories = repo.get_categories()

        if user["is_authenticated"]:
            self._build_private_home(user)
            return

        intro = Card(tone="primary")
        intro.add_widget(SectionTitle(text="Поддержка SkyNet"))
        intro.add_widget(WrapLabel(text="Оставьте обращение в пару шагов. Экран собран под телефон: короткие блоки, ровные поля и понятный маршрут до отправки заявки."))
        steps_row = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        steps_row.bind(minimum_height=steps_row.setter("height"))
        for num, title in (
            ("1", "Контактные данные"),
            ("2", "Описание проблемы"),
            ("3", "Вложения и отправка"),
        ):
            step_card = Card(tone="soft", padding=dp(12), spacing=dp(6))
            step_header = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(34))
            step_header.add_widget(NumberBadge(text=num))
            step_header.add_widget(CaptionLabel(text=title, color=TEXT))
            step_card.add_widget(step_header)
            steps_row.add_widget(step_card)
        intro.add_widget(steps_row)
        self.body.layout.add_widget(intro)

        form_card = Card()
        form_card.add_widget(SectionTitle(text="Форма обращения"))
        form_card.add_widget(CaptionLabel(text="Все поля сгруппированы так, чтобы форма читалась сверху вниз без визуального шума."))
        self.full_name_input = AppInput(hint_text="Как к вам обращаться")
        self.email_input = AppInput(hint_text="example@mail.ru")
        self.organization_input = AppInput(hint_text="Организация или тариф")
        self.title_input = AppInput(hint_text="Не получается войти в личный кабинет")
        self.category_map = {category["name"]: category["id"] for category in categories}
        self.category_spinner = AppSpinner(text="Выберите категорию", values=[category["name"] for category in categories])
        self.priority_spinner = AppSpinner(text="Средний", values=["Низкий", "Средний", "Высокий"])
        self.description_input = AppTextArea(hint_text="Опишите проблему, укажите время, сообщения об ошибке и что уже пробовали сделать.")
        contact_block = Card(tone="soft", padding=dp(12), spacing=dp(6))
        contact_block.add_widget(SubSectionTitle(text="Контактные данные"))
        contact_block.add_widget(FormRow("Имя", self.full_name_input))
        contact_block.add_widget(FormRow("Email", self.email_input))
        contact_block.add_widget(FormRow("Организация", self.organization_input, "Необязательное поле"))
        form_card.add_widget(contact_block)
        params_block = Card(tone="soft", padding=dp(12), spacing=dp(6))
        params_block.add_widget(SubSectionTitle(text="Параметры заявки"))
        params_block.add_widget(FormRow("Тема заявки", self.title_input))
        params_block.add_widget(FormRow("Категория", self.category_spinner))
        params_block.add_widget(FormRow("Приоритет", self.priority_spinner))
        form_card.add_widget(params_block)
        description_block = Card(tone="soft", padding=dp(12), spacing=dp(6))
        description_block.add_widget(SubSectionTitle(text="Описание"))
        description_block.add_widget(FormRow("Описание проблемы", self.description_input))
        form_card.add_widget(description_block)
        attach_block = Card(tone="soft", padding=dp(12), spacing=dp(6))
        attach_block.add_widget(SubSectionTitle(text="Вложения"))
        self.attachment_name_input = AppInput(hint_text="Например: screenshot.png")
        attach_block.add_widget(FormRow("Имя файла", self.attachment_name_input, "Для офлайн-версии укажите имя вложения вручную"))
        form_card.add_widget(attach_block)

        consent_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(36))
        self.consent = CheckBox(size_hint=(None, None), size=(dp(24), dp(24)))
        consent_row.add_widget(self.consent)
        consent_row.add_widget(CaptionLabel(text="Согласен на обработку персональных данных и правила обращения в поддержку.", color=TEXT))
        form_card.add_widget(consent_row)
        submit_button = AppButton(text="Отправить заявку")
        submit_button.bind(on_release=lambda *_: self.submit_ticket())
        form_card.add_widget(submit_button)
        self.body.layout.add_widget(form_card)

        tips_card = Card(tone="soft")
        tips_card.add_widget(SectionTitle(text="Чем быстрее вам помогут"))
        for text in (
            "Укажите номер договора или логин, если применимо.",
            "Приложите скриншоты ошибок или опишите их текстом.",
            "Укажите время возникновения проблемы.",
        ):
            tips_card.add_widget(CaptionLabel(text=f"• {text}"))
        tips_card.add_widget(SubSectionTitle(text="Статусы заявки"))
        for title, desc in (
            ("Новая", "Заявка зарегистрирована."),
            ("В работе", "Оператор занимается вашей проблемой."),
            ("Решена", "Предложено решение."),
            ("Закрыта", "Заявка завершена."),
        ):
            tips_card.add_widget(CaptionLabel(text=f"{title} — {desc}"))
        self.body.layout.add_widget(tips_card)

        steps_card = Card()
        steps_card.add_widget(SectionTitle(text="Как это работает"))
        for num, title, desc in (
            ("1", "Создайте заявку", "Заполните форму выше или войдите в систему и создайте заявку в разделе «Мои заявки»."),
            ("2", "Оператор ответит", "Специалист назначит исполнителя и при необходимости оставит комментарий."),
            ("3", "Отследите заявку", "В карточке обращения можно следить за статусом и историей общения."),
        ):
            block = Card(tone="soft", padding=dp(12), spacing=dp(6))
            header = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(32))
            header.add_widget(NumberBadge(text=num, size=(dp(32), dp(32))))
            header.add_widget(CaptionLabel(text=title, color=TEXT))
            block.add_widget(header)
            block.add_widget(CaptionLabel(text=desc))
            steps_card.add_widget(block)
        self.body.layout.add_widget(steps_card)

        categories_card = Card()
        categories_card.add_widget(SectionTitle(text="Категории обращений"))
        categories_card.add_widget(CaptionLabel(text="Выберите категорию — откроется база знаний с материалами по теме."))
        for category in categories:
            button = GhostButton(text=category["name"])
            button.bind(on_release=lambda *_args, code=category["code"]: app.open_knowledge_category(code))
            categories_card.add_widget(button)
        self.body.layout.add_widget(categories_card)

    def _build_private_home(self, user):
        app = App.get_running_app()
        stats = app.repository.get_client_dashboard_stats()
        hero = Card(tone="primary")
        hero.add_widget(SectionTitle(text=f"Здравствуйте, {user['full_name']}"))
        hero.add_widget(CaptionLabel(text=f"Роль: {user['role_name']}"))
        hero.add_widget(WrapLabel(text="Личный кабинет повторяет структуру клиентского дашборда сайта: быстрый переход к заявкам, базе знаний и настройкам профиля."))
        self.body.layout.add_widget(hero)

        self.body.layout.add_widget(
            make_stat_grid(
                [
                    (str(stats["tickets"]), "Всего заявок", "soft"),
                    (str(stats["active"]), "Активные", "soft"),
                    (str(stats["articles"]), "Статей", "soft"),
                    (user["role_name"], "Текущая роль", "primary"),
                ]
            )
        )

        actions_card = Card()
        actions_card.add_widget(SubSectionTitle(text="Быстрые разделы"))
        cards = [
            ("Мои заявки", "Создание новой заявки, просмотр статусов и переписка с поддержкой.", "tickets"),
            ("База знаний", "Инструкции, ответы и рекомендации по типовым вопросам.", "knowledge"),
            ("Профиль", "Личные данные, пароль и локальные настройки аккаунта.", "profile"),
        ]
        if user["is_operator"] or user["is_admin"]:
            cards.append(("Панель управления", "Отчёты, пользователи, заявки и системный журнал.", "admin"))
        for title, subtitle, screen in cards:
            card = make_info_card(title, subtitle, "Открыть", callback=lambda name=screen: app.switch_screen(name))
            actions_card.add_widget(card)
        self.body.layout.add_widget(actions_card)

        help_card = Card()
        help_card.add_widget(SubSectionTitle(text="Что доступно в мобильной версии"))
        for text in (
            "Создание и редактирование заявок с теми же ролями доступа, что и на сайте.",
            "Просмотр и наполнение базы знаний прямо внутри приложения.",
            "Локальная работа без сервера: данные сохраняются в базе приложения.",
        ):
            help_card.add_widget(CaptionLabel(text=f"• {text}"))
        self.body.layout.add_widget(help_card)

    def submit_ticket(self):
        app = App.get_running_app()
        category_name = self.category_spinner.text.strip()
        if not self.full_name_input.text.strip() or not self.email_input.text.strip() or not self.title_input.text.strip() or not self.description_input.text.strip():
            app.show_message("Проверьте форму", "Заполните имя, email, тему и описание проблемы.")
            return
        if category_name not in self.category_map:
            app.show_message("Проверьте форму", "Выберите категорию заявки.")
            return
        if not self.consent.active:
            app.show_message("Проверьте форму", "Подтвердите согласие на обработку данных.")
            return
        priority_map = {"Низкий": "low", "Средний": "medium", "Высокий": "high"}
        ticket = app.repository.create_ticket(
            {
                "full_name": self.full_name_input.text,
                "email": self.email_input.text,
                "organization": self.organization_input.text,
                "title": self.title_input.text,
                "description": self.description_input.text,
                "category_id": self.category_map[category_name],
                "priority": priority_map.get(self.priority_spinner.text, "medium"),
            }
        )
        app.selected_ticket_id = ticket["id"]
        app.refresh_all_screens()
        app.show_message("Заявка создана", f"Обращение №{ticket['id']} добавлено в локальную систему.")
        app.switch_screen("ticket_detail")


class AuthScreen(BaseScreen):
    title = "Личный кабинет"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()
        if not user["is_authenticated"]:
            self._build_login()
            return

        hero = Card(tone="primary")
        hero.add_widget(SectionTitle(text=user["full_name"]))
        hero.add_widget(CaptionLabel(text=f"Роль: {user['role_name']}"))
        hero.add_widget(CaptionLabel(text=f"Логин: {user['login']}"))
        hero.add_widget(CaptionLabel(text=f"Email: {user['email']}"))
        if user["organization"]:
            hero.add_widget(CaptionLabel(text=f"Организация: {user['organization']}"))
        if user.get("avatar_path"):
            hero.add_widget(CaptionLabel(text=f"Аватар: {user['avatar_path']}"))
        self.body.layout.add_widget(hero)

        profile_card = Card(tone="soft")
        profile_card.add_widget(SubSectionTitle(text="Мой профиль"))
        profile_card.add_widget(CaptionLabel(text="Перейдите в профиль, чтобы изменить логин, email, ФИО и организацию."))
        profile_button = AppButton(text="Открыть профиль")
        profile_button.bind(on_release=lambda *_: app.switch_screen("profile"))
        profile_card.add_widget(profile_button)
        password_button = GhostButton(text="Сменить пароль")
        password_button.bind(on_release=lambda *_: app.switch_screen("password"))
        profile_card.add_widget(password_button)
        self.body.layout.add_widget(profile_card)

        nav = Card()
        nav.add_widget(SubSectionTitle(text="Разделы"))
        for label, subtitle, callback in [
            ("Мои заявки", "Создание и просмотр заявок", lambda: app.switch_screen("tickets")),
            ("База знаний", "Ответы на частые вопросы", lambda: app.switch_screen("knowledge")),
        ]:
            item = make_info_card(label, subtitle, "Открыть", callback=callback)
            nav.add_widget(item)
        if user["is_operator"] or user["is_admin"]:
            item = make_info_card("Отчёты", "Статистика и экспорт", "Открыть", callback=lambda: app.switch_screen("reports"))
            nav.add_widget(item)
        if user["is_admin"]:
            nav.add_widget(make_info_card("Пользователи", "Управление учётными записями", "Открыть", callback=lambda: app.switch_screen("users")))
            nav.add_widget(make_info_card("Журнал", "История изменений", "Открыть", callback=lambda: app.switch_screen("logs")))
        logout_button = DangerButton(text="Выйти")
        logout_button.bind(on_release=lambda *_: self.logout())
        nav.add_widget(logout_button)
        self.body.layout.add_widget(nav)

    def _build_login(self):
        app = App.get_running_app()
        hero = Card(tone="primary")
        hero.add_widget(SectionTitle(text="Личный кабинет"))
        hero.add_widget(WrapLabel(text="Войдите, чтобы управлять заявками и настройками. Экран повторяет кабинет сайта, но собран в вертикальную телефонную компоновку."))
        self.login_input = AppInput(hint_text="Логин или email")
        self.password_field = PasswordField(hint_text="Пароль")
        hero.add_widget(FormRow("Логин", self.login_input))
        hero.add_widget(FormRow("Пароль", self.password_field))
        login_button = AppButton(text="Войти")
        login_button.bind(on_release=lambda *_: self.login())
        register_button = GhostButton(text="Регистрация")
        register_button.bind(on_release=lambda *_: app.switch_screen("register"))
        forgot_button = GhostButton(text="Забыли пароль?")
        forgot_button.bind(on_release=lambda *_: app.switch_screen("password"))
        hero.add_widget(login_button)
        hero.add_widget(make_button_row(register_button, forgot_button))
        hero.add_widget(CaptionLabel(text="Демо-учётные записи: admin/admin123, operator/operator123, ivan.petrov/client123"))
        self.body.layout.add_widget(hero)

        quick_help = Card(tone="soft")
        quick_help.add_widget(SubSectionTitle(text="После входа будет доступно"))
        for text in (
            "Просмотр и создание заявок.",
            "Статусы, комментарии и вложения.",
            "База знаний, профиль и восстановление доступа.",
        ):
            quick_help.add_widget(CaptionLabel(text=f"• {text}"))
        self.body.layout.add_widget(quick_help)

    def login(self):
        app = App.get_running_app()
        try:
            user = app.repository.login(self.login_input.text, self.password_field.input.text)
        except ValueError as error:
            app.show_message("Ошибка входа", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Вход выполнен", f"Здравствуйте, {user['full_name']}.")
        if user["is_admin"] or user["is_operator"]:
            app.switch_screen("admin")
        else:
            app.switch_screen("home")

    def logout(self):
        app = App.get_running_app()
        app.repository.logout()
        app.refresh_all_screens()
        app.switch_screen("home")


class RegisterScreen(BaseScreen):
    title = "Регистрация"

    def refresh(self):
        super().refresh()
        card = Card(tone="primary")
        card.add_widget(SectionTitle(text="Регистрация"))
        card.add_widget(CaptionLabel(text="Создайте локальный клиентский аккаунт для работы с заявками и базой знаний."))
        self.login_input = AppInput(hint_text="Логин")
        self.email_input = AppInput(hint_text="Email")
        self.full_name_input = AppInput(hint_text="ФИО")
        self.organization_input = AppInput(hint_text="Организация или тариф")
        self.password_field = PasswordField(hint_text="Пароль")
        self.password_repeat_field = PasswordField(hint_text="Повторите пароль")
        card.add_widget(FormRow("Логин", self.login_input))
        card.add_widget(FormRow("Email", self.email_input))
        card.add_widget(FormRow("ФИО", self.full_name_input))
        card.add_widget(FormRow("Организация", self.organization_input))
        card.add_widget(FormRow("Пароль", self.password_field))
        card.add_widget(CaptionLabel(text="Требования: минимум 8 символов, 1 цифра и 1 спецсимвол.", color=TEXT))
        card.add_widget(FormRow("Повтор пароля", self.password_repeat_field))
        create_button = AppButton(text="Зарегистрироваться")
        create_button.bind(on_release=lambda *_: self.register())
        back_button = GhostButton(text="У меня уже есть аккаунт")
        back_button.bind(on_release=lambda *_: App.get_running_app().switch_screen("auth"))
        card.add_widget(create_button)
        card.add_widget(back_button)
        self.body.layout.add_widget(card)

    def register(self):
        app = App.get_running_app()
        if self.password_field.input.text != self.password_repeat_field.input.text:
            app.show_message("Ошибка регистрации", "Пароли не совпадают.")
            return
        try:
            user = app.repository.register_user(
                self.login_input.text,
                self.email_input.text,
                self.full_name_input.text,
                self.password_field.input.text,
                self.organization_input.text,
            )
        except ValueError as error:
            app.show_message("Ошибка регистрации", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Регистрация завершена", f"Аккаунт {user['login']} создан.")
        app.switch_screen("home")


class PasswordScreen(BaseScreen):
    title = "Пароль"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()

        if user["is_authenticated"]:
            change_card = Card(tone="primary")
            change_card.add_widget(SectionTitle(text="Смена пароля"))
            change_card.add_widget(CaptionLabel(text="Форма повторяет страницу смены пароля из кабинета."))
            self.old_password_field = PasswordField(hint_text="Старый пароль")
            self.new_password_field = PasswordField(hint_text="Новый пароль")
            self.new_password_repeat_field = PasswordField(hint_text="Повторите новый пароль")
            change_card.add_widget(FormRow("Старый пароль", self.old_password_field))
            change_card.add_widget(FormRow("Новый пароль", self.new_password_field))
            change_card.add_widget(FormRow("Повтор", self.new_password_repeat_field))
            button = AppButton(text="Сменить пароль")
            button.bind(on_release=lambda *_: self.change_password())
            change_card.add_widget(button)
            self.body.layout.add_widget(change_card)
            return

        request_card = Card(tone="primary")
        request_card.add_widget(SectionTitle(text="Восстановление доступа"))
        request_card.add_widget(WrapLabel(text="Схема повторяет веб-версию: укажите email, получите код и затем задайте новый пароль."))
        self.reset_identity_input = AppInput(text=app.last_reset_email, hint_text="Email")
        request_card.add_widget(FormRow("Email", self.reset_identity_input))
        request_button = AppButton(text="Получить код восстановления")
        request_button.bind(on_release=lambda *_: self.request_reset_code())
        request_card.add_widget(request_button)
        self.body.layout.add_widget(request_card)

        reset_card = Card(tone="soft")
        reset_card.add_widget(SubSectionTitle(text="Сбросить пароль"))
        self.reset_email_input = AppInput(text=app.last_reset_email, hint_text="Email")
        self.reset_code_input = AppInput(hint_text="Код восстановления")
        self.reset_password_field = PasswordField(hint_text="Новый пароль")
        self.reset_password_confirm_field = PasswordField(hint_text="Повторите новый пароль")
        reset_card.add_widget(FormRow("Email", self.reset_email_input))
        reset_card.add_widget(FormRow("Код", self.reset_code_input))
        reset_card.add_widget(FormRow("Новый пароль", self.reset_password_field, "Минимум 8 символов, цифра и спецсимвол"))
        reset_card.add_widget(FormRow("Повтор пароля", self.reset_password_confirm_field))
        reset_button = AppButton(text="Сбросить пароль")
        reset_button.bind(on_release=lambda *_: self.reset_password())
        reset_card.add_widget(reset_button)
        self.body.layout.add_widget(reset_card)

    def request_reset_code(self):
        app = App.get_running_app()
        try:
            result = app.repository.request_password_reset(self.reset_identity_input.text)
        except ValueError as error:
            app.show_message("Ошибка восстановления", str(error))
            return
        app.last_reset_code = result["code"]
        app.last_reset_email = result["email"]
        if result["sent_to_email"]:
            app.show_message("Код отправлен", f"Письмо отправлено на {result['email']}. Код действует до {result['expires_at']}.")
            return
        app.show_message(
            "Код создан",
            f"SMTP не настроен, поэтому код показан локально: {result['code']}. Действует до {result['expires_at']}.",
        )

    def reset_password(self):
        app = App.get_running_app()
        try:
            app.repository.reset_password(
                self.reset_email_input.text,
                self.reset_code_input.text,
                self.reset_password_field.input.text,
                self.reset_password_confirm_field.input.text,
            )
        except ValueError as error:
            app.show_message("Ошибка сброса", str(error))
            return
        app.show_message("Пароль обновлён", "Теперь вы можете войти с новым паролем.")
        app.switch_screen("auth")

    def change_password(self):
        app = App.get_running_app()
        if self.new_password_field.input.text != self.new_password_repeat_field.input.text:
            app.show_message("Ошибка", "Новые пароли не совпадают.")
            return
        try:
            app.repository.change_password(self.old_password_field.input.text, self.new_password_field.input.text)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.show_message("Пароль изменён", "Новый пароль сохранён локально.")
        app.switch_screen("profile")
