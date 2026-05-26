from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout

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
    SectionTitle,
    StatusBadge,
    SubSectionTitle,
    WrapLabel,
    make_button_row,
    make_chip,
    make_chip_fill,
    make_info_card,
    make_stat_grid,
    make_stat_line,
)


class TicketsScreen(BaseScreen):
    title = "Заявки"

    def __init__(self, **kwargs):
        self.search_query = ""
        self.category_filter = ""
        self.status_filter = ""
        self.author_filter = ""
        super().__init__(**kwargs)

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        repo = app.repository
        user = repo.get_current_user()
        if not user["is_authenticated"]:
            self._show_restricted("Чтобы просматривать заявки, войдите в личный кабинет.")
            return

        categories = repo.get_categories()
        statuses = repo.get_statuses()
        authors = repo.get_users() if user["is_admin"] else []

        filter_card = Card(tone="primary")
        filter_card.add_widget(SectionTitle(text="Заявки"))
        filter_card.add_widget(CaptionLabel(text="Поиск, фильтрация и создание обращений по образцу веб-раздела."))
        filter_card.add_widget(SubSectionTitle(text="Фильтры"))
        self.search_input = AppInput(text=self.search_query, hint_text="Тема или описание")
        self.category_spinner = AppSpinner(text=self.category_filter or "Все категории", values=["Все категории"] + [item["name"] for item in categories])
        filter_card.add_widget(FormRow("Поиск", self.search_input))
        filter_card.add_widget(FormRow("Категория", self.category_spinner))
        if user["is_operator"] or user["is_admin"]:
            self.status_spinner = AppSpinner(text=self.status_filter or "Все статусы", values=["Все статусы"] + [item["name"] for item in statuses])
            filter_card.add_widget(FormRow("Статус", self.status_spinner))
        if user["is_admin"]:
            self.author_spinner = AppSpinner(text=self.author_filter or "Все авторы", values=["Все авторы"] + [item["full_name"] for item in authors])
            filter_card.add_widget(FormRow("Автор", self.author_spinner))
        apply_button = AppButton(text="Применить")
        apply_button.bind(on_release=lambda *_: self.apply_filters())
        filter_card.add_widget(apply_button)
        self.body.layout.add_widget(filter_card)

        create_card = Card(tone="soft")
        create_card.add_widget(SubSectionTitle(text="Новая заявка"))
        self.new_title_input = AppInput(hint_text="Тема")
        self.new_description_input = AppTextArea(hint_text="Описание")
        self.new_category_spinner = AppSpinner(text="Выберите категорию", values=[item["name"] for item in categories])
        self.new_priority_spinner = AppSpinner(text="Средний", values=["Низкий", "Средний", "Высокий"])
        create_card.add_widget(FormRow("Тема", self.new_title_input))
        create_card.add_widget(FormRow("Описание", self.new_description_input))
        create_card.add_widget(FormRow("Категория", self.new_category_spinner))
        create_card.add_widget(FormRow("Приоритет", self.new_priority_spinner))
        create_button = AppButton(text="Создать заявку")
        create_button.bind(on_release=lambda *_: self.create_ticket())
        create_card.add_widget(create_button)
        self.body.layout.add_widget(create_card)

        category_map = {item["name"]: item["id"] for item in categories}
        status_map = {item["name"]: item["code"] for item in statuses}
        author_map = {item["full_name"]: item["id"] for item in authors}
        items = repo.get_tickets(
            search=self.search_query,
            category_id=category_map.get(self.category_filter),
            status_code=status_map.get(self.status_filter, ""),
            author_id=author_map.get(self.author_filter),
        )
        summary_items = [(str(len(items)), "Найдено заявок", "soft")]
        if user["is_client"]:
            active_count = len([item for item in items if item["status_code"] in ("new", "in_progress")])
            summary_items.append((str(active_count), "Активных", "soft"))
        self.body.layout.add_widget(make_stat_grid(summary_items, cols=min(2, len(summary_items))))
        for ticket in items:
            card = Card(tone="soft")
            header = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(34))
            title = SubSectionTitle(text=f"#{ticket['id']} {ticket['title']}")
            title.size_hint_x = 1
            title.shorten = True
            title.shorten_from = "right"
            title.max_lines = 1
            header.add_widget(title)
            header.add_widget(StatusBadge(text=ticket["status_name"], status_code=ticket["status_code"]))
            card.add_widget(header)
            card.add_widget(make_stat_line("Категория", ticket["category_name"]))
            card.add_widget(make_stat_line("Приоритет", ticket["priority_name"]))
            card.add_widget(make_stat_line("Автор", ticket["author_name"]))
            card.add_widget(make_stat_line("Исполнитель", ticket["assignee_name"]))
            card.add_widget(make_stat_line("Создана", ticket["created_at"]))
            preview = (ticket["description"] or "").strip()
            if len(preview) > 140:
                preview = preview[:140].rstrip() + "…"
            if preview:
                card.add_widget(WrapLabel(text=preview, max_lines=3, shorten=True, shorten_from="right"))
            open_button = GhostButton(text="Открыть заявку")
            open_button.bind(on_release=lambda *_args, value=ticket["id"]: app.open_ticket(value))
            card.add_widget(open_button)
            self.body.layout.add_widget(card)

        if not items:
            self.body.layout.add_widget(make_info_card("Ничего не найдено", "Измените фильтры или создайте новую заявку."))

    def apply_filters(self):
        self.search_query = self.search_input.text.strip()
        self.category_filter = self.category_spinner.text.strip()
        self.status_filter = getattr(self, "status_spinner", AppSpinner(text="")).text.strip() if hasattr(self, "status_spinner") else ""
        self.author_filter = getattr(self, "author_spinner", AppSpinner(text="")).text.strip() if hasattr(self, "author_spinner") else ""
        self.refresh()

    def create_ticket(self):
        app = App.get_running_app()
        categories = {item["name"]: item["id"] for item in app.repository.get_categories()}
        if not self.new_title_input.text.strip() or not self.new_description_input.text.strip() or self.new_category_spinner.text not in categories:
            app.show_message("Ошибка", "Заполните тему, описание и категорию.")
            return
        priority_map = {"Низкий": "low", "Средний": "medium", "Высокий": "high"}
        ticket = app.repository.create_ticket(
            {
                "title": self.new_title_input.text,
                "description": self.new_description_input.text,
                "category_id": categories[self.new_category_spinner.text],
                "priority": priority_map.get(self.new_priority_spinner.text, "medium"),
                "organization": app.repository.get_current_user().get("organization", ""),
            }
        )
        app.refresh_all_screens()
        app.open_ticket(ticket["id"])

    def _show_restricted(self, text):
        card = Card()
        card.add_widget(SectionTitle(text="Доступ ограничен"))
        card.add_widget(CaptionLabel(text=text))
        button = AppButton(text="Открыть экран входа")
        button.bind(on_release=lambda *_: App.get_running_app().switch_screen("auth"))
        card.add_widget(button)
        self.body.layout.add_widget(card)


