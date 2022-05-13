import os
import pytest
import responses
import json

from unittest.mock import patch
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from pytz import UTC, timezone as pytz_timezone, UnknownTimeZoneError

from django.core.files.storage import FileSystemStorage
from django.conf import settings

from baserow.core.user_files.models import UserFile
from baserow.core.utils import Progress
from baserow.core.exceptions import UserNotInGroup
from baserow.contrib.database.fields.models import TextField
from baserow.contrib.database.airtable.constants import (
    AIRTABLE_EXPORT_JOB_DOWNLOADING_PENDING,
)
from baserow.contrib.database.airtable.exceptions import (
    AirtableShareIsNotABase,
    AirtableImportJobDoesNotExist,
    AirtableImportJobAlreadyRunning,
)
from baserow.contrib.database.airtable.models import AirtableImportJob
from baserow.contrib.database.airtable.handler import AirtableHandler


@pytest.mark.django_db
@responses.activate
def test_fetch_publicly_shared_base():
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    path = os.path.join(base_path, "airtable_base.html")

    with open(path, "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/shrXxmp0WmqsTkFWTzv",
            status=200,
            body=file,
            headers={"Set-Cookie": "brw=test;"},
        )

        request_id, init_data, cookies = AirtableHandler.fetch_publicly_shared_base(
            "shrXxmp0WmqsTkFWTzv"
        )
        assert request_id == "req8wbZoh7Be65osz"
        assert init_data["pageLoadId"] == "pglUrFAGTNpbxUymM"
        assert cookies["brw"] == "test"


@pytest.mark.django_db
@responses.activate
def test_fetch_table():
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    path = os.path.join(base_path, "airtable_base.html")
    application_response_path = os.path.join(base_path, "airtable_application.json")
    table_response_path = os.path.join(base_path, "airtable_table.json")

    with open(path, "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/shrXxmp0WmqsTkFWTzv",
            status=200,
            body=file,
            headers={"Set-Cookie": "brw=test;"},
        )
        request_id, init_data, cookies = AirtableHandler.fetch_publicly_shared_base(
            "shrXxmp0WmqsTkFWTzv"
        )

    cookies = {
        "brw": "brw",
        "__Host-airtable-session": "__Host-airtable-session",
        "__Host-airtable-session.sig": "__Host-airtable-session.sig",
        "AWSELB": "AWSELB",
        "AWSELBCORS": "AWSELBCORS",
    }

    with open(application_response_path, "rb") as application_response_file:
        responses.add(
            responses.GET,
            "https://airtable.com/v0.3/application/appZkaH3aWX3ZjT3b/read",
            status=200,
            body=application_response_file,
        )
        application_response = AirtableHandler.fetch_table_data(
            "tblRpq315qnnIcg5IjI",
            init_data,
            request_id,
            cookies,
            fetch_application_structure=True,
            stream=False,
        )

    with open(table_response_path, "rb") as table_response_file:
        responses.add(
            responses.GET,
            "https://airtable.com/v0.3/table/tbl7glLIGtH8C8zGCzb/readData",
            status=200,
            body=table_response_file,
        )
        table_response = AirtableHandler.fetch_table_data(
            "tbl7glLIGtH8C8zGCzb",
            init_data,
            request_id,
            cookies,
            fetch_application_structure=False,
            stream=False,
        )

    assert (
        application_response.json()["data"]["tableSchemas"][0]["id"]
        == "tblRpq315qnnIcg5IjI"
    )
    assert table_response.json()["data"]["id"] == "tbl7glLIGtH8C8zGCzb"


@pytest.mark.django_db
@responses.activate
def test_extract_schema():
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    user_table_path = os.path.join(base_path, "airtable_application.json")
    data_table_path = os.path.join(base_path, "airtable_table.json")
    user_table_json = json.loads(Path(user_table_path).read_text())
    data_table_json = json.loads(Path(data_table_path).read_text())

    schema, tables = AirtableHandler.extract_schema([user_table_json, data_table_json])

    assert "tableDatas" not in schema
    assert len(schema["tableSchemas"]) == 2
    assert schema["tableSchemas"][0]["id"] == "tblRpq315qnnIcg5IjI"
    assert schema["tableSchemas"][1]["id"] == "tbl7glLIGtH8C8zGCzb"
    assert tables["tblRpq315qnnIcg5IjI"]["id"] == "tblRpq315qnnIcg5IjI"
    assert tables["tbl7glLIGtH8C8zGCzb"]["id"] == "tbl7glLIGtH8C8zGCzb"


