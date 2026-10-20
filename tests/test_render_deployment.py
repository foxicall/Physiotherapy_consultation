import copy
import json
import unittest

import httpx

from scripts.configure_render import (
    API_URL, REPOSITORY, SERVICE_URL, RenderError, desired_settings,
    find_service, migrate, request, validate_service,
)


def clinic_service():
    return {
        'id': 'srv-clinic123', 'type': 'web_service', 'repo': REPOSITORY,
        'branch': 'main', 'rootDir': '', 'suspended': 'not_suspended',
        'serviceDetails': {'runtime': 'python', 'url': SERVICE_URL, 'plan': 'free'},
    }


class RenderDeploymentTests(unittest.TestCase):
    def client(self, handler):
        return httpx.Client(base_url=API_URL, transport=httpx.MockTransport(handler))

    def test_discovery_matches_url_and_rechecks_repository(self):
        service = clinic_service()
        other = copy.deepcopy(service)
        other['serviceDetails']['url'] = 'https://other.onrender.com'
        def handle(req):
            if req.url.path == '/v1/services':
                return httpx.Response(200, json=[{'service': other}, {'service': service}])
            return httpx.Response(200, json=service)
        with self.client(handle) as client:
            self.assertEqual(find_service(client)['id'], service['id'])
        service['repo'] = 'https://github.com/example/other'
        with self.client(handle) as client, self.assertRaises(RenderError):
            find_service(client)

    def test_service_guards_reject_wrong_target_runtime_and_shared_build(self):
        for change in (
            {'repo': 'https://github.com/example/other'}, {'type': 'static_site'},
            {'id': '../other'}, {'suspended': 'suspended'}, {'buildSourceId': 'bld-source'},
            {'serviceDetails': {'runtime': 'docker', 'url': SERVICE_URL}},
        ):
            with self.subTest(change=change), self.assertRaises(RenderError):
                validate_service({**clinic_service(), **change})

    def test_apply_updates_only_commands_branch_root_and_health_then_deploys_commit(self):
        calls = []
        service = clinic_service()
        def handle(req):
            body = json.loads(req.content)
            calls.append((req.method, req.url.path, body))
            if req.method == 'PATCH':
                updated = copy.deepcopy(service)
                updated.update({key: value for key, value in body.items() if key != 'serviceDetails'})
                updated['serviceDetails'].update(body['serviceDetails'])
                return httpx.Response(200, json=updated)
            return httpx.Response(201, json={'id': 'dep-clinic', 'status': 'build_in_progress'})
        with self.client(handle) as client:
            self.assertEqual(migrate(client, service, 'a'*40)['id'], 'dep-clinic')
        self.assertEqual(calls, [
            ('PATCH', '/v1/services/srv-clinic123', desired_settings()),
            ('POST', '/v1/services/srv-clinic123/deploys', {'commitId': 'a'*40, 'clearCache': 'do_not_clear'}),
        ])

    def test_does_not_deploy_when_patch_is_not_confirmed(self):
        calls = []
        def handle(req):
            calls.append(req.method)
            return httpx.Response(200, json=clinic_service())
        with self.client(handle) as client, self.assertRaises(RenderError):
            migrate(client, clinic_service(), 'a'*40)
        self.assertEqual(calls, ['PATCH'])

    def test_errors_hide_response_bodies_and_network_request_details(self):
        with self.client(lambda req: httpx.Response(401, text='secret-api-key')) as client:
            with self.assertRaises(RenderError) as error:
                request(client, 'GET', 'services')
            self.assertNotIn('secret-api-key', str(error.exception))
        def failure(req):
            raise httpx.ConnectError('secret-api-key', request=req)
        with self.client(failure) as client:
            with self.assertRaises(RenderError) as error:
                request(client, 'GET', 'services')
            self.assertNotIn('secret-api-key', str(error.exception))


if __name__ == '__main__':
    unittest.main()