class TicketDetailScreen(BaseScreen):
    title = "Карточка заявки"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        repo = app.repository
        ticket = repo.get_ticket(app.selected_ticket_id) if app.selected_ticket_id else None
        user = repo.get_current_user()
        if not user["is_authenticated"]:
            self.body.layout.add_widget(make_info_card("Нет доступа", "Откройте кабинет, чтобы увидеть детали обращений.", "К входу", lambda: app.switch_screen("auth")))
            return
        if not ticket:
            self.body.layout.add_widget(make_info_card("Заявка не выбрана", "Откройте раздел заявок и выберите карточку.", "К списку", lambda: app.switch_screen("tickets")))
            return

        categories = repo.get_categories()
        category_map = {item["name"]: item["id"] for item in categories}
        statuses = repo.get_statuses()
        status_map = {item["name"]: item["code"] for item in statuses}
        staff = repo.get_staff_users()
        staff_map = {"—": None, **{item["full_name"]: item["id"] for item in staff}}

        top_card = Card(tone="soft", padding=dp(12))
        back_button = GhostButton(text="← К списку заявок")
        back_button.bind(on_release=lambda *_: app.switch_screen("tickets"))
        top_card.add_widget(back_button)
        self.body.layout.add_widget(top_card)

        card = Card(tone="primary")
        header = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None)
        header.bind(minimum_height=header.setter("height"))
        header.add_widget(SectionTitle(text=f"#{ticket['id']} {ticket['title']}"))
        header.add_widget(StatusBadge(text=ticket["status_name"], status_code=ticket["status_code"]))
        card.add_widget(header)
        card.add_widget(CaptionLabel(text=f"Автор: {ticket['author_name']} • Исполнитель: {ticket['assignee_name']}"))
        self.title_input = AppInput(text=ticket["title"])
        self.description_input = AppTextArea(text=ticket["description"])
        self.organization_input = AppInput(text=ticket.get("organization", ""))
        card.add_widget(FormRow("Тема", self.title_input))
        card.add_widget(FormRow("Описание", self.description_input))
        card.add_widget(FormRow("Организация", self.organization_input))
        card.add_widget(make_stat_line("Категория", ticket["category_name"]))
        card.add_widget(make_stat_line("Приоритет", ticket["priority_name"]))
        card.add_widget(make_stat_line("Автор", ticket["author_name"]))
        card.add_widget(make_stat_line("Исполнитель", ticket["assignee_name"]))
        card.add_widget(make_stat_line("Создана", ticket["created_at"]))
        self.body.layout.add_widget(card)

        if ticket["can_manage"]:
            manage_card = Card(tone="soft")
            manage_card.add_widget(SubSectionTitle(text="Управление заявкой"))
            self.category_spinner = AppSpinner(text=ticket["category_name"], values=[item["name"] for item in categories])
            self.priority_spinner = AppSpinner(text=ticket["priority_name"], values=["Низкий", "Средний", "Высокий"])
            self.status_spinner = AppSpinner(text=ticket["status_name"], values=[item["name"] for item in statuses])
            self.assignee_spinner = AppSpinner(text=ticket["assignee_name"], values=["—"] + [item["full_name"] for item in staff])
            manage_card.add_widget(FormRow("Категория", self.category_spinner))
            manage_card.add_widget(FormRow("Приоритет", self.priority_spinner))
            manage_card.add_widget(FormRow("Статус", self.status_spinner))
            manage_card.add_widget(FormRow("Исполнитель", self.assignee_spinner))
            self.body.layout.add_widget(manage_card)

        save_button = AppButton(text="Сохранить изменения")
        save_button.bind(on_release=lambda *_: self.save_ticket(category_map, status_map, staff_map, ticket))
        action_buttons = [save_button]
        if ticket["can_delete"]:
            delete_button = DangerButton(text="Удалить заявку")
            delete_button.bind(on_release=lambda *_: self.delete_ticket(ticket["id"]))
            action_buttons.append(delete_button)
        buttons_card = Card(tone="soft", padding=dp(12))
        if len(action_buttons) == 2:
            buttons_card.add_widget(make_button_row(*action_buttons))
        else:
            buttons_card.add_widget(action_buttons[0])
        self.body.layout.add_widget(buttons_card)

        attach_card = Card(tone="soft")
        attach_card.add_widget(SubSectionTitle(text="Вложения"))
        for attachment in ticket["attachments"]:
            attach_card.add_widget(CaptionLabel(text=f"{attachment['filename']} • {attachment['created_at']}"))
        if not ticket["attachments"]:
            attach_card.add_widget(CaptionLabel(text="Вложений пока нет."))
        self.attachment_input = AppInput(hint_text="Например: screenshot.png")
        attach_card.add_widget(FormRow("Имя файла", self.attachment_input))
        add_attachment_button = AppButton(text="Добавить вложение")
        add_attachment_button.bind(on_release=lambda *_: self.add_attachment(ticket["id"]))
        attach_card.add_widget(add_attachment_button)
        self.body.layout.add_widget(attach_card)

        comments = Card()
        comments.add_widget(SectionTitle(text="Комментарии"))
        for comment in ticket["comments"]:
            bubble = Card(tone="soft", padding=dp(12), spacing=dp(6))
            bubble.add_widget(CaptionLabel(text=f"{comment['author_name']} • {comment['created_at']}"))
            bubble.add_widget(WrapLabel(text=comment["text"]))
            comments.add_widget(bubble)
        if not ticket["comments"]:
            comments.add_widget(CaptionLabel(text="Комментариев пока нет."))
        self.comment_input = AppTextArea(hint_text="Добавить комментарий")
        comments.add_widget(FormRow("Комментарий", self.comment_input))
        comment_button = AppButton(text="Отправить комментарий")
        comment_button.bind(on_release=lambda *_: self.add_comment(ticket["id"]))
        comments.add_widget(comment_button)
        self.body.layout.add_widget(comments)

        activity_card = Card(tone="soft")
        activity_card.add_widget(SubSectionTitle(text="История изменений"))
        activity = repo.get_ticket_logs(ticket["id"])
        if not activity:
            activity_card.add_widget(CaptionLabel(text="Изменений пока нет."))
        for item in activity:
            activity_card.add_widget(CaptionLabel(text=f"{item['created_at']} • {item.get('actor_name') or 'Система'}"))
            if item.get("details"):
                activity_card.add_widget(WrapLabel(text=item["details"]))
        self.body.layout.add_widget(activity_card)

    def save_ticket(self, category_map, status_map, staff_map, ticket):
        app = App.get_running_app()
        payload = {
            "title": self.title_input.text,
            "description": self.description_input.text,
            "organization": self.organization_input.text,
        }
        if ticket["can_manage"]:
            priority_map = {"Низкий": "low", "Средний": "medium", "Высокий": "high"}
            payload.update(
                {
                    "category_id": category_map.get(self.category_spinner.text, ticket["category_id"]),
                    "priority": priority_map.get(self.priority_spinner.text, ticket["priority"]),
                    "status_code": status_map.get(self.status_spinner.text, ticket["status_code"]),
                    "assignee_id": staff_map.get(self.assignee_spinner.text),
                }
            )
        try:
            app.repository.update_ticket(ticket["id"], **payload)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Изменения сохранены", "Карточка заявки обновлена.")
        app.open_ticket(ticket["id"])

    def add_comment(self, ticket_id):
        app = App.get_running_app()
        try:
            app.repository.add_comment(ticket_id, self.comment_input.text)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.open_ticket(ticket_id)

    def add_attachment(self, ticket_id):
        app = App.get_running_app()
        try:
            app.repository.add_attachment(ticket_id, self.attachment_input.text)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.open_ticket(ticket_id)

    def delete_ticket(self, ticket_id):
        app = App.get_running_app()
        try:
            app.repository.delete_ticket(ticket_id)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Заявка удалена", "Карточка была удалена из локальной базы.")
        app.switch_screen("tickets")