@pytest.mark.django_db
@responses.activate
def test_to_baserow_database_export():
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    path = os.path.join(base_path, "airtable_base.html")
    user_table_path = os.path.join(base_path, "airtable_application.json")
    data_table_path = os.path.join(base_path, "airtable_table.json")
    user_table_json = json.loads(Path(user_table_path).read_text())
    data_table_json = json.loads(Path(data_table_path).read_text())

    with open(os.path.join(base_path, "file-sample.txt"), "rb") as file:
        responses.add(
            responses.GET,
            "https://dl.airtable.com/.attachments/70e50b90fb83997d25e64937979b6b5b/f3f62d23/file-sample.txt",
            status=200,
            body=file.read(),
        )

    with open(os.path.join(base_path, "file-sample_500kB.doc"), "rb") as file:
        responses.add(
            responses.GET,
            "https://dl.airtable.com/.attachments/e93dc201ce27080d9ad9df5775527d09/93e85b28/file-sample_500kB.doc",
            status=200,
            body=file.read(),
        )

    with open(os.path.join(base_path, "file_example_JPG_100kB.jpg"), "rb") as file:
        responses.add(
            responses.GET,
            "https://dl.airtable.com/.attachments/025730a04991a764bb3ace6d524b45e5/bd61798a/file_example_JPG_100kB.jpg",
            status=200,
            body=file.read(),
        )

    with open(path, "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/shrXxmp0WmqsTkFWTzv",
            status=200,
            body=file.read(),
            headers={"Set-Cookie": "brw=test;"},
        )
        request_id, init_data, cookies = AirtableHandler.fetch_publicly_shared_base(
            "shrXxmp0WmqsTkFWTzv"
        )

    schema, tables = AirtableHandler.extract_schema([user_table_json, data_table_json])
    baserow_database_export, files_buffer = AirtableHandler.to_baserow_database_export(
        init_data, schema, tables, pytz_timezone("Europe/Amsterdam")
    )

    with ZipFile(files_buffer, "r", ZIP_DEFLATED, False) as zip_file:
        assert len(zip_file.infolist()) == 3
        assert (
            zip_file.read(
                "70e50b90fb83997d25e64937979b6b5b_f3f62d23_file-sample" ".txt"
            )
            == b"test\n"
        )

    assert baserow_database_export["id"] == 1
    assert baserow_database_export["name"] == "Test"
    assert baserow_database_export["order"] == 1
    assert baserow_database_export["type"] == "database"
    assert len(baserow_database_export["tables"]) == 2

    assert baserow_database_export["tables"][0]["id"] == "tblRpq315qnnIcg5IjI"
    assert baserow_database_export["tables"][0]["name"] == "Users"
    assert baserow_database_export["tables"][0]["order"] == 0
    assert len(baserow_database_export["tables"][0]["fields"]) == 4

    assert baserow_database_export["tables"][1]["id"] == "tbl7glLIGtH8C8zGCzb"
    assert baserow_database_export["tables"][1]["name"] == "Data"
    assert baserow_database_export["tables"][1]["order"] == 1
    assert len(baserow_database_export["tables"][1]["fields"]) == 23

    # We don't have to check all the fields and rows, just a single one, because we have
    # separate tests for mapping the Airtable fields and values to Baserow.
    assert (
        baserow_database_export["tables"][0]["fields"][0]["id"] == "fldG9y88Zw7q7u4Z7i4"
    )
    assert baserow_database_export["tables"][0]["fields"][0] == {
        "type": "text",
        "id": "fldG9y88Zw7q7u4Z7i4",
        "name": "Name",
        "order": 0,
        "primary": True,
        "text_default": "",
    }
    assert baserow_database_export["tables"][0]["fields"][1] == {
        "type": "email",
        "id": "fldB7wkyR0buF1sRF9O",
        "name": "Email",
        "order": 1,
        "primary": False,
    }
    assert len(baserow_database_export["tables"][0]["rows"]) == 3
    assert baserow_database_export["tables"][0]["rows"][0] == {
        "id": 1,
        "order": "1.00000000000000000000",
        "created_on": "2022-01-16T17:59:13+00:00",
        "updated_on": None,
        "field_fldB7wkyR0buF1sRF9O": "bram@email.com",
        "field_fldG9y88Zw7q7u4Z7i4": "Bram 1",
        "field_fldFh5wIL430N62LN6t": [1],
        "field_fldZBmr4L45mhjILhlA": "1",
    }
    assert baserow_database_export["tables"][0]["rows"][1] == {
        "id": 2,
        "order": "2.00000000000000000000",
        "created_on": "2022-01-16T17:59:13+00:00",
        "updated_on": None,
        "field_fldB7wkyR0buF1sRF9O": "bram@test.nl",
        "field_fldG9y88Zw7q7u4Z7i4": "Bram 2",
        "field_fldFh5wIL430N62LN6t": [2, 3, 1],
        "field_fldZBmr4L45mhjILhlA": "2",
    }
    assert baserow_database_export["tables"][0]["rows"][2] == {
        "id": 3,
        "order": "3.00000000000000000000",
        "created_on": "2022-01-17T17:59:13+00:00",
        "updated_on": None,
    }
    assert (
        baserow_database_export["tables"][1]["rows"][0]["field_fldEB5dp0mNjVZu0VJI"]
        == "2022-01-21T01:00:00+00:00"
    )
    assert baserow_database_export["tables"][0]["views"] == [
        {
            "id": 1,
            "type": "grid",
            "name": "Grid",
            "order": 1,
            "filter_type": "AND",
            "filters_disabled": False,
            "filters": [],
            "sortings": [],
            "decorations": [],
            "public": False,
            "field_options": [],
        }
    ]


