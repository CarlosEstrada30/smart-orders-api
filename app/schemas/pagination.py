from typing import List, TypeVar, Generic
from pydantic import BaseModel, Field
import math

# Type variable for generic pagination
T = TypeVar('T')


class PaginationInfo(BaseModel):
    """Pagination metadata"""
    total: int = Field(..., description="Total number of records")
    count: int = Field(..., description="Number of records in current page")
    page: int = Field(..., description="Current page number (1-based)")
    pages: int = Field(..., description="Total number of pages")
    per_page: int = Field(..., description="Records per page")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(...,
                               description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T] = Field(..., description="List of items in current page")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        skip: int,
        limit: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response from items and pagination parameters"""
        count = len(items)
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = math.ceil(total / limit) if limit > 0 else 1
        has_next = skip + limit < total
        has_previous = skip > 0

        pagination_info = PaginationInfo(
            total=total,
            count=count,
            page=page,
            pages=pages,
            per_page=limit,
            has_next=has_next,
            has_previous=has_previous
        )

        return cls(items=items, pagination=pagination_info)
