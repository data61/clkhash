import requests


def project_upload_clks(server, project, apikey, clk_data):
    response = requests.post(
        '{}/api/v1/projects/{}/clks'.format(server, project),
        data=clk_data,
        headers={
            "Authorization": apikey,
            'content-type': 'application/json'
        }
    )
    return response


def run_get_status(server, project, run, apikey):
    response = requests.get(
        '{}/api/v1/projects/{}/runs/{}/status'.format(server, project, run),
        headers={"Authorization": apikey}
    )
    assert response.status_code == 200
    return response.json()


def run_get_result(server, project, run, apikey):
    return requests.get(
        '{}/api/v1/projects/{}/runs/{}/result'.format(server, project, run),
        headers={"Authorization": apikey}
    )
