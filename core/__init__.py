# core/__init__.py
from .database import get_db, is_demo_mode, db_select, db_insert, db_update, db_upsert, db_delete
from .auth import (
    authenticate, login, logout, is_authenticated,
    get_current_user, get_current_role,
    is_super, is_editor, is_viewer,
    require_login, require_editor, require_super,
    login_ui
)
from .session import (
    init_session, get_session, set_session, update_session,
    clear_session_key, clear_solver_state, increment_cache_version,
    get_current_branch_id, set_current_branch, get_current_branch_name,
    get_language, set_language, get_theme, set_theme, toggle_theme,
    get_current_page, set_current_page,
    get_demo_data, set_demo_data, add_demo_data, update_demo_data, delete_demo_data
)