class KnowledgeScreen(BaseScreen):
    title = "База знаний"

    def __init__(self, **kwargs):
        self.current_category = ""
        self.search_query = ""
        super().__init__(**kwargs)

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        repo = app.repository
        user = repo.get_current_user()
        categories = repo.get_categories()
        category_map = {item["name"]: item["code"] for item in categories}

        filter_card = Card(tone="primary")
        filter_card.add_widget(SectionTitle(text="База знаний"))
        ai_enabled = bool(getattr(app.configData, "openrouterApiKey", ""))
        description = "Категории — в 2 колонки, плюс AI‑поиск по заголовкам и тексту статей." if ai_enabled else "Категории — в 2 колонки, поиск работает локально по заголовкам и тексту статей."
        filter_card.add_widget(CaptionLabel(text=description))
        self.search_input = AppInput(text=self.search_query, hint_text="AI‑поиск: например «wifi пароль», «не входит кабинет», «оплата»")
        search_button = GhostButton(text="Найти")
        search_button.bind(on_release=lambda *_: self.apply_search())
        filter_card.add_widget(FormRow("Поиск", self.search_input))
        filter_card.add_widget(search_button)
        filter_card.add_widget(SubSectionTitle(text="Категории"))
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(make_chip_fill("Все", lambda: self.set_category(""), active=self.current_category == ""))
        for category in categories:
            grid.add_widget(
                make_chip_fill(
                    category["name"],
                    lambda value=category["code"]: self.set_category(value),
                    active=self.current_category == category["code"],
                )
            )
        filter_card.add_widget(grid)
        self.body.layout.add_widget(filter_card)

        if user["is_operator"] or user["is_admin"]:
            add_card = Card(tone="soft")
            add_card.add_widget(SubSectionTitle(text="Добавить статью"))
            self.article_title = AppInput(hint_text="Заголовок")
            self.article_category = AppSpinner(text="Выберите категорию", values=[item["name"] for item in categories])
            self.article_content = AppTextArea(hint_text="Содержание статьи")
            self.import_content = AppTextArea(hint_text="Вставьте несколько абзацев для импорта")
            add_card.add_widget(FormRow("Заголовок", self.article_title))
            add_card.add_widget(FormRow("Категория", self.article_category))
            add_card.add_widget(FormRow("Содержание", self.article_content))
            save_button = AppButton(text="Сохранить статью")
            save_button.bind(on_release=lambda *_: self.add_article(category_map))
            add_card.add_widget(save_button)
            add_card.add_widget(SubSectionTitle(text="Импорт из текста"))
            add_card.add_widget(FormRow("Текст для импорта", self.import_content))
            import_button = GhostButton(text="Импортировать статьи")
            import_button.bind(on_release=lambda *_: self.import_articles(category_map))
            add_card.add_widget(import_button)
            self.body.layout.add_widget(add_card)

        if self.search_query.strip():
            articles = repo.search_articles(self.search_query, self.current_category)
        else:
            articles = repo.get_articles(self.current_category)
        for article in articles:
            card = Card(tone="soft")
            card.add_widget(SectionTitle(text=article["title"]))
            card.add_widget(CaptionLabel(text=f"Категория: {article['category_name']}"))
            card.add_widget(CaptionLabel(text=f"Обновлено: {article['updated_at']}"))
            preview = article["content"][:180] + ("..." if len(article["content"]) > 180 else "")
            card.add_widget(WrapLabel(text=preview))
            open_button = AppButton(text="Читать статью")
            open_button.bind(on_release=lambda *_args, value=article["id"]: app.open_article(value))
            card.add_widget(open_button)
            self.body.layout.add_widget(card)

        if not articles:
            text = "По запросу ничего не найдено." if self.search_query.strip() else "Пока нет статей."
            self.body.layout.add_widget(make_info_card(text, "Попробуйте другой запрос или категорию."))

    def set_category(self, code):
        self.current_category = code
        self.search_query = ""
        self.refresh()

    def apply_search(self):
        self.search_query = self.search_input.text.strip()
        self.refresh()

    def add_article(self, category_map):
        app = App.get_running_app()
        if self.article_category.text not in category_map:
            app.show_message("Ошибка", "Выберите категорию для статьи.")
            return
        try:
            article = app.repository.add_article(self.article_title.text, self.article_content.text, category_map[self.article_category.text])
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.open_article(article["id"])

    def import_articles(self, category_map):
        app = App.get_running_app()
        if self.article_category.text not in category_map:
            app.show_message("Ошибка", "Выберите категорию для импорта.")
            return
        try:
            created = app.repository.import_articles(self.import_content.text, category_map[self.article_category.text])
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Импорт завершён", f"Добавлено статей: {created}")


