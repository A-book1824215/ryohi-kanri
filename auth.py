import os
import streamlit as st
from datetime import datetime, timedelta
from db import is_password_configured, verify_password, set_password

_SESSION_HOURS = 8      # セッション有効時間
_MAX_FAILURES = 3       # ログイン失敗の上限回数
_LOCKOUT_MINUTES = 30   # ロック時間（分）


def require_auth():
    """管理ページの先頭で呼ぶ。未認証なら画面を乗っ取ってst.stop()する。"""
    if not is_password_configured():
        _show_setup()
        st.stop()

    if not _is_session_valid():
        _show_login()
        st.stop()

    _show_logout_button()


def _is_session_valid() -> bool:
    if not st.session_state.get("authenticated"):
        return False
    login_time: datetime = st.session_state.get("login_time")
    if not login_time:
        return False
    if datetime.now() - login_time > timedelta(hours=_SESSION_HOURS):
        st.session_state.clear()
        return False
    return True


def _is_locked_out() -> bool:
    lockout_until: datetime = st.session_state.get("lockout_until")
    if lockout_until and datetime.now() < lockout_until:
        return True
    return False


def _show_setup():
    st.title("初期設定")
    st.info("管理者パスワードを設定してください。このページは初回のみ表示されます。")
    with st.form("setup_form"):
        pw1 = st.text_input("パスワード（8文字以上）", type="password")
        pw2 = st.text_input("パスワード（確認）", type="password")
        submitted = st.form_submit_button("設定する", use_container_width=True)
    if submitted:
        err = _validate_password(pw1, pw2)
        if err:
            st.error(err)
        else:
            set_password(pw1)
            st.success("パスワードを設定しました。")
            st.rerun()


def _show_login():
    st.title("管理者ログイン")

    if os.getenv("DEMO_MODE", "").lower() == "true":
        st.info("デモ用パスワード: **demo1234**")

    if _is_locked_out():
        until: datetime = st.session_state["lockout_until"]
        remaining = int((until - datetime.now()).total_seconds() / 60) + 1
        st.error(f"ログイン試行が{_MAX_FAILURES}回失敗しました。{remaining}分後に再試行してください。")
        st.stop()

    with st.form("login_form"):
        pw = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン", use_container_width=True)

    if submitted:
        if verify_password(pw):
            st.session_state["authenticated"] = True
            st.session_state["login_time"] = datetime.now()
            st.session_state.pop("fail_count", None)
            st.session_state.pop("lockout_until", None)
            st.rerun()
        else:
            count = st.session_state.get("fail_count", 0) + 1
            st.session_state["fail_count"] = count
            remaining = _MAX_FAILURES - count
            if count >= _MAX_FAILURES:
                st.session_state["lockout_until"] = datetime.now() + timedelta(minutes=_LOCKOUT_MINUTES)
                st.error(f"ログインに{_MAX_FAILURES}回失敗しました。{_LOCKOUT_MINUTES}分間ロックします。")
            else:
                st.error(f"パスワードが違います。（あと{remaining}回失敗するとロックされます）")


def _show_logout_button():
    with st.sidebar:
        st.divider()
        login_time: datetime = st.session_state.get("login_time")
        if login_time:
            st.caption(f"ログイン: {login_time.strftime('%H:%M')}")
        if st.button("ログアウト", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def show_change_password():
    """設定ページ等に埋め込むパスワード変更フォーム。"""
    with st.expander("パスワード変更", icon="🔑"):
        with st.form("change_pw_form"):
            current = st.text_input("現在のパスワード", type="password")
            new1 = st.text_input("新しいパスワード（8文字以上）", type="password")
            new2 = st.text_input("新しいパスワード（確認）", type="password")
            submitted = st.form_submit_button("変更する")
        if submitted:
            if not verify_password(current):
                st.error("現在のパスワードが違います。")
            else:
                err = _validate_password(new1, new2)
                if err:
                    st.error(err)
                else:
                    set_password(new1)
                    st.success("パスワードを変更しました。")


def _validate_password(pw1: str, pw2: str) -> str:
    """問題があればエラーメッセージを返す。なければ空文字。"""
    if len(pw1) < 8:
        return "パスワードは8文字以上にしてください。"
    if pw1 != pw2:
        return "パスワードが一致しません。"
    return ""