@pytest.mark.django_db
@responses.activate
def test_to_baserow_database_export_without_primary_value():
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    path = os.path.join(base_path, "airtable_base.html")
    user_table_path = os.path.join(base_path, "airtable_application.json")
    user_table_json = json.loads(Path(user_table_path).read_text())

    # Remove the data table because we don't need that one.
    del user_table_json["data"]["tableSchemas"][1]
    user_table_json["data"]["tableDatas"][0]["rows"] = []

    # Rename the primary column so that we depend on the fallback in the migrations.
    user_table_json["data"]["tableSchemas"][0][
        "primaryColumnId"
    ] = "fldG9y88Zw7q7u4Z7i4_unknown"

    with open(path, "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/shrXxmp0WmqsTkFWTzv",
            status=200,
            body=file.read(),
            headers={"Set-Cookie": "brw=test;"},
        )
        request_id, init_data, cookies = AirtableHandler.fetch_publicly_shared_base(
            "shrXxmp0WmqsTkFWTzv"
        )

    schema, tables = AirtableHandler.extract_schema(deepcopy([user_table_json]))
    baserow_database_export, files_buffer = AirtableHandler.to_baserow_database_export(
        init_data, schema, tables, UTC
    )
    assert baserow_database_export["tables"][0]["fields"][0]["primary"] is True

    user_table_json["data"]["tableSchemas"][0]["columns"] = []
    schema, tables = AirtableHandler.extract_schema(deepcopy([user_table_json]))
    baserow_database_export, files_buffer = AirtableHandler.to_baserow_database_export(
        init_data, schema, tables, UTC
    )
    assert baserow_database_export["tables"][0]["fields"] == [
        {
            "type": "text",
            "id": "primary_field",
            "name": "Primary field (auto created)",
            "order": 32767,
            "primary": True,
            "text_default": "",
        }
    ]


@pytest.mark.django_db
@responses.activate
def test_import_from_airtable_to_group(data_fixture, tmpdir):
    group = data_fixture.create_group()
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    storage = FileSystemStorage(location=(str(tmpdir)), base_url="http://localhost")

    with open(os.path.join(base_path, "file-sample.txt"), "rb") as file:
        responses.add(
            responses.GET,
            "https://dl.airtable.com/.attachments/70e50b90fb83997d25e64937979b6b5b/f3f62d23/file-sample.txt",
            status=200,
            body=file.read(),
        )

    with open(os.path.join(base_path, "file-sample_500kB.doc"), "rb") as file:
        responses.add(
            responses.GET,
            "https://dl.airtable.com/.attachments/e93dc201ce27080d9ad9df5775527d09/93e85b28/file-sample_500kB.doc",
            status=200,
            body=file.read(),
        )

    with open(os.path.join(base_path, "file_example_JPG_100kB.jpg"), "rb") as file:
        responses.add(
            responses.GET,
            "https://dl.airtable.com/.attachments/025730a04991a764bb3ace6d524b45e5/bd61798a/file_example_JPG_100kB.jpg",
            status=200,
            body=file.read(),
        )

    with open(os.path.join(base_path, "airtable_base.html"), "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/shrXxmp0WmqsTkFWTzv",
            status=200,
            body=file.read(),
            headers={"Set-Cookie": "brw=test;"},
        )

    with open(os.path.join(base_path, "airtable_application.json"), "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/v0.3/application/appZkaH3aWX3ZjT3b/read",
            status=200,
            body=file.read(),
        )

    with open(os.path.join(base_path, "airtable_table.json"), "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/v0.3/table/tbl7glLIGtH8C8zGCzb/readData",
            status=200,
            body=file.read(),
        )

    progress = Progress(1000)
    databases, id_mapping = AirtableHandler.import_from_airtable_to_group(
        group,
        "shrXxmp0WmqsTkFWTzv",
        timezone=UTC,
        storage=storage,
        progress_builder=progress.create_child_builder(represents_progress=1000),
    )

    assert progress.progress == progress.total
    assert UserFile.objects.all().count() == 3
    file_path = tmpdir.join("user_files", UserFile.objects.all()[0].name)
    assert file_path.isfile()
    assert file_path.open().read() == "test\n"

    database = databases[0]

    assert database.name == "Test"
    all_tables = database.table_set.all()
    assert len(all_tables) == 2

    assert all_tables[0].name == "Users"
    assert all_tables[1].name == "Data"

    user_fields = all_tables[0].field_set.all()
    assert len(user_fields) == 4

    assert user_fields[0].name == "Name"
    assert isinstance(user_fields[0].specific, TextField)

    user_model = all_tables[0].get_model(attribute_names=True)
    row_0, row_1, _ = user_model.objects.all()
    assert row_0.id == 1
    assert str(row_0.order) == "1.00000000000000000000"
    assert row_0.name == "Bram 1"
    assert row_0.email == "bram@email.com"
    assert str(row_0.number) == "1"
    assert [r.id for r in row_0.data.all()] == [1]

    data_model = all_tables[1].get_model(attribute_names=True)
    row_0, row_1, *_ = data_model.objects.all()
    assert row_0.checkbox is True
    assert row_1.checkbox is False