class ArticleScreen(BaseScreen):
    title = "Статья"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        article = app.repository.get_article(app.selected_article_id) if app.selected_article_id else None
        user = app.repository.get_current_user()
        if not article:
            self.body.layout.add_widget(make_info_card("Статья не выбрана", "Откройте базу знаний и выберите материал.", "К базе знаний", lambda: app.switch_screen("knowledge")))
            return

        card = Card(tone="primary")
        card.add_widget(SectionTitle(text=article["title"]))
        card.add_widget(CaptionLabel(text=f"Категория: {article['category_name']}"))
        card.add_widget(CaptionLabel(text=f"Автор: {article['author_name']}"))
        card.add_widget(CaptionLabel(text=f"Обновлено: {article['updated_at']}"))
        for paragraph in article["content"].split("\n\n"):
            card.add_widget(WrapLabel(text=paragraph))
        back_button = GhostButton(text="Назад в базу знаний")
        back_button.bind(on_release=lambda *_: app.switch_screen("knowledge"))
        card.add_widget(back_button)
        self.body.layout.add_widget(card)

        if user["is_operator"] or user["is_admin"]:
            edit_card = Card(tone="soft")
            edit_card.add_widget(SubSectionTitle(text="Редактирование"))
            self.title_input = AppInput(text=article["title"])
            self.category_spinner = AppSpinner(text=article["category_name"], values=[item["name"] for item in app.repository.get_categories()])
            self.content_input = AppTextArea(text=article["content"])
            edit_card.add_widget(FormRow("Заголовок", self.title_input))
            edit_card.add_widget(FormRow("Категория", self.category_spinner))
            edit_card.add_widget(FormRow("Содержание", self.content_input))
            save_button = AppButton(text="Сохранить статью")
            save_button.bind(on_release=lambda *_: self.save_article(article["id"]))
            edit_card.add_widget(save_button)
            if user["is_admin"]:
                delete_button = DangerButton(text="Удалить статью")
                delete_button.bind(on_release=lambda *_: self.delete_article(article["id"]))
                edit_card.add_widget(delete_button)
            self.body.layout.add_widget(edit_card)

    def save_article(self, article_id):
        app = App.get_running_app()
        category_map = {item["name"]: item["code"] for item in app.repository.get_categories()}
        try:
            app.repository.update_article(article_id, self.title_input.text, self.content_input.text, category_map[self.category_spinner.text])
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Статья обновлена", "Изменения сохранены.")
        app.open_article(article_id)

    def delete_article(self, article_id):
        app = App.get_running_app()
        try:
            app.repository.delete_article(article_id)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Статья удалена", "Материал удалён из базы знаний.")
        app.switch_screen("knowledge")


