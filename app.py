from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import date
from html import escape

import streamlit as st

from hikvision import HikvisionClient, HikvisionError, response_message
from sites import Site, load_sites


st.set_page_config(
    page_title="Bahdela Hikvision Registration",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {--bahdela-maroon:#8B0000;--bahdela-gold:#D4A017;--bahdela-cream:#FFF9F2;}
      .block-container {max-width:760px;padding:1rem 1rem 5rem;}
      h1 {font-size:1.7rem!important;margin-bottom:.15rem;color:var(--bahdela-maroon)!important;}
      div[data-testid="stForm"] {
        border:1px solid rgba(128,128,128,.35);
        border-top:5px solid var(--bahdela-gold);
        border-radius:18px;padding:1rem;
        box-shadow:0 10px 26px rgba(90,0,0,.08);
      }
      .profile {
        background:var(--bahdela-cream);border:1px solid #D8C4A7;
        border-radius:15px;padding:14px 16px;margin:.5rem 0 1rem;
      }
      .profile strong {font-size:1.1rem;color:var(--bahdela-maroon);}
      .profile small {display:block;opacity:.75;margin-top:4px;}
      .step {
        display:inline-flex;align-items:center;justify-content:center;
        width:29px;height:29px;border-radius:50%;
        background:var(--bahdela-maroon);color:#fff;font-weight:750;
        margin-right:7px;border:3px solid var(--bahdela-gold);
      }
      .stButton>button,.stFormSubmitButton>button {
        min-height:48px;border-radius:12px;font-weight:700;
      }
      button[kind="primary"] {background:var(--bahdela-maroon)!important;border-color:var(--bahdela-maroon)!important;}
      @media(max-width:600px) {
        .block-container {padding:.7rem .7rem 4rem;}
        h1 {font-size:1.4rem!important;}
        div[data-testid="stForm"] {padding:.75rem;border-radius:14px;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_equal(left: str, right: str) -> bool:
    if not left or not right:
        return False
    left_digest = hashlib.sha256(left.encode()).digest()
    right_digest = hashlib.sha256(right.encode()).digest()
    return hmac.compare_digest(left_digest, right_digest)


def api_client(site: Site) -> HikvisionClient:
    return HikvisionClient(site.url, site.username, site.password, site.timeout, site.verify_tls)


def reset_registration() -> None:
    for key in list(st.session_state):
        if key in {"employee", "verified_at", "face_done", "fingerprint_done", "registration_site"} or key.startswith("reg_"):
            st.session_state.pop(key, None)


def active_employee() -> dict | None:
    employee = st.session_state.get("employee")
    if not employee:
        return None
    if (time.time() - st.session_state.get("verified_at", 0) > 600
            or employee.get("site") != st.session_state.get("registration_site")):
        reset_registration()
        return None
    return employee


st.title("Bahdela Hikvision Registration")
st.caption("Select your site, then begin a new employee registration")

try:
    secret_values = st.secrets.to_dict()
except Exception:
    secret_values = {}
sites = load_sites(secret_values, os.environ)
employee = active_employee()
site_name = st.session_state.get("registration_site")
if site_name not in sites:
    reset_registration()
    st.markdown('<h3><span class="step">1</span>Select site</h3>', unsafe_allow_html=True)
    choice = st.selectbox("Registration site", list(sites), index=None, placeholder="Choose a site…", key="site_choice")
    selected = sites.get(choice)
    if selected and not selected.ready:
        st.warning(f"{selected.name} needs a device password and enrollment PIN in Streamlit Secrets before registration can begin.")
    if st.button("Begin new registration", type="primary", use_container_width=True,
                 disabled=selected is None or not selected.ready):
        reset_registration()
        st.session_state.registration_site = selected.name
        st.rerun()
    st.info("Choose the site where the employee will use the Hikvision terminal.")
    st.stop()

site = sites[site_name]
st.info(f"Registration site: {site.name}. Employee details and biometrics will be saved to this site's terminal.")
if st.button("Change site / start new registration", use_container_width=True, on_click=reset_registration):
    st.rerun()
if not site.ready:
    st.error("This site's device password or enrollment PIN is missing. Ask the administrator to update Streamlit Secrets.")
    st.stop()

if employee is None:
    st.markdown('<h3><span class="step">2</span>Enter employee information</h3>', unsafe_allow_html=True)
    with st.form("employee_form"):
        employee_no = st.text_input("Employee ID *", key="reg_employee_id", max_chars=32, placeholder="Example: 1001")
        first_name = st.text_input("First name *", key="reg_first_name", max_chars=40)
        middle_name = st.text_input("Middle name", key="reg_middle_name", max_chars=40)
        last_name = st.text_input("Last name *", key="reg_last_name", max_chars=60)
        gender = st.selectbox("Gender", ["unspecified", "male", "female"], key="reg_gender")
        d1, d2 = st.columns(2)
        valid_from = d1.date_input("Effective from", value=date.today(), key="reg_from")
        valid_until = d2.date_input("Effective until", value=date(2036, 12, 31), key="reg_until")
        access_plan = st.number_input("Access plan template", min_value=1, max_value=255, value=1, key="reg_access_plan")
        pin = st.text_input("Enrollment PIN *", key="reg_enrollment_pin", type="password")
        confirm = st.checkbox("I confirm the information belongs to me and is correct.", key="reg_confirm")
        submitted = st.form_submit_button("Save and continue", type="primary", use_container_width=True)

    if submitted:
        employee_id = employee_no.strip()
        required_names = [first_name.strip(), last_name.strip()]
        if not employee_id or not all(required_names):
            st.error("Employee ID, first name and last name are required.")
        elif not employee_id.isalnum():
            st.error("Employee ID may contain letters and numbers only.")
        elif valid_until < valid_from:
            st.error("The end date cannot be earlier than the start date.")
        elif not confirm:
            st.error("Confirm that the information is yours and is correct.")
        elif not safe_equal(pin, site.enrollment_pin):
            st.error("Incorrect enrollment PIN.")
        else:
            full_name = " ".join(filter(None, [first_name.strip(), middle_name.strip(), last_name.strip()]))
            record = {
                "site": site.name,
                "employee_no": employee_id,
                "name": full_name,
                "gender": gender,
                "valid_from": valid_from.isoformat(),
                "valid_until": valid_until.isoformat(),
                "access_plan": int(access_plan),
            }
            try:
                client = api_client(site)
                with st.spinner("Saving employee information to the Hikvision device…"):
                    result, action = client.upsert_user(record)
                if result.ok:
                    st.session_state.employee = record
                    st.session_state.verified_at = time.time()
                    st.success(f"Employee information {action} successfully.")
                    st.rerun()
                else:
                    st.error(f"Employee information was not saved: {response_message(result)}")
            except HikvisionError as exc:
                st.error(str(exc))
    st.info("For security, registration should be supervised by an authorized Bahdela administrator.")
    st.stop()

st.markdown(
    f"""
    <div class="profile"><strong>{escape(employee['employee_no'])} · {escape(employee['name'])}</strong>
    <small>Site: {escape(employee['site'])} · Valid until {escape(employee['valid_until'])}</small></div>
    """,
    unsafe_allow_html=True,
)

def change_employee() -> None:
    current_site = st.session_state.registration_site
    reset_registration()
    st.session_state.registration_site = current_site


if st.button("Change employee information", use_container_width=True, on_click=change_employee):
    st.rerun()

client = api_client(site)
st.markdown('<h3><span class="step">3</span>Add biometric information</h3>', unsafe_allow_html=True)
face_tab, fingerprint_tab = st.tabs(["Face registration", "Fingerprint registration"])

with face_tab:
    st.write("Use a clear, front-facing photograph with only one person visible.")
    camera_photo = st.camera_input("Take face photograph", key="reg_camera")
    uploaded_photo = st.file_uploader("Or upload a JPEG", type=["jpg", "jpeg"], key="reg_upload")
    photo = camera_photo or uploaded_photo
    if st.button("Save my face", type="primary", use_container_width=True, disabled=photo is None):
        try:
            filename = getattr(photo, "name", None) or "face.jpg"
            with st.spinner("Registering face on the Hikvision device…"):
                result = client.upload_face(employee["employee_no"], photo.getvalue(), filename)
            if result.ok:
                st.session_state.face_done = True
                st.success("Face registered successfully.")
            else:
                st.error(f"Face registration failed: {response_message(result)}")
        except HikvisionError as exc:
            st.error(str(exc))

with fingerprint_tab:
    st.warning("Stand beside the Hikvision terminal. One fingerprint will be captured in slot 1.")
    capture_status = st.empty()
    if st.button("Capture one fingerprint", type="primary", use_container_width=True):
        try:
            capture_status.warning("Place one finger on the Hikvision sensor and keep it still…")
            with st.spinner("Waiting for the terminal sensor…"):
                captured = client.capture_fingerprint(1)
            if not captured.data:
                capture_status.empty()
                st.error(captured.message or "The device returned no fingerprint data. Try again.")
            else:
                capture_status.success("Fingerprint captured. Saving it to the employee…")
                if captured.quality is not None:
                    st.metric("Fingerprint quality", f"{captured.quality}%")
                result = client.apply_fingerprint(employee["employee_no"], captured.data, 1)
                if result.ok:
                    st.session_state.fingerprint_done = True
                    capture_status.success("Fingerprint captured and registered successfully.")
                else:
                    capture_status.empty()
                    st.error(f"Fingerprint registration failed: {response_message(result)}")
        except HikvisionError as exc:
            capture_status.empty()
            st.error(str(exc))

if st.session_state.get("face_done") or st.session_state.get("fingerprint_done"):
    st.divider()
    st.success("Registration is saved. You may add the other biometric method or finish.")
    if st.button("Finish and clear this session", use_container_width=True, on_click=reset_registration):
        st.rerun()

st.caption("The application does not permanently store face images or fingerprint templates. They are sent directly to the configured Hikvision terminal.")
