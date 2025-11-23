# Backend Django Project

This Django project is a refactored version of the AWS Lambda function, organized into clean, maintainable apps.

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/          # Authentication, JWT, user management
│   ├── models.py   # User model
│   ├── views.py    # Login, register, admin functions
│   └── urls.py
├── stock/          # Stock, transactions, production, groups
│   ├── models.py   # Stock, Product, Group, Transaction models
│   ├── views.py    # CRUD operations, production logic
│   ├── services.py # Business logic helpers
│   └── urls.py
└── reports/        # Daily, weekly, monthly reports
    ├── models.py   # Report cache models
    ├── views.py    # Report generation endpoints
    ├── services.py # Report calculation logic
    └── urls.py
```

## Apps Overview

### Users App
- **Purpose**: Authentication, JWT, user management
- **Key Functions**: `register_user`, `login_user`, `admin_view_users`, `admin_update_user`
- **Models**: Extended User model

### Stock App
- **Purpose**: Stock management, transactions, production, groups logic
- **Key Functions**: 
  - Stock CRUD: `create_stock`, `update_stock`, `delete_stock`, `get_all_stocks`
  - Quantity management: `add_stock_quantity`, `subtract_stock_quantity`
  - Production: `create_product`, `push_to_production`, `undo_action`
  - Groups: `create_group`, `list_groups`
- **Models**: Stock, Product, Group, StockTransaction, PushToProduction, UndoAction

### Reports App
- **Purpose**: Daily, weekly, monthly reports and aggregations
- **Key Functions**: 
  - Reports: `get_daily_report`, `get_weekly_report`, `get_monthly_report`
  - Production reports: `get_daily_push_to_production`, etc.
  - Consumption: `get_daily_consumption_summary`
- **Models**: ReportCache for expensive calculations

## Migration Notes

All database operations are currently marked with `# TODO: migrate to Django ORM or RDS model` comments. The original Lambda function used DynamoDB, which needs to be migrated to:

1. **Django ORM with PostgreSQL/MySQL** (recommended for production)
2. **Keep DynamoDB** (update boto3 calls to work with Django)

## Key Changes from Lambda

1. **Request/Response**: Replaced `event`/`context` with Django's `HttpRequest`/`JsonResponse`
2. **Routing**: Lambda's operation-based routing converted to Django URL patterns
3. **Structure**: Monolithic Lambda split into focused Django apps
4. **Error Handling**: Maintained original error handling patterns
5. **Business Logic**: Preserved all calculations and workflows

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```

4. Run development server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Users
- `POST /api/users/register/` - Register user
- `POST /api/users/login/` - User login
- `POST /api/users/admin/view/` - Admin view users
- `POST /api/users/admin/update/` - Admin update user

### Stock
- `POST /api/stock/create/` - Create stock item
- `POST /api/stock/update/` - Update stock item
- `POST /api/stock/delete/` - Delete stock item
- `GET /api/stock/list/` - List all stocks
- `POST /api/stock/add-quantity/` - Add stock quantity
- `POST /api/stock/subtract-quantity/` - Subtract stock quantity
- `POST /api/stock/products/create/` - Create product
- `POST /api/stock/production/push/` - Push to production
- `POST /api/stock/undo/` - Undo action

### Reports
- `POST /api/reports/daily/` - Daily report
- `POST /api/reports/weekly/` - Weekly report
- `POST /api/reports/monthly/` - Monthly report
- `POST /api/reports/production/daily/` - Daily production report
- `POST /api/reports/transactions/` - All transactions

## Next Steps

1. **Database Migration**: Choose between Django ORM or keeping DynamoDB
2. **Authentication**: Implement proper JWT authentication
3. **Testing**: Add comprehensive test suite
4. **Documentation**: Add API documentation (Django REST Framework)
5. **Deployment**: Configure for production deployment