class ProfileScreen(BaseScreen):
    title = "Профиль"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()
        if not user["is_authenticated"]:
            self.body.layout.add_widget(make_info_card("Профиль недоступен", "Сначала выполните вход в систему.", "К входу", lambda: app.switch_screen("auth")))
            return

        stats = app.repository.get_client_dashboard_stats()
        hero = Card(tone="primary")
        hero.add_widget(SectionTitle(text=user["full_name"]))
        hero.add_widget(CaptionLabel(text=f"Роль: {user['role_name']}"))
        hero.add_widget(CaptionLabel(text=f"Логин: {user['login']}"))
        hero.add_widget(CaptionLabel(text=f"Email: {user['email']}"))
        hero.add_widget(CaptionLabel(text=f"Моих заявок: {stats['tickets']} • Активных: {stats['active']}"))
        if user.get("avatar_path"):
            hero.add_widget(CaptionLabel(text=f"Аватар: {user['avatar_path']}"))
        self.body.layout.add_widget(hero)

        card = Card(tone="soft")
        card.add_widget(SubSectionTitle(text="Мой профиль"))
        self.login_input = AppInput(text=user["login"])
        self.email_input = AppInput(text=user["email"])
        self.full_name_input = AppInput(text=user["full_name"])
        self.organization_input = AppInput(text=user.get("organization", ""))
        self.avatar_input = AppInput(text=user.get("avatar_path", ""), hint_text="storage/avatar.png")
        card.add_widget(FormRow("Логин", self.login_input))
        card.add_widget(FormRow("Email", self.email_input))
        card.add_widget(FormRow("ФИО", self.full_name_input))
        card.add_widget(FormRow("Организация", self.organization_input))
        card.add_widget(FormRow("Путь к аватару", self.avatar_input, "Для локальной версии можно указать путь вручную"))
        save_button = AppButton(text="Сохранить изменения")
        save_button.bind(on_release=lambda *_: self.save_profile())
        password_button = GhostButton(text="Сменить пароль")
        password_button.bind(on_release=lambda *_: app.switch_screen("password"))
        card.add_widget(save_button)
        card.add_widget(password_button)
        self.body.layout.add_widget(card)

    def save_profile(self):
        app = App.get_running_app()
        try:
            app.repository.update_profile(
                self.login_input.text,
                self.email_input.text,
                self.full_name_input.text,
                self.organization_input.text,
            )
            app.repository.update_avatar(self.avatar_input.text.strip())
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.show_message("Профиль сохранён", "Личные данные обновлены.")


