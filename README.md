# Bahdela Hikvision Registration

A mobile-friendly Streamlit app for creating or updating a Hikvision employee and registering one face and/or one fingerprint directly on a compatible Hikvision access-control terminal.

## Multi-site registration

Supported sites: **Buguruni, Puma Upanga, Puma Ocean Road, Puma Survey, India, Kibaha and Livingstone**. Device addresses are taken from the supplied multi-site report configuration.

1. Open the app and choose **Registration site** (for example **Puma Upanga**).
2. Click **Begin new registration**.
3. Enter the employee ID, names, validity dates and enrollment PIN, confirm the details, then click **Save and continue**.
4. Save a face photograph and/or capture a fingerprint at the selected site’s terminal.
5. Click **Finish and clear this session**, then choose a site for the next person.

The chosen site stays fixed throughout the registration. **Change site / start new registration** clears the current employee, input fields, uploaded photograph and completion flags. It does not delete anything already saved on a terminal. An existing employee ID updates the employee on the selected terminal only, as in the original app. Registration does not copy a person to other sites or update the separate attendance-report app’s roster.

### Configure site credentials

The example secrets file includes all seven site addresses. Enter each device password in its matching `[sites."Site name"]` table and set the shared `ENROLLMENT_PIN`. A site without a password or PIN cannot begin registration. You may override the shared PIN with `enrollment_pin` inside any site table. Site tables can also override `url`, `username`, `timeout` and `verify_tls`.

For an environment-variable deployment, use `SITE_PUMA_UPANGA_URL`, `SITE_PUMA_UPANGA_USERNAME`, `SITE_PUMA_UPANGA_PASSWORD` and optionally `SITE_PUMA_UPANGA_ENROLLMENT_PIN`; use the same naming pattern for each site. The shared `ENROLLMENT_PIN` remains available as a fallback. Never put real device passwords in source code.

Existing top-level `HIKVISION_URL` / `HIKVISION_PASSWORD` configuration works for **Buguruni only**; credentials are never reused for other sites. If that old URL belongs to a different site, move it into the correct site table before enrolling. To add another site, add a new `[sites."New site name"]` table with a URL and password.

## Files

- `app.py` — Bahdela registration interface
- `sites.py` — site addresses, per-site configuration and credential isolation
- `hikvision.py` — Hikvision ISAPI client using HTTP Digest authentication
- `requirements.txt` — Python dependencies
- `.streamlit/secrets.toml.example` — safe configuration template

## Run locally

1. Install Python 3.10 or later.
2. Open a terminal in this folder.
3. Create and activate a virtual environment.
4. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and enter the Hikvision address, administrator password, and a private enrollment PIN.
6. Start the app:

   ```bash
   streamlit run app.py
   ```

## Streamlit Community Cloud

Push the folder to a private GitHub repository. Create a Streamlit app with `app.py` as the entry point, then add the values from `.streamlit/secrets.toml.example` under **App settings → Secrets**. Never commit the real `secrets.toml` file.

## Important network requirement

The Streamlit server must be able to reach the Hikvision terminal's HTTP/HTTPS ISAPI address. A private LAN address such as `192.168.x.x` cannot normally be reached from Streamlit Community Cloud. For Cloud deployment, use a secure VPN/tunnel or run Streamlit on the same Bahdela network. Do not expose the terminal directly to the public internet.

## Device compatibility

The terminal must support Hikvision ISAPI user, face, fingerprint-capture, and fingerprint-setup endpoints. Endpoint behavior can vary by model and firmware. If the device returns `notSupport`, confirm that remote fingerprint capture and face libraries are supported and enabled.

## Security

- Keep the GitHub repository private.
- Use a strong administrator password and enrollment PIN.
- Set `HIKVISION_VERIFY_TLS = "true"` when the terminal has a trusted HTTPS certificate.
- Supervise enrollment and obtain employee consent.
- The app retains the active employee only in the Streamlit session for 10 minutes; it does not write biometric files to disk.

## Validation

Run `python -m unittest discover -s tests -v` to verify configuration isolation and the Streamlit registration workflow with mocked device responses. Tests do not contact real terminals.