@pytest.mark.django_db
@responses.activate
def test_import_unsupported_publicly_shared_view(data_fixture, tmpdir):
    group = data_fixture.create_group()
    base_path = os.path.join(settings.BASE_DIR, "../../../tests/airtable_responses")
    storage = FileSystemStorage(location=(str(tmpdir)), base_url="http://localhost")

    with open(os.path.join(base_path, "airtable_view.html"), "rb") as file:
        responses.add(
            responses.GET,
            "https://airtable.com/shrXxmp0WmqsTkFWTzv",
            status=200,
            body=file.read(),
            headers={"Set-Cookie": "brw=test;"},
        )

    with pytest.raises(AirtableShareIsNotABase):
        AirtableHandler.import_from_airtable_to_group(
            group, "shrXxmp0WmqsTkFWTzv", timezone=UTC, storage=storage
        )


@pytest.mark.django_db(transaction=True)
@responses.activate
@patch("baserow.contrib.database.airtable.handler.run_import_from_airtable")
def test_create_and_start_airtable_import_job(
    mock_run_import_from_airtable, data_fixture
):
    user = data_fixture.create_user()
    group = data_fixture.create_group(user=user)
    group_2 = data_fixture.create_group()

    with pytest.raises(UserNotInGroup):
        AirtableHandler.create_and_start_airtable_import_job(user, group_2, "test")

    job = AirtableHandler.create_and_start_airtable_import_job(user, group, "test")
    assert job.user_id == user.id
    assert job.group_id == group.id
    assert job.airtable_share_id == "test"
    assert job.progress_percentage == 0
    assert job.timezone is None
    assert job.state == "pending"
    assert job.error == ""

    mock_run_import_from_airtable.delay.assert_called_once()
    args = mock_run_import_from_airtable.delay.call_args
    assert args[0][0] == job.id

    job.delete()
    job = AirtableHandler.create_and_start_airtable_import_job(
        user, group, "test", timezone="Europe/Amsterdam"
    )
    assert job.timezone == "Europe/Amsterdam"


@pytest.mark.django_db(transaction=True)
@responses.activate
@patch("baserow.contrib.database.airtable.handler.run_import_from_airtable")
def test_create_and_start_airtable_import_job_with_timezone(
    mock_run_import_from_airtable, data_fixture
):
    user = data_fixture.create_user()
    group = data_fixture.create_group(user=user)

    with pytest.raises(UnknownTimeZoneError):
        AirtableHandler.create_and_start_airtable_import_job(
            user, group, "test", timezone="UNKNOWN"
        )

    assert AirtableImportJob.objects.all().count() == 0

    job = AirtableHandler.create_and_start_airtable_import_job(
        user, group, "test", timezone="Europe/Amsterdam"
    )
    assert job.timezone == "Europe/Amsterdam"


@pytest.mark.django_db
@responses.activate
def test_create_and_start_airtable_import_job_while_other_job_is_running(data_fixture):
    user = data_fixture.create_user()
    group = data_fixture.create_group(user=user)
    data_fixture.create_airtable_import_job(
        user=user, state=AIRTABLE_EXPORT_JOB_DOWNLOADING_PENDING
    )

    with pytest.raises(AirtableImportJobAlreadyRunning):
        AirtableHandler.create_and_start_airtable_import_job(user, group, "test")


@pytest.mark.django_db
def test_get_airtable_import_job(data_fixture):
    user = data_fixture.create_user()
    job_1 = data_fixture.create_airtable_import_job(user=user)
    job_2 = data_fixture.create_airtable_import_job()

    with pytest.raises(AirtableImportJobDoesNotExist):
        AirtableHandler.get_airtable_import_job(user, job_2.id)

    job = AirtableHandler.get_airtable_import_job(user, job_1.id)
    assert isinstance(job, AirtableImportJob)
    assert job.id == job_1.id