class AdminScreen(BaseScreen):
    title = "Панель управления"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()
        if not (user["is_operator"] or user["is_admin"]):
            self.body.layout.add_widget(make_info_card("Раздел только для сотрудников", "Войдите как оператор или администратор.", "К входу", lambda: app.switch_screen("auth")))
            return

        report = app.repository.get_report_stats()
        hero = Card(tone="primary")
        hero.add_widget(SectionTitle(text="Панель управления"))
        hero.add_widget(WrapLabel(text=f"Управление заявками, пользователями и отчётами. Вы вошли как {user['full_name']} ({user['role_name']})."))
        self.body.layout.add_widget(hero)

        totals = report.get("totals", {})
        self.body.layout.add_widget(
            make_stat_grid(
                [
                    (str(totals.get("tickets", 0)), "Заявок", "soft"),
                    (str(totals.get("users", 0)), "Пользователей", "soft"),
                    (str(totals.get("articles", 0)), "Статей", "soft"),
                    (str(totals.get("logs", 0)), "Логов", "soft"),
                ]
            )
        )

        actions = Card()
        actions.add_widget(SectionTitle(text="Разделы"))
        sections = [
            ("Заявки", "Просмотр и обработка всех заявок, смена статусов и назначение исполнителей.", "tickets"),
            ("Отчёты", "Статистика по заявкам и нагрузка операторов.", "reports"),
            ("База знаний", "Статьи и материалы для клиентов и операторов.", "knowledge"),
        ]
        if user["is_admin"]:
            sections.extend(
                [
                    ("Пользователи", "Управление учётными записями и ролями.", "users"),
                    ("Журнал", "История изменений и действий в системе.", "logs"),
                ]
            )
        for label, subtitle, screen in sections:
            actions.add_widget(make_info_card(label, subtitle, "Открыть", callback=lambda name=screen: app.switch_screen(name)))
        self.body.layout.add_widget(actions)


