"""
Pagination Mock API
"""

class PaginationMock:
    """Mock pagination object for manual pagination"""
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if page > 1 else None
        self.next_num = page + 1 if page < self.pages else None

class PaginationAPI:
    """Mock API for pagination operations"""
    
    @staticmethod
    def paginate_users(users, page=1, per_page=10):
        """Paginate users list"""
        total_users = len(users)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_users = users[start_idx:end_idx]
        
        return PaginationMock(paginated_users, page, per_page, total_users)
    
    @staticmethod
    def paginate_items(items, page=1, per_page=10):
        """Generic pagination for any list of items"""
        total_items = len(items)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_items = items[start_idx:end_idx]
        
        return PaginationMock(paginated_items, page, per_page, total_items)

# Global instance
pagination_api = PaginationAPI()
