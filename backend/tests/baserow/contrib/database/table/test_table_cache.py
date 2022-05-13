from unittest.mock import patch, call

import pytest
from baserow.contrib.database.table.cache import (
    invalidate_table_in_model_cache,
    get_latest_cached_model_field_attrs,
)


@pytest.mark.django_db
def test_changing_link_row_field_invalidates_both_tables(data_fixture):
    unrelated_table = data_fixture.create_database_table()
    table_a, table_b, link_field = data_fixture.create_two_linked_tables()
    table_a.get_model()
    table_b.get_model()
    unrelated_table.get_model()

    assert get_latest_cached_model_field_attrs(table_a.id) is not None
    assert get_latest_cached_model_field_attrs(table_b.id) is not None
    assert get_latest_cached_model_field_attrs(unrelated_table.id) is not None

    link_field.save()

    assert get_latest_cached_model_field_attrs(table_a.id) is None
    assert get_latest_cached_model_field_attrs(table_b.id) is None
    assert get_latest_cached_model_field_attrs(unrelated_table.id) is not None


@pytest.mark.django_db
@patch("baserow.contrib.database.table.cache.generated_models_cache")
def test_invalidating_the_cache_clears_all_versions_keys(patched_model_cache):
    invalidate_table_in_model_cache(1, invalidate_related_tables=True)

    assert call.delete_pattern("full_table_model_1_*") in patched_model_cache.mock_calls


@pytest.mark.django_db
def test_invalidating_related_table_then_cache_clears_all_versions_keys(data_fixture):
    table_a, table_b, link_field = data_fixture.create_two_linked_tables()

    with patch(
        "baserow.contrib.database.table.cache.generated_models_cache.delete_pattern",
        return_value=None,
        create=True,
    ) as patched_deleted_pattern:
        invalidate_table_in_model_cache(table_a.id, invalidate_related_tables=True)

        assert patched_deleted_pattern.mock_calls == [
            call(f"full_table_model_{table_b.id}_*"),
            call(f"full_table_model_{table_a.id}_*"),
        ]


@pytest.mark.django_db
def test_deleting_field_removes_tables_generated_model_cache_entry(data_fixture):
    field = data_fixture.create_text_field()
    field.table.get_model()

    assert get_latest_cached_model_field_attrs(field.table_id) is not None

    field.delete()

    assert get_latest_cached_model_field_attrs(field.table_id) is None


@pytest.mark.django_db
def test_deleting_table_removes_generated_model_cache_entry(data_fixture):
    table = data_fixture.create_database_table()
    table.get_model()

    assert get_latest_cached_model_field_attrs(table.id) is not None

    table.delete()

    assert get_latest_cached_model_field_attrs(table.id) is None


@pytest.mark.django_db
def test_deleting_tables_database_removes_generated_model_cache_entry(data_fixture):
    table = data_fixture.create_database_table()
    table.get_model()

    assert get_latest_cached_model_field_attrs(table.id) is not None

    table.database.delete()

    assert get_latest_cached_model_field_attrs(table.id) is None


@pytest.mark.django_db
def test_deleting_tables_group_removes_generated_model_cache_entry(data_fixture):
    table = data_fixture.create_database_table()
    table.get_model()

    assert get_latest_cached_model_field_attrs(table.id) is not None

    table.database.group.delete()

    assert get_latest_cached_model_field_attrs(table.id) is None
