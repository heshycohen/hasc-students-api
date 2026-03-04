"""Custom pagination so student/employee lists can show all records."""
from rest_framework.pagination import PageNumberPagination


class OptionalPageSizePagination(PageNumberPagination):
    page_size = 500
    page_size_query_param = "page_size"
    max_page_size = 10000
