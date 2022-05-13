from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


ERROR_KANBAN_DOES_NOT_EXIST = (
    "ERROR_KANBAN_DOES_NOT_EXIST",
    HTTP_404_NOT_FOUND,
    "The requested kanban view does not exist.",
)
ERROR_KANBAN_VIEW_HAS_NO_SINGLE_SELECT_FIELD = (
    "ERROR_KANBAN_VIEW_HAS_NO_SINGLE_SELECT_FIELD",
    HTTP_400_BAD_REQUEST,
    "The requested kanban view does not have a single select option field.",
)
ERROR_INVALID_SELECT_OPTION_PARAMETER = (
    "ERROR_INVALID_SELECT_OPTION_PARAMETER",
    HTTP_400_BAD_REQUEST,
    "The provided select option parameter {e.select_option_name} is invalid. The "
    "following structure is expected ?select_option=id,limit,offset (e.g. "
    "?select_option=1,2,3).",
)
ERROR_KANBAN_VIEW_FIELD_DOES_NOT_BELONG_TO_SAME_TABLE = (
    "ERROR_KANBAN_VIEW_FIELD_DOES_NOT_BELONG_TO_SAME_TABLE",
    HTTP_400_BAD_REQUEST,
    "The provided single select field does not belong to the same table.",
)