class ReportsScreen(BaseScreen):
    title = "Отчёты"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()
        if not (user["is_operator"] or user["is_admin"]):
            self.body.layout.add_widget(make_info_card("Нет доступа", "Отчёты доступны только сотрудникам.", "К панели", lambda: app.switch_screen("admin")))
            return
        report = app.repository.get_report_stats()

        header_card = Card(tone="primary")
        header_card.add_widget(SectionTitle(text="Отчёты и статистика"))
        header_card.add_widget(CaptionLabel(text="Страница повторяет веб-раздел отчётов, но графики здесь собраны как компактные мобильные панели."))
        export_tickets_button = GhostButton(text="Экспорт заявок в CSV")
        export_tickets_button.bind(on_release=lambda *_: self.export_tickets())
        export_operators_button = AppButton(text="Экспорт нагрузки операторов")
        export_operators_button.bind(on_release=lambda *_: self.export_operators())
        header_card.add_widget(export_tickets_button)
        header_card.add_widget(export_operators_button)
        self.body.layout.add_widget(header_card)

        totals = report.get("totals", {})
        self.body.layout.add_widget(
            make_stat_grid(
                [
                    (str(totals.get("tickets", 0)), "Заявок", "soft"),
                    (str(totals.get("users", 0)), "Пользователей", "soft"),
                    (str(totals.get("articles", 0)), "Статей", "soft"),
                    (str(totals.get("logs", 0)), "Логов", "soft"),
                ]
            )
        )

        for title, key in (
            ("Статусы заявок", "status_stats"),
            ("Категории заявок", "category_stats"),
            ("Нагрузка по исполнителям", "assignee_stats"),
        ):
            card = Card(tone="soft")
            card.add_widget(SubSectionTitle(text=title))
            for row in report.get(key, []):
                card.add_widget(make_stat_line(row["label"], str(row["total"])))
                card.add_widget(CaptionLabel(text=self._make_bar(row["total"])))
            self.body.layout.add_widget(card)

    def _make_bar(self, total):
        return "#" * max(1, min(int(total), 20))

    def export_tickets(self):
        export_path = App.get_running_app().repository.export_tickets_csv()
        App.get_running_app().show_message("Экспорт завершён", f"Файл сохранён: {export_path}")

    def export_operators(self):
        export_path = App.get_running_app().repository.export_operator_summary()
        App.get_running_app().show_message("Экспорт завершён", f"Файл сохранён: {export_path}")


