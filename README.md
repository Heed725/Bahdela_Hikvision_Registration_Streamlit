# Bahdela Hikvision Registration

A mobile-friendly Streamlit app for creating or updating a Hikvision employee and registering one face and/or one fingerprint directly on a compatible Hikvision access-control terminal.

## Files

- `app.py` — Bahdela registration interface
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
