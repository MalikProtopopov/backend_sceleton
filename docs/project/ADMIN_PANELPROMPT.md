Ты — Staff Product Designer (B2B SaaS / Admin panels) + UX Researcher + Content Strategist + Security-aware PM.
Нужно провести исследование и выдать рекомендации по проектированию административной панели (admin) для управления корпоративным сайтом и контентом. Панель должна быть универсальной и переиспользуемой для разных клиентов (как “движок”). Составь md файл один общий. 

Контекст продукта
Мы строим backend-движок для корпоративных сайтов (FastAPI + PostgreSQL) с CRUD сущностями:
- сотрудники (team members) + привязка к направлениям/ролям
- направления работы компании (practice areas)
- услуги
- кейсы компании
- статьи и темы/категории статей
- FAQ
- отзывы
- документы/файлы (media library)
- контакты (контактный блок)
- преимущества компании
- почтовые адреса/офисы
- заявки/лиды (forms/inquiries)
Плюс: управление локализациями (добавлять/редактировать/удалять языки) и SEO метатегами по URL (route-level SEO).

Главная цель исследования
Собрать лучшие практики и сформировать требования/решения для админ-панели:
1) Информационная архитектура (IA), навигация, структура разделов.
2) UX-паттерны для CRUD, таблиц, фильтров, форм, массовых операций.
3) Контентные воркфлоу: черновики/публикация, ревью, расписание публикаций.
4) Управление локалями и переводами: удобные сценарии перевода, fallback, контроль “missing translations”.
5) SEO-центр: управление meta title/description/OG/canonical/robots/json-ld по URL + превью.
6) Медиа/документы: загрузка, версии, теги, права доступа, переиспользование.
7) Роли и права (RBAC) + аудит лог (кто что менял) + безопасность админки (MFA/сессии).
8) Доступность (WCAG/ARIA), качество форм (ошибки/валидация), чтобы панель была удобна и надежна.
9) Список экранов (screen list), ключевые компоненты UI kit, состояния (loading/empty/error).

Ограничения/принципы
- Панель должна быть “data-heavy friendly”: таблицы, фильтры, быстрые действия, поиск. Опирайся на признанные паттерны data tables (сортировка, выбор строк, batch actions).  [oai_citation:1‡Material Design](https://m2.material.io/components/data-tables?utm_source=chatgpt.com)
- Формы должны иметь корректные сообщения об ошибках (ясные, текстом, с подсветкой поля).  [oai_citation:2‡W3C](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html?utm_source=chatgpt.com)
- Доступность: учитывай ARIA Authoring Practices для таблиц, диалогов, алертов, меню и т.п.  [oai_citation:3‡W3C](https://www.w3.org/WAI/ARIA/apg/?utm_source=chatgpt.com)
- Безопасность админки: учти рекомендации по authentication/session management (MFA для админов, защищенные сессии, время жизни, защита cookie, выход из всех сессий при компромете).  [oai_citation:4‡OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html?utm_source=chatgpt.com)
- Масштабируемость: проектирование под будущие сущности/модули и кастомизацию клиента (брендинг, модули on/off, разные роли).

Что нужно сделать (структура исследования и выход)
Сделай результат как “Admin Panel Product Spec + UX Blueprint”.

ШАГ 1 — Роли и JTBD (jobs-to-be-done)
Определи роли:
- Owner/директор
- Маркетолог
- Контент-менеджер/редактор
- HR/PR
- SEO-специалист
- Sales/менеджер по лидам
- Администратор системы
Для каждой:
- JTBD statement
- Частые задачи (top tasks)
- Критичность/частота (high/med/low)
- Какие данные/сущности они трогают
- Какие боли обычно в админках (slow, хаос, ошибки, нет прозрачности)

ШАГ 2 — IA: карта админки и навигация
Составь:
- sitemap админки (разделы и подпункты)
- вариант навигации: sidebar + topbar + breadcrumbs
- глобальный поиск по сущностям (command palette или global search) — если уместно
- принципы именования и группировки модулей

Минимальные модули админки:
1) Dashboard / Overview
2) Content: Articles, Topics
3) Company: Services, Practice Areas, Advantages
4) Portfolio: Cases
5) People: Team Members
6) Social proof: Reviews, FAQ
7) Contacts: Contact block, Addresses/Offices
8) Leads: Applications/Inquiries (list + details + статус)
9) Media Library: Documents/Files
10) SEO Center: SEO by URL (+ redirects опционально)
11) Localization: languages + translation status
12) Users & Roles (RBAC) + Audit log
13) Settings (site-wide settings, brand, integrations)

