import time
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from hikvision import ApiResult, CapturedFingerprint
from sites import DEFAULT_SITES, load_sites


class SiteConfigTests(unittest.TestCase):
    def test_seven_sites_and_no_cross_site_password_fallback(self):
        sites = load_sites({'HIKVISION_URL': 'http://old-terminal',
                            'HIKVISION_PASSWORD': 'legacy', 'ENROLLMENT_PIN': 'pin'}, {})
        self.assertEqual(len(sites), 7)
        self.assertTrue(sites['Buguruni'].ready)
        self.assertEqual(sites['Buguruni'].url, 'http://old-terminal')
        for name, site in sites.items():
            if name != 'Buguruni':
                self.assertFalse(site.ready)
                self.assertEqual(site.password, '')

    def test_site_overrides_environment_and_additional_site(self):
        sites = load_sites({'ENROLLMENT_PIN': 'shared', 'sites': {
            'Puma Upanga': {'password': 'upanga', 'enrollment_pin': 'private'},
            'New site': {'url': 'https://new-terminal', 'password': 'new'},
        }}, {'SITE_INDIA_PASSWORD': 'india', 'SITE_INDIA_TIMEOUT': 'bad'})
        self.assertEqual(sites['Puma Upanga'].enrollment_pin, 'private')
        self.assertEqual(sites['India'].password, 'india')
        self.assertEqual(sites['India'].timeout, 45)
        self.assertTrue(sites['New site'].ready)


class RegistrationTests(unittest.TestCase):
    def app(self, configured=True):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        if configured:
            app.secrets['ENROLLMENT_PIN'] = 'test-pin'
            app.secrets['sites'] = {name: {'password': 'test-password'} for name in DEFAULT_SITES}
        app.run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(button for button in app.button if button.label == label)

    def begin(self, app, site):
        app.selectbox(key='site_choice').select(site).run()
        self.button(app, 'Begin new registration').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['registration_site'], site)

    def fill(self, app, pin='test-pin'):
        app.text_input(key='reg_employee_id').input('1001')
        app.text_input(key='reg_first_name').input('Test')
        app.text_input(key='reg_last_name').input('Person')
        app.text_input(key='reg_enrollment_pin').input(pin)
        app.checkbox(key='reg_confirm').check()

    def test_site_choice_required_and_unconfigured_site_disabled(self):
        app = self.app(False)
        self.assertTrue(self.button(app, 'Begin new registration').disabled)
        app.selectbox(key='site_choice').select('Puma Upanga').run()
        self.assertTrue(self.button(app, 'Begin new registration').disabled)
        self.assertTrue(app.warning)
        self.assertEqual(len(app.text_input), 0)

    def test_employee_and_fingerprint_route_to_each_selected_site(self):
        routes = []

        def save(client, record):
            routes.append(('employee', client.base_url, record['site']))
            return ApiResult(True, 200, {}), 'created'

        def capture(client, slot):
            routes.append(('capture', client.base_url, slot))
            return CapturedFingerprint('mock-template', 90)

        def apply(client, employee, data, slot):
            routes.append(('fingerprint', client.base_url, employee))
            return ApiResult(True, 200, {})

        with patch('hikvision.HikvisionClient.upsert_user', save), \
             patch('hikvision.HikvisionClient.capture_fingerprint', capture), \
             patch('hikvision.HikvisionClient.apply_fingerprint', apply):
            app = self.app()
            for site, config in DEFAULT_SITES.items():
                self.begin(app, site)
                self.fill(app)
                self.button(app, 'Save and continue').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['employee']['site'], site)
                self.button(app, 'Capture one fingerprint').click().run()
                self.assertFalse(app.exception)
                self.assertTrue(app.session_state['fingerprint_done'])
                self.assertEqual([route[1] for route in routes[-3:]], [config['url']] * 3)
                self.button(app, 'Finish and clear this session').click().run()
                self.assertFalse(app.exception)
                self.assertNotIn('employee', app.session_state)
                self.assertNotIn('fingerprint_done', app.session_state)
                self.assertEqual(len(app.text_input), 0)

    def test_change_site_clears_form_and_wrong_pin_prevents_device_calls(self):
        app = self.app()
        self.begin(app, 'Buguruni')
        self.fill(app, 'wrong-pin')
        with patch('hikvision.HikvisionClient.upsert_user') as save:
            self.button(app, 'Save and continue').click().run()
            save.assert_not_called()
        self.assertFalse(app.exception)
        self.assertIn('Incorrect enrollment PIN.', [error.value for error in app.error])
        self.button(app, 'Change site / start new registration').click().run()
        self.begin(app, 'Puma Survey')
        self.assertEqual(app.text_input(key='reg_employee_id').value, '')
        self.assertEqual(app.text_input(key='reg_enrollment_pin').value, '')
        self.assertFalse(app.checkbox(key='reg_confirm').value)

    def test_expired_employee_returns_to_site_selection(self):
        app = self.app()
        app.session_state['registration_site'] = 'India'
        app.session_state['employee'] = {'site': 'India'}
        app.session_state['verified_at'] = time.time() - 601
        app.session_state['face_done'] = True
        app.run()
        self.assertFalse(app.exception)
        self.assertNotIn('employee', app.session_state)
        self.assertNotIn('face_done', app.session_state)
        self.assertEqual(len(app.text_input), 0)


if __name__ == '__main__':
    unittest.main()