class UsersScreen(BaseScreen):
    title = "Пользователи"

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()
        if not user["is_admin"]:
            self.body.layout.add_widget(make_info_card("Нет доступа", "Управление пользователями доступно только администратору.", "К панели", lambda: app.switch_screen("admin")))
            return

        self.roles = [(item["code"], item["name"]) for item in app.repository.get_roles()]
        users = app.repository.get_users()
        current_edit = next((item for item in users if item["id"] == app.selected_user_id), None)

        summary = Card(tone="primary")
        summary.add_widget(SectionTitle(text="Пользователи"))
        summary.add_widget(CaptionLabel(text=f"Всего локальных пользователей: {len(users)}"))
        for _, role_name in self.roles:
            total = len([item for item in users if item["role_name"] == role_name])
            summary.add_widget(make_stat_line(role_name, str(total)))
        if current_edit:
            summary.add_widget(CaptionLabel(text=f"Сейчас редактируется: {current_edit['full_name']}"))
        self.body.layout.add_widget(summary)

        form = Card(tone="soft")
        form.add_widget(SectionTitle(text="Создать или изменить пользователя"))
        self.login_input = AppInput(text=current_edit["login"] if current_edit else "")
        self.email_input = AppInput(text=current_edit["email"] if current_edit else "")
        self.name_input = AppInput(text=current_edit["full_name"] if current_edit else "")
        self.organization_input = AppInput(text=current_edit["organization"] if current_edit else "")
        self.password_input = AppInput(password=True, hint_text="Пароль для нового пользователя")
        current_role_name = current_edit["role_name"] if current_edit else "Клиент"
        self.role_spinner = AppSpinner(text=current_role_name, values=[role_name for _, role_name in self.roles])
        form.add_widget(FormRow("Логин", self.login_input))
        form.add_widget(FormRow("Email", self.email_input))
        form.add_widget(FormRow("ФИО", self.name_input))
        form.add_widget(FormRow("Организация", self.organization_input))
        form.add_widget(FormRow("Роль", self.role_spinner))
        form.add_widget(FormRow("Пароль", self.password_input, "Для редактирования пароль можно оставить пустым"))
        save_button = AppButton(text="Сохранить пользователя")
        save_button.bind(on_release=lambda *_: self.save_user(current_edit["id"] if current_edit else None))
        clear_button = GhostButton(text="Очистить форму")
        clear_button.bind(on_release=lambda *_: self.clear_selected())
        form.add_widget(save_button)
        form.add_widget(clear_button)
        self.body.layout.add_widget(form)

        for item in users:
            card = Card(tone="soft")
            card.add_widget(SectionTitle(text=item["full_name"]))
            card.add_widget(CaptionLabel(text=f"Логин: {item['login']}"))
            card.add_widget(CaptionLabel(text=f"Email: {item['email']}"))
            card.add_widget(CaptionLabel(text=f"Роль: {item['role_name']}"))
            if item["organization"]:
                card.add_widget(CaptionLabel(text=f"Организация: {item['organization']}"))
            edit_button = AppButton(text="Редактировать")
            edit_button.bind(on_release=lambda *_args, value=item["id"]: app.open_user(value))
            card.add_widget(edit_button)
            if item["id"] != user["id"]:
                delete_button = DangerButton(text="Удалить")
                delete_button.bind(on_release=lambda *_args, value=item["id"]: self.delete_user(value))
                card.add_widget(delete_button)
            self.body.layout.add_widget(card)

    def save_user(self, user_id):
        app = App.get_running_app()
        role_map = {name: code for code, name in self.roles}
        try:
            if user_id:
                app.repository.update_user(
                    user_id,
                    self.login_input.text,
                    self.email_input.text,
                    self.name_input.text,
                    role_map[self.role_spinner.text],
                    self.organization_input.text,
                )
            else:
                app.repository.create_user(
                    self.login_input.text,
                    self.email_input.text,
                    self.name_input.text,
                    self.password_input.text or "changeMe123",
                    role_map[self.role_spinner.text],
                    self.organization_input.text,
                )
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.selected_user_id = None
        app.refresh_all_screens()
        app.show_message("Готово", "Данные пользователя сохранены.")
        app.switch_screen("users")

    def delete_user(self, user_id):
        app = App.get_running_app()
        try:
            app.repository.delete_user(user_id)
        except ValueError as error:
            app.show_message("Ошибка", str(error))
            return
        app.refresh_all_screens()
        app.switch_screen("users")

    def clear_selected(self):
        app = App.get_running_app()
        app.selected_user_id = None
        app.switch_screen("users")


class LogsScreen(BaseScreen):
    title = "Журнал"

    def __init__(self, **kwargs):
        self.page = 1
        super().__init__(**kwargs)

    def refresh(self):
        super().refresh()
        app = App.get_running_app()
        user = app.repository.get_current_user()
        if not user["is_admin"]:
            self.body.layout.add_widget(make_info_card("Нет доступа", "Журнал доступен только администратору.", "К панели", lambda: app.switch_screen("admin")))
            return
        data = app.repository.get_logs(page=self.page)
        if not data["items"]:
            self.body.layout.add_widget(make_info_card("Журнал пуст", "Логов пока нет."))
            return
        summary = Card(tone="primary")
        summary.add_widget(SectionTitle(text="Журнал действий"))
        summary.add_widget(make_stat_line("Страница", f"{self.page} / {data['pages']}"))
        summary.add_widget(CaptionLabel(text="Здесь сохраняются локальные изменения пользователей, заявок и статей."))
        self.body.layout.add_widget(summary)
        for item in data["items"]:
            card = Card(tone="soft")
            entity_suffix = f" #{item['entity_id']}" if item.get("entity_id") else ""
            card.add_widget(SectionTitle(text=f"{item['action']} • {item['entity_type']}{entity_suffix}"))
            card.add_widget(CaptionLabel(text=f"Исполнитель: {item.get('actor_name') or 'Система'}"))
            card.add_widget(CaptionLabel(text=f"Время: {item['created_at']}"))
            if item["details"]:
                card.add_widget(WrapLabel(text=item["details"]))
            self.body.layout.add_widget(card)
        pager = Card(tone="soft")
        pager.add_widget(make_stat_line("Текущая страница", f"{self.page} / {data['pages']}"))
        prev_button = GhostButton(text="Назад")
        prev_button.bind(on_release=lambda *_: self.change_page(-1, data["pages"]))
        next_button = AppButton(text="Вперёд")
        next_button.bind(on_release=lambda *_: self.change_page(1, data["pages"]))
        pager.add_widget(make_button_row(prev_button, next_button))
        self.body.layout.add_widget(pager)

    def change_page(self, delta, pages):
        self.page = min(max(1, self.page + delta), pages)
        self.refresh()