ШАГ 3 — CRUD UX: списки, таблицы, фильтры, массовые операции
Для каждого CRUD-раздела опиши UX-паттерны:
- list view: таблица/карточки (когда что), колонки, сортировки, sticky header
- фильтры: быстрые чипы, расширенный фильтр, сохраненные фильтры
- поиск: по полям, подсказки
- массовые действия: publish/unpublish, delete, assign tag/category, export
- bulk edit: когда нужен
- empty states: как мотивировать заполнение
- states: loading/error/permission denied
- пагинация: page-based или cursor, какие элементы управления удобнее

ШАГ 4 — Формы и редакторы
Опиши:
- структуру form layout (sections, accordions)
- обязательные поля, подсказки, inline help
- валидация: client + server, отображение ошибок согласно WCAG “Error Identification”  [oai_citation:5‡W3C](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html?utm_source=chatgpt.com)
- автосохранение черновика (draft autosave), предупреждение о несохраненных изменениях
- “предпросмотр” публичной страницы (preview) до публикации
- rich text editor: требования (markdown/WYSIWYG), вставка изображений, ссылки, embed (YouTube), таблицы
- управление slug/URL: автогенерация + ручное редактирование + проверки уникальности

ШАГ 5 — Публикация и контентный workflow
Сформируй требования:
- статусы: draft → review(optional) → published → archived
- планирование публикации (schedule)
- version history + diff (опционально)
- роли: кто может публиковать
- аудит: кто изменил и когда
- undo/restore (soft delete)

ШАГ 6 — Localization UX
Опиши модель управления переводами:
- справочник языков (add/edit/remove locale)
- для каждой сущности: вкладки языков + индикатор заполненности
- массовый отчет “missing translations”
- fallback логика: что показывать на фронте если перевода нет
- импорт/экспорт переводов (CSV/JSON) — если уместно
- запрет удаления локали, если есть опубликованный контент (или сценарий миграции)

ШАГ 7 — SEO Center (управление мета по URL)
Опиши UX раздела SEO:
- таблица URL/route: path, тип страницы, canonical, robots, title/description, og fields, status “complete”
- фильтры: только страницы без SEO, только опубликованные, по языку
- редактор SEO для URL: preview snippet (как будет в поиске), OG preview (условно)
- x-default / hreflang (если нужно показывать как справку)
- массовые операции: экспорт, шаблоны, генерация дефолтных значений
- правила валидации: длина title/description, запрет пустых, предупреждения

ШАГ 8 — Media Library / Documents
Опиши:
- загрузка (drag&drop), прогресс, ограничения по типу/размеру
- метаданные: title, alt (если изображения), tags, folder/collections
- переиспользование файла в разных сущностях
- версии/замена файла без поломки ссылок (если важно)
- права доступа: кто видит/кто может удалять

ШАГ 9 — Leads / Заявки
Опиши:
- list: фильтры по статусу, источнику, дате
- карточка заявки: данные, UTM, комментарии, назначение ответственного
- статусы обработки (new/in progress/done/spam)
- экспорт CSV
- уведомления (email/telegram) — как фича v2

ШАГ 10 — Security, RBAC, Audit
Сформируй требования:
- RBAC: роли (Owner/Admin/Editor/SEO/HR/Sales/Viewer) и матрица прав
- MFA requirement для админов (рекомендация)
- session management: timeout, logout all devices, secure cookies (как минимум требования)  [oai_citation:6‡OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html?utm_source=chatgpt.com)
- audit log: кто/что/когда (entity, field changes, ip/user agent опционально)
- ограничение опасных действий: подтверждения, “type to confirm”, “undo window”

