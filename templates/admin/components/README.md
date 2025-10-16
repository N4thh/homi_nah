# Chart Dropdown Component

## 📋 Tổng quan

Component `chart_dropdown` đã được tái sử dụng thành công cho 2 dropdown trong trang **Quản lý khách hàng**.

## 🎯 Các dropdown đã áp dụng:

### 1. **Filter Dropdown** (Lọc theo vai trò)

- **ID**: `filterSelect`
- **Options**: Tất cả, Owner, Renter
- **Icons**: filter, home, user
- **Logic**: Lọc danh sách theo vai trò người dùng

### 2. **Sort Dropdown** (Sắp xếp)

- **ID**: `sortSelect`
- **Options**: ID, Tên, Ngày tạo (tăng/giảm dần)
- **Icons**: sort, arrow-up, arrow-down, sort-alpha-up/down, calendar
- **Logic**: Sắp xếp danh sách theo tiêu chí

## 🔧 Cách hoạt động:

### **HTML Template:**

```jinja2
<!-- Import component -->
{% from 'admin/components/chart_dropdown.html' import chart_dropdown %}

<!-- Filter Dropdown -->
{% set filter_options = [
  {'value': 'all', 'text': 'Tất cả', 'icon': 'filter'},
  {'value': 'owner', 'text': 'Owner', 'icon': 'home'},
  {'value': 'renter', 'text': 'Renter', 'icon': 'user'}
] %}
{{ chart_dropdown('filterSelect', current_role_filter, filter_options) }}

<!-- Sort Dropdown -->
{% set sort_options = [
  {'value': '', 'text': 'Sắp xếp', 'icon': 'sort'},
  {'value': 'id_asc', 'text': 'ID tăng dần', 'icon': 'arrow-up'},
  // ... more options
] %}
{{ chart_dropdown('sortSelect', request.args.get('sort', ''), sort_options) }}
```

### **JavaScript:**

- Sử dụng **Choices.js** để enhanced dropdown
- Event handling cho filter và sort
- URL navigation tự động

### **CSS:**

- Class `.chart-navbar` cho styling
- Giao diện giống hệt dropdown thống kê
- Responsive và accessible

## ✅ Lợi ích:

1. **Consistency**: Giao diện thống nhất across trang
2. **Maintainability**: Chỉ cần sửa 1 component cho tất cả
3. **Reusability**: Dễ dàng sử dụng ở trang khác
4. **Clean Code**: Code gọn gàng, dễ đọc
5. **Performance**: Không duplicate CSS/JS

## 🚀 Tái sử dụng ở trang khác:

```jinja2
{% from 'admin/components/chart_dropdown.html' import chart_dropdown %}

{{ chart_dropdown('myDropdown', 'selected_value', [
  {'value': 'option1', 'text': 'Option 1', 'icon': 'icon-name'}
]) }}
```