ШАГ 11 — Accessibility (WCAG/ARIA)
Сформируй чек-лист:
- клавиатурная навигация
- focus management в модалках/диалогах
- aria-label/role для сложных компонентов (table, combobox, dialogs)  [oai_citation:7‡W3C](https://www.w3.org/WAI/ARIA/apg/?utm_source=chatgpt.com)
- тексты ошибок и подсказки в формах  [oai_citation:8‡W3C](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html?utm_source=chatgpt.com)

ШАГ 12 — Выходные артефакты (что ты должен отдать)
1) IA + sitemap админки (списком)
2) Список экранов (screen list) с назначением каждого
3) Для топ-10 экранов: описание layout + ключевые компоненты + user flow
4) Матрица ролей/прав (RBAC) (таблично)
5) Чек-листы: формы/валидация, таблицы/фильтры, локализация, SEO, безопасность, доступность
6) Рекомендации по UI kit/Design System (на что опираться: Material/другие) и какие компоненты обязательны
7) Milestones внедрения: MVP админки → v1 → v2
8) Риски и антипаттерны админок (хаос, слабый поиск, нет статусов, нет аудита, опасные удаления) + как избежать

Требования к стилю ответа:
- Максимальная конкретика, без воды.
- Везде trade-offs и почему выбранный вариант лучше для переиспользуемого движка.
- Фокус на удобство контент-менеджера и SEO-специалиста (быстрота, ясность, меньше ошибок).








------------------------------


Ты — Senior Technical Writer + API Architect, у тебя есть:
1) Доступ к коду backend-движка (FastAPI + PostgreSQL) со всеми моделями, routers и схемами.
2) Файл admin_panel_spec.md — продуктовый/UX-спек админ-панели (IA, роли, экраны, UX-паттерны).

Твоя задача — на основе:
- фактического API/схем/таблиц в коде,
- требований из admin_panel_spec.md,

подготовить СНАЧАЛА НЕ САМУ ДОКУ, а **план работ по документации** и структуру будущего API‑документа для фронтенда.

### ЧТО НУЖНО НА ВЫХОДЕ

1. **High-level план работ по документации (Work Plan)**  
   Структурированный список шагов, чтобы привести документацию к состоянию, когда по ней фронтендер может полностью реализовать админ-панель:
   - какие модули/сущности описывать (Articles, Cases, Team Members, Services, Practice Areas, FAQ, Reviews, Media, Leads, SEO, Localization, Users/Roles, Settings и т.д.);
   - в каком порядке (например: сначала foundation — auth, tenants, users, затем content, затем SEO/Localization, затем Leads/Audit);
   - какие артефакты нужны по каждому модулю:
     - OpenAPI/Swagger актуализация,
     - reference-док по эндпоинтам,
     - примеры запросов/ответов,
     - описание бизнес-логики / состояний,
     - заметки для фронта (edge cases, rate limits, ограничения).

2. **Структура будущей документации (API Documentation Outline)**  
   Скелет одного общего документа (или developer portal), в котором будет описан функционал админки С ТОЧКИ ЗРЕНИЯ ФРОНТА:
   - Разделы верхнего уровня (например):
     1) Overview (auth, tenants, common conventions, error format)
     2) Content Module (Articles, Cases, Services, FAQ, Reviews)
     3) People & Company (Team, Practice Areas, Offices, Contacts)
     4) Media Library
     5) Leads & Forms
     6) Localization
     7) SEO Center
     8) Users & RBAC
     9) Audit & Logs
     10) Settings & Integrations
   - Для КАЖДОГО раздела — подсекция **per сущность**, где обязательно будут:
     - Назначение сущности в контексте админки (кратко, опираясь на admin_panel_spec.md).
     - Список API-эндпоинтов (из кода), сгруппированных по CRUD/специализированным действиям:
       - URL, метод
       - краткое описание
       - auth требования (какие роли могут)
     - Структура запросов:
       - path params
       - query params (фильтры, сортировки, пагинация)
       - body (JSON-схема + пояснения по полям и валидации)
     - Структура ответов:
       - success (200/201) JSON-схема
       - error ответы (422, 401, 403, 404, 409 и др.)
     - Особая бизнес-логика:
       - статусные машины (Draft → Review → Published → Archived и т.п.)
       - ограничения (например: нельзя удалить язык, если на нем есть Published контент)
       - side effects (отправка email, аудита, логирование, webhooks).
     - Примеры:
       - 1–2 примерa запроса/ответа для типичных сценариев UI (list, create, update, bulk, фильтрация).

3. **Mapping “UX экраны → API” (Screen-to-API Map)**  
   Таблично/списком: для КАЖДОГО экрана админки из admin_panel_spec.md указать:
   - Название экрана (например, “Articles List”, “Article Edit”, “SEO Center Route Detail”, “Leads Kanban”, “Role Editor”)
   - Основные пользовательские действия на экране:
     - список: load list, apply filters, search, open detail, create, edit, bulk actions, preview, publish и т.д.
   - Какие конкретные backend эндпоинты задействованы для каждого действия:
     - метод + URL, например:
       - `GET /api/v1/admin/articles`
       - `GET /api/v1/admin/articles/{id}`
       - `POST /api/v1/admin/articles`
       - `PATCH /api/v1/admin/articles/{id}`
       - `POST /api/v1/admin/articles/{id}/publish`
       - `DELETE /api/v1/admin/articles/{id}` (soft delete)
   - Какие query‑параметры и фильтры используются:
     - `page`, `limit`, `search`, `status`, `ordering`, `locale` и т.д.
   - Особые моменты для фронта:
     - нужна ли client-side сортировка или только server-side;
     - есть ли rate limiting;
     - какие статусы/ошибки фронт обязан обрабатывать (например для SEO Center — 409 на конфликт canonical, 422 на валидацию meta title длины, и т.п.).

4. **Описание схем авторизации и контекста (Auth & Context Section)**  
   Отдельный раздел, где ты:
   - Опишешь текущую auth-схему: 
     - login endpoint,
     - refresh,
     - формат JWT/сессии,
     - где лежит tenant_id (в токене, в header `X-Tenant-ID` или ещё где).
   - Опишешь как фронт должен:
     - хранить токен (localStorage/cookie),
     - передавать его в запросах (Authorization header),
     - обновлять по refresh,
     - обрабатывать 401/403.
   - Опишешь модель ролей/прав:
     - какие есть роли,
     - как backend сообщает об этом (в payload токена / отдельный endpoint `/me`),
     - какие действия должны быть скрыты во фронте в зависимости от ролей (опираясь на RBAC из admin_panel_spec.md).

5. **Gap-Analysis между бекендом и UX-спеком**  
   Список мест, где:
   - В **admin_panel_spec.md** описан функционал, но в API/схемах его сейчас нет или он реализован иначе:
     - например: в спеках есть “Publishing Calendar” или “Version History/Diff”, но таких эндпоинтов нет.
   - Для каждого такого кейса:
     - кратко: что описано в UX-спеке,
     - что есть/нет в текущем backend,
     - рекомендации:
       - какие новые эндпоинты/поля нужны,
       - какие изменения в существующих endpoints потребуются.
   Это поможет PM/техлиду решить: доработать backend или скорректировать требования.

### ТРЕБОВАНИЯ К ФОРМАТУ ОТВЕТА

- Один markdown‑документ.
- Структура:
  1. Work Plan (шаги, что делать с документацией)
  2. API Documentation Outline (оглавление будущего API-дока)
  3. Screen-to-API Map (таблицы/подразделы per экран)
  4. Auth & Context section
  5. Gap Analysis (Backend vs admin_panel_spec.md)
- Максимум конкретики: никаких общих фраз «нужно описать эндпоинты», а конкретно «для Articles описать `GET /api/v1/admin/articles`, ...».
- Всё писать с прицелом, что следующий шаг — на основе этого плана написать полноценную документацию, а не перепроектировать backend.

Если тебе нужно — отдельно могу прислать сам файл admin_panel_spec.md.